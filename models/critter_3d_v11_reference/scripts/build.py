import bpy, math, json, os
from mathutils import Vector
from mathutils.geometry import tessellate_polygon
from math import sin,cos,pi,sqrt
ROOT='/Users/kunruiwang/Documents/Codex/2026-10-17/ni'
OUT=ROOT+'/outputs/CatNap-3D'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
model=bpy.data.collections.new('CATNAP • shape review v01');bpy.context.scene.collection.children.link(model)
studio=bpy.data.collections.new('STUDIO • cameras and lighting');bpy.context.scene.collection.children.link(studio)
def move(obj,col=model):
 for c in list(obj.users_collection):c.objects.unlink(obj)
 col.objects.link(obj)
 return obj
def mat(name,color,rough=.6,metal=0,bump=False):
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
 n=m.node_tree.nodes;p=n.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
 if bump:
  tex=n.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=115;tex.inputs['Detail'].default_value=2
  b=n.new('ShaderNodeBump');b.inputs['Strength'].default_value=.12;b.inputs['Distance'].default_value=.012;m.node_tree.links.new(tex.outputs['Fac'],b.inputs['Height']);m.node_tree.links.new(b.outputs['Normal'],p.inputs['Normal']);p.inputs['Sheen Weight'].default_value=.22
 return m
purple=mat('01 • CatNap purple • temporary surface',(.235,.045,.46),.64,bump=True)
dark=mat('02 • paws and inner ears',(.115,.023,.23),.72,bump=True)
black=mat('03 • dark eye buttons',(.006,.004,.011),.28)
inside=mat('04 • mouth cavity • matte',(.002,.001,.004),.95)
white=mat('05 • small white pupils',(.97,.95,1),.3)
gold=mat('06 • crescent pendant',(.93,.58,.07),.27,.7)
zipmat=mat('07 • zipper fabric',(.035,.015,.055),.8)
teeth=mat('08 • zipper teeth',(.15,.12,.19),.48,.3)
seammat=mat('09 • seam thread',(.47,.25,.65),.8)
def finish(o,m):
 if m:o.data.materials.append(m)
 if o.type=='MESH':
  for p in o.data.polygons:p.use_smooth=True
 move(o);return o
def ell(name,loc,scale,m,seg=64,rings=48):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=seg,ring_count=rings,location=loc);o=bpy.context.object;o.name=name;o.scale=scale;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);return finish(o,m)
def curve(name,pts,r,m,radii=None,cyclic=False):
 cu=bpy.data.curves.new(name,'CURVE');cu.dimensions='3D';cu.resolution_u=16;cu.bevel_depth=r;cu.bevel_resolution=5;cu.use_fill_caps=True;s=cu.splines.new('BEZIER');s.bezier_points.add(len(pts)-1)
 for i,(p,co) in enumerate(zip(s.bezier_points,pts)):
  p.co=co;p.handle_left_type='AUTO';p.handle_right_type='AUTO';p.radius=(radii[i] if radii else 1)
 s.use_cyclic_u=cyclic;o=bpy.data.objects.new(name,cu);model.objects.link(o);cu.materials.append(m);return o
def polyextrude(name,xz,yfront,yback,m,bevel=0):
 n=len(xz);v=[(x,yfront,z) for x,z in xz]+[(x,yback,z) for x,z in xz];faces=[]
 vectors=[Vector((x,z,0)) for x,z in xz];tris=tessellate_polygon([vectors]);lookup={tuple(v):i for i,v in enumerate(vectors)}
 for t in tris:
  ids=[p if isinstance(p,int) else lookup[tuple(p)] for p in t];faces.append(tuple(reversed(ids)));faces.append(tuple(i+n for i in ids))
 faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 me=bpy.data.meshes.new(name);me.from_pydata(v,[],faces);me.update();o=bpy.data.objects.new(name,me);model.objects.link(o)
 if m:me.materials.append(m)
 # Consistent closed-surface normals before boolean/bevel.
 bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o;bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT')
 if bevel:
  b=o.modifiers.new('soft sculpted edges','BEVEL');b.width=bevel;b.segments=4
  bpy.ops.object.modifier_apply(modifier=b.name)
 for p in me.polygons:p.use_smooth=True
 return o
