"""
Whyzzle — Cross-Section template
Nested concentric spheres rotating to reveal inner layers.
Reads layer definitions from params JSON; falls back to Earth's interior.
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

TOTAL_FRAMES = scene.frame_end
topic = params.get("topic", "").lower()

# ─── Scene parameters ─────────────────────────────────────────────────────────
_bg = params.get("background_color", [0.02, 0.04, 0.1])

_default_layers = [
    {"label": "Inner Core", "radius": 0.7, "color": [1.0, 0.55, 0.1], "emit": 10.0, "alpha": 0.0},
    {"label": "Outer Core", "radius": 1.3, "color": [0.9, 0.25, 0.0], "emit":  4.0, "alpha": 0.4},
    {"label": "Mantle",     "radius": 2.1, "color": [0.75, 0.4, 0.1], "emit":  1.5, "alpha": 0.6},
    {"label": "Crust",      "radius": 2.6, "color": [0.35, 0.5, 0.25],"emit":  0.6, "alpha": 0.80},
]
layers_raw = params.get("layers", _default_layers)
LAYERS = [
    (l["label"], float(l["radius"]), tuple(l["color"]),
     float(l.get("emit", 2.0)), float(l.get("alpha", 0.5)))
    for l in layers_raw
]

# ─── World ────────────────────────────────────────────────────────────────────
world = bpy.data.worlds.new("W")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (*_bg, 1)

# ─── fcurves compatibility ────────────────────────────────────────────────────
def _set_interp(obj, mode="LINEAR"):
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

# ─── Build layered spheres ────────────────────────────────────────────────────
objects = []
for (lname, radius, color, emit_str, alpha) in LAYERS:
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=radius, location=(0, 0, 0), segments=24, ring_count=16)
    obj = bpy.context.active_object
    obj.name = lname

    m = bpy.data.materials.new(f"{lname}Mat")
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value        = (*color, 1)
    bsdf.inputs["Emission Color"].default_value    = (*color, 1)
    bsdf.inputs["Emission Strength"].default_value = emit_str * 0.1
    bsdf.inputs["Roughness"].default_value         = 0.7
    bsdf.inputs["Alpha"].default_value             = max(0.0, 1.0 - alpha)
    if alpha > 0:
        try:
            m.blend_method = "BLEND"
        except AttributeError:
            pass
    obj.data.materials.append(m)
    objects.append((obj, lname, radius, color))

# ─── Labels (positioned just outside each sphere, facing camera) ──────────────
for obj, lname, radius, color in objects:
    bpy.ops.object.text_add(location=(0, -(radius + 0.25), radius * 0.6))
    t = bpy.context.active_object
    t.data.body      = lname.upper()
    t.data.size      = max(0.14, min(0.22, 0.18))
    t.data.align_x   = "CENTER"
    t.rotation_euler = (math.radians(68), 0, 0)
    lbl_m = bpy.data.materials.new(f"{lname}LblMat")
    lbl_m.use_nodes = True
    lbl_m.node_tree.nodes.clear()
    em  = lbl_m.node_tree.nodes.new("ShaderNodeEmission")
    out = lbl_m.node_tree.nodes.new("ShaderNodeOutputMaterial")
    em.inputs["Color"].default_value    = (*color, 1)
    em.inputs["Strength"].default_value = 3.0
    lbl_m.node_tree.links.new(em.outputs["Emission"], out.inputs["Surface"])
    t.data.materials.append(lbl_m)

# ─── Rotation animation ───────────────────────────────────────────────────────
for obj, *_ in objects:
    obj.rotation_euler = (0, 0, 0)
    obj.keyframe_insert("rotation_euler", frame=1)
    obj.rotation_euler = (0, 0, math.tau)
    obj.keyframe_insert("rotation_euler", frame=TOTAL_FRAMES)
    _set_interp(obj, "LINEAR")

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

# ─── Camera ───────────────────────────────────────────────────────────────────
bpy.ops.object.camera_add(location=(0, -7, 3))
cam = bpy.context.active_object
cam.name = "Camera"
cam.data.lens = 40
cam.rotation_euler = (math.radians(68), 0, 0)
scene.camera = cam

for frame in range(1, TOTAL_FRAMES + 2, 4):
    t     = (frame - 1) / TOTAL_FRAMES
    angle = math.radians(t * 40)
    r     = 7 + t * 2
    cam.location = (-r * math.sin(angle), -r * math.cos(angle), 3 + t)
    cam.keyframe_insert("location", frame=frame)

# ─── Render ───────────────────────────────────────────────────────────────────
bpy.ops.render.render(animation=True)
