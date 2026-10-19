from pathlib import Path
import ast
s=Path('work/catnap-model/build-v07.py').read_text();tree=ast.parse(s)
names=['move','mat','finish','ell','curve','polyextrude','plush_loft','aim']
helpers='\n'.join(ast.get_source_segment(s,n) for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names)
header='''import bpy,math,os,json,hashlib,struct
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import tessellate_polygon
from math import sin,cos,pi,sqrt
ROOT='/Users/kunruiwang/Documents/Codex/2026-10-17/ni'
OUT=ROOT+'/outputs/CatNap-3D-v08';os.makedirs(OUT,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=ROOT+'/outputs/CatNap-3D-v07/CatNap-shape-v07.blend')
model=bpy.data.collections['CATNAP • shape review v07'];model.name='CATNAP • shape review v08'
studio=bpy.data.collections['STUDIO • cameras and lighting']
purple=bpy.data.materials['01 • CatNap purple • temporary surface'];dark=bpy.data.materials['02 • paws and inner ears']
root=bpy.data.objects['CATNAP_ROOT • unrigged shape draft']
head=next(o for o in model.objects if o.name.startswith('Head •'))
def mesh_hash(ob):
 h=hashlib.sha256()
 for v in ob.data.vertices:h.update(struct.pack('<3f',*v.co))
 for p in ob.data.polygons:h.update(struct.pack('<'+str(len(p.vertices))+'I',*p.vertices))
 return h.hexdigest()
head_before=mesh_hash(head)
'''
body='''
sc=bpy.context.scene;sc.cycles.samples=32;sc.render.film_transparent=True;sc.render.image_settings.color_mode='RGBA'
# Body cameras share a fixed scale so shape differences remain visible.
def camera(name,loc,target,scale):
 da=bpy.data.cameras.new(name);da.type='ORTHO';da.ortho_scale=scale;o=bpy.data.objects.new(name,da);studio.objects.link(o);o.location=loc;aim(o,target);return o
bodycam=camera('Body-front',(0,-12,1.05),(0,0,1.05),4.1)
sc.camera=bodycam;sc.render.resolution_x=1200;sc.render.resolution_y=1200
oldpath=ROOT+'/work/catnap-model/v07-body-front.png'
if not os.path.exists(oldpath):
 sc.render.filepath=oldpath;bpy.ops.render.render(write_still=True)
# Remove only body components; all approved head objects remain untouched.
for ob in list(model.objects):
 if ob.name.startswith(('Torso •','Leg.','Arm.','Tail •')):bpy.data.objects.remove(ob,do_unlink=True)
parts=[]
body_profile=[(1.37,.08,.11),(1.405,.37,.25),(1.48,.51,.35),(1.68,.58,.41),(1.90,.60,.43),(2.10,.565,.415),(2.32,.48,.36),(2.50,.44,.31),(2.63,.35,.275),(2.73,.26,.24),(2.82,.16,.20),(2.85,.06,.12)]
body=plush_loft('Body • continuous plush shell',[(z,w,d,0,0) for z,w,d in body_profile],[purple]);parts.append(body)
for sg,label in [(-1,'L'),(1,'R')]:
 legp=[(.275,.045,.07,sg*.44,-.07),(.29,.16,.17,sg*.44,-.07),(.34,.275,.25,sg*.44,-.05),(.45,.345,.29,sg*.44,-.02),(.65,.355,.295,sg*.445,.005),(.88,.32,.28,sg*.41,.02),(1.10,.285,.26,sg*.375,.025),(1.31,.25,.245,sg*.34,.025),(1.49,.23,.235,sg*.32,.025),(1.61,.15,.18,sg*.30,.025),(1.67,.035,.06,sg*.29,.025)]
 ob=plush_loft('Leg.'+label+' • softly rounded sole and smooth inner line',legp,[purple,dark]);parts.append(ob)
 for f in ob.data.polygons:
  c=f.center
  if c.z<.55+.08*((abs(c.x)-.44)/.35)**2:f.material_index=1
 armp=[(1.375,.04,.06,sg*.97,-.065),(1.40,.12,.125,sg*.98,-.065),(1.47,.195,.175,sg*.99,-.065),(1.58,.225,.20,sg*.965,-.055),(1.74,.205,.195,sg*.87,-.035),(1.96,.18,.185,sg*.735,-.005),(2.18,.175,.18,sg*.60,.015),(2.39,.19,.185,sg*.46,.025),(2.55,.18,.185,sg*.35,.025),(2.68,.125,.14,sg*.26,.025),(2.75,.025,.045,sg*.20,.025)]
 ob=plush_loft('Arm.'+label+' • curved mitten and seated shoulder',armp,[purple,dark]);parts.append(ob)
 for f in ob.data.polygons:
  c=f.center
  if c.z-.60*(abs(c.x)-.90)<1.74:f.material_index=1
# Smooth three-dimensional S sweep. The terminal hemisphere is part of the same mesh.
controls=[((0,.36,1.60),(-.65,.40,1.50),(-1.28,.25,.85),(-1.32,.08,.34)),((-1.32,.08,.34),(-1.36,-.09,-.17),(-.93,-.31,-.24),(-.22,-.30,-.20)),((-.22,-.30,-.20),(.49,-.29,-.16),(1.28,-.25,-.34),(1.10,-.25,-.62))]
centers=[];tangents=[];radii=[]
for seg,(a,b,c,d) in enumerate(controls):
 a,b,c,d=map(Vector,(a,b,c,d))
 for j in range(40+(seg==2)):
  t=j/40;centers.append((1-t)**3*a+3*(1-t)**2*t*b+3*(1-t)*t*t*c+t**3*d)
  tangents.append((3*(1-t)**2*(b-a)+6*(1-t)*t*(c-b)+3*t*t*(d-c)).normalized())
  u=(seg+t)/3;radii.append(.15-.03*u*u)
end=centers[-1].copy();tan=tangents[-1];rad=radii[-1]
for j in range(1,9):
 a=(pi/2)*j/9;centers.append(end+tan*rad*sin(a));tangents.append(tan);radii.append(rad*cos(a))
N=40;vs=[]
for co,tan,r in zip(centers,tangents,radii):
 normal=(Vector((0,1,0))-tan*tan.y).normalized();bi=tan.cross(normal).normalized()
 for j in range(N):vs.append(tuple(co+r*(normal*cos(2*pi*j/N)+bi*sin(2*pi*j/N))))
fs=[]
for k in range(len(centers)-1):
 for j in range(N):fs.append((k*N+j,k*N+(j+1)%N,(k+1)*N+(j+1)%N,(k+1)*N+j))
vs.append(tuple(end+tan*rad));tip=len(vs)-1
for j in range(N):fs.append(((len(centers)-1)*N+j,(len(centers)-1)*N+(j+1)%N,tip))
fs.append(tuple(reversed(range(N))))
me=bpy.data.meshes.new('Flowing tail with integrated round tip');me.from_pydata(vs,[],fs);me.update();ob=bpy.data.objects.new('Tail • continuous swept plush form',me);model.objects.link(ob);me.materials.append(purple)
for f in me.polygons:f.use_smooth=True
bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob;bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT');parts.append(ob)
# Transfer cuff colors after a real union of shoulders, hips and tail root.
source_surfaces=[]
for ob in parts:
 source_surfaces.append((BVHTree.FromPolygons([v.co for v in ob.data.vertices],[list(f.vertices) for f in ob.data.polygons]),[f.material_index for f in ob.data.polygons]))
bpy.ops.object.select_all(action='DESELECT')
for ob in parts:ob.select_set(True)
bpy.context.view_layer.objects.active=body;bpy.ops.object.join()
mo=body.modifiers.new('Joined shoulders hips and tail base','REMESH');mo.mode='VOXEL';mo.voxel_size=.010;mo.use_smooth_shade=True;bpy.ops.object.modifier_apply(modifier=mo.name)
mo=body.modifiers.new('Soft cloth transitions','SMOOTH');mo.factor=.62;mo.iterations=10;bpy.ops.object.modifier_apply(modifier=mo.name)
body.data.materials.clear();body.data.materials.append(purple);body.data.materials.append(dark)
for f in body.data.polygons:
 f.use_smooth=True;c=f.center;best=(100,0)
 for tree,indices in source_surfaces:
  co,no,idx,dist=tree.find_nearest(c)
  if idx is not None and dist<best[0]:best=(dist,indices[idx])
 f.material_index=best[1]
body.parent=root
# Fit zipper tape/teeth to the revised torso; pendant stays suspended in front.
btree=BVHTree.FromPolygons([v.co for v in body.data.vertices],[list(f.vertices) for f in body.data.polygons])
def torso_y(z):
 hit,no,idx,dist=btree.ray_cast(Vector((0,-2,z)),Vector((0,1,0)),4);return hit.y if hit else -.3
for ob in model.objects:
 if ob.name.startswith('Zipper •'):
  for sp in ob.data.splines:
   for bp in sp.bezier_points:bp.co.y=torso_y(bp.co.z)-.015
 elif ob.name.startswith('Zipper tooth'):ob.location.y=torso_y(ob.location.z)-.021
assert mesh_hash(head)==head_before,'Approved head changed'
open(OUT+'/head-preservation.json','w').write(json.dumps({'source':'v07','unchanged_head_mesh':True,'sha256':head_before},indent=2))
cams=[bpy.data.objects['Front'],bpy.data.objects['Three-quarter'],bpy.data.objects['Back'],bodycam,camera('Body-three-quarter',(6,-12,2.5),(0,0,1.05),4.1)]
sc.render.resolution_x=1200;sc.render.resolution_y=1200;sc.camera=bodycam
bpy.ops.wm.save_as_mainfile(filepath=OUT+'/CatNap-shape-v08.blend')
if os.environ.get('CATNAP_PREVIEW')=='1':
 sc.cycles.samples=16;sc.render.resolution_x=800;sc.render.resolution_y=800
 for cam in [bodycam,cams[-1]]:
  sc.camera=cam;sc.render.filepath=ROOT+'/work/catnap-model/v08-preview-'+cam.name+'.png';bpy.ops.render.render(write_still=True)
 print('PREVIEW_COMPLETE',flush=True);raise SystemExit(0)
bpy.ops.object.select_all(action='DESELECT')
for ob in model.objects:ob.select_set(True)
bpy.context.view_layer.objects.active=body
bpy.ops.export_scene.gltf(filepath=OUT+'/CatNap-shape-v08.glb',export_format='GLB',use_selection=True,export_apply=True,export_animations=False,export_cameras=False,export_lights=False)
sc.cycles.samples=40
for cam in cams:
 sc.camera=cam
 sc.render.resolution_x=1200;sc.render.resolution_y=1500 if cam in cams[:3] else 1200
 sc.render.filepath=OUT+'/'+cam.name+'.png';bpy.ops.render.render(write_still=True)
sc.camera=cams[1];bpy.ops.wm.save_as_mainfile(filepath=OUT+'/CatNap-shape-v08.blend');print('BODY_REVISION_COMPLETE',flush=True)
'''
Path('work/catnap-model/build-v08.py').write_text(header+helpers+'\n'+body)
s=Path('work/catnap-model/verify-v07.py').read_text().replace('v07','v08');s=s.replace("bm.free()", "bm.free()\nbody=next(o for o in mesh if o.name.startswith('Body •'))\nbm=bmesh.new();bm.from_mesh(body.data);stat['body_nonmanifold_edges']=sum(not e.is_manifold for e in bm.edges);bm.free()")
Path('work/catnap-model/verify-v08.py').write_text(s)
