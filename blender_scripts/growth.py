"""
Whyzzle — Growth template
A seed sprouts, grows a stem, then unfolds leaves.
Reads colour overrides and title from params JSON.
"""
import bpy, json, math, sys, os

params = {}
argv = sys.argv
if "--" in argv:
    extra = argv[argv.index("--") + 1:]
    if "--params" in extra:
        idx = extra.index("--params") + 1
        if idx < len(extra):
            with open(extra[idx], encoding="utf-8") as f:
                params = json.load(f)

frames_dir = params.get("frames_dir", os.path.join(os.path.dirname(__file__), "frames"))
os.makedirs(frames_dir, exist_ok=True)

# ─── Render settings ──────────────────────────────────────────────────────────
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end   = int(params.get("frames",  120))
scene.render.fps  = 24
scene.render.image_settings.file_format = "PNG"
scene.render.filepath     = os.path.join(frames_dir, "frame_####")
scene.render.resolution_x = int(params.get("width",   480))
scene.render.resolution_y = int(params.get("height",  270))
scene.render.engine  = "CYCLES"
scene.cycles.samples = int(params.get("samples", 4))
scene.cycles.device  = "CPU"
scene.cycles.max_bounces             = 2
scene.cycles.diffuse_bounces         = 1
scene.cycles.glossy_bounces          = 1
scene.cycles.transmission_bounces    = 1
scene.cycles.volume_bounces          = 0
scene.cycles.transparent_max_bounces = 2

F = scene.frame_end   # total frames — scale all keyframes to this

# ─── Scene parameters ─────────────────────────────────────────────────────────
_bg     = params.get("background_color", [0.45, 0.72, 1.0])
g_color = tuple(params.get("ground_color", [0.28, 0.52, 0.14]))
st_col  = tuple(params.get("stem_color",   [0.18, 0.62, 0.12]))
lf_col  = tuple(params.get("leaf_color",   [0.15, 0.72, 0.18]))
sd_col  = tuple(params.get("seed_color",   [0.50, 0.30, 0.08]))
title   = params.get("title", "")

# ─── World ────────────────────────────────────────────────────────────────────
world = bpy.data.worlds.new("W")
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (*_bg, 1)
bg.inputs[1].default_value = 0.5

# ─── fcurves compatibility ────────────────────────────────────────────────────
def _set_interp(obj, mode="BEZIER"):
    if not obj.animation_data or not obj.animation_data.action:
        return
    action = obj.animation_data.action
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
    obj.keyframe_insert(attr, frame=max(1, min(frame, F)))

# Scale a keyframe number from the 120-frame reference to actual F
def s(n):
    return max(1, round(n * F / 120))

# ─── Ground ───────────────────────────────────────────────────────────────────
bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, 0))
ground = bpy.context.active_object
ground.name = "Ground"
ground.data.materials.append(make_mat("GroundMat", g_color, roughness=1.0))

bpy.ops.mesh.primitive_uv_sphere_add(radius=0.35, location=(0, 0, -0.2), segments=16, ring_count=8)
soil = bpy.context.active_object
soil.name = "Soil"
soil.scale.z = 0.5
soil.data.materials.append(make_mat("SoilMat", (0.38, 0.24, 0.10), roughness=1.0))

# ─── Seed ─────────────────────────────────────────────────────────────────────
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.12, location=(0, 0, 0.05), segments=12, ring_count=8)
seed = bpy.context.active_object
seed.name = "Seed"
seed.data.materials.append(make_mat("SeedMat", sd_col))

seed.scale = (1, 1, 1);              kf(seed, "scale",  1)
seed.scale = (1.1, 1.1, 1.1);       kf(seed, "scale",  s(15))
seed.scale = (0.9, 0.9, 0.9);       kf(seed, "scale",  s(25))
seed.scale = (0.001, 0.001, 0.001); kf(seed, "scale",  s(40))

# ─── Root ─────────────────────────────────────────────────────────────────────
bpy.ops.mesh.primitive_cylinder_add(radius=0.025, depth=1.0, location=(0, 0, -0.3))
root = bpy.context.active_object
root.name = "Root"
root.data.materials.append(make_mat("RootMat", (0.55, 0.35, 0.12)))
root.scale.z = 0.001; kf(root, "scale",    1)
root.scale.z = 0.001; kf(root, "scale",    s(10))
root.scale.z = 1.0;   kf(root, "scale",    s(45))
root.location.z = -0.3; kf(root, "location", s(10))
root.location.z = -0.5; kf(root, "location", s(45))
_set_interp(root, "BEZIER")

# ─── Stem ─────────────────────────────────────────────────────────────────────
bpy.ops.mesh.primitive_cylinder_add(radius=0.04, depth=1.8, location=(0, 0, 0.1))
stem = bpy.context.active_object
stem.name = "Stem"
stem.data.materials.append(make_mat("StemMat", st_col))
stem.scale.z = 0.001; kf(stem, "scale",     s(35))
stem.scale.z = 1.0;   kf(stem, "scale",     s(95))
stem.location.z = 0.1; kf(stem, "location", s(35))
stem.location.z = 1.1; kf(stem, "location", s(95))
_set_interp(stem, "BEZIER")

# ─── Leaves ───────────────────────────────────────────────────────────────────
for sign, rot in [(1, 0), (-1, math.pi)]:
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=0.3, location=(sign * 0.4, 0, 1.6), segments=8, ring_count=4)
    leaf = bpy.context.active_object
    leaf.name = f"Leaf_{sign}"
    leaf.scale = (1.0, 0.4, 0.12)
    leaf.rotation_euler.z = rot
    leaf.data.materials.append(make_mat("LeafMat", lf_col, emit=0.05))
    leaf.scale.x = 0.001; kf(leaf, "scale", s(80))
    leaf.scale = (1.0, 0.4, 0.12); kf(leaf, "scale", s(115))
    _set_interp(leaf, "BEZIER")

# ─── Optional title label ─────────────────────────────────────────────────────
if title:
    bpy.ops.object.text_add(location=(-1.5, -1.5, 2.8))
    t = bpy.context.active_object
    t.data.body      = title.upper()
    t.data.size      = 0.3
    t.data.align_x   = "LEFT"
    t.rotation_euler = (math.radians(72), 0, math.radians(45))
    lbl_m = bpy.data.materials.new("TitleMat")
    lbl_m.use_nodes = True
    lbl_m.node_tree.nodes.clear()
    em  = lbl_m.node_tree.nodes.new("ShaderNodeEmission")
    out = lbl_m.node_tree.nodes.new("ShaderNodeOutputMaterial")
    em.inputs["Color"].default_value    = (0.1, 0.1, 0.1, 1)
    em.inputs["Strength"].default_value = 2.0
    lbl_m.node_tree.links.new(em.outputs["Emission"], out.inputs["Surface"])
    t.data.materials.append(lbl_m)

# ─── Sun disc ─────────────────────────────────────────────────────────────────
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

cam.location.z = 1.0; kf(cam, "location",  1)
cam.location.z = 2.8; kf(cam, "location",  F)

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
