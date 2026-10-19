from pathlib import Path
s=Path('work/catnap-model/build-v02.py').read_text().replace('/outputs/CatNap-3D-v02','/outputs/CatNap-3D-v03').replace('shape review v02','shape review v03').replace('shape-v02','shape-v03')
a=s.index('# Body and limbs:');b=s.index('# Reference-driven silhouette:',a)
s=s[:a]+'''# Chubby plush proportions: short round torso, tucked limbs, no human waist/shoulders.
body=ell('Torso • round plush belly',(0,0,1.35),(.76,.59,.69),purple)
for v in body.data.vertices:
 f=v.co.z/.69;v.co.x*=1-.07*f;v.co.y*=1-.035*f
for sg,label in [(-1,'L'),(1,'R')]:
 ell('Leg.'+label+' • short tucked stub',(sg*.32,.025,.65),(.285,.30,.345),purple)
 ell('Foot.'+label+' • round cat paw',(sg*.34,-.17,.405),(.325,.365,.205),dark)
 curve('Arm.'+label,[(sg*.54,.015,1.78),(sg*.68,-.045,1.57),(sg*.775,-.105,1.36),(sg*.79,-.14,1.24)],.19,purple,[1.10,1.12,1.04,.96])
 ell('Paw.'+label+' • plump rounded mitten',(sg*.79,-.16,1.14),(.24,.255,.235),dark)
shoulders=[ell('Soft limb root.'+label,(sg*.54,.005,1.76),(.25,.235,.255),purple) for sg,label in [(-1,'L'),(1,'R')]]
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
''' +s[b:]
a=s.index('def ear_shell(');b=s.index('def inset_patch(',a)
s=s[:a]+'''ear_dark=mat('11 • recessed dark-purple inner ear',(.038,.006,.09),.90)
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
''' +s[b:]
s=s.replace("points=[(sg*.26,4.47),(sg*.48,4.72),(sg*.72,4.94),(sg*.86,4.995),(sg*.99,4.88),(sg*1.075,4.61),(sg*1.075,4.31),(sg*1.015,4.065),(sg*.79,4.105),(sg*.57,4.27)]", "points=[(sg*.36,4.29),(sg*.48,4.57),(sg*.65,4.87),(sg*.75,5.035),(sg*.80,5.055),(sg*.85,4.98),(sg*.95,4.70),(sg*1.005,4.38),(sg*.99,4.16),(sg*.77,4.18),(sg*.56,4.24)]")
s=s.replace("points,sg*.73,4.50,purple)","points,sg*.735,4.515,purple)")
s=s.replace("inset_patch('Ear inset.'+label+' • fitted surface',patch,points,sg*.73,4.50)","# Inner-ear bowl is part of the shell mesh; no separate flat inset.")
# Move the entire head assembly down together while preserving the approved face shape.
a=s.index('# Signature tail.');s=s[:a]+'''for ob in model.objects:
 if ob.name not in body_objects:ob.location.z-=.65
''' +s[a:]
s=s.replace("[(0,.31,1.53),(.54,.56,1.22),(1.21,.55,.72),(1.76,.42,.64),(2.04,.30,1.03),(2.06,.23,1.77),(1.95,.16,2.42),(1.66,.10,2.73),(1.38,.055,2.62)],.145", "[(0,.47,1.10),(.55,.63,.93),(1.16,.58,.56),(1.63,.43,.50),(1.88,.27,.85),(1.93,.17,1.49),(1.82,.10,2.05),(1.56,.03,2.31),(1.30,-.01,2.19)],.16")
s=s.replace("(1.38,.055,2.62),(.052,.052,.052)","(1.30,-.01,2.19),(.057,.057,.057)")
s=s.replace("[(0,-.35,2.54),(0,-.395,2.20),(0,-.393,1.85),(0,-.30,1.47)],.034", "[(0,-.40,1.86),(0,-.575,1.55),(0,-.60,1.20),(0,-.425,.89)],.026")
s=s.replace("z=1.53+i*.037;yy=-.39*sqrt(max(.1,1-((z-2.03)/.71)**2))-.025", "z=.94+i*.036;yy=-.59*sqrt(max(.1,1-((z-1.35)/.69)**2))-.025")
s=s.replace("2.39+R*sin(t)","1.58+R*sin(t)").replace("2.39+r*sin(t)","1.58+r*sin(t)")
s=s.replace("moonpts,-.535,-.455,gold,.022", "moonpts,-.685,-.605,gold,.022")
s=s.replace("location=(0,-.455,2.70)","location=(0,-.605,1.89)")
s=s.replace("tongue=mat('10 • tongue'", "curve('Pendant • short attachment',[(0,-.39,1.88),(0,-.49,1.91),(0,-.605,1.89)],.013,gold)\ntongue=mat('10 • tongue'")
s=s.replace("(sg*.075,-.20,2.995)","(sg*.075,-.20,2.345)")
s=s.replace("(0,.025,2.70),(.21,.23,.16)","(0,.02,2.04),(.20,.22,.13)")
# Improve cavity preview: suppress bright specular seams in an otherwise matte black mouth.
s=s.replace("inside=mat('04 • mouth cavity • matte',(.002,.001,.004),.95)","inside=mat('04 • mouth cavity • matte',(.0005,.0003,.001),1.0)\ninside.node_tree.nodes.get('Principled BSDF').inputs['Specular IOR Level'].default_value=0")
s=s.replace("('Front',(0,-12,2.70),5.7),('Three-quarter',(7,-11,4.2),6.0),('Side',(12,0,2.7),5.7),('Back',(0,12,2.7),5.7)","('Front',(0,-12,2.38),4.85),('Three-quarter',(7,-11,3.5),5.1),('Side',(12,0,2.38),4.85),('Back',(0,12,2.38),4.85)")
s=s.replace("aim(o,(.30,0,2.62))", "aim(o,(.25,0,2.25))")
s=s.replace("cam.location=(0,-12,3.95);aim(cam,(0,0,3.93))", "cam.location=(0,-12,3.30);aim(cam,(0,0,3.28))")
s=s.replace("cam.location=(6,-12,4.8);aim(cam,(0,0,3.93))", "cam.location=(6,-12,4.15);aim(cam,(0,0,3.28))")
s=s.replace("# Save original editable model;", "ref3=bpy.data.images.load(ROOT+'/work/model-reference/official-catnap-icon.png');ref3.pack();ref3.name='REFERENCE • official CatNap page icon'\n# Save original editable model;")
Path('work/catnap-model/build-v03.py').write_text(s)
Path('outputs/CatNap-3D-v03').mkdir(exist_ok=True)
v=Path('work/catnap-model/verify-v02.py').read_text().replace('CatNap-3D-v02','CatNap-3D-v03').replace('shape-v02','shape-v03').replace('shape review v02','shape review v03')
Path('work/catnap-model/verify-v03.py').write_text(v)