# Body and limbs: neutral shape-review pose, no toilet and no animation.
body=ell('Torso • pear silhouette',(0,0,2.03),(.55,.39,.71),purple)
for s,label in [(-1,'L'),(1,'R')]:
 leg=ell('Leg.'+label,(s*.29,.015,.99),(.255,.265,.59),purple)
 foot=ell('Foot.'+label,(s*.30,-.095,.44),(.275,.33,.21),dark)
 arm=curve('Arm.'+label,[(s*.43,.015,2.5),(s*.59,-.015,2.19),(s*.77,-.025,1.84),(s*.86,-.055,1.62)],.18,purple,[1.18,1.05,.95,.92])
 hand=ell('Mitten.'+label,(s*.86,-.055,1.53),(.205,.21,.26),dark)
 # restrained toy-like paw crease
 curve('Mitten crease.'+label,[(s*.86-.095,-.25,1.51),(s*.86,-.268,1.46),(s*.86+.09,-.25,1.49)],.009,zipmat)
# Blend the torso and shoulders into one continuous mesh for shape review.
shoulders=[ell('Shoulder.'+label,(sgn*.43,.015,2.45),(.225,.21,.26),purple) for sgn,label in [(-1,'L'),(1,'R')]]
parts=[body]+shoulders+[bpy.data.objects['Arm.L'],bpy.data.objects['Arm.R']]
for ob in parts:
 bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
 if ob.type=='CURVE':bpy.ops.object.convert(target='MESH')
bpy.ops.object.select_all(action='DESELECT')
for ob in parts:ob.select_set(True)
bpy.context.view_layer.objects.active=body;bpy.ops.object.join()
rem=body.modifiers.new('Continuous torso and shoulders','REMESH');rem.mode='VOXEL';rem.voxel_size=.021;rem.use_smooth_shade=True;bpy.ops.object.modifier_apply(modifier=rem.name)
sm=body.modifiers.new('Smooth shoulder transitions','SMOOTH');sm.factor=.65;sm.iterations=5;bpy.ops.object.modifier_apply(modifier=sm.name)
sub=body.modifiers.new('Subdivided shape','SUBSURF');sub.levels=1
# Broad head; widen lower cheeks slightly without turning it into a kitten muzzle.
head=ell('Head • mouth cut into actual mesh',(0,0,3.60),(1.12,.69,.96),purple,128,96)
for v in head.data.vertices:
 z=v.co.z
 v.co.x*=1+.045*math.exp(-((z+.10)/.30)**2)
# Smoothed mouth outline, with raised smile corners and a very broad open grin.
ctrl=[(-1.00,3.73),(-.92,3.85),(-.72,3.82),(-.40,3.67),(0,3.63),(.40,3.67),(.72,3.82),(.92,3.85),(1.00,3.73),(.96,3.43),(.79,3.12),(.48,2.88),(0,2.77),(-.48,2.88),(-.79,3.12),(-.96,3.43)]
def catmull(points,n=8):
 arr=[]
 for i in range(len(points)):
  p0=Vector(points[(i-1)%len(points)]);p1=Vector(points[i]);p2=Vector(points[(i+1)%len(points)]);p3=Vector(points[(i+2)%len(points)])
  for j in range(n):
   t=j/n;v=.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t);arr.append(tuple(v))
 return arr
