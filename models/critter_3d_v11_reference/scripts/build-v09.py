import bpy,math,os,json,hashlib,struct
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import tessellate_polygon
from math import sin,cos,pi,sqrt
ROOT='/Users/kunruiwang/Documents/Codex/2026-10-17/ni'
OUT=ROOT+'/outputs/CatNap-3D-v09';os.makedirs(OUT,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=ROOT+'/outputs/CatNap-3D-v07/CatNap-shape-v07.blend')
model=bpy.data.collections['CATNAP • shape review v07'];model.name='CATNAP • shape review v09'
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
def plush_loft(name,profile,mats,cuff=None,N=96):
 rows=[]
 for i in range(len(profile)-1):
  p0=Vector(profile[max(0,i-1)]);p1=Vector(profile[i]);p2=Vector(profile[i+1]);p3=Vector(profile[min(len(profile)-1,i+2)])
  for j in range(7):
   t=j/7;rows.append(tuple(.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t)))
 rows.append(profile[-1]);v=[]
 for z,w,d,cx,cy in rows:
  for k in range(N):
   t=k/N*2*pi;v.append((cx+max(.006,w)*cos(t),cy+max(.006,d)*sin(t),z))
 faces=[];bands=[]
 for r in range(len(rows)-1):
  for k in range(N):faces.append((r*N+k,r*N+(k+1)%N,(r+1)*N+(k+1)%N,(r+1)*N+k));bands.append(1 if cuff is not None and (rows[r][0]+rows[r+1][0])*.5<cuff else 0)
 faces.extend([tuple(reversed(range(N))),tuple(range((len(rows)-1)*N,len(rows)*N))]);bands.extend([1 if cuff is not None else 0,0])
 me=bpy.data.meshes.new(name);me.from_pydata(v,[],faces);me.update();ob=bpy.data.objects.new(name,me);model.objects.link(ob)
 for m in mats:me.materials.append(m)
 for p,idx in zip(me.polygons,bands):p.use_smooth=True;p.material_index=idx
 bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob;bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT')
 return ob
def aim(o,point):o.rotation_euler=(Vector(point)-o.location).to_track_quat('-Z','Y').to_euler()

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
 legp=[(.275,.045,.07,sg*.44,-.07),(.29,.10,.115,sg*.44,-.07),(.34,.225,.22,sg*.44,-.05),(.45,.33,.28,sg*.44,-.02),(.65,.355,.295,sg*.445,.005),(.88,.32,.28,sg*.41,.02),(1.10,.285,.26,sg*.375,.025),(1.31,.25,.245,sg*.34,.025),(1.49,.23,.235,sg*.32,.025),(1.61,.15,.18,sg*.30,.025),(1.67,.035,.06,sg*.29,.025)]
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
# Clamped cubic spline with continuous second derivatives.
knots=list(map(Vector,[(0,.15,1.62),(-.90,.29,1.08),(-1.32,.08,.34),(-1.05,-.22,-.10),(-.22,-.30,-.20),(.60,-.28,-.27),(1.10,-.25,-.59)]))
h=[(knots[i+1]-knots[i]).length for i in range(len(knots)-1)];K=len(knots)
lo=[0.0]*K;diag=[0.0]*K;up=[0.0]*K;rhs=[Vector((0,0,0)) for _ in range(K)]
d0=Vector((-.65,.20,-.10)).normalized();dn=Vector((-.02,0,-.29)).normalized()
diag[0]=2*h[0];up[0]=h[0];rhs[0]=6*((knots[1]-knots[0])/h[0]-d0)
for i in range(1,K-1):
 lo[i]=h[i-1];diag[i]=2*(h[i-1]+h[i]);up[i]=h[i];rhs[i]=6*((knots[i+1]-knots[i])/h[i]-(knots[i]-knots[i-1])/h[i-1])
lo[-1]=h[-1];diag[-1]=2*h[-1];rhs[-1]=6*(dn-(knots[-1]-knots[-2])/h[-1])
for i in range(1,K):
 w=lo[i]/diag[i-1];diag[i]-=w*up[i-1];rhs[i]-=w*rhs[i-1]
M=[Vector((0,0,0)) for _ in range(K)];M[-1]=rhs[-1]/diag[-1]
for i in range(K-2,-1,-1):M[i]=(rhs[i]-up[i]*M[i+1])/diag[i]
centers=[];tangents=[];radii=[];length=sum(h);walk=0
for i,H in enumerate(h):
 for j in range(24+(i==len(h)-1)):
  t=j/24;a=1-t;b=t
  co=a*knots[i]+b*knots[i+1]+((a*a*a-a)*M[i]+(b*b*b-b)*M[i+1])*(H*H/6)
  tangent=(knots[i+1]-knots[i])/H+((-3*a*a+1)*M[i]+(3*b*b-1)*M[i+1])*(H/6)
  centers.append(co);tangents.append(tangent.normalized());u=(walk+t*H)/length;taper=max(0,min(1,(u-.70)/.30));taper=taper*taper*(3-2*taper);radii.append((.15-.03*u*u)*(1-taper)+.165*taper)
 walk+=H
