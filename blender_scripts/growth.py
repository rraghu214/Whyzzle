"""
Whyzzle Blender Template — Seed / Plant Growth
Animates a seed sprouting, growing a stem, then unfolding leaves —
a 10-second time-lapse of plant growth.

Usage:  blender --background --python growth.py -- --params <json>
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

output_path = params.get("output_path", "//output/growth.mp4")

# ─── Scene setup ─────────────────────────────────────────────────────────────
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end   = 240
scene.render.fps  = 24

scene.render.image_settings.file_format  = "FFMPEG"
scene.render.ffmpeg.format               = "MPEG4"
scene.render.ffmpeg.codec                = "H264"
scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
scene.render.filepath     = output_path
scene.render.resolution_x = 640
scene.render.resolution_y = 360
bpy.context.scene.render.engine = "BLENDER_EEVEE_NEXT"

# Bloom was removed in Blender 4.2+ EEVEE Next — skip gracefully
try:
    scene.eevee.use_bloom = True
    scene.eevee.bloom_intensity = 0.15
except AttributeError:
    pass

# World — bright sky
world = bpy.data.worlds.new("W")
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.45, 0.72, 1.0, 1)
bg.inputs[1].default_value = 0.8

# ─── Helper ───────────────────────────────────────────────────────────────────
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

# ─── Ground plane ─────────────────────────────────────────────────────────────
bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, 0))
ground = bpy.context.active_object
ground.name = "Ground"
ground.data.materials.append(make_mat("GroundMat", (0.28, 0.52, 0.14), roughness=1.0))

# ─── Soil mound (small dome) ──────────────────────────────────────────────────
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.35, location=(0, 0, -0.2), segments=16, ring_count=8)
soil = bpy.context.active_object
soil.name = "Soil"
soil.scale.z = 0.5
soil.data.materials.append(make_mat("SoilMat", (0.38, 0.24, 0.10), roughness=1.0))

# ─── Seed ─────────────────────────────────────────────────────────────────────
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.12, location=(0, 0, 0.05), segments=12, ring_count=8)
seed = bpy.context.active_object
seed.name = "Seed"
seed.data.materials.append(make_mat("SeedMat", (0.50, 0.30, 0.08)))

# Seed: present at frame 1, pulses slightly, then disappears at frame 80
seed.scale = (1, 1, 1);              kf(seed, "scale", 1)
seed.scale = (1.1, 1.1, 1.1);       kf(seed, "scale", 30)
seed.scale = (0.9, 0.9, 0.9);       kf(seed, "scale", 50)
seed.scale = (0.001, 0.001, 0.001); kf(seed, "scale", 80)

# ─── Root (thin cylinder growing downward) ────────────────────────────────────
bpy.ops.mesh.primitive_cylinder_add(radius=0.025, depth=1.0, location=(0, 0, -0.3))
root = bpy.context.active_object
root.name = "Root"
root.data.materials.append(make_mat("RootMat", (0.55, 0.35, 0.12)))
root.scale.z = 0.001; kf(root, "scale", 1)
root.scale.z = 0.001; kf(root, "scale", 20)
root.scale.z = 1.0;   kf(root, "scale", 90)
root.location.z = -0.3; kf(root, "location", 20)
root.location.z = -0.5; kf(root, "location", 90)
for fc in root.animation_data.action.fcurves:
    for kp in fc.keyframe_points: kp.interpolation = "BEZIER"

# ─── Stem (cylinder growing upward) ──────────────────────────────────────────
bpy.ops.mesh.primitive_cylinder_add(radius=0.04, depth=1.8, location=(0, 0, 0.1))
stem = bpy.context.active_object
stem.name = "Stem"
stem.data.materials.append(make_mat("StemMat", (0.18, 0.62, 0.12)))
stem.scale.z = 0.001; kf(stem, "scale", 70)
stem.scale.z = 1.0;   kf(stem, "scale", 190)
stem.location.z = 0.1; kf(stem, "location", 70)
stem.location.z = 1.1; kf(stem, "location", 190)
for fc in stem.animation_data.action.fcurves:
    for kp in fc.keyframe_points: kp.interpolation = "BEZIER"

# ─── Leaf pair (flat ovals, unfurl) ──────────────────────────────────────────
for sign, rot in [(1, 0), (-1, math.pi)]:
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=0.3, location=(sign * 0.4, 0, 1.6), segments=8, ring_count=4
    )
    leaf = bpy.context.active_object
    leaf.name = f"Leaf_{sign}"
    leaf.scale = (1.0, 0.4, 0.12)
    leaf.rotation_euler.z = rot
    leaf.data.materials.append(make_mat("LeafMat", (0.15, 0.72, 0.18), emit=0.05))
    leaf.scale.x = 0.001; kf(leaf, "scale", 160)
    leaf.scale = (1.0, 0.4, 0.12); kf(leaf, "scale", 230)
    for fc in leaf.animation_data.action.fcurves:
        for kp in fc.keyframe_points: kp.interpolation = "BEZIER"

# ─── Sun disc (background) ───────────────────────────────────────────────────
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.6, location=(4, 2, 5))
sun_disc = bpy.context.active_object
sun_disc.name = "SunDisc"
sun_disc.data.materials.append(make_mat("SunDiscMat", (1.0, 0.92, 0.3), emit=6.0))

# ─── Camera ───────────────────────────────────────────────────────────────────
bpy.ops.object.camera_add(location=(3.5, -3.5, 2.0))
cam = bpy.context.active_object
cam.name = "Camera"
cam.data.lens = 45
cam.rotation_euler = (math.radians(72), 0, math.radians(45))
scene.camera = cam

# Camera slowly rises and tilts to follow growth
cam.location.z = 1.0; kf(cam, "location", 1)
cam.location.z = 2.8; kf(cam, "location", 240)

# ─── Lights ───────────────────────────────────────────────────────────────────
bpy.ops.object.light_add(type="SUN", location=(5, 2, 8))
sun = bpy.context.active_object
sun.data.energy = 4
sun.data.color  = (1.0, 0.95, 0.85)
sun.rotation_euler = (math.radians(45), 0, math.radians(-30))

bpy.ops.object.light_add(type="AREA", location=(-4, -2, 5))
fill = bpy.context.active_object
fill.data.energy = 150
fill.data.color  = (0.7, 0.85, 1.0)

# ─── Render ───────────────────────────────────────────────────────────────────
bpy.ops.render.render(animation=True)
