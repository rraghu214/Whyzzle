"""
Whyzzle — Orbit template
Objects revolving around a central body (solar system, atom, satellites…).
Reads scene parameters from the params JSON; falls back to solar system defaults.
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

# ─── Render settings (overridable via params) ─────────────────────────────────
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

# ─── Scene parameters (from LLM or defaults) ─────────────────────────────────
_bg = params.get("background_color", [0.008, 0.008, 0.04])
_cb = params.get("central_body", {})
central_label  = _cb.get("label",  "Sun")
central_color  = tuple(_cb.get("color",  [1.0, 0.85, 0.3]))
central_radius = float(_cb.get("radius", 1.2))

_default_bodies = [
    {"label": "Mercury", "color": [0.65, 0.55, 0.45], "radius": 0.13, "orbit_r": 2.2, "speed": 3.8},
    {"label": "Venus",   "color": [0.9,  0.75, 0.4],  "radius": 0.20, "orbit_r": 3.3, "speed": 2.4},
    {"label": "Earth",   "color": [0.2,  0.5,  0.95], "radius": 0.22, "orbit_r": 4.5, "speed": 1.5},
    {"label": "Mars",    "color": [0.85, 0.3,  0.1],  "radius": 0.16, "orbit_r": 5.7, "speed": 0.9},
]
orbiting_bodies = params.get("orbiting_bodies", _default_bodies)

# ─── World ────────────────────────────────────────────────────────────────────
world = bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (*_bg, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 1.0

# ─── Blender 4.x / 5.x fcurves compatibility ─────────────────────────────────
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

# ─── Materials ────────────────────────────────────────────────────────────────
def emission_mat(name, color, strength=6.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes.clear()
    em  = m.node_tree.nodes.new("ShaderNodeEmission")
    out = m.node_tree.nodes.new("ShaderNodeOutputMaterial")
    em.inputs["Color"].default_value    = (*color, 1)
    em.inputs["Strength"].default_value = strength
    m.node_tree.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return m

def diffuse_mat(name, color):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value  = 0.5
    return m

def label_mat(color):
    m = bpy.data.materials.new("LblMat")
    m.use_nodes = True
    m.node_tree.nodes.clear()
    em  = m.node_tree.nodes.new("ShaderNodeEmission")
    out = m.node_tree.nodes.new("ShaderNodeOutputMaterial")
    em.inputs["Color"].default_value    = (*color, 1)
    em.inputs["Strength"].default_value = 3.0
    m.node_tree.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return m

# ─── Central body ─────────────────────────────────────────────────────────────
bpy.ops.mesh.primitive_uv_sphere_add(
    radius=central_radius, location=(0, 0, 0), segments=20, ring_count=14)
central = bpy.context.active_object
central.name = central_label
central.data.materials.append(emission_mat(f"{central_label}Mat", central_color, strength=10))

# Label above central body
bpy.ops.object.text_add(location=(0, 0, central_radius + 0.4))
lbl = bpy.context.active_object
lbl.data.body      = central_label.upper()
lbl.data.size      = 0.28
lbl.data.align_x   = "CENTER"
lbl.rotation_euler = (math.radians(60), 0, 0)
lbl.data.materials.append(label_mat(central_color))

# Central point light
bpy.ops.object.light_add(type="POINT", location=(0, 0, 0))
sun_light = bpy.context.active_object
sun_light.data.energy = 1200
sun_light.data.color  = (1, 0.95, 0.8)

# ─── Orbiting bodies ─────────────────────────────────────────────────────────
for body in orbiting_bodies:
    blabel  = body.get("label", "Body")
    bcolor  = tuple(body.get("color",  [0.6, 0.6, 0.6]))
    bradius = float(body.get("radius", 0.2))
    orbit_r = float(body.get("orbit_r", 4.0))
    speed   = float(body.get("speed",   1.0))

    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=bradius, location=(orbit_r, 0, 0), segments=12, ring_count=8)
    obj = bpy.context.active_object
    obj.name = blabel
    obj.data.materials.append(diffuse_mat(f"{blabel}Mat", bcolor))

    # Name label parented to planet
    bpy.ops.object.text_add(location=(0, 0, bradius + 0.18))
    t = bpy.context.active_object
    t.data.body      = blabel.upper()
    t.data.size      = 0.16
    t.data.align_x   = "CENTER"
    t.rotation_euler = (math.radians(60), 0, 0)
    t.data.materials.append(label_mat(bcolor))
    t.parent = obj

    # Orbit animation
    for frame in range(1, TOTAL_FRAMES + 2, 2):
        t_norm = (frame - 1) / TOTAL_FRAMES
        angle  = math.tau * t_norm * speed
        obj.location = (
            math.cos(angle) * orbit_r,
            math.sin(angle) * orbit_r,
            math.sin(angle * 0.15) * 0.3,
        )
        obj.keyframe_insert("location", frame=frame)
    _set_interp(obj, "LINEAR")

    # Thin orbit ring
    bpy.ops.mesh.primitive_torus_add(
        major_radius=orbit_r, minor_radius=0.012,
        major_segments=48, minor_segments=4)
    ring = bpy.context.active_object
    ring.data.materials.append(emission_mat("RingMat", [0.3, 0.35, 0.7], strength=0.4))

# ─── Fill light ───────────────────────────────────────────────────────────────
bpy.ops.object.light_add(type="AREA", location=(-8, 4, 6))
fill = bpy.context.active_object
fill.data.energy = 80
fill.data.color  = (0.5, 0.6, 1.0)
fill.data.size   = 6

# ─── Camera ───────────────────────────────────────────────────────────────────
bpy.ops.object.camera_add(location=(0, -14, 8))
cam = bpy.context.active_object
cam.name = "Camera"
cam.data.lens = 38
cam.rotation_euler = (math.radians(58), 0, 0)
scene.camera = cam

for frame in range(1, TOTAL_FRAMES + 2, 4):
    t     = (frame - 1) / TOTAL_FRAMES
    angle = math.radians(t * 30)
    cam.location = (-14 * math.sin(angle), -14 * math.cos(angle), 8.0 - t * 1.5)
    cam.keyframe_insert("location", frame=frame)

# ─── Render ───────────────────────────────────────────────────────────────────
bpy.ops.render.render(animation=True)
