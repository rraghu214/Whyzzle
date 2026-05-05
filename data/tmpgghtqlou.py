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

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end   = 120          # 5 s @ 24 fps
scene.render.fps  = 24
scene.render.image_settings.file_format = "PNG"
scene.render.filepath     = os.path.join(frames_dir, "frame_####")
scene.render.resolution_x = 480
scene.render.resolution_y = 270
scene.render.engine  = "CYCLES"
scene.cycles.samples = 4
scene.cycles.device  = "CPU"

# World — created here so scene.world is never None
world = bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
_bg_node = world.node_tree.nodes["Background"]
_bg_node.inputs[0].default_value = (0.01, 0.01, 0.05, 1)  # default dark; override below
_bg_node.inputs[1].default_value = 1.0

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

world.node_tree.nodes["Background"].inputs[0].default_value = (0.2, 0.2, 0.4, 1)

bpy.ops.mesh.primitive_uv_sphere_add(radius=2, enter_editmode=False, align='WORLD', location=(0, 0, 0))
earth = bpy.context.active_object
earth.name = "Earth"
mat_earth = bpy.data.materials.new(name="EarthMat")
mat_earth.use_nodes = True
bsdf = mat_earth.node_tree.nodes["Principled BSDF"]
bsdf.inputs['Base Color'].default_value = (0.2, 0.5, 1, 1)
earth.data.materials.append(mat_earth)

bpy.ops.mesh.primitive_uv_sphere_add(radius=1, enter_editmode=False, align='WORLD', location=(4, 0, 0))
mars = bpy.context.active_object
mars.name = "Mars"
mat_mars = bpy.data.materials.new(name="MarsMat")
mat_mars.use_nodes = True
bsdf = mat_mars.node_tree.nodes["Principled BSDF"]
bsdf.inputs['Base Color'].default_value = (1, 0.2, 0, 1)
mars.data.materials.append(mat_mars)

bpy.ops.object.text_add(enter_editmode=False, align='WORLD', location=(0, 2, 0))
gravity = bpy.context.active_object
gravity.name = "Gravity"
gravity.data.body = "Gravity"
gravity.data.size = 0.3
gravity.data.align_x = "CENTER"
gravity.rotation_euler = (math.radians(90), 0, 0)

bpy.ops.object.text_add(enter_editmode=False, align='WORLD', location=(4, 2, 0))
orbits = bpy.context.active_object
orbits.name = "Orbits"
orbits.data.body = "Orbits"
orbits.data.size = 0.3
orbits.data.align_x = "CENTER"
orbits.rotation_euler = (math.radians(90), 0, 0)

earth.location = (0, 0, 0)
earth.keyframe_insert(data_path="location", frame=1)
earth.location = (0, 0, 4)
earth.keyframe_insert(data_path="location", frame=120)
_set_interp(earth)

mars.location = (4, 0, 0)
mars.keyframe_insert(data_path="location", frame=1)
mars.location = (4, 0, 4)
mars.keyframe_insert(data_path="location", frame=120)
_set_interp(mars)

gravity.location = (0, 2, 0)
gravity.keyframe_insert(data_path="location", frame=1)
gravity.location = (0, 2, 4)
gravity.keyframe_insert(data_path="location", frame=120)
_set_interp(gravity)

orbits.location = (4, 2, 0)
orbits.keyframe_insert(data_path="location", frame=1)
orbits.location = (4, 2, 4)
orbits.keyframe_insert(data_path="location", frame=120)
_set_interp(orbits)

bpy.ops.object.light_add(type="SUN", radius=1, align='WORLD', location=(0, 0, 8))
sun = bpy.context.active_object
sun.name = "Sun"

bpy.ops.object.camera_add(enter_editmode=False, align='VIEW', location=(0, -8, 2), rotation=(math.radians(45), 0, 0))
camera = bpy.context.active_object
scene.camera = camera

bpy.ops.render.render(animation=True)