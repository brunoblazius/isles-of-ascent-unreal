"""Morning look for the island levels (target: Lightyear Frontier reference).

Clean, saturated foreground; bluish haze only at distance; warm sun with soft
shadows. Rerun to reset a level's sky and post process to these values.
"""
import unreal


def _first(world, cls):
    found = unreal.GameplayStatics.get_all_actors_of_class(world, cls)
    return found[0] if found else None


def apply_morning(world=None):
    world = world or unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()

    sun = _first(world, unreal.DirectionalLight)
    sun.set_actor_rotation(unreal.Rotator(roll=0.0, pitch=-38.0, yaw=55.0), False)
    light = sun.get_component_by_class(unreal.DirectionalLightComponent)
    light.set_intensity(7.0)
    light.set_editor_property('temperature', 6000.0)
    light.set_editor_property('light_source_angle', 2.0)

    sky = _first(world, unreal.SkyLight).get_component_by_class(unreal.SkyLightComponent)
    sky.set_intensity(1.2)

    # Height fog only for distance depth; the near field must stay crisp.
    fog = _first(world, unreal.ExponentialHeightFog).get_component_by_class(unreal.ExponentialHeightFogComponent)
    fog.set_editor_property('fog_density', 0.006)
    fog.set_editor_property('fog_height_falloff', 0.15)
    fog.set_editor_property('start_distance', 4000.0)
    fog.set_editor_property('enable_volumetric_fog', True)
    fog.set_editor_property('volumetric_fog_extinction_scale', 0.5)

    atmosphere = _first(world, unreal.SkyAtmosphere).get_component_by_class(unreal.SkyAtmosphereComponent)
    atmosphere.set_editor_property('aerial_pespective_view_distance_scale', 2.0)

    volume = _first(world, unreal.PostProcessVolume)
    if volume is None:
        volume = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).spawn_actor_from_class(
            unreal.PostProcessVolume, unreal.Vector(0, 0, 0))
        volume.set_actor_label('PPV_Global')
        volume.set_folder_path('Lighting')
    volume.set_editor_property('unbound', True)
    s = volume.settings
    values = {
        'auto_exposure_bias': -0.3,
        'color_saturation': unreal.Vector4(1.0, 1.0, 1.0, 1.18),
        'color_contrast': unreal.Vector4(1.0, 1.0, 1.0, 1.08),
        'color_gain_highlights': unreal.Vector4(1.03, 1.0, 0.95, 1.0),
        'bloom_intensity': 0.35,
        'vignette_intensity': 0.25,
        'ambient_occlusion_intensity': 0.6,
    }
    for name, value in values.items():
        s.set_editor_property('override_' + name, True)
        s.set_editor_property(name, value)
    volume.set_editor_property('settings', s)
    return volume


def apply_forest_pack(world=None):
    """Lighting and grade of the StyleHex forest kit's World_Demo: warm sun, deeper greens.

    Keeps the morning sun direction; takes the demo's sun colour and strength, sky,
    fog and post process so the kit's foliage reads as authored.
    """
    world = world or unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    volume = apply_morning(world)

    light = _first(world, unreal.DirectionalLight).get_component_by_class(unreal.DirectionalLightComponent)
    # The demo pairs a 3000 K tint with an old AtmosphericFog; under our SkyAtmosphere
    # that turns everything orange, so keep only a slight warm tint.
    light.set_intensity(5.0)
    light.set_editor_property('use_temperature', True)
    light.set_editor_property('temperature', 5600.0)
    light.set_light_color(unreal.LinearColor(1.0, 0.96, 0.86, 1.0))

    _first(world, unreal.SkyLight).get_component_by_class(unreal.SkyLightComponent).set_intensity(1.0)
    fog = _first(world, unreal.ExponentialHeightFog).get_component_by_class(unreal.ExponentialHeightFogComponent)
    fog.set_editor_property('fog_density', 0.015)
    fog.set_editor_property('fog_height_falloff', 0.2)

    s = volume.settings
    values = {
        # The listing shots are brighter and a touch more saturated than the demo map.
        'auto_exposure_bias': 1.1,
        'auto_exposure_min_brightness': 1.0,
        'auto_exposure_max_brightness': 2.0,
        'color_saturation': unreal.Vector4(1.0, 1.0, 1.0, 1.08),
        'color_contrast': unreal.Vector4(1.1, 1.1, 1.1, 1.0),
        'color_gamma': unreal.Vector4(0.95, 0.95, 0.95, 1.0),
        'color_gain_highlights': unreal.Vector4(1.0, 1.0, 1.0, 1.0),
        'bloom_intensity': 0.5,
        'vignette_intensity': 0.6,
        'ambient_occlusion_intensity': 0.25,
    }
    for name, value in values.items():
        s.set_editor_property('override_' + name, True)
        s.set_editor_property(name, value)
    volume.set_editor_property('settings', s)
    return volume
