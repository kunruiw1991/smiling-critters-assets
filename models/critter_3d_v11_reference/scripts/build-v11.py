import bpy,math,os,json,bmesh,random
from math import sin, cos, pi, sqrt
from mathutils import Vector
from mathutils.bvhtree import BVHTree
R='/Users/kunruiwang/Documents/Codex/2026-10-17/ni';O=R+'/outputs/CatNap-Final-v11';os.makedirs(O,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=R+'/outputs/CatNap-3D-v10/CatNap-shape-v10.blend')
col=bpy.data.collections['CATNAP • shape review v10'];col.name='CATNAP • shape review v11';root=bpy.data.objects['CATNAP_ROOT • unrigged shape draft'];sc=bpy.context.scene
body=next(o for o in col.objects if o.name.startswith('Body •'));head=next(o for o in col.objects if o.name.startswith('Head •'));lining=bpy.data.objects['Mouth • smoothly recessed lining']
def tree(o):return BVHTree.FromPolygons([v.co for v in o.data.vertices],[list(p.vertices) for p in o.data.polygons])
bt,ht,mt=tree(body),tree(head),tree(lining)
for o in list(col.objects):
 if o.name.startswith(('Forehead •','Forehead stitch')):bpy.data.objects.remove(o,do_unlink=True)
def material(name,color):
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=.87;p.inputs['Sheen Weight'].default_value=.3;return m
thread=material('Stitch • warm lavender cotton',(.52,.48,.57));groove=material('Stitch • recessed purple join',(.058,.021,.095));mouththread=material('Stitch • mouth muted thread',(.17,.15,.20))
# Fine isotropic textile microrelief, kept in object coordinates for consistent scale.
for name in ['01 • CatNap purple • temporary surface','02 • paws and inner ears']:
 m=bpy.data.materials[name];nt=m.node_tree;p=nt.nodes.get('Principled BSDF');p.inputs['Roughness'].default_value=.84;p.inputs['Sheen Weight'].default_value=.28
 tex=nt.nodes.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=235;tex.inputs['Detail'].default_value=2;coord=nt.nodes.new('ShaderNodeTexCoord');nt.links.new(coord.outputs['Object'],tex.inputs['Vector']);bu=nt.nodes.new('ShaderNodeBump');bu.inputs['Strength'].default_value=.32;bu.inputs['Distance'].default_value=.0035;nt.links.new(tex.outputs['Fac'],bu.inputs['Height']);nt.links.new(bu.outputs['Normal'],p.inputs['Normal'])
def curve(name,paths,r,mat):
 cu=bpy.data.curves.new(name,'CURVE');cu.dimensions='3D';cu.resolution_u=2;cu.bevel_depth=r;cu.bevel_resolution=3;cu.use_fill_caps=True
 for pts in paths:
  sp=cu.splines.new('POLY');sp.points.add(len(pts)-1)
  for p,co in zip(sp.points,pts):p.co=(*co,1)
 o=bpy.data.objects.new(name,cu);col.objects.link(o);o.parent=root;cu.materials.append(mat);return o
counts={}
def seam(name,points,bvh,closed=False,spacing=.032,mat=thread):
 pts=[Vector(p) for p in points]
 if closed:pts.append(pts[0])
 # Arc-length samples give uniform stitch spacing on all curves.
 samples=[];walk=0;nextd=0
 for a,b in zip(pts,pts[1:]):
  le=(b-a).length
  if le<1e-8:continue
  while nextd<=walk+le:
   p=a+(b-a)*((nextd-walk)/le);q,n,_,_=bvh.find_nearest(p);samples.append((q,n));nextd+=spacing
  walk+=le
 if len(samples)<3:return
 seampts=[p+n*.0003 for p,n in samples]
 if closed:seampts.append(seampts[0])
 curve('Seam • '+name,[seampts],.0018,groove)
 paths=[]
 for i,(p,n) in enumerate(samples):
  t=(samples[min(i+1,len(samples)-1)][0]-samples[max(0,i-1)][0]).normalized();side=n.cross(t).normalized();pts=[]
  for j in range(7):
   u=j/6;co=p+t*((u-.5)*.014)+side*((u-.5)*.010);q,nn,_,_=bvh.find_nearest(co);pts.append(q+nn*(-.0006+.0038*math.sin(math.pi*u)))
  paths.append(pts)
 curve('Stitches • '+name,paths,.0022,mat);counts[name]=len(paths)
def frontpoints(xz,bvh):
 arr=[]
 for x,z in xz:
  q,n,_,_=bvh.ray_cast(Vector((x,-3,z)),Vector((0,1,0)),6)
  if q is not None:arr.append(q)
 return arr
