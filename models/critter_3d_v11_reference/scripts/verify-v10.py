import bpy,json,math,bmesh
root='/Users/kunruiwang/Documents/Codex/2026-10-17/ni/outputs/CatNap-3D-v10/'
bpy.ops.wm.open_mainfile(filepath=root+'CatNap-shape-v10.blend')
col=bpy.data.collections['CATNAP • shape review v10']
mesh=[o for o in col.objects if o.type=='MESH'];curves=[o for o in col.objects if o.type=='CURVE']
stat={'engine':bpy.app.version_string,'mesh_objects':len(mesh),'editable_curves':len(curves),'vertices':sum(len(o.data.vertices) for o in mesh),'faces':sum(len(o.data.polygons) for o in mesh),'has_armature':any(o.type=='ARMATURE' for o in col.objects),'has_animation':any(o.animation_data is not None for o in col.objects),'nonfinite_vertices':sum(not all(math.isfinite(x) for x in v.co) for o in mesh for v in o.data.vertices)}
head=next(o for o in mesh if o.name.startswith('Head • reference'))
bm=bmesh.new();bm.from_mesh(head.data);stat['head_nonmanifold_edges']=sum(not e.is_manifold for e in bm.edges);bm.free()
body=next(o for o in mesh if o.name.startswith('Body •'))
bm=bmesh.new();bm.from_mesh(body.data);stat['body_nonmanifold_edges']=sum(not e.is_manifold for e in bm.edges)
seen=set();components=[]
for v in bm.verts:
 if v.index in seen:continue
 stack=[v];seen.add(v.index);count=0
 while stack:
  cur=stack.pop();count+=1
  for e in cur.link_edges:
   other=e.other_vert(cur)
   if other.index not in seen:seen.add(other.index);stack.append(other)
 components.append(count)
stat['body_connected_components']=len(components);stat['body_component_vertices']=components;bm.free()
open(root+'model-check.json','w').write(json.dumps(stat,indent=2));print('MODEL_CHECK',stat)
props=bpy.ops.wm.usd_export.get_rna_type().properties.keys();print('USD_PROPS',list(props))
bpy.ops.object.select_all(action='DESELECT')
for o in curves:o.select_set(True)
if curves:
 bpy.context.view_layer.objects.active=curves[0];bpy.ops.object.convert(target='MESH')
bpy.ops.object.select_all(action='DESELECT')
for o in col.objects:o.select_set(True)
try:
 bpy.ops.wm.usd_export(filepath=root+'CatNap-shape-v10.usdz',selected_objects_only=True,export_cameras=False,export_lights=False,export_animation=False,export_materials=True)
 print('USDZ_EXPORT_COMPLETE')
except Exception as e:print('USDZ_EXPORT_FAILED',repr(e))
