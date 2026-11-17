"""Procedural blockout heightmap for Island 01.

Sea level is world Z = 0 with the landscape actor at Z = 0 and scale.z = 100,
so one heightmap unit is 100 / 128 cm. Coordinates below are in meters from the
landscape center: +X is the cliff side, -X the beach side.
"""
import math
import struct

SEA_LEVEL = 32768
UNITS_PER_METER = 128.0  # 100 cm / (100 / 128 cm)

COAST_RADIUS = 340.0       # mean distance from center to shoreline
COVE_ANGLE = math.radians(215)
COVE_DEPTH = 95.0          # how far the cove cuts into the coast
SEA_FLOOR = -14.0

HILLS = [  # (x, y, height, radius) in meters
    (0, 0, 8, 120),
    (-120, 150, 6, 80),
    (150, -100, 10, 90),
]


def coast_radius(theta):
    r = (COAST_RADIUS + 25 * math.sin(3 * theta + 1) + 15 * math.sin(5 * theta + 2)
         + 8 * math.sin(9 * theta))
    delta = math.atan2(math.sin(theta - COVE_ANGLE), math.cos(theta - COVE_ANGLE))
    return r - COVE_DEPTH * math.exp(-(delta / 0.12) ** 2)


def smoothstep(edge0, edge1, v):
    t = min(1.0, max(0.0, (v - edge0) / (edge1 - edge0)))
    return t * t * (3 - 2 * t)


def height_at(x, y):
    r = math.hypot(x, y)
    theta = math.atan2(y, x)
    c = math.cos(theta)
    cliff = max(0.0, c) ** 3
    beach = max(0.0, -c) ** 2
    d = r / coast_radius(theta)

    if d >= 1.0:
        return max(SEA_FLOOR, -(d - 1.0) * 60 * (1 + 3 * cliff))

    shore_width = 0.30 + 0.25 * beach - 0.27 * cliff
    t = min(1.0, (1.0 - d) / shore_width)
    s = t * t * (3 - 2 * t)
    # Plateau rises toward the cliff (+X) and drops toward the beach (-X).
    top = 28 + 45 * smoothstep(60, 240, x) - 10 * smoothstep(60, 240, -x)
    hills = sum(h * math.exp(-((x - hx) ** 2 + (y - hy) ** 2) / (hr * hr))
                for hx, hy, h, hr in HILLS)
    return s * (top + hills)


SAND_TOP = 0.3          # m: full sand at or below this height
SAND_FADE = 0.7         # m: sand fades to grass over this band
ROCK_SLOPE = 0.70       # rise/run where rock starts (~35 deg)
ROCK_FADE = 0.20


def write_layer_weights(path_prefix, width, height, origin_x, origin_y):
    """Writes <prefix>_Grass/_Sand/_Rock.r8 weight files (bytes summing to ~255 per vertex)."""
    h = [[height_at(origin_x + i, origin_y + j) for i in range(width)] for j in range(height)]
    out = {'Grass': bytearray(), 'Sand': bytearray(), 'Rock': bytearray()}
    for j in range(height):
        row = h[j]
        up = h[max(0, j - 1)]
        dn = h[min(height - 1, j + 1)]
        for i in range(width):
            dx = (row[min(width - 1, i + 1)] - row[max(0, i - 1)]) / 2.0
            dy = (dn[i] - up[i]) / 2.0
            slope = (dx * dx + dy * dy) ** 0.5
            rock = smoothstep(ROCK_SLOPE, ROCK_SLOPE + ROCK_FADE, slope)
            sand = (1.0 - smoothstep(SAND_TOP, SAND_TOP + SAND_FADE, row[i])) * (1.0 - rock)
            grass = 1.0 - rock - sand
            r, s = round(rock * 255), round(sand * 255)
            out['Rock'].append(r)
            out['Sand'].append(s)
            out['Grass'].append(max(0, 255 - r - s))
    paths = {}
    for name, data in out.items():
        paths[name] = f'{path_prefix}_{name}.r8'
        with open(paths[name], 'wb') as f:
            f.write(bytes(data))
    return paths


def write_r16(file_path, width, height, origin_x, origin_y):
    """Writes the island as .r16; origin is the world position (m) of vertex 0."""
    values = []
    for j in range(height):
        y = origin_y + j
        for i in range(width):
            h = SEA_LEVEL + height_at(origin_x + i, y) * UNITS_PER_METER
            values.append(max(0, min(65535, round(h))))
    with open(file_path, 'wb') as f:
        f.write(struct.pack(f'<{len(values)}H', *values))
