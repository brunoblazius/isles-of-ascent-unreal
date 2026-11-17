"""Builds the Isles of Ascent master materials and their instances.

Rerunning rebuilds each master from scratch, so tweak colours on the
instances (MI_*) rather than by hand inside the masters.
Vertex colour layout comes from the Blender export (see the asset guide):
R = wind weight (height), G = leaf flutter (root->tip), B = per-cluster random,
A = canopy occlusion.
"""
import unreal

MASTER_DIR = '/Game/IoA/Materials/Master'
INSTANCE_DIR = '/Game/IoA/Materials/Instances'
GRASS_WIND = '/Engine/Functions/Engine_MaterialFunctions01/WorldPositionOffset/SimpleGrassWind.SimpleGrassWind'

mel = unreal.MaterialEditingLibrary
eal = unreal.EditorAssetLibrary


def _new_material(name):
    path = f'{MASTER_DIR}/{name}'
    if eal.does_asset_exist(path):
        mat = unreal.load_asset(path)
        mel.delete_all_material_expressions(mat)
        return mat
    return unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        name, MASTER_DIR, unreal.Material, unreal.MaterialFactoryNew())


def _expr(mat, cls, x, y):
    return mel.create_material_expression(mat, cls, x, y)


def _scalar(mat, name, value, x, y):
    e = _expr(mat, unreal.MaterialExpressionScalarParameter, x, y)
    e.set_editor_property('parameter_name', name)
    e.set_editor_property('default_value', value)
    return e


def _color(mat, name, rgb, x, y):
    e = _expr(mat, unreal.MaterialExpressionVectorParameter, x, y)
    e.set_editor_property('parameter_name', name)
    e.set_editor_property('default_value', unreal.LinearColor(*rgb, 1.0))
    return e


def _lerp(mat, a, b, alpha, x, y, a_out='', b_out='', alpha_out=''):
    e = _expr(mat, unreal.MaterialExpressionLinearInterpolate, x, y)
    mel.connect_material_expressions(a, a_out, e, 'A')
    mel.connect_material_expressions(b, b_out, e, 'B')
    mel.connect_material_expressions(alpha, alpha_out, e, 'Alpha')
    return e


def _multiply(mat, a, b, x, y, a_out='', b_out=''):
    e = _expr(mat, unreal.MaterialExpressionMultiply, x, y)
    mel.connect_material_expressions(a, a_out, e, 'A')
    mel.connect_material_expressions(b, b_out, e, 'B')
    return e


def _wind(mat, weight, weight_out, intensity, speed, x, y):
    fn = _expr(mat, unreal.MaterialExpressionMaterialFunctionCall, x, y)
    fn.set_editor_property('material_function', unreal.load_asset(GRASS_WIND))
    mel.connect_material_expressions(weight, weight_out, fn, 'WindWeight')
    mel.connect_material_expressions(_scalar(mat, 'WindIntensity', intensity, x - 300, y + 120), '', fn, 'WindIntensity')
    mel.connect_material_expressions(_scalar(mat, 'WindSpeed', speed, x - 300, y + 200), '', fn, 'WindSpeed')
    mel.connect_material_property(fn, '', unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)


def _finish(mat):
    mel.layout_material_expressions(mat)
    mel.recompile_material(mat)
    eal.save_loaded_asset(mat)
    return mat


