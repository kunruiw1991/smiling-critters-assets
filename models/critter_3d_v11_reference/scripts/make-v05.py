from pathlib import Path
p=Path('work/catnap-model/build-v04.py').read_text().replace('v04','v05')
p=p.replace("OUT=ROOT+'/outputs/CatNap-3D-v05'", "OUT=ROOT+'/outputs/CatNap-3D-v05'\nos.makedirs(OUT,exist_ok=True)")
a=p.index('profile=[(2.76');b=p.index('\ndef prof',a)
p=p[:a]+'''profile=[(2.76,.015,.10),(2.78,.18,.20),(2.82,.37,.31),(2.90,.55,.40),(2.98,.65,.46),(3.13,.82,.53),(3.32,.97,.59),(3.52,1.065,.65),(3.71,1.108,.67),(3.90,1.095,.65),(4.02,1.045,.62),(4.12,.89,.56),(4.24,.75,.49),(4.37,.63,.38),(4.48,.45,.27),(4.56,.25,.15),(4.605,.02,.025)]'''+p[b:]
p=p.replace('Head • tapered cheeks and compact crown','Head • reference traced crown and fused ear roots')
# Move closed-ear construction before the cavity Boolean, weld by voxel union.
fna=p.index('def catmull(');fnb=p.index('outline=catmull(ctrl)',fna);fn=p[fna:fnb];p=p[:fna]+p[fnb:]
ea=p.index('ear_dark=');eb=p.index('def inset_patch',ea);earfn=p[ea:eb]
ea=p.index('# Broad outward-opening ears');eb=p.index('# Larger oval pupils',ea);p=p[:ea]+p[eb:]
a=p.index('# Smoothed mouth outline');b=p.index('outline=catmull(ctrl)',a)
p=p[:a]+fn+earfn+'''
ears=[]
for sg,label in [(-1,'L'),(1,'R')]:
 points=[(sg*.22,4.45),(sg*.33,4.63),(sg*.50,4.82),(sg*.63,4.98),(sg*.68,5.00),(sg*.73,4.91),(sg*.80,4.68),(sg*.84,4.39),(sg*.845,4.14),(sg*.64,4.15),(sg*.40,4.28)]
 ob=ear_shell('Ear.'+label,points,sg*.605,4.54,purple)
 bpy.context.view_layer.objects.active=ob
 for mo in list(ob.modifiers):bpy.ops.object.modifier_apply(modifier=mo.name)
 ears.append(ob)
bpy.ops.object.select_all(action='DESELECT')
for ob in [head]+ears:ob.select_set(True)
bpy.context.view_layer.objects.active=head;bpy.ops.object.join()
mo=head.modifiers.new('Continuous plush ear roots','REMESH');mo.mode='VOXEL';mo.voxel_size=.012;mo.use_smooth_shade=True;bpy.ops.object.modifier_apply(modifier=mo.name)
mo=head.modifiers.new('Soft root transition','SMOOTH');mo.factor=.65;mo.iterations=7;bpy.ops.object.modifier_apply(modifier=mo.name)
# Trace the official frontal grin, preserving raised corners and central scallop.
pixels=[(525,266),(550,268),(585,288),(625,307),(665,317),(700,317),(730,309),(750,302),(770,309),(800,317),(835,317),(875,307),(915,288),(950,268),(975,266),(999,285),(1010,320),(1012,355),(1000,395),(978,441),(950,477),(915,515),(875,542),(835,562),(790,572),(750,575),(710,572),(665,562),(625,542),(585,515),(550,477),(522,441),(500,395),(488,355),(490,320),(501,285)]
ctrl=[((x-750)/258,2.76+(595-y)/258) for x,y in pixels]
'''+p[b:]
p=p.replace('face.material_index=1','face.material_index=len(head.data.materials)-1')
p=p.replace("],.045,purple,cyclic=True)","],.032,purple,cyclic=True)")
a=p.index('# Larger oval pupils');b=p.index('for ob in model.objects:',a)
p=p[:a]+'''# Official toy uses round black button eyes, without cartoon white pupils.
for sg,label in [(-1,'L'),(1,'R')]:
 eye=ell('Eye.'+label,(sg*.338,fronty(sg*.338,4.205)-.025,4.205),(.232,.105,.228),black)
 eye.rotation_euler[1]=sg*math.radians(-8)
polyextrude('Nose',catmull([(-.135,4.035),(.135,4.035),(.075,3.965),(0,3.92),(-.075,3.965)],5),-.672,-.56,black,.012)
# Fine central cloth seam, with restrained stitched detail.
curve('Forehead • central seam',[(0,fronty(0,z)-.002,z) for z in [4.585,4.54,4.47,4.38,4.28,4.17,4.08]],.0028,dark)
for j in range(13):
 z=4.115+j*.032
 curve('Forehead stitch %02d'%j,[(-.009,fronty(-.009,z)-.004,z+.003),(.009,fronty(.009,z)-.004,z-.003)],.0015,seammat)
# Perforated speaker plate recessed in the smile cavity, as in the reference toy.
speaker=mat('12 • recessed speaker',(.012,.010,.017),.7)
bpy.ops.mesh.primitive_cylinder_add(vertices=96,radius=.213,depth=.042,location=(0,-.036,3.29),rotation=(pi/2,0,0));plate=finish(bpy.context.object,speaker);plate.name='Mouth • perforated speaker grille'
holes=[]
for row in range(-4,5):
 for col in range(-4,5):
  x=(col+.5*(row%2))*.043;z=row*.038
  if x*x+z*z<.18**2:
   bpy.ops.mesh.primitive_cylinder_add(vertices=12,radius=.012,depth=.12,location=(x,-.036,3.29+z),rotation=(pi/2,0,0));holes.append(bpy.context.object)
bpy.ops.object.select_all(action='DESELECT')
for ob in holes:ob.select_set(True)
bpy.context.view_layer.objects.active=holes[0];bpy.ops.object.join();cut=holes[0]
bpy.context.view_layer.objects.active=plate;mo=plate.modifiers.new('Actual speaker perforations','BOOLEAN');mo.operation='DIFFERENCE';mo.object=cut;bpy.ops.object.modifier_apply(modifier=mo.name);bpy.data.objects.remove(cut,do_unlink=True)
bpy.ops.mesh.primitive_torus_add(major_segments=96,minor_segments=12,major_radius=.214,minor_radius=.009,location=(0,-.059,3.29),rotation=(pi/2,0,0));finish(bpy.context.object,speaker).name='Mouth • speaker rim'
'''+p[b:]
a=p.index("tongue=mat(");b=p.index('# Neck transition',a);p=p[:a]+p[b:]
# Add square orthographic head cameras for dimensionally consistent comparison.
a=p.index('sc.camera=cams[1]')
p=p[:a]+'''headcams=[]
for name,loc,target,scale in [('Head-front',(0,-12,3.9),(0,0,3.9),2.7),('Head-three-quarter',(6,-12,4.8),(0,0,3.9),2.8),('Ear-root',(5,-10,5.1),(.45,0,4.35),1.8)]:
 da=bpy.data.cameras.new(name);da.type='ORTHO';da.ortho_scale=scale;ob=bpy.data.objects.new(name,da);studio.objects.link(ob);ob.location=loc;aim(ob,target);headcams.append(ob)
'''+p[a:]
a=p.index("if os.environ.get('CATNAP_PREVIEW')")
p=p[:a]+'''if os.environ.get('CATNAP_PREVIEW')=='1':
 sc.cycles.samples=16;sc.render.resolution_x=800;sc.render.resolution_y=800;sc.render.film_transparent=True
 for cam in [headcams[0],headcams[2]]:
  sc.camera=cam;sc.render.filepath=ROOT+'/work/catnap-model/v05-preview-'+cam.name+'.png';bpy.ops.render.render(write_still=True)
 print('PREVIEW_COMPLETE',flush=True);raise SystemExit(0)
for cam in cams[:2]:
 sc.camera=cam;sc.render.filepath=OUT+'/'+cam.name+'.png';bpy.ops.render.render(write_still=True)
sc.render.resolution_x=1200;sc.render.resolution_y=1200;sc.render.film_transparent=True;sc.render.image_settings.color_mode='RGBA'
for cam in headcams:
 sc.camera=cam;sc.render.filepath=OUT+'/'+cam.name+'.png';bpy.ops.render.render(write_still=True)
sc.camera=headcams[1];bpy.ops.wm.save_as_mainfile(filepath=OUT+'/CatNap-shape-v05.blend')
print('CATNAP_MODEL_COMPLETE',flush=True)
'''
Path('work/catnap-model/build-v05.py').write_text(p)
Path('work/catnap-model/verify-v05.py').write_text(Path('work/catnap-model/verify-v04.py').read_text().replace('v04','v05').replace('Head • tapered','Head • reference'))
