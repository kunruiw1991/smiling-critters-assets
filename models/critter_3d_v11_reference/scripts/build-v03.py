import bpy, math, json, os
from mathutils import Vector
from mathutils.geometry import tessellate_polygon
from math import sin,cos,pi,sqrt
ROOT='/Users/kunruiwang/Documents/Codex/2026-10-17/ni'
OUT=ROOT+'/outputs/CatNap-3D-v03'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
model=bpy.data.collections.new('CATNAP • shape review v03');bpy.context.scene.collection.children.link(model)
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
inside=mat('04 • mouth cavity • matte',(.0005,.0003,.001),1.0)
inside.node_tree.nodes.get('Principled BSDF').inputs['Specular IOR Level'].default_value=0
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
# Chubby plush proportions: short round torso, tucked limbs, no human waist/shoulders.
body=ell('Torso • round plush belly',(0,0,1.35),(.76,.59,.69),purple)
for v in body.data.vertices:
 f=v.co.z/.69;v.co.x*=1-.07*f;v.co.y*=1-.035*f
for sg,label in [(-1,'L'),(1,'R')]:
 ell('Leg.'+label+' • short tucked stub',(sg*.32,.025,.65),(.285,.30,.345),purple)
 ell('Foot.'+label+' • round cat paw',(sg*.34,-.17,.405),(.325,.365,.205),dark)
 curve('Arm.'+label,[(sg*.52,.015,1.66),(sg*.65,-.045,1.50),(sg*.775,-.105,1.33),(sg*.79,-.14,1.24)],.18,purple,[1.10,1.12,1.04,.96])
 ell('Paw.'+label+' • plump rounded mitten',(sg*.79,-.16,1.14),(.24,.255,.235),dark)
shoulders=[ell('Soft limb root.'+label,(sg*.54,.005,1.64),(.22,.23,.21),purple) for sg,label in [(-1,'L'),(1,'R')]]
parts=[body]+shoulders+[bpy.data.objects['Arm.L'],bpy.data.objects['Arm.R']]
for ob in parts:
 bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
 if ob.type=='CURVE':bpy.ops.object.convert(target='MESH')
bpy.ops.object.select_all(action='DESELECT')
for ob in parts:ob.select_set(True)
bpy.context.view_layer.objects.active=body;bpy.ops.object.join()
rem=body.modifiers.new('Round continuous plush body','REMESH');rem.mode='VOXEL';rem.voxel_size=.020;rem.use_smooth_shade=True;bpy.ops.object.modifier_apply(modifier=rem.name)
sm=body.modifiers.new('Soft rounded limb transitions','SMOOTH');sm.factor=.70;sm.iterations=7;bpy.ops.object.modifier_apply(modifier=sm.name)
sub=body.modifiers.new('Plush surface subdivision','SUBSURF');sub.levels=1
body_objects=set(o.name for o in model.objects)
# Reference-driven silhouette: compact crown, wide smile cheeks, tapered rounded chin.
profile=[(2.76,.012,.10),(2.80,.17,.20),(2.88,.36,.29),(3.02,.56,.40),(3.20,.77,.50),(3.42,.96,.58),(3.65,1.095,.625),(3.83,1.125,.63),(3.96,1.035,.60),(4.12,.88,.55),(4.28,.785,.47),(4.42,.62,.355),(4.50,.40,.235),(4.535,.20,.13),(4.54,.012,.025)]
def prof(z):
 for i in range(len(profile)-1):
  a,b=profile[i],profile[i+1]
  if z<=b[0]:
   t=max(0,min(1,(z-a[0])/(b[0]-a[0])));return a[1]*(1-t)+b[1]*t,a[2]*(1-t)+b[2]*t
 return profile[-1][1:]
# Catmull-Rom resampling keeps the loft curved, avoiding a stack-of-rings look.
ringdata=[]
for i in range(len(profile)-1):
 p0=Vector(profile[max(0,i-1)]);p1=Vector(profile[i]);p2=Vector(profile[i+1]);p3=Vector(profile[min(len(profile)-1,i+2)])
 for j in range(8):
  t=j/8;p=.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t);ringdata.append(tuple(p))
ringdata.append(profile[-1]);verts=[];n=128
for z,w,d in ringdata:
 for j in range(n):
  a=j/n*2*pi;verts.append((max(.007,w)*cos(a),max(.015,d)*sin(a)+.035,z))
faces=[]
for i in range(len(ringdata)-1):
 for j in range(n):faces.append((i*n+j,i*n+(j+1)%n,(i+1)*n+(j+1)%n,(i+1)*n+j))
