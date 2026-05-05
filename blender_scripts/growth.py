"""
Whyzzle Blender Template — Seed / Plant Growth
Animates a seed sprouting, growing a stem, then unfolding leaves —
a 5-second time-lapse of plant growth.

Usage:  blender --background --python growth.py -- --params <json>

Engine: CYCLES (CPU) — reliable headless rendering.
Frames: 120 @ 24 fps = 5 s.  Keyframes scaled from original 240-frame design.
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

# World — bright sky
world = bpy.data.worlds.new("W")
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.45, 0.72, 1.0, 1)
bg.inputs[1].default_value = 0.5

# ─── Blender 4.x / 5.x fcurves compatibility ────────────────────────────────
def _set_interp(obj, mode="BEZIER"):
    if not obj.animation_data or not obj.animation_data.action:
        return
    action  = obj.animation_data.action
    fcurves = []
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

# ─── Helpers ─────────────────────────────────────────────────────────────────
def make_mat(name, color, emit=0.0, roughness=0.7):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value        = (*color, 1)
    b.inputs["Roughness"].default_value         = roughness
    b.inputs["Emission Color"].default_value    = (*color, 1)
    b.inputs["Emission Strength"].default_value = emit
    return m

def kf(obj, attr, frame):
    obj.keyframe_insert(attr, frame=frame)

# ─── Ground ───────────────────────────────────────────────────────────────────
bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, 0))
ground = bpy.context.active_object
ground.name = "Ground"
ground.data.materials.append(make_mat("GroundMat", (0.28, 0.52, 0.14), roughness=1.0))

# Soil mound
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.35, location=(0, 0, -0.2), segments=16, ring_count=8)
soil = bpy.context.active_object
soil.name = "Soil"
soil.scale.z = 0.5
soil.data.materials.append(make_mat("SoilMat", (0.38, 0.24, 0.10), roughness=1.0))

# ─── Seed (frames 1–40, then shrinks away) ───────────────────────────────────
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.12, location=(0, 0, 0.05), segments=12, ring_count=8)
seed = bpy.context.active_object
seed.name = "Seed"
seed.data.materials.append(make_mat("SeedMat", (0.50, 0.30, 0.08)))

seed.scale = (1, 1, 1);              kf(seed, "scale",  1)
seed.scale = (1.1, 1.1, 1.1);       kf(seed, "scale", 15)
seed.scale = (0.9, 0.9, 0.9);       kf(seed, "scale", 25)
seed.scale = (0.001, 0.001, 0.001); kf(seed, "scale", 40)

# ─── Root (grows downward, frames 1–45) ──────────────────────────────────────
bpy.ops.mesh.primitive_cylinder_add(radius=0.025, depth=1.0, location=(0, 0, -0.3))
root = bpy.context.active_object
root.name = "Root"
root.data.materials.append(make_mat("RootMat", (0.55, 0.35, 0.12)))
root.scale.z = 0.001; kf(root, "scale",     1)
root.scale.z = 0.001; kf(root, "scale",    10)
root.scale.z = 1.0;   kf(root, "scale",    45)
root.location.z = -0.3; kf(root, "location", 10)
root.location.z = -0.5; kf(root, "location", 45)
_set_interp(root, "BEZIER")

# ─── Stem (grows upward, frames 35–95) ───────────────────────────────────────
bpy.ops.mesh.primitive_cylinder_add(radius=0.04, depth=1.8, location=(0, 0, 0.1))
stem = bpy.context.active_object
stem.name = "Stem"
stem.data.materials.append(make_mat("StemMat", (0.18, 0.62, 0.12)))
stem.scale.z = 0.001; kf(stem, "scale",     35)
stem.scale.z = 1.0;   kf(stem, "scale",     95)
stem.location.z = 0.1; kf(stem, "location", 35)
stem.location.z = 1.1; kf(stem, "location", 95)
_set_interp(stem, "BEZIER")

# ─── Leaves (unfurl frames 80–115) ───────────────────────────────────────────
for sign, rot in [(1, 0), (-1, math.pi)]:
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=0.3, location=(sign * 0.4, 0, 1.6), segments=8, ring_count=4,
    )
    leaf = bpy.context.active_object
    leaf.name = f"Leaf_{sign}"
    leaf.scale = (1.0, 0.4, 0.12)
    leaf.rotation_euler.z = rot
    leaf.data.materials.append(make_mat("LeafMat", (0.15, 0.72, 0.18), emit=0.05))
    leaf.scale.x = 0.001; kf(leaf, "scale",  80)
    leaf.scale = (1.0, 0.4, 0.12); kf(leaf, "scale", 115)
    _set_interp(leaf, "BEZIER")

# ─── Sun disc (background decoration) ────────────────────────────────────────
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.6, location=(4, 2, 5))
sun_disc = bpy.context.active_object
sun_disc.name = "SunDisc"
sun_disc.data.materials.append(make_mat("SunDiscMat", (1.0, 0.92, 0.3), emit=6.0))

# ─── Camera (rises to follow growth) ─────────────────────────────────────────
bpy.ops.object.camera_add(location=(3.5, -3.5, 2.0))
cam = bpy.context.active_object
cam.name = "Camera"
cam.data.lens = 45
cam.rotation_euler = (math.radians(72), 0, math.radians(45))
scene.camera = cam

cam.location.z = 1.0; kf(cam, "location",   1)
cam.location.z = 2.8; kf(cam, "location", 120)

# ─── Lights ──────────────────────────────────────────────────────────────────
bpy.ops.object.light_add(type="SUN", location=(5, 2, 8))
sun = bpy.context.active_object
sun.data.energy = 4
sun.data.color  = (1.0, 0.95, 0.85)
sun.rotation_euler = (math.radians(45), 0, math.radians(-30))

bpy.ops.object.light_add(type="AREA", location=(-4, -2, 5))
fill = bpy.context.active_object
fill.data.energy = 150
fill.data.color  = (0.7, 0.85, 1.0)

# ─── Render ──────────────────────────────────────────────────────────────────
bpy.ops.render.render(animation=True)
