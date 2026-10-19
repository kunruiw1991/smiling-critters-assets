import bpy,json,math
root='/Users/kunruiwang/Documents/Codex/2026-10-17/ni/outputs/CatNap-3D/'
bpy.ops.wm.open_mainfile(filepath=root+'CatNap-shape-v01.blend')
col=bpy.data.collections['CATNAP • shape review v01']
mesh=[o for o in col.objects if o.type=='MESH'];curves=[o for o in col.objects if o.type=='CURVE']
stat={'engine':bpy.app.version_string,'mesh_objects':len(mesh),'editable_curves':len(curves),'vertices':sum(len(o.data.vertices) for o in mesh),'faces':sum(len(o.data.polygons) for o in mesh),'has_armature':any(o.type=='ARMATURE' for o in col.objects),'has_animation':any(o.animation_data is not None for o in col.objects),'nonfinite_vertices':sum(not all(math.isfinite(x) for x in v.co) for o in mesh for v in o.data.vertices)}
open(root+'model-check.json','w').write(json.dumps(stat,indent=2));print('MODEL_CHECK',stat)
props=bpy.ops.wm.usd_export.get_rna_type().properties.keys();print('USD_PROPS',list(props))
bpy.ops.object.select_all(action='DESELECT')
for o in curves:o.select_set(True)
if curves:
 bpy.context.view_layer.objects.active=curves[0];bpy.ops.object.convert(target='MESH')
bpy.ops.object.select_all(action='DESELECT')
for o in col.objects:o.select_set(True)
try:
 bpy.ops.wm.usd_export(filepath=root+'CatNap-shape-v01.usdz',selected_objects_only=True,export_cameras=False,export_lights=False,export_animation=False,export_materials=True)
 print('USDZ_EXPORT_COMPLETE')
except Exception as e:print('USDZ_EXPORT_FAILED',repr(e))