faces.extend([tuple(reversed(range(n))),tuple(range((len(ringdata)-1)*n,len(ringdata)*n))])
me=bpy.data.meshes.new('CatNap reference silhouette loft');me.from_pydata(verts,[],faces);me.update();head=bpy.data.objects.new('Head • tapered cheeks and compact crown',me);model.objects.link(head);me.materials.append(purple)
for p in me.polygons:p.use_smooth=True
bpy.ops.object.select_all(action='DESELECT');head.select_set(True);bpy.context.view_layer.objects.active=head;bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT')
# Smoothed mouth outline, with raised smile corners and a very broad open grin.
ctrl=[(-1.055,3.79),(-1.00,3.885),(-.82,3.895),(-.43,3.72),(0,3.715),(.43,3.72),(.82,3.895),(1.00,3.885),(1.055,3.79),(.97,3.54),(.77,3.26),(.44,3.005),(0,2.865),(-.44,3.005),(-.77,3.26),(-.97,3.54)]
def catmull(points,n=8):
 arr=[]
 for i in range(len(points)):
  p0=Vector(points[(i-1)%len(points)]);p1=Vector(points[i]);p2=Vector(points[(i+1)%len(points)]);p3=Vector(points[(i+2)%len(points)])
  for j in range(n):
   t=j/n;v=.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t);arr.append(tuple(v))
 return arr
