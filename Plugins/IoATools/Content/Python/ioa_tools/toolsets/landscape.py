import struct
import zlib

import unreal

import toolset_registry


@unreal.uclass()
class LandscapeTools(unreal.ToolsetDefinition):
    """Reads and writes Landscape heightmaps and creates levels to hold them.
    Heightmaps use Unreal's .r16 format: little-endian uint16 per vertex, row-major from -X/-Y,
    where 32768 is the landscape actor's Z and each unit is scale.z / 128 cm."""

    @toolset_registry.tool_call
    @staticmethod
    def create_level(level_path: str, open_world: bool = False) -> None:
        """Creates a new level, saves it and opens it in the editor.

        Args:
            level_path: Content path of the new level, e.g. '/Game/Maps/L_Test'.
            open_world: Creates a World Partition level when True.
        """
        if unreal.EditorAssetLibrary.does_asset_exist(level_path):
            raise ValueError(f'{level_path} already exists.')
        subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        if not subsystem.new_level(level_path, open_world):
            raise RuntimeError(f'Could not create {level_path}.')

    @toolset_registry.tool_call
    @staticmethod
    def get_heightmap_resolution(landscape: unreal.Landscape) -> unreal.IntPoint:
        """Returns the number of heightmap vertices along X and Y."""
        return LandscapeTools._resolution(landscape)

    @toolset_registry.tool_call
    @staticmethod
    def import_heightmap_r16(landscape: unreal.Landscape, file_path: str) -> None:
        """Overwrites the landscape's heights with an .r16 file of matching resolution.

        Args:
            landscape: The landscape to modify.
            file_path: Absolute path of the .r16 file.
        """
        res = LandscapeTools._resolution(landscape)
        with open(file_path, 'rb') as f:
            data = f.read()
        expected = res.x * res.y * 2
        if len(data) != expected:
            raise ValueError(
                f'{file_path} has {len(data)} bytes; a {res.x}x{res.y} heightmap needs {expected}.')

        heights = struct.unpack(f'<{res.x * res.y}H', data)
        world = LandscapeTools._world()
        texture = unreal.RenderingLibrary.import_buffer_as_texture2d(
            world, LandscapeTools._encode_png(heights, res.x, res.y))
        if texture is None:
            raise RuntimeError('Could not create the heightmap texture.')
        texture.set_editor_property('srgb', False)
        texture.set_editor_property('filter', unreal.TextureFilter.TF_NEAREST)

        target = unreal.RenderingLibrary.create_render_target2d(
            world, res.x, res.y, unreal.TextureRenderTargetFormat.RTF_RGBA32F)
        canvas, size, context = unreal.RenderingLibrary.begin_draw_canvas_to_render_target(world, target)
        canvas.draw_texture(
            texture, unreal.Vector2D(0, 0), unreal.Vector2D(res.x, res.y),
            unreal.Vector2D(0, 0), unreal.Vector2D(1, 1),
            blend_mode=unreal.BlendMode.BLEND_OPAQUE)
        unreal.RenderingLibrary.end_draw_canvas_to_render_target(world, context)

        if not landscape.landscape_import_heightmap_from_render_target(target, True):
            raise RuntimeError('The landscape rejected the heightmap.')

    @toolset_registry.tool_call
    @staticmethod
    def export_heightmap_r16(landscape: unreal.Landscape, file_path: str) -> None:
        """Writes the landscape's current heights to an .r16 file.

        Args:
            landscape: The landscape to read.
            file_path: Absolute path of the .r16 file to write. Overwritten if it exists.
        """
        res = LandscapeTools._resolution(landscape)
        world = LandscapeTools._world()
        target = unreal.RenderingLibrary.create_render_target2d(
            world, res.x, res.y, unreal.TextureRenderTargetFormat.RTF_RGBA32F)
        if not landscape.landscape_export_heightmap_to_render_target(target, True):
            raise RuntimeError('Could not export the heightmap.')
        pixels = unreal.RenderingLibrary.read_render_target_raw(world, target)
        heights = [
            (round(p.r * 255) << 8) | round(p.g * 255) for p in pixels]
        with open(file_path, 'wb') as f:
            f.write(struct.pack(f'<{len(heights)}H', *heights))

    @staticmethod
    def _world() -> unreal.World:
        return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()

    @staticmethod
    def _resolution(landscape: unreal.Landscape) -> unreal.IntPoint:
        _, extent = landscape.get_actor_bounds(False)
        scale = landscape.get_actor_scale3d()
        return unreal.IntPoint(
            round(2 * extent.x / scale.x) + 1, round(2 * extent.y / scale.y) + 1)

    @staticmethod
    def _encode_png(heights, width: int, height: int) -> bytes:
        """RGBA8 PNG with the high byte in R and the low byte in G."""
        rows = bytearray()
        for y in range(height):
            rows.append(0)
            for h in heights[y * width:(y + 1) * width]:
                rows += bytes((h >> 8, h & 0xFF, 0, 255))

        def chunk(tag, body):
            return (struct.pack('>I', len(body)) + tag + body
                    + struct.pack('>I', zlib.crc32(tag + body) & 0xFFFFFFFF))

        header = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
        return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', header)
                + chunk(b'IDAT', zlib.compress(bytes(rows), 6)) + chunk(b'IEND', b''))