outline=catmull(ctrl)
cutter=polyextrude('TEMP • mouth subtraction',outline,-1.1,.30,None)
bpy.context.view_layer.objects.active=head;mod=head.modifiers.new('True hollow grin','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)
for p in head.data.polygons:p.use_smooth=True
# A curved, deep black lining inside the actual mouth, not a flat decal.
def fronty(x,z):return -.69*sqrt(max(.03,1-(x/1.13)**2-((z-3.6)/.96)**2))-.014
verts=[];N=len(outline)
for ring,f in enumerate([1,.80,.48,.12]):
 for x,z in outline:
  xx=x*f;zz=3.29+(z-3.29)*f
  yy=fronty(x,z) if ring==0 else [-9,-.015,.16,.22][ring]
  verts.append((xx,yy,zz))
faces=[]
for r in range(3):
 for i in range(N):faces.append((r*N+i,r*N+(i+1)%N,(r+1)*N+(i+1)%N,(r+1)*N+i))
faces.append(tuple(range(3*N,4*N)))
me=bpy.data.meshes.new('Mouth curved lining');me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new('Mouth • deep curved black interior',me);model.objects.link(o);me.materials.append(inside)
for p in me.polygons:p.use_smooth=True
sub=o.modifiers.new('Smooth cavity bowl','SUBSURF');sub.levels=2
curve('Smile rim • continuous sculpted lip',[(x,fronty(x,z)-.005,z) for x,z in outline],.045,purple,cyclic=True)
# Upright original-style ears, with distinct darker inset panels.
for s,label in [(-1,'L'),(1,'R')]:
 pts=[(s*.40,4.19),(s*.64,4.57),(s*.86,5.03),(s*1.01,4.72),(s*1.05,4.15)]
 polyextrude('Ear.'+label,pts,-.20,.25,purple,.105)
 innerpts=[(s*.57,4.26),(s*.71,4.62),(s*.85,4.84),(s*.94,4.59),(s*.96,4.25)]
 polyextrude('Ear inset.'+label,innerpts,-.239,-.18,dark,.055)
# Eyes stay black: tiny white pupils, no kitten irises or white sclera.
for s,label in [(-1,'L'),(1,'R')]:
 eye=ell('Eye.'+label,(s*.405,-.588,4.036),(.265,.142,.287),black)
 ell('Pupil.'+label,(s*.405,-.726,4.055),(.039,.018,.044),white,32,24)
# Rounded triangular toy nose.
polyextrude('Nose',catmull([(-.135,3.832),(.135,3.832),(.075,3.749),(0,3.718),(-.075,3.749)],5),-.763,-.64,black,.015)
# Signature tail. Editable Bezier curve, long, tapered and fully three-dimensional.
curve('Tail • editable long curling spline',[(0,.31,1.53),(.54,.56,1.22),(1.21,.55,.72),(1.76,.42,.64),(2.04,.30,1.03),(2.06,.23,1.77),(1.95,.16,2.42),(1.66,.10,2.73),(1.38,.055,2.62)],.145,purple,[1.05,1,1,.97,.94,.90,.85,.75,.35])
ell('Tail • rounded tip',(1.38,.055,2.62),(.052,.052,.052),purple,32,24)
# Recessed front zipper and individual small teeth.
curve('Zipper • dark tape',[(0,-.35,2.54),(0,-.395,2.20),(0,-.393,1.85),(0,-.30,1.47)],.034,zipmat)
for i in range(25):
 z=1.53+i*.037;yy=-.39*sqrt(max(.1,1-((z-2.03)/.71)**2))-.025
 bpy.ops.mesh.primitive_cube_add(size=1,location=((-.016 if i%2 else .016),yy,z));o=bpy.context.object;o.name='Zipper tooth %02d'%i;o.scale=(.026,.019,.015);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);finish(o,teeth);b=o.modifiers.new('round','BEVEL');b.width=.004;b.segments=2
# Actual concave crescent, open to the right, with thickness and bevel.
R=.27;r=.233;d=.145;xx=(R*R-r*r+d*d)/(2*d);zz=sqrt(R*R-xx*xx);a=math.atan2(zz,xx);b=math.atan2(-zz,xx-d)
moonpts=[]
for i in range(65):
 t=a+(2*pi-2*a)*i/64;moonpts.append((R*cos(t),2.39+R*sin(t)))