def build_foliage():
    """Two-sided foliage leaves: dark interior -> light top, per-cluster hue shift, wind."""
    mat = _new_material('M_Foliage')
    mat.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)
    mat.set_editor_property('two_sided', True)
    vc = _expr(mat, unreal.MaterialExpressionVertexColor, -1400, 0)
    dark = _color(mat, 'ColorShadow', (0.020, 0.075, 0.012), -1100, -300)
    light = _color(mat, 'ColorLight', (0.180, 0.420, 0.045), -1100, -150)
    warm = _color(mat, 'ColorVariation', (0.300, 0.420, 0.040), -1100, 0)
    # Occlusion (A) sharpened so cluster interiors read dark like the reference.
    occ = _expr(mat, unreal.MaterialExpressionPower, -850, 150)
    mel.connect_material_expressions(vc, 'A', occ, 'Base')
    mel.connect_material_expressions(_scalar(mat, 'OcclusionContrast', 1.6, -1100, 200), '', occ, 'Exp')
    base = _lerp(mat, dark, light, occ, -600, -200)
    varied = _lerp(mat, base, warm, _multiply(mat, vc, _scalar(mat, 'VariationAmount', 0.35, -1100, 320), -850, 300, 'B'), -350, -100)
    mel.connect_material_property(varied, '', unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(_color(mat, 'SubsurfaceColor', (0.25, 0.45, 0.04), -350, 150), '', unreal.MaterialProperty.MP_SUBSURFACE_COLOR)
    mel.connect_material_property(_scalar(mat, 'Roughness', 0.75, -350, 300), '', unreal.MaterialProperty.MP_ROUGHNESS)
    _wind(mat, vc, 'R', 0.25, 0.6, -350, 450)
    return _finish(mat)


def build_bark():
    """Reddish-brown bark, darker at the root."""
    mat = _new_material('M_Bark')
    vc = _expr(mat, unreal.MaterialExpressionVertexColor, -900, 0)
    root = _color(mat, 'ColorRoot', (0.060, 0.025, 0.012), -600, -150)
    top = _color(mat, 'ColorTop', (0.220, 0.080, 0.035), -600, 0)
    mel.connect_material_property(_lerp(mat, root, top, vc, -300, -50, alpha_out='R'), '', unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(_scalar(mat, 'Roughness', 0.85, -300, 150), '', unreal.MaterialProperty.MP_ROUGHNESS)
    _wind(mat, vc, 'R', 0.08, 0.6, -300, 300)
    return _finish(mat)


def build_grass():
    """Grass blades: dark root -> yellow-green tip, per-instance tint, wind."""
    mat = _new_material('M_Grass')
    mat.set_editor_property('two_sided', True)
    vc = _expr(mat, unreal.MaterialExpressionVertexColor, -1300, 0)
    root = _color(mat, 'ColorRoot', (0.030, 0.110, 0.010), -1000, -300)
    tip = _color(mat, 'ColorTip', (0.330, 0.560, 0.060), -1000, -150)
    tip_alt = _color(mat, 'ColorTipVariation', (0.420, 0.520, 0.070), -1000, 0)
    rnd = _expr(mat, unreal.MaterialExpressionPerInstanceRandom, -1000, 150)
    tips = _lerp(mat, tip, tip_alt, rnd, -700, -100)
    grad = _expr(mat, unreal.MaterialExpressionPower, -700, 100)
    mel.connect_material_expressions(vc, 'R', grad, 'Base')
    mel.connect_material_expressions(_scalar(mat, 'GradientPower', 0.7, -1000, 300), '', grad, 'Exp')
    mel.connect_material_property(_lerp(mat, root, tips, grad, -400, -150), '', unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(_scalar(mat, 'Roughness', 0.8, -400, 100), '', unreal.MaterialProperty.MP_ROUGHNESS)
    _wind(mat, vc, 'R', 0.35, 0.8, -400, 300)
    return _finish(mat)


def build_landscape():
    """Ground tinted like the grass root so blades blend into a continuous carpet.

    Layered painting (grass/dirt/sand/rock) and the runtime virtual texture come
    in Phase 3 proper; this is the single-layer base.
    """
    mat = _new_material('M_Landscape')
    noise = _expr(mat, unreal.MaterialExpressionNoise, -900, 100)
    noise.set_editor_property('scale', 0.0015)
    noise.set_editor_property('levels', 4)
    noise.set_editor_property('output_min', 0.0)
    noise.set_editor_property('output_max', 1.0)
    a = _color(mat, 'ColorGround', (0.040, 0.120, 0.012), -900, -250)
    b = _color(mat, 'ColorGroundVariation', (0.090, 0.150, 0.020), -900, -100)
    mel.connect_material_property(_lerp(mat, a, b, noise, -500, -100), '', unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(_scalar(mat, 'Roughness', 0.9, -500, 150), '', unreal.MaterialProperty.MP_ROUGHNESS)
    return _finish(mat)


def make_instance(name, parent):
    path = f'{INSTANCE_DIR}/{name}'
    if eal.does_asset_exist(path):
        mi = unreal.load_asset(path)
    else:
        mi = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            name, INSTANCE_DIR, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mel.set_material_instance_parent(mi, parent)
    eal.save_loaded_asset(mi)
    return mi
