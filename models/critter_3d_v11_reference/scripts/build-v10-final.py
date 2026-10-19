import bpy, math, os, json, hashlib, struct, bmesh
from mathutils import Vector
from mathutils.geometry import tessellate_polygon
R='/Users/kunruiwang/Documents/Codex/2026-10-17/ni'
O=R+'/outputs/CatNap-3D-v10';os.makedirs(O,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=R+'/outputs/CatNap-3D-v09/CatNap-shape-v09.blend')
col=bpy.data.collections['CATNAP • shape review v09'];col.name='CATNAP • shape review v10'
root=bpy.data.objects['CATNAP_ROOT • unrigged shape draft'];sc=bpy.context.scene
sc.render.resolution_x=1000;sc.render.resolution_y=1000;sc.cycles.samples=32

def digest(o):
 h=hashlib.sha256()
 for v in o.data.vertices:h.update(struct.pack('<3f',*v.co))
 return h.hexdigest()
keep={o.name:digest(o) for o in col.objects if o.type=='MESH' and not o.name.startswith('Pendant')}
def cam(name,loc,target,scale):
 data=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,data);bpy.data.collections['STUDIO • cameras and lighting'].objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();data.type='ORTHO';data.ortho_scale=scale;return o
front=cam('Pendant-front',(0,-12,2.35),(0,0,2.35),.95)
angle=cam('Pendant-angle',(4,-12,3.7),(0,-.45,2.35),1.03)
sc.camera=front
gold=bpy.data.materials['06 • crescent pendant']
for ob in list(col.objects):
 if ob.name.startswith('Pendant'):bpy.data.objects.remove(ob,do_unlink=True)
# Reference silhouette, clockwise around the outer arc then back along the inner arc.
points=[(815,673),(811,661),(792,647),(770,639),(747,636),(720,641),(697,655),(682,676),(676,701),(678,724),(686,746),(702,766),(724,781),(749,787),(772,784),(793,774),(809,759),(815,749),(808,749),(790,753),(772,751),(757,744),(747,732),(742,716),(743,700),(749,686),(760,676),(777,670),(795,669),(809,672)]
pts=[]
for i in range(len(points)):
 p0,p1,p2,p3=[Vector(points[k%len(points)]) for k in (i-1,i,i+1,i+2)]
 for j in range(6):
  t=j/6;p=.5*(2*p1+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t);pts.append(((p.x-750)/258,2.76+(595-p.y)/258))
n=len(pts);vec=[Vector((x,z,0)) for x,z in pts];lookup={tuple(v):i for i,v in enumerate(vec)}
faces=[]
for tri in tessellate_polygon([vec]):
 ids=[p if isinstance(p,int) else lookup[tuple(p)] for p in tri];faces += [tuple(reversed(ids)),tuple(i+n for i in ids)]
faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
me=bpy.data.meshes.new('Official crescent traced contour');me.from_pydata([(x,-.55,z) for x,z in pts]+[(x,-.45,z) for x,z in pts],[],faces);me.update()
o=bpy.data.objects.new('Pendant • broad rounded reference crescent',me);col.objects.link(o);o.parent=root;me.materials.append(gold)
bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bmesh.ops.dissolve_limit(bm,angle_limit=.001,verts=list(bm.verts),edges=list(bm.edges));bm.to_mesh(me);bm.free()
bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
be=o.modifiers.new('Rounded cast edges','BEVEL');be.width=.010;be.use_clamp_overlap=True;be.segments=5;be.limit_method='ANGLE';be.angle_limit=.45
bpy.ops.object.modifier_apply(modifier=be.name)
for p in o.data.polygons:p.use_smooth=True
wn=o.modifiers.new('Weighted face normals','WEIGHTED_NORMAL');wn.keep_sharp=True;wn.weight=50;bpy.ops.object.modifier_apply(modifier=wn.name)
# Seated attachment above the taller moon.
bpy.ops.mesh.primitive_torus_add(major_segments=48,minor_segments=16,location=(0,-.46,2.652),rotation=(math.pi/2,0,0),major_radius=.041,minor_radius=.012)
b=bpy.context.object;b.name='Pendant • bail'
for c in list(b.users_collection):c.objects.unlink(b)
col.objects.link(b);b.parent=root;b.data.materials.append(gold)
for p in b.data.polygons:p.use_smooth=True
bpy.ops.mesh.primitive_uv_sphere_add(segments=40,ring_count=24,location=(0,-.491,2.619));b=bpy.context.object;b.name='Pendant • rounded attachment seat';b.scale=(.052,.036,.032);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
for c in list(b.users_collection):c.objects.unlink(b)
col.objects.link(b);b.parent=root;b.data.materials.append(gold)
for p in b.data.polygons:p.use_smooth=True
assert all(digest(bpy.data.objects[k])==v for k,v in keep.items())
bm=bmesh.new();bm.from_mesh(o.data);edges=sum(not e.is_manifold for e in bm.edges);bm.free()
assert edges==0
open(O+'/geometry-check.json','w').write(json.dumps({'unchanged_non_pendant_meshes':len(keep),'pendant_nonmanifold_edges':edges,'preserved_mesh_hashes':keep},indent=2))
sc.camera=bpy.data.objects['Front'];bpy.ops.wm.save_as_mainfile(filepath=O+'/CatNap-shape-v10.blend')
bpy.ops.object.select_all(action='DESELECT')
for ob in col.objects:ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=O+'/CatNap-shape-v10.glb',export_format='GLB',use_selection=True,export_apply=True,export_animations=False,export_cameras=False,export_lights=False)
for camera in [front,angle,bpy.data.objects['Front']]:
 sc.camera=camera;sc.render.resolution_y=1250 if camera.name=='Front' else 1000;sc.render.filepath=O+'/'+camera.name+'.png';bpy.ops.render.render(write_still=True)
print('MOON_REVISION_COMPLETE',flush=True)