outline=catmull(ctrl)
cutter=polyextrude('TEMP • mouth subtraction',outline,-1.1,-.005,None)
bpy.context.view_layer.objects.active=head;mod=head.modifiers.new('True hollow grin','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)
head.data.materials.append(inside)
for face in head.data.polygons:
 if all(abs(head.data.vertices[i].co.y+.005)<.0001 for i in face.vertices):face.material_index=1
for p in head.data.polygons:p.use_smooth=True
# A curved, deep black lining inside the actual mouth, not a flat decal.
def fronty(x,z):
 w,d=prof(z);return .035-d*sqrt(max(.04,1-(x/max(.01,w))**2))-.014
verts=[];N=len(outline)
for ring,f in enumerate([1,.80,.48,.12]):
 for x,z in outline:
  xx=x*f;zz=3.35+(z-3.35)*f
  yy=fronty(x,z) if ring==0 else [-9,-.040,-.015,-.008][ring]
  verts.append((xx,yy,zz))
faces=[]
for r in range(3):
 for i in range(N):faces.append((r*N+i,r*N+(i+1)%N,(r+1)*N+(i+1)%N,(r+1)*N+i))
faces.append(tuple(range(3*N,4*N)))
me=bpy.data.meshes.new('Mouth curved lining');me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new('Mouth • deep curved black interior',me);model.objects.link(o);me.materials.append(inside)
for p in me.polygons:p.use_smooth=True
sub=o.modifiers.new('Smooth cavity bowl','SUBSURF');sub.levels=2
curve('Smile rim • continuous sculpted lip',[(x,fronty(x,z)-.005,z) for x,z in outline],.045,purple,cyclic=True)
# Broad outward-opening ears, with rounded tips and sculpted thin 3D shells.
ear_dark=mat('11 • recessed dark-purple inner ear',(.038,.006,.09),.90)
def ear_shell(name,outline,cx,cz,material):
 points=catmull(outline,7);N=len(points);verts=[]
 # Sculpted front dish: rounded purple rim and a genuinely recessed inner bowl.
 rings=[(.012,.095),(.30,.08),(.58,.025),(.70,-.045),(.75,-.115),(.86,-.145),(1.0,-.065)]
 for f,y in rings:
  for x,z in points:verts.append((cx+(x-cx)*f,y,cz+(z-cz)*f))
 back_start=len(verts)
 for f,y in [(1,.035),(.72,.155),(.32,.215),(.012,.23)]:
  for x,z in points:verts.append((cx+(x-cx)*f,y,cz+(z-cz)*f))
 faces=[];mi=[]
 for r in range(len(rings)-1):
  for j in range(N):faces.append((r*N+j,r*N+(j+1)%N,(r+1)*N+(j+1)%N,(r+1)*N+j));mi.append(1 if r<3 else 0)
 faces.append(tuple(reversed(range(N))));mi.append(1)
 off=(len(rings)-1)*N
 for j in range(N):faces.append((off+j,off+(j+1)%N,back_start+(j+1)%N,back_start+j));mi.append(0)
 for r in range(3):
  for j in range(N):faces.append((back_start+r*N+j,back_start+r*N+(j+1)%N,back_start+(r+1)*N+(j+1)%N,back_start+(r+1)*N+j));mi.append(0)
 faces.append(tuple(range(back_start+3*N,back_start+4*N)));mi.append(0)
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();ob=bpy.data.objects.new(name,me);model.objects.link(ob);me.materials.append(material);me.materials.append(ear_dark)
 for p,idx in zip(me.polygons,mi):p.use_smooth=True;p.material_index=idx
 bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob;bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT')
 su=ob.modifiers.new('Soft pointed triangular ear','SUBSURF');su.levels=2
 return ob
def inset_patch(name,patch,ear_outline,cx,cz):
 edge=catmull(ear_outline,6);outline=catmull(patch,6);N=len(outline);pcx=sum(p[0] for p in outline)/N;pcz=sum(p[1] for p in outline)/N
 def cross(a,b):return a[0]*b[1]-a[1]*b[0]
 def front_surface(x,z):
  ray=(x-cx,z-cz);hits=[]
  for i in range(len(edge)):
   a=edge[i];b=edge[(i+1)%len(edge)];seg=(b[0]-a[0],b[1]-a[1]);den=cross(ray,seg)
   if abs(den)<1e-10:continue
   ac=(a[0]-cx,a[1]-cz);t=cross(ac,seg)/den;u=cross(ac,ray)/den
   if t>0 and 0<=u<=1:hits.append(t)
  f=1/min(hits) if hits else .5
  return .025-.14*f*f-.018
 verts=[]
 for r in [.01,.25,.5,.75,1]:
  for x,z in outline:
   xx=pcx+(x-pcx)*r;zz=pcz+(z-pcz)*r;verts.append((xx,front_surface(xx,zz),zz))
 faces=[tuple(reversed(range(N)))]
 for i in range(4):
  for j in range(N):faces.append((i*N+j,i*N+(j+1)%N,(i+1)*N+(j+1)%N,(i+1)*N+j))
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();ob=bpy.data.objects.new(name,me);model.objects.link(ob);me.materials.append(dark)
 for f in me.polygons:f.use_smooth=True
 su=ob.modifiers.new('Conforming inner-ear surface','SUBSURF');su.levels=1
 return ob
for sg,label in [(-1,'L'),(1,'R')]:
 points=[(sg*.36,4.29),(sg*.48,4.57),(sg*.65,4.87),(sg*.75,5.035),(sg*.80,5.055),(sg*.85,4.98),(sg*.95,4.70),(sg*1.005,4.38),(sg*.99,4.16),(sg*.77,4.18),(sg*.56,4.24)]
 ear_shell('Ear.'+label+' • broad rounded shell',points,sg*.735,4.515,purple)
 # Lower inner-ear patch, framed by a generous purple outer rim.
 patch=[(sg*.52,4.24),(sg*.64,4.47),(sg*.78,4.62),(sg*.87,4.59),(sg*.91,4.39),(sg*.94,4.13),(sg*.76,4.13)]
 # Inner-ear bowl is part of the shell mesh; no separate flat inset.
 # A pair of short cheek flicks follows the reference silhouette.
 curve('Cheek tuft upper.'+label,[(sg*.91,fronty(sg*.91,3.95),3.95),(sg*1.10,-.20,3.955),(sg*1.215,-.11,3.88)],.033,purple,[1.3,1,.08])
 curve('Cheek tuft lower.'+label,[(sg*1.015,-.20,3.875),(sg*1.17,-.13,3.84),(sg*1.19,-.07,3.765)],.025,purple,[1.2,1,.08])
# Larger oval pupils, like the supplied design; eyes sit within the narrowed forehead.
for sg,label in [(-1,'L'),(1,'R')]:
 eye=ell('Eye.'+label,(sg*.365,-.523,4.045),(.282,.117,.340),black)
 eye.rotation_euler[1]=sg*math.radians(-10)
 ell('Pupil.'+label,(sg*.365,-.638,4.055),(.098,.019,.137),white,48,32)
# Rounded triangular toy nose.
polyextrude('Nose',catmull([(-.135,3.832),(.135,3.832),(.075,3.749),(0,3.718),(-.075,3.749)],5),-.708,-.59,black,.015)
for ob in model.objects:
 if ob.name not in body_objects:ob.location.z-=.73
# Signature tail. Editable Bezier curve, long, tapered and fully three-dimensional.
curve('Tail • editable long curling spline',[(0,.47,1.10),(.55,.63,.93),(1.16,.58,.56),(1.63,.43,.50),(1.88,.27,.85),(1.93,.17,1.49),(1.82,.10,2.05),(1.56,.03,2.31),(1.30,-.01,2.19)],.16,purple,[1.05,1,1,.97,.94,.90,.85,.75,.35])
ell('Tail • rounded tip',(1.30,-.01,2.19),(.057,.057,.057),purple,32,24)
# Recessed front zipper and individual small teeth.
curve('Zipper • dark tape',[(0,-.40,1.86),(0,-.575,1.55),(0,-.60,1.20),(0,-.425,.89)],.026,zipmat)
for i in range(25):
 z=.94+i*.036;yy=-.59*sqrt(max(.1,1-((z-1.35)/.69)**2))-.025
 bpy.ops.mesh.primitive_cube_add(size=1,location=((-.016 if i%2 else .016),yy,z));o=bpy.context.object;o.name='Zipper tooth %02d'%i;o.scale=(.026,.019,.015);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);finish(o,teeth);b=o.modifiers.new('round','BEVEL');b.width=.004;b.segments=2
