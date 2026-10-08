import bpy, math
from mathutils import Vector
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
scene.render.engine='BLENDER_EEVEE_NEXT'
scene.render.resolution_x=360
scene.render.resolution_y=640
scene.render.resolution_percentage=100
scene.render.fps=12
scene.frame_end=72
scene.render.image_settings.file_format='PNG'
scene.render.filepath='frames/'
def mat(name,color,rough=0.75):
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
 p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough
 return m
fur=mat('Warm brown fur',(.35,.145,.065));light=mat('Muzzle tan',(.8,.49,.25));pink=mat('Pink cheeks',(.95,.25,.36));blue=mat('Denim overalls',(.08,.25,.7));black=mat('Eyes and nose',(.018,.012,.012),.2);white=mat('Eye whites',(.96,.94,.89));grass=mat('Green playground',(.21,.57,.21));red=mat('Balloon red',(.9,.04,.06));yellow=mat('Sun yellow',(.98,.7,.08))
def sphere(name,loc,scale,material,parent=None):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=20,ring_count=12,location=loc)
 o=bpy.context.object;o.name=name;o.scale=scale;o.data.materials.append(material)
 if parent:o.parent=parent
 bpy.ops.object.shade_smooth();return o
def empty(name,loc,parent=None):
 o=bpy.data.objects.new(name,None);scene.collection.objects.link(o);o.location=loc
 if parent:o.parent=parent
 return o
root=empty('Bobo body root',(0,0,0))
sphere('Body',(0,0,1.55),(.65,.38,.83),fur,root)
sphere('Blue overalls bib',(0,-.36,1.35),(.51,.12,.51),blue,root)
sphere('Head',(0,-.02,2.55),(.67,.52,.64),fur,root)
for side in (-1,1):
 sphere('Ear',(side*.52,0,3.05),(.25,.18,.28),fur,root)
 sphere('Inner ear',(side*.52,-.16,3.05),(.14,.065,.17),pink,root)
 sphere('Eye white',(side*.27,-.49,2.7),(.19,.105,.22),white,root)
 sphere('Pupil',(side*.27,-.585,2.68),(.112,.06,.15),black,root)
 sphere('Cheek',(side*.45,-.47,2.38),(.17,.065,.12),pink,root)
sphere('Muzzle',(0,-.5,2.37),(.3,.18,.22),light,root)
sphere('Nose',(0,-.665,2.46),(.14,.085,.095),black,root)
limbs=[]
for side in (-1,1):
 arm=empty('Arm pivot '+str(side),(side*.65,0,2.02),root)
 sphere('Arm',(side*.16,-.01,-.35),(.2,.2,.46),fur,arm)
 sphere('Paw',(side*.19,-.02,-.75),(.23,.2,.2),fur,arm)
 leg=empty('Leg pivot '+str(side),(side*.34,0,1.0),root)
 sphere('Leg',(0,0,-.36),(.25,.24,.48),blue,leg)
 sphere('Foot',(0,-.14,-.75),(.3,.39,.17),fur,leg)
 limbs.append((arm,leg,side))
sphere('Playground ground',(0,0,-.25),(30,30,.2),grass)
for side in (-1,1):
 sphere('Playground ball',(side*2,1,.25),(.38,.38,.38),red if side==1 else yellow)
for frame in range(1,73):
 scene.frame_set(frame)
 if frame<=24:
  phase=frame*.48
  root.location.z=.06+abs(math.sin(phase))*.09
  for arm,leg,side in limbs:
   arm.rotation_euler.x=side*.45*math.sin(phase)
   leg.rotation_euler.x=-side*.55*math.sin(phase)
 elif frame<=48:
  root.location.z=0
  for arm,leg,side in limbs:
   arm.rotation_euler.x=0;leg.rotation_euler.x=0
   arm.rotation_euler.y=(.15+(.85 if side==1 else 0))*math.sin((frame-24)*.5)
 else:
  t=(frame-48)/24
  root.location.z=max(0,math.sin(t*math.pi*2))*0.8
  for arm,leg,side in limbs:
   arm.rotation_euler.y=side*.65
   leg.rotation_euler.x=side*.15
 root.keyframe_insert(data_path='location',frame=frame)
 for arm,leg,_ in limbs:
  arm.keyframe_insert(data_path='rotation_euler',frame=frame)
  leg.keyframe_insert(data_path='rotation_euler',frame=frame)
world=bpy.data.worlds.new('Bright sky');scene.world=world;world.use_nodes=True
world.node_tree.nodes['Background'].inputs['Color'].default_value=(.45,.7,1,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.8
def point(obj,loc):
 obj.rotation_euler=(Vector(loc)-obj.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.light_add(type='AREA',location=(-3,-4,7))
bpy.context.object.data.energy=900;bpy.context.object.data.shape='DISK';bpy.context.object.data.size=5
bpy.ops.object.camera_add(location=(5,-10,5))
cam=bpy.context.object;point(cam,(0,0,1.65));cam.data.type='ORTHO';cam.data.ortho_scale=5.1;scene.camera=cam
scene.render.film_transparent=False
scene.frame_set(1)
bpy.ops.render.render(animation=True)
