"""
Whyzzle Blender Template — Cross-Section / Layered Structure
Shows Earth's interior layers (or any layered structure) as nested
translucent spheres that slowly rotate to reveal their depths.

Usage:  blender --background --python cross_section.py -- --params <json>

Engine: CYCLES (CPU) — reliable headless rendering.
Frames: 120 @ 24 fps = 5 s.
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

import os
frames_dir = params.get("frames_dir", os.path.join(os.path.dirname(__file__), "frames"))
os.makedirs(frames_dir, exist_ok=True)
topic      = params.get("topic", "").lower()

is_volcano = any(w in topic for w in ("volcano", "eruption", "lava"))
is_atom    = any(w in topic for w in ("atom", "nucleus", "electron", "proton"))

# ─── Scene ───────────────────────────────────────────────────────────────────
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end   = 120   # 5 s @ 24 fps
scene.render.fps  = 24

scene.render.image_settings.file_format = "PNG"
scene.render.filepath     = os.path.join(frames_dir, "frame_####")
scene.render.resolution_x = 480
scene.render.resolution_y = 270

scene.render.engine  = "CYCLES"
scene.cycles.samples = 4
scene.cycles.device  = "CPU"
scene.cycles.max_bounces             = 2
scene.cycles.diffuse_bounces         = 1
scene.cycles.glossy_bounces          = 1
scene.cycles.transmission_bounces    = 1
scene.cycles.volume_bounces          = 0
scene.cycles.transparent_max_bounces = 2

# World background
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
        ("Magma Chamber", 0.6, (1.0, 0.3, 0.0), 12.0, 0.0),
        ("Mantle",        1.3, (0.8, 0.4, 0.1),  3.0, 0.5),
        ("Crust",         1.9, (0.5, 0.35, 0.2), 0.8, 0.7),
        ("Surface Rock",  2.4, (0.35, 0.3, 0.25),0.5, 0.85),
    ]
elif is_atom:
    LAYERS = [
        ("Nucleus", 0.4, (1.0, 0.6, 0.1), 8.0, 0.0),
        ("Shell 1", 1.0, (0.2, 0.6, 1.0), 1.5, 0.75),
        ("Shell 2", 1.7, (0.1, 0.8, 0.8), 1.0, 0.80),
        ("Shell 3", 2.4, (0.3, 0.3, 0.9), 0.6, 0.85),
    ]
else:  # Earth interior
    LAYERS = [
        ("Inner Core", 0.7, (1.0, 0.55, 0.1), 10.0, 0.0),
        ("Outer Core", 1.3, (0.9, 0.25, 0.0),  4.0, 0.4),
        ("Mantle",     2.1, (0.75, 0.4, 0.1),  1.5, 0.6),
        ("Crust",      2.6, (0.35, 0.5, 0.25), 0.6, 0.80),
    ]

# ─── Blender 4.x / 5.x fcurves compatibility ────────────────────────────────
def _set_interp(obj, mode="LINEAR"):
    if not obj.animation_data or not obj.animation_data.action:
        return
    action   = obj.animation_data.action
    fcurves  = []
    try:
        fcurves = list(action.fcurves)
    except AttributeError:
        try:
            for layer in action.layers:
                for strip in layer.strips:
                    for bag in getattr(strip, "channelbags", []):
                        fcurves.extend(bag.fcurves)
        except (AttributeError, TypeError):
            pass
    for fc in fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = mode

# ─── Build layered spheres ───────────────────────────────────────────────────
objects = []
for (lname, radius, color, emit_str, alpha) in LAYERS:
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=radius, location=(0, 0, 0), segments=24, ring_count=16,
    )
    obj = bpy.context.active_object
    obj.name = lname

    m = bpy.data.materials.new(f"{lname}Mat")
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value        = (*color, 1)
    bsdf.inputs["Emission Color"].default_value    = (*color, 1)
    bsdf.inputs["Emission Strength"].default_value = emit_str * 0.1
    bsdf.inputs["Roughness"].default_value         = 0.7
    bsdf.inputs["Alpha"].default_value             = 1.0 - alpha
    # blend_method is an EEVEE property; CYCLES uses Alpha directly
    if alpha > 0:
        try:
            m.blend_method = "BLEND"
        except AttributeError:
            pass
    obj.data.materials.append(m)
    objects.append(obj)

# ─── Animation — rotation ────────────────────────────────────────────────────
for obj in objects:
    obj.rotation_euler = (0, 0, 0)
    obj.keyframe_insert("rotation_euler", frame=1)
    obj.rotation_euler = (0, 0, math.tau)
    obj.keyframe_insert("rotation_euler", frame=120)
    _set_interp(obj, "LINEAR")

# ─── Camera ──────────────────────────────────────────────────────────────────
bpy.ops.object.camera_add(location=(0, -7, 3))
cam = bpy.context.active_object
cam.name = "Camera"
cam.data.lens = 40
cam.rotation_euler = (math.radians(68), 0, 0)
scene.camera = cam

for frame in range(1, 122, 4):
    t     = (frame - 1) / 120.0
    angle = math.radians(t * 40)
    r     = 7 + t * 2
    cam.location = (-r * math.sin(angle), -r * math.cos(angle), 3 + t)
    cam.keyframe_insert("location", frame=frame)

# ─── Lights ──────────────────────────────────────────────────────────────────
bpy.ops.object.light_add(type="AREA", location=(5, -5, 8))
key_light = bpy.context.active_object
key_light.data.energy = 400
key_light.data.size   = 4
key_light.data.color  = (1, 0.95, 0.9)

bpy.ops.object.light_add(type="AREA", location=(-5, 5, 4))
fill_light = bpy.context.active_object
fill_light.data.energy = 100
fill_light.data.color  = (0.6, 0.7, 1.0)

# ─── Render ──────────────────────────────────────────────────────────────────
bpy.ops.render.render(animation=True)
