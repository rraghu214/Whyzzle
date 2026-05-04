"""
Whyzzle Blender Template — Planetary Orbital Motion
Renders 10 seconds of animated planetary orbits around a glowing sun.

Receives parameters via:  blender --background --python orbit.py -- --params <json_file>
"""
import bpy, json, math, sys

# ─── Load parameters ─────────────────────────────────────────────────────────
params = {}
argv = sys.argv
if "--" in argv:
    extra = argv[argv.index("--") + 1:]
    if "--params" in extra:
        idx = extra.index("--params") + 1
        if idx < len(extra):
            with open(extra[idx], encoding="utf-8") as f:
                params = json.load(f)

import os
frames_dir = params.get("frames_dir", os.path.join(os.path.dirname(__file__), "frames"))
os.makedirs(frames_dir, exist_ok=True)

# ─── Scene ───────────────────────────────────────────────────────────────────
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end   = 240  # 10 s @ 24 fps
scene.render.fps  = 24

# Blender 5.x: render to PNG frames; ffmpeg combines them server-side
scene.render.image_settings.file_format = "PNG"
scene.render.filepath       = os.path.join(frames_dir, "frame_####")
scene.render.resolution_x   = 640
scene.render.resolution_y   = 360
# Engine name changed back to BLENDER_EEVEE in Blender 5.x
try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError:
    scene.render.engine = "BLENDER_EEVEE"

# Bloom removed in Blender 4.2+ — skip gracefully
try:
    scene.eevee.use_bloom = True
    scene.eevee.bloom_intensity = 0.3
except AttributeError:
    pass

# World — deep space
world = bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.008, 0.008, 0.04, 1)

# ─── Materials helper ────────────────────────────────────────────────────────
def emission_mat(name, color, strength=3.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes.clear()
    em = m.node_tree.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value   = (*color, 1)
    em.inputs["Strength"].default_value = strength
    out = m.node_tree.nodes.new("ShaderNodeOutputMaterial")
    m.node_tree.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return m

def diffuse_mat(name, color, roughness=0.7):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value  = (*color, 1)
    bsdf.inputs["Roughness"].default_value   = roughness
    return m

# ─── Sun ─────────────────────────────────────────────────────────────────────
bpy.ops.mesh.primitive_uv_sphere_add(radius=1.2, location=(0, 0, 0))
sun = bpy.context.active_object
sun.name = "Sun"
sun.data.materials.append(emission_mat("SunMat", (1.0, 0.85, 0.3), strength=8))

bpy.ops.object.light_add(type="POINT", location=(0, 0, 0))
sun_light = bpy.context.active_object
sun_light.data.energy = 1200
sun_light.data.color  = (1, 0.9, 0.6)
sun_light.data.shadow_soft_size = 1.5

# ─── Planets ─────────────────────────────────────────────────────────────────
PLANETS = [
    # name,        radius, orbit_r, color_rgb,           speed_mult
    ("Mercury",    0.13,   2.2,     (0.65, 0.55, 0.45),  3.8),
    ("Venus",      0.20,   3.3,     (0.9,  0.75, 0.4),   2.4),
    ("Earth",      0.22,   4.5,     (0.2,  0.5,  0.95),  1.5),
    ("Mars",       0.16,   5.7,     (0.85, 0.3,  0.1),   0.9),
]

def add_planet(name, radius, orbit_r, color, speed_mult):
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=radius,
        location=(orbit_r, 0, 0),
        segments=24, ring_count=16,
    )
    obj = bpy.context.active_object
    obj.name = name
    obj.data.materials.append(diffuse_mat(f"{name}Mat", color))

    # Animate one full orbit over (240 / speed_mult) frames, repeat
    total_frames = 241
    for frame in range(1, total_frames, 3):
        t     = (frame - 1) / 240.0
        angle = math.tau * t * speed_mult
        obj.location = (
            math.cos(angle) * orbit_r,
            math.sin(angle) * orbit_r,
            math.sin(angle * 0.15) * 0.3,
        )
        obj.keyframe_insert("location", frame=frame)

    # Linear interpolation (constant speed)
    for fc in obj.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"

    return obj

for args in PLANETS:
    add_planet(*args)

# Draw orbit rings (thin tori)
for _, _, orbit_r, _, _ in PLANETS:
    bpy.ops.mesh.primitive_torus_add(
        major_radius=orbit_r, minor_radius=0.01,
        major_segments=64, minor_segments=4,
    )
    ring = bpy.context.active_object
    m = bpy.data.materials.new("RingMat")
    m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.4, 0.4, 0.6, 1)
    m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value  = 1.0
    m.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value      = 0.3
    m.blend_method = "BLEND"
    ring.data.materials.append(m)

# ─── Camera — slow arc ───────────────────────────────────────────────────────
bpy.ops.object.camera_add(location=(0, -13, 7))
cam = bpy.context.active_object
cam.name = "Camera"
cam.data.lens = 35
cam.rotation_euler = (math.radians(58), 0, 0)
scene.camera = cam

for frame in range(1, 242, 4):
    t     = (frame - 1) / 240.0
    angle = math.radians(t * 25)
    cam.location = (
        -13 * math.sin(angle),
        -13 * math.cos(angle),
        7.0,
    )
    cam.keyframe_insert("location", frame=frame)

# ─── Render ───────────────────────────────────────────────────────────────────
bpy.ops.render.render(animation=True)
