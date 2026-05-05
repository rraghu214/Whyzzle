"""
Whyzzle Blender Template — Planetary Orbital Motion
Renders 5 seconds of animated planetary orbits around a glowing sun.
Planet name labels float above each planet.

Receives parameters via:  blender --background --python orbit.py -- --params <json_file>

Engine: CYCLES (CPU) — reliable in headless mode on any hardware.
Frames: 120 @ 24 fps = 5 s.  Resolution 480x270, 4 samples.
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

# World — deep space background with faint stars effect
world = bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.008, 0.008, 0.04, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 1.0

# ─── Blender 4.x / 5.x fcurves compatibility ────────────────────────────────
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

# ─── Materials ───────────────────────────────────────────────────────────────
def emission_mat(name, color, strength=3.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes.clear()
    em  = m.node_tree.nodes.new("ShaderNodeEmission")
    out = m.node_tree.nodes.new("ShaderNodeOutputMaterial")
    em.inputs["Color"].default_value    = (*color, 1)
    em.inputs["Strength"].default_value = strength
    m.node_tree.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return m

def diffuse_mat(name, color, roughness=0.4):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value  = roughness
    return m

def label_mat(name, color):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes.clear()
    em  = m.node_tree.nodes.new("ShaderNodeEmission")
    out = m.node_tree.nodes.new("ShaderNodeOutputMaterial")
    em.inputs["Color"].default_value    = (*color, 1)
    em.inputs["Strength"].default_value = 2.5
    m.node_tree.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return m

# ─── Sun ─────────────────────────────────────────────────────────────────────
bpy.ops.mesh.primitive_uv_sphere_add(radius=1.2, location=(0, 0, 0), segments=20, ring_count=14)
sun = bpy.context.active_object
sun.name = "Sun"
sun.data.materials.append(emission_mat("SunMat", (1.0, 0.85, 0.3), strength=10))

# "SUN" label
bpy.ops.object.text_add(location=(0, 0, 1.6))
sun_label = bpy.context.active_object
sun_label.data.body = "SUN"
sun_label.data.size = 0.28
sun_label.data.align_x = "CENTER"
sun_label.data.materials.append(label_mat("SunLabelMat", (1.0, 0.92, 0.4)))
sun_label.rotation_euler = (math.radians(58), 0, 0)

bpy.ops.object.light_add(type="POINT", location=(0, 0, 0))
sun_light = bpy.context.active_object
sun_light.data.energy = 1200
sun_light.data.color  = (1, 0.9, 0.6)
sun_light.data.shadow_soft_size = 1.5

# ─── Planets ─────────────────────────────────────────────────────────────────
PLANETS = [
    # name,     radius, orbit_r, color_rgb,           speed_mult, label_color
    ("Mercury", 0.13,   2.2,    (0.65, 0.55, 0.45),  3.8,        (0.9,  0.8,  0.7)),
    ("Venus",   0.20,   3.3,    (0.95, 0.78, 0.35),  2.4,        (1.0,  0.9,  0.5)),
    ("Earth",   0.22,   4.5,    (0.2,  0.5,  0.95),  1.5,        (0.4,  0.8,  1.0)),
    ("Mars",    0.16,   5.7,    (0.85, 0.3,  0.1),   0.9,        (1.0,  0.5,  0.3)),
]

planet_objects = []

def add_planet(name, radius, orbit_r, color, speed_mult, label_color):
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=radius, location=(orbit_r, 0, 0), segments=16, ring_count=12,
    )
    obj = bpy.context.active_object
    obj.name = name
    obj.data.materials.append(diffuse_mat(f"{name}Mat", color))

    # Floating name label above planet — follows planet by parenting
    bpy.ops.object.text_add(location=(orbit_r, 0, radius + 0.22))
    lbl = bpy.context.active_object
    lbl.data.body = name.upper()
    lbl.data.size = 0.18
    lbl.data.align_x = "CENTER"
    lbl.data.materials.append(label_mat(f"{name}LabelMat", label_color))
    lbl.rotation_euler = (math.radians(58), 0, 0)
    lbl.parent = obj

    for frame in range(1, 122, 2):
        t     = (frame - 1) / 120.0
        angle = math.tau * t * speed_mult
        obj.location = (
            math.cos(angle) * orbit_r,
            math.sin(angle) * orbit_r,
            math.sin(angle * 0.15) * 0.3,
        )
        obj.keyframe_insert("location", frame=frame)

    _set_interp(obj, "LINEAR")
    planet_objects.append(obj)
    return obj

for args in PLANETS:
    add_planet(*args)

# Orbit rings (thin tori)
for _, _, orbit_r, _, _, _ in PLANETS:
    bpy.ops.mesh.primitive_torus_add(
        major_radius=orbit_r, minor_radius=0.012,
        major_segments=48, minor_segments=4,
    )
    ring = bpy.context.active_object
    m = bpy.data.materials.new("RingMat")
    m.use_nodes = True
    m.node_tree.nodes.clear()
    em  = m.node_tree.nodes.new("ShaderNodeEmission")
    out = m.node_tree.nodes.new("ShaderNodeOutputMaterial")
    em.inputs["Color"].default_value    = (0.3, 0.35, 0.7, 1)
    em.inputs["Strength"].default_value = 0.4
    m.node_tree.links.new(em.outputs["Emission"], out.inputs["Surface"])
    ring.data.materials.append(m)

# ─── Camera — slow arc ───────────────────────────────────────────────────────
bpy.ops.object.camera_add(location=(0, -14, 8))
cam = bpy.context.active_object
cam.name = "Camera"
cam.data.lens = 38
cam.rotation_euler = (math.radians(58), 0, 0)
scene.camera = cam

for frame in range(1, 122, 4):
    t     = (frame - 1) / 120.0
    angle = math.radians(t * 30)
    cam.location = (
        -14 * math.sin(angle),
        -14 * math.cos(angle),
        8.0 - t * 1.5,
    )
    cam.keyframe_insert("location", frame=frame)

# ─── Fill light (from the side) ──────────────────────────────────────────────
bpy.ops.object.light_add(type="AREA", location=(-8, 4, 6))
fill = bpy.context.active_object
fill.data.energy = 80
fill.data.color  = (0.5, 0.6, 1.0)
fill.data.size   = 6

# ─── Render ──────────────────────────────────────────────────────────────────
bpy.ops.render.render(animation=True)