# Actual concave crescent, open to the right, with thickness and bevel.
R=.27;r=.233;d=.145;xx=(R*R-r*r+d*d)/(2*d);zz=sqrt(R*R-xx*xx);a=math.atan2(zz,xx);b=math.atan2(-zz,xx-d)
moonpts=[]
for i in range(65):
 t=a+(2*pi-2*a)*i/64;moonpts.append((R*cos(t),1.58+R*sin(t)))
for i in range(65):
 t=b+(-2*pi-2*b)*i/64;moonpts.append((d+r*cos(t),1.58+r*sin(t)))
polyextrude('Pendant • solid gold crescent',moonpts,-.685,-.605,gold,.022)
# Pendant bail.
bpy.ops.mesh.primitive_torus_add(major_segments=40,minor_segments=12,location=(0,-.605,1.89),rotation=(pi/2,0,0),major_radius=.045,minor_radius=.014);finish(bpy.context.object,gold).name='Pendant • bail'
curve('Pendant • short attachment',[(0,-.39,1.88),(0,-.49,1.91),(0,-.605,1.89)],.013,gold)
tongue=mat('10 • tongue',(.92,.16,.24),.65)
for sg in [-1,1]:ell('Tongue lobe '+str(sg),(sg*.075,-.20,2.265),(.115,.065,.040),tongue,48,24)
ell('Neck • joins head and torso',(0,.02,2.04),(.20,.22,.13),purple)
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
for name,loc,scale in [('Front',(0,-12,2.38),4.85),('Three-quarter',(7,-11,3.5),5.1),('Side',(12,0,2.38),4.85),('Back',(0,12,2.38),4.85)]:
 da=bpy.data.cameras.new(name);da.type='ORTHO';da.ortho_scale=scale;o=bpy.data.objects.new(name,da);studio.objects.link(o);o.location=loc;aim(o,(.25,0,2.25));cams.append(o)
sc.camera=cams[1]
# Embed the official reference inside the editable scene, but keep it out of exports/renders.
ref=bpy.data.images.load(ROOT+'/work/model-reference/official-catnap.png');ref.pack();ref.name='REFERENCE • official CatNap • source in README'
ref2=bpy.data.images.load(ROOT+'/work/model-reference/teepublic-catnap.jpg');ref2.pack();ref2.name='REFERENCE • user supplied TeePublic design'
ref3=bpy.data.images.load(ROOT+'/work/model-reference/official-catnap-icon.png');ref3.pack();ref3.name='REFERENCE • official CatNap page icon'
# Save original editable model; export only character objects.
bpy.ops.wm.save_as_mainfile(filepath=OUT+'/CatNap-shape-v03.blend')
bpy.ops.object.select_all(action='DESELECT')
for o in model.objects:o.select_set(True)
bpy.context.view_layer.objects.active=head
bpy.ops.export_scene.gltf(filepath=OUT+'/CatNap-shape-v03.glb',export_format='GLB',use_selection=True,export_apply=True,export_animations=False,export_cameras=False,export_lights=False)
for cam in cams:
 sc.camera=cam;sc.render.filepath=OUT+'/'+cam.name+'.png';bpy.ops.render.render(write_still=True)
# Head close-up for this round of review.
da=bpy.data.cameras.new('Head close-up');da.type='ORTHO';da.ortho_scale=2.95;cam=bpy.data.objects.new('Head close-up',da);studio.objects.link(cam);cam.location=(0,-12,3.22);aim(cam,(0,0,3.20));sc.camera=cam;sc.render.resolution_x=1200;sc.render.resolution_y=1100;sc.render.filepath=OUT+'/Head-front.png';bpy.ops.render.render(write_still=True)
cam.location=(6,-12,4.07);aim(cam,(0,0,3.20));sc.render.filepath=OUT+'/Head-three-quarter.png';bpy.ops.render.render(write_still=True)
sc.camera=cams[1];sc.render.resolution_x=1000;sc.render.resolution_y=1200;bpy.ops.wm.save_as_mainfile(filepath=OUT+'/CatNap-shape-v03.blend')
print('CATNAP_MODEL_COMPLETE',flush=True)
