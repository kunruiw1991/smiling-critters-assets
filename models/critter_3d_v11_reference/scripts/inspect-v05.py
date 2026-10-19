import bpy,collections
bpy.ops.wm.open_mainfile(filepath='/Users/kunruiwang/Documents/Codex/2026-10-17/ni/outputs/CatNap-3D-v05/CatNap-shape-v05.blend')
o=next(o for o in bpy.data.objects if o.name.startswith('Head •'))
print('HEAD',len(o.data.vertices),len(o.data.polygons),max(len(f.vertices) for f in o.data.polygons),[(m.name if m else '') for m in o.data.materials],collections.Counter(f.material_index for f in o.data.polygons),flush=True)