# Ordered color-boundary loops follow the actual cuffs and ear panel joins.
def boundaries(ob,bvh,label):
 bm=bmesh.new();bm.from_mesh(ob.data);bm.verts.ensure_lookup_table();adj={}
 for e in bm.edges:
  if len(e.link_faces)==2 and e.link_faces[0].material_index!=e.link_faces[1].material_index:
   a,b=[v.index for v in e.verts];adj.setdefault(a,[]).append(b);adj.setdefault(b,[]).append(a)
 seen=set();num=0
 for start in adj:
  if start in seen:continue
  path=[];cur=start;prev=-1
  while cur not in seen:
   seen.add(cur);path.append(bm.verts[cur].co.copy());nxt=[x for x in adj[cur] if x!=prev and x not in seen]
   if not nxt:break
   prev,cur=cur,nxt[0]
  if len(path)<35:continue
  for _ in range(6):path=[(path[i-1]+2*p+path[(i+1)%len(path)])/4 for i,p in enumerate(path)]
  num+=1;seam(label+str(num),path,bvh,True)
 bm.free()
boundaries(body,bt,'Cuff ');boundaries(head,ht,'Ear panel ')
seam('Forehead',frontpoints([(0,4.59-i*.008) for i in range(66)],ht),ht,spacing=.029)
seam('Chin',frontpoints([(0,2.76+i*.004) for i in range(19)],ht),ht,spacing=.028)
for lo,hi in [(2.86,3.055),(3.52,3.94)]:seam('Mouth lining '+str(lo),frontpoints([(0,lo+i*(hi-lo)/80) for i in range(81)],mt),mt,spacing=.033,mat=mouththread)
# Tail centreline uses exactly the accepted v09 spline.
source=open(R+'/work/catnap-model/build-v09.py').read();code=source[source.index('knots=list(map(Vector'):source.index('N=40;vs=[]')];exec(code,globals())
tail=[]
for co,tan,rad in zip(centers,tangents,radii):
 q,n,_,_=bt.find_nearest(co+Vector((0,-rad,0)));tail.append(q)
seam('Tail longitudinal',tail[12:],bt,spacing=.037)
# Underarm and inner-leg cloth joins, restrained darker seams rather than large white trim.
for sg in [-1,1]:
 seam('Inner leg '+str(sg),frontpoints([(sg*(.17+.045*math.sin(i/60*math.pi)),.48+i*.014) for i in range(61)],bt),bt,spacing=.039)
 seam('Shoulder '+str(sg),frontpoints([(sg*(.29+i*.0035),2.69-i*.006) for i in range(38)],bt),bt,spacing=.037,mat=mouththread)
# Lift existing zipper teeth just above the fitted tape.
for o in col.objects:
 if o.name.startswith('Zipper tooth'):o.location.y-=.022
# Rear construction seam, projected on the shell back.
arr=[]
for i in range(100):
 z=1.46+i*.011;q,n,_,_=bt.ray_cast(Vector((0,3,z)),Vector((0,-1,0)),6)
 if q is not None:arr.append(q)
seam('Back body',arr,bt,spacing=.036,mat=mouththread)
open(O+'/stitch-details.json','w').write(json.dumps({'stitch_counts':counts,'total_stitches':sum(counts.values()),'method':'surface-projected individual cotton thread arcs; preserved base geometry'},indent=2))
# Export all stitch curves as real mesh in GLB/USDZ, retaining editable curves in .blend.
sc.camera=bpy.data.objects['Front'];sc.render.resolution_x=1600;sc.render.resolution_y=2000;sc.cycles.samples=48
bpy.ops.wm.save_as_mainfile(filepath=O+'/CatNap-Final-v11.blend')
def camera(name,loc,target,scale):
 da=bpy.data.cameras.new(name);da.type='ORTHO';da.ortho_scale=scale;o=bpy.data.objects.new(name,da);bpy.data.collections['STUDIO • cameras and lighting'].objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();return o
close=camera('Stitch-detail',(0,-12,1.65),(0,0,1.65),2.5)
for cam in [bpy.data.objects['Front'],bpy.data.objects['Three-quarter'],bpy.data.objects['Back'],close]:
 sc.camera=cam;sc.render.resolution_x=1400;sc.render.resolution_y=1750 if cam!=close else 1400;sc.render.filepath=O+'/'+cam.name+'.png';bpy.ops.render.render(write_still=True)
bpy.ops.object.select_all(action='DESELECT')
for o in col.objects:
 if o.type=='CURVE':o.select_set(True);bpy.context.view_layer.objects.active=o
bpy.ops.object.convert(target='MESH')
bpy.ops.object.select_all(action='DESELECT')
for o in col.objects:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=O+'/CatNap-Final-v11.glb',export_format='GLB',use_selection=True,export_apply=True,export_animations=False,export_cameras=False,export_lights=False)
bpy.ops.wm.usd_export(filepath=O+'/CatNap-Final-v11.usdz',selected_objects_only=True,export_cameras=False,export_lights=False,export_animation=False,export_materials=True)
print('FINAL_MODEL_COMPLETE',counts,flush=True)
