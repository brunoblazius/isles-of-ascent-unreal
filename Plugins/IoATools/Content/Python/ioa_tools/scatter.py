"""Scatters the StyleHex stylized forest kit over Island 01.

Composition follows the pack's World_Demo: dense groves of broadleaf and birch
with bushes underneath, rock clusters, flower patches in the open meadow.
Rerunning replaces every instance (same seed, same result).
Coordinates are meters with sea level at 0, as in island_gen.
"""
import math
import random

import unreal

from editor_toolset.toolsets.actor import ActorTools
from ioa_tools import island_gen as ig

KIT = '/Game/StyleHex_Studio/Free_Packs/FREE_Stylized_Forest_Sample/Meshes/'
FOLDER = 'Foliage'

FOREST = (-20.0, 190.0, 150.0)   # main grove around MK_Floresta (x, y, radius)
QUARRY = (190.0, -170.0, 45.0)   # boulder field around MK_Pedreira
KEEP_CLEAR = [(-230.0, 20.0, 25.0), (-225.0, -158.0, 22.0), (-215.0, -151.0, 15.0)]  # spawn, cove, boat

MIN_HEIGHT = 1.4   # m: stay off the sand
TREE_SLOPE = 0.45
ROCK_SLOPE = 0.65


def slope_at(x, y):
    dx = (ig.height_at(x + 1, y) - ig.height_at(x - 1, y)) / 2
    dy = (ig.height_at(x, y + 1) - ig.height_at(x, y - 1)) / 2
    return math.hypot(dx, dy)


def groves(x, y):
    """0..1 woodland density: the main forest plus smaller groves elsewhere."""
    fx, fy, fr = FOREST
    main = math.exp(-((x - fx) ** 2 + (y - fy) ** 2) / (fr * fr))
    n = (math.sin(x * 0.031 + 1.7) * math.cos(y * 0.027 - 0.4)
         + 0.5 * math.sin(x * 0.067 - y * 0.051 + 2.3))
    return max(main, min(1.0, max(0.0, (n - 0.3) * 1.2)))


def usable(x, y, max_slope):
    if any(math.hypot(x - cx, y - cy) < r for cx, cy, r in KEEP_CLEAR):
        return False
    return ig.height_at(x, y) >= MIN_HEIGHT and slope_at(x, y) <= max_slope


def _holder(name):
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for a in eas.get_all_level_actors():
        if a.get_actor_label() == name:
            a.destroy_actor()
    holder = eas.spawn_actor_from_class(unreal.Actor, unreal.Vector(0, 0, 0))
    holder.set_actor_label(name)
    holder.set_folder_path(FOLDER)
    return holder


def _hism(holder, mesh, transforms, collision, cull_end=0.0, shadows=True):
    comp = ActorTools.add_component(
        holder, unreal.HierarchicalInstancedStaticMeshComponent.static_class(), 'HISM_' + mesh.split('/')[-1])
    comp.set_static_mesh(unreal.load_asset(KIT + mesh))
    comp.set_collision_enabled(
        unreal.CollisionEnabled.QUERY_AND_PHYSICS if collision else unreal.CollisionEnabled.NO_COLLISION)
    comp.set_editor_property('cast_shadow', shadows)
    if cull_end:
        comp.set_editor_property('instance_start_cull_distance', int(cull_end * 0.7))
        comp.set_editor_property('instance_end_cull_distance', int(cull_end))
    comp.add_instances(transforms, False, True)
    return comp.get_instance_count()


def _xf(rng, x, y, scale, sink=0.1, tilt=0.0):
    z = ig.height_at(x, y) - sink
    return unreal.Transform(
        unreal.Vector(x * 100, y * 100, z * 100),
        unreal.Rotator(roll=rng.uniform(-tilt, tilt), pitch=rng.uniform(-tilt, tilt), yaw=rng.uniform(0, 360)),
        unreal.Vector(scale, scale, scale))


def _poisson(rng, count, spacing, accept):
    """Dart throwing over the island; accept(x, y) -> bool."""
    pts = []
    tries = count * 40
    while len(pts) < count and tries:
        tries -= 1
        x, y = rng.uniform(-330, 330), rng.uniform(-330, 330)
        if accept(x, y) and all((x - px) ** 2 + (y - py) ** 2 >= spacing * spacing for px, py in pts):
            pts.append((x, y))
    return pts


