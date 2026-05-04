"""
Whyzzle Blender Template — Cross-Section / Layered Structure
Shows Earth's interior layers (or any layered structure) as nested
translucent spheres that slowly rotate to reveal their depths.

Usage:  blender --background --python cross_section.py -- --params <json>
"""
import bpy, json, math, sys

params = {}
argv = sys.argv
if "--" in argv:
    extra = argv[argv.index("--") + 1:]
    if "--params" in extra:
        idx = extra.index("--params") + 1
        if idx < len(extra):
            with open(extra[idx], encoding="utf-8") as f:
                params = json.load(f)

output_path  = params.get("output_path", "//output/cross_section.mp4")
topic        = params.get("topic", "").lower()

# Decide theme: volcano vs earth vs generic atom/cell
is_volcano   = any(w in topic for w in ("volcano", "eruption", "lava"))
is_atom      = any(w in topic for w in ("atom", "nucleus", "electron", "proton"))

# ─── Scene setup ─────────────────────────────────────────────────────────────
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end   = 240
scene.render.fps  = 24

scene.render.image_settings.file_format = "FFMPEG"
scene.render.ffmpeg.format              = "MPEG4"
scene.render.ffmpeg.codec               = "H264"
scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
scene.render.filepath     = output_path
scene.render.resolution_x = 640
scene.render.resolution_y = 360
bpy.context.scene.render.engine = "BLENDER_EEVEE_NEXT"

# Bloom was removed in Blender 4.2+ EEVEE Next — skip gracefully
try:
    scene.eevee.use_bloom = True
    scene.eevee.bloom_intensity = 0.2
except AttributeError:
    pass

# World
world = bpy.data.worlds.new("W")
scene.world = world
world.use_nodes = True
if is_volcano:
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.02, 0.01, 1)
elif is_atom:
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.01, 0.01, 0.06, 1)
else:
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.02, 0.04, 0.1,  1)

# ─── Layer definitions ───────────────────────────────────────────────────────
if is_volcano:
    LAYERS = [
        ("Magma Chamber",  0.6, (1.0, 0.3, 0.0), 12.0, 0.0),   # hot orange glow
        ("Mantle",         1.3, (0.8, 0.4, 0.1),  3.0, 0.5),
        ("Crust",          1.9, (0.5, 0.35, 0.2), 0.8, 0.8),
        ("Surface Rock",   2.4, (0.35, 0.3, 0.25),0.5, 0.9),
    ]
elif is_atom:
    LAYERS = [
        ("Nucleus",  0.4, (1.0, 0.6, 0.1), 8.0, 0.0),
        ("Shell 1",  1.0, (0.2, 0.6, 1.0), 1.5, 0.85),
        ("Shell 2",  1.7, (0.1, 0.8, 0.8), 1.0, 0.88),
        ("Shell 3",  2.4, (0.3, 0.3, 0.9), 0.6, 0.92),
    ]
else:  # Earth interior
    LAYERS = [
        ("Inner Core",  0.7, (1.0, 0.55, 0.1), 10.0, 0.0),
        ("Outer Core",  1.3, (0.9, 0.25, 0.0),  4.0, 0.5),
        ("Mantle",      2.1, (0.75, 0.4, 0.1),  1.5, 0.7),
        ("Crust",       2.6, (0.35, 0.5, 0.25), 0.6, 0.88),
    ]

# ─── Build layered spheres ───────────────────────────────────────────────────
objects = []
for (lname, radius, color, emit_str, alpha) in LAYERS:
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=radius, location=(0, 0, 0), segments=32, ring_count=20
    )
    obj = bpy.context.active_object
    obj.name = lname

    m = bpy.data.materials.new(f"{lname}Mat")
    m.use_nodes = True
    m.blend_method = "BLEND" if alpha > 0 else "OPAQUE"
    nodes = m.node_tree.nodes
    bsdf  = nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value        = (*color, 1)
    bsdf.inputs["Emission Color"].default_value    = (*color, 1)
    bsdf.inputs["Emission Strength"].default_value = emit_str * 0.1
    bsdf.inputs["Roughness"].default_value         = 0.7
    bsdf.inputs["Alpha"].default_value             = 1.0 - alpha
    obj.data.materials.append(m)
    objects.append(obj)

# ─── Animation — slow rotation + camera pull-back ────────────────────────────
for obj in objects:
    obj.rotation_euler = (0, 0, 0)
    obj.keyframe_insert("rotation_euler", frame=1)
    obj.rotation_euler = (0, 0, math.tau)
    obj.keyframe_insert("rotation_euler", frame=240)
    for fc in obj.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"

# ─── Camera ───────────────────────────────────────────────────────────────────
bpy.ops.object.camera_add(location=(0, -7, 3))
cam = bpy.context.active_object
cam.name = "Camera"
cam.data.lens = 40
cam.rotation_euler = (math.radians(68), 0, 0)
scene.camera = cam

# Slowly orbit and pull back
for frame in range(1, 242, 4):
    t     = (frame - 1) / 240.0
    angle = math.radians(t * 40)
    r     = 7 + t * 2
    cam.location = (-r * math.sin(angle), -r * math.cos(angle), 3 + t)
    cam.keyframe_insert("location", frame=frame)

# ─── Lights ───────────────────────────────────────────────────────────────────
bpy.ops.object.light_add(type="AREA", location=(5, -5, 8))
key = bpy.context.active_object
key.data.energy = 400
key.data.size   = 4
key.data.color  = (1, 0.95, 0.9)

bpy.ops.object.light_add(type="AREA", location=(-5, 5, 4))
fill = bpy.context.active_object
fill.data.energy = 100
fill.data.color  = (0.6, 0.7, 1.0)

# ─── Render ───────────────────────────────────────────────────────────────────
bpy.ops.render.render(animation=True)