end=centers[-1].copy();tan=tangents[-1];rad=radii[-1]
for j in range(1,17):
 a=(pi/2)*j/17;centers.append(end+tan*rad*sin(a));tangents.append(tan);radii.append(rad*cos(a))
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
mo=body.modifiers.new('Joined shoulders hips and tail base','REMESH');mo.mode='VOXEL';mo.voxel_size=.008;mo.use_smooth_shade=True;bpy.ops.object.modifier_apply(modifier=mo.name)
mo=body.modifiers.new('Soft cloth transitions','SMOOTH');mo.factor=.62;mo.iterations=10;bpy.ops.object.modifier_apply(modifier=mo.name)
vg=body.vertex_groups.new(name='Shoulder transition')
for v in body.data.vertices:
 x,y,z=v.co;w=math.exp(-(((abs(x)-.37)/.26)**2+((z-2.53)/.23)**2))
 if w>.01:vg.add([v.index],w,'REPLACE')
mo=body.modifiers.new('Rounded shoulder insertion','SMOOTH');mo.vertex_group=vg.name;mo.factor=.65;mo.iterations=36;bpy.ops.object.modifier_apply(modifier=mo.name)
vg=body.vertex_groups.new(name='Tail root transition')
for v in body.data.vertices:
 x,y,z=v.co;w=math.exp(-(((x+.32)/.32)**2+((y-.27)/.27)**2+((z-1.52)/.26)**2))
 if w>.01:vg.add([v.index],w,'REPLACE')
mo=body.modifiers.new('Softly seated tail root','SMOOTH');mo.vertex_group=vg.name;mo.factor=.65;mo.iterations=36;bpy.ops.object.modifier_apply(modifier=mo.name)
body.data.materials.clear();body.data.materials.append(purple);body.data.materials.append(dark)
for f in body.data.polygons:
 f.use_smooth=True;c=f.center;best=(100,0)
 for part_index,(tree,indices) in enumerate(source_surfaces):
  co,no,idx,dist=tree.find_nearest(c)
  if idx is not None and dist<best[0]:best=(dist,part_index)
 f.material_index=0
 if best[1] in (2,4) and c.z-.60*(abs(c.x)-.90)<1.74:f.material_index=1
 if best[1] in (1,3) and c.z<.55+.08*((abs(c.x)-.44)/.35)**2:f.material_index=1
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
cams=[bpy.data.objects['Front'],bodycam,camera('Tail-tip',(0,-12,-.36),(.85,-.25,-.36),1.45),camera('Tail-tip-angle',(3,-8,.5),(.85,-.25,-.36),1.45)]
sc.render.resolution_x=1200;sc.render.resolution_y=1200;sc.camera=bodycam
bpy.ops.wm.save_as_mainfile(filepath=OUT+'/CatNap-shape-v09.blend')
if os.environ.get('CATNAP_PREVIEW')=='1':
 sc.cycles.samples=16;sc.render.resolution_x=800;sc.render.resolution_y=800
 for cam in [bodycam,cams[-1]]:
  sc.camera=cam;sc.render.filepath=ROOT+'/work/catnap-model/v09-preview-'+cam.name+'.png';bpy.ops.render.render(write_still=True)
 print('PREVIEW_COMPLETE',flush=True);raise SystemExit(0)
bpy.ops.object.select_all(action='DESELECT')
for ob in model.objects:ob.select_set(True)
bpy.context.view_layer.objects.active=body
bpy.ops.export_scene.gltf(filepath=OUT+'/CatNap-shape-v09.glb',export_format='GLB',use_selection=True,export_apply=True,export_animations=False,export_cameras=False,export_lights=False)
sc.cycles.samples=40
for cam in cams:
 sc.camera=cam
 sc.render.resolution_x=1200;sc.render.resolution_y=1500 if cam==cams[0] else 1200
 sc.render.filepath=OUT+'/'+cam.name+'.png';bpy.ops.render.render(write_still=True)
sc.camera=cams[1];bpy.ops.wm.save_as_mainfile(filepath=OUT+'/CatNap-shape-v09.blend');print('BODY_REVISION_COMPLETE',flush=True)