def scatter(seed=21):
    rng = random.Random(seed)
    report = {}

    # Trees: dense in groves, a few lone trees in the meadow.
    trees = _poisson(rng, 650, 5.5, lambda x, y: usable(x, y, TREE_SLOPE)
                     and rng.random() < 0.04 + 0.96 * groves(x, y))
    kinds = {'Trees/SM_Tree_Broadleaf_1': [], 'Trees/SM_Tree_Broadleaf_2': [],
             'Trees/SM_Tree_Birch_1': [], 'Trees/SM_Tree_Birch_2': []}
    for x, y in trees:
        birch = groves(x, y) > 0.5 and rng.random() < 0.5
        name = rng.choice(['Trees/SM_Tree_Birch_1', 'Trees/SM_Tree_Birch_2'] if birch
                          else ['Trees/SM_Tree_Broadleaf_1', 'Trees/SM_Tree_Broadleaf_2'])
        kinds[name].append(_xf(rng, x, y, rng.uniform(0.8, 1.15), sink=0.2))
    holder = _holder('Foliage_Trees')
    for name, xs in kinds.items():
        report[name] = _hism(holder, name, xs, collision=True)

    # Bushes: under and around the trees, plus some along grove edges.
    bushes = {'Foliage/SM_Fol_Bush_1': [], 'Foliage/SM_Fol_Bush_2': []}
    for x, y in trees:
        for _ in range(rng.randint(1, 4)):
            a, d = rng.uniform(0, math.tau), rng.uniform(2.5, 8)
            bx, by = x + math.cos(a) * d, y + math.sin(a) * d
            if usable(bx, by, TREE_SLOPE):
                bushes[rng.choice(list(bushes))].append(_xf(rng, bx, by, rng.uniform(0.7, 1.2), sink=0.15))
    holder = _holder('Foliage_Bushes')
    for name, xs in bushes.items():
        report[name] = _hism(holder, name, xs, collision=False)

    # Rocks: boulder field at the quarry, small clusters scattered in the groves.
    rocks = {'Stones/SM_Stone_1': [], 'Stones/SM_Stone_2': [], 'Stones/SM_Stone_3': [], 'Stones/SM_Stone_Boulder_1': []}
    qx, qy, qr = QUARRY
    for _ in range(110):
        a, d = rng.uniform(0, math.tau), qr * math.sqrt(rng.random())
        x, y = qx + math.cos(a) * d, qy + math.sin(a) * d
        if usable(x, y, ROCK_SLOPE):
            name = rng.choice(['Stones/SM_Stone_Boulder_1', 'Stones/SM_Stone_Boulder_1', 'Stones/SM_Stone_3', 'Stones/SM_Stone_2'])
            rocks[name].append(_xf(rng, x, y, rng.uniform(1.2, 2.6), sink=0.6, tilt=8))
    # Big rock outcrops all over the island: a boulder or two with rubble around them.
    outcrops = _poisson(rng, 45, 35, lambda x, y: usable(x, y, ROCK_SLOPE))
    for cx, cy in outcrops:
        for _ in range(rng.randint(1, 2)):
            x, y = cx + rng.uniform(-3, 3), cy + rng.uniform(-3, 3)
            rocks[rng.choice(['Stones/SM_Stone_Boulder_1', 'Stones/SM_Stone_3'])].append(
                _xf(rng, x, y, rng.uniform(1.0, 2.2), sink=0.6, tilt=6))
        for _ in range(rng.randint(2, 5)):
            a, d = rng.uniform(0, math.tau), rng.uniform(3, 9)
            x, y = cx + math.cos(a) * d, cy + math.sin(a) * d
            if usable(x, y, ROCK_SLOPE):
                rocks[rng.choice(['Stones/SM_Stone_1', 'Stones/SM_Stone_2'])].append(
                    _xf(rng, x, y, rng.uniform(0.6, 1.4), sink=0.3, tilt=10))
    centers = _poisson(rng, 35, 25, lambda x, y: usable(x, y, ROCK_SLOPE))
    for cx, cy in centers:
        for _ in range(rng.randint(2, 5)):
            x, y = cx + rng.uniform(-4, 4), cy + rng.uniform(-4, 4)
            if usable(x, y, ROCK_SLOPE):
                rocks[rng.choice(['Stones/SM_Stone_1', 'Stones/SM_Stone_2', 'Stones/SM_Stone_2'])].append(
                    _xf(rng, x, y, rng.uniform(0.5, 1.1), sink=0.25, tilt=10))
    holder = _holder('Foliage_Rocks')
    for name, xs in rocks.items():
        report[name] = _hism(holder, name, xs, collision=True)

    # Flowers: dense patches in the open meadow, sparse ones at grove edges.
    flowers = {f'Foliage/SM_Fol_Flower_Clump_{i}': [] for i in (1, 2, 3)}
    patches = _poisson(rng, 60, 18, lambda x, y: usable(x, y, ROCK_SLOPE) and groves(x, y) < 0.6)
    for px, py in patches:
        name = rng.choice(list(flowers))
        radius = rng.uniform(3, 8)
        for _ in range(rng.randint(25, 60)):
            a, d = rng.uniform(0, math.tau), radius * math.sqrt(rng.random())
            x, y = px + math.cos(a) * d, py + math.sin(a) * d
            if usable(x, y, ROCK_SLOPE):
                flowers[name].append(_xf(rng, x, y, rng.uniform(0.8, 1.3), sink=0.02))
    holder = _holder('Foliage_Flowers')
    for name, xs in flowers.items():
        report[name] = _hism(holder, name, xs, collision=False, cull_end=7000, shadows=False)

    # Tall grass clumps: everywhere on grass, thicker near groves.
    grass = {f'Foliage/SM_Fol_Grass_Clump_{i}': [] for i in range(1, 6)}
    for _ in range(9000):
        x, y = rng.uniform(-330, 330), rng.uniform(-330, 330)
        if rng.random() < 0.35 + 0.65 * groves(x, y) and usable(x, y, ROCK_SLOPE):
            grass[rng.choice(list(grass))].append(_xf(rng, x, y, rng.uniform(0.8, 1.3), sink=0.05))
    holder = _holder('Foliage_Grass')
    for name, xs in grass.items():
        report[name] = _hism(holder, name, xs, collision=False, cull_end=5000, shadows=False)

    return report