for i in range(65):
 t=b+(-2*pi-2*b)*i/64;moonpts.append((d+r*cos(t),2.39+r*sin(t)))
polyextrude('Pendant • solid gold crescent',moonpts,-.535,-.455,gold,.022)
# Pendant bail.
bpy.ops.mesh.primitive_torus_add(major_segments=40,minor_segments=12,location=(0,-.455,2.70),rotation=(pi/2,0,0),major_radius=.045,minor_radius=.014);finish(bpy.context.object,gold).name='Pendant • bail'
# Small central head seam, very restrained and separate for easy revision.
curve('Head • top seam',[(0,-.02,4.556),(0,-.28,4.49),(0,-.45,4.34)],.004,seammat)
# Group objects under one clear root, retaining every mesh/spline editable.
root=bpy.data.objects.new('CATNAP_ROOT • unrigged shape draft',None);model.objects.link(root)
for o in list(model.objects):
 if o!=root:o.parent=root
# Studio: neutral lighting for silhouette approval.
floor=mat('Studio neutral floor',(.19,.205,.23),.85)
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,.20));o=bpy.context.object;o.name='Studio floor';move(o,studio);o.data.materials.append(floor)
def aim(o,point):o.rotation_euler=(Vector(point)-o.location).to_track_quat('-Z','Y').to_euler()
def area(name,loc,power,size,color):
 da=bpy.data.lights.new(name,'AREA');da.energy=power;da.shape='DISK';da.size=size;da.color=color;o=bpy.data.objects.new(name,da);studio.objects.link(o);o.location=loc;aim(o,(0,0,2.6))
area('Key • large neutral softbox',(-3.8,-5,7),700,5,(1,.94,.88));area('Fill • frontal',(4,-4,4.6),500,4,(.90,.94,1));area('Separation',(2,3,6),800,4,(1,1,1))
world=bpy.data.worlds.new('Neutral studio') if not bpy.data.worlds else bpy.data.worlds[0];bpy.context.scene.world=world;world.use_nodes=True;world.node_tree.nodes.get('Background').inputs[0].default_value=(.16,.18,.22,1);world.node_tree.nodes.get('Background').inputs[1].default_value=.4
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.device='CPU';sc.cycles.samples=32;sc.cycles.use_denoising=True
sc.render.resolution_x=1000;sc.render.resolution_y=1200;sc.render.resolution_percentage=100;sc.view_settings.view_transform='AgX';sc.render.image_settings.file_format='PNG';sc.render.film_transparent=False
cams=[]
for name,loc,scale in [('Front',(0,-12,2.70),5.7),('Three-quarter',(7,-11,4.2),6.0),('Side',(12,0,2.7),5.7),('Back',(0,12,2.7),5.7)]:
 da=bpy.data.cameras.new(name);da.type='ORTHO';da.ortho_scale=scale;o=bpy.data.objects.new(name,da);studio.objects.link(o);o.location=loc;aim(o,(.30,0,2.62));cams.append(o)
sc.camera=cams[1]
# Embed the official reference inside the editable scene, but keep it out of exports/renders.
ref=bpy.data.images.load(ROOT+'/work/model-reference/official-catnap.png');ref.pack();ref.name='REFERENCE • official CatNap • source in README'
# Save original editable model; export only character objects.
bpy.ops.wm.save_as_mainfile(filepath=OUT+'/CatNap-shape-v01.blend')
bpy.ops.object.select_all(action='DESELECT')
for o in model.objects:o.select_set(True)
bpy.context.view_layer.objects.active=head
bpy.ops.export_scene.gltf(filepath=OUT+'/CatNap-shape-v01.glb',export_format='GLB',use_selection=True,export_apply=True,export_animations=False,export_cameras=False,export_lights=False)
for cam in cams:
 sc.camera=cam;sc.render.filepath=OUT+'/'+cam.name+'.png';bpy.ops.render.render(write_still=True)
print('CATNAP_MODEL_COMPLETE',flush=True)
