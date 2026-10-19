from pathlib import Path
s=Path('work/catnap-model/build.py').read_text()
s=s.replace("OUT=ROOT+'/outputs/CatNap-3D'", "OUT=ROOT+'/outputs/CatNap-3D-v02'")
s=s.replace('shape review v01','shape review v02').replace('shape-v01','shape-v02')
start=s.index('# Broad head;')
end=s.index('# Smoothed mouth outline',start)
s=s[:start]+'''# Reference-driven silhouette: compact crown, wide smile cheeks, tapered rounded chin.
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
''' +s[end:]
s=s.replace("ctrl=[(-1.00,3.73),(-.92,3.85),(-.72,3.82),(-.40,3.67),(0,3.63),(.40,3.67),(.72,3.82),(.92,3.85),(1.00,3.73),(.96,3.43),(.79,3.12),(.48,2.88),(0,2.77),(-.48,2.88),(-.79,3.12),(-.96,3.43)]", "ctrl=[(-1.055,3.79),(-1.00,3.885),(-.82,3.895),(-.43,3.72),(0,3.715),(.43,3.72),(.82,3.895),(1.00,3.885),(1.055,3.79),(.97,3.54),(.77,3.26),(.44,3.005),(0,2.865),(-.44,3.005),(-.77,3.26),(-.97,3.54)]")
s=s.replace("def fronty(x,z):return -.69*sqrt(max(.03,1-(x/1.13)**2-((z-3.6)/.96)**2))-.014", "def fronty(x,z):\n w,d=prof(z);return .035-d*sqrt(max(.04,1-(x/max(.01,w))**2))-.014")
s=s.replace("xx=x*f;zz=3.29+(z-3.29)*f", "xx=x*f;zz=3.35+(z-3.35)*f")
start=s.index('# Upright original-style ears,')
end=s.index('# Rounded triangular toy nose.',start)
s=s[:start]+'''# Broad outward-opening ears, with rounded tips and sculpted thin 3D shells.
def ear_shell(name,outline,cx,cz,material):
 points=catmull(outline,6);N=len(points);verts=[]
 # Four concentric rings on each side; thickness decreases toward the rim.
 for side in [0,1]:
  for f in [.015,.35,.70,1.0]:
   for x,z in points:
    xx=cx+(x-cx)*f;zz=cz+(z-cz)*f
    yy=(.025-.14*f*f) if side==0 else (.22-.24*f*f)
    verts.append((xx,yy,zz))
 faces=[]
 for side in [0,1]:
  off=side*4*N
  for r in range(3):
   for j in range(N):
    face=(off+r*N+j,off+r*N+(j+1)%N,off+(r+1)*N+(j+1)%N,off+(r+1)*N+j);faces.append(face if side==0 else tuple(reversed(face)))
  ids=list(range(off,off+N));faces.append(tuple(reversed(ids)) if side==0 else tuple(ids))
 for j in range(N):faces.append((3*N+j,3*N+(j+1)%N,7*N+(j+1)%N,7*N+j))
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();ob=bpy.data.objects.new(name,me);model.objects.link(ob);me.materials.append(material)
 bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob;bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT')
 for p in me.polygons:p.use_smooth=True
 su=ob.modifiers.new('Soft continuous ear shell','SUBSURF');su.levels=2
 return ob
for sg,label in [(-1,'L'),(1,'R')]:
 points=[(sg*.26,4.47),(sg*.48,4.72),(sg*.72,4.94),(sg*.86,4.995),(sg*.99,4.88),(sg*1.075,4.61),(sg*1.075,4.31),(sg*1.015,4.065),(sg*.79,4.105),(sg*.57,4.27)]
 ear_shell('Ear.'+label+' • broad rounded shell',points,sg*.73,4.50,purple)
 # Lower inner-ear patch, framed by a generous purple outer rim.
 patch=[(sg*.52,4.24),(sg*.64,4.47),(sg*.78,4.62),(sg*.87,4.59),(sg*.91,4.39),(sg*.94,4.13),(sg*.76,4.13)]
 polyextrude('Ear inset.'+label,catmull(patch,6),-.155,-.105,dark,.015)
 # A pair of short cheek flicks follows the reference silhouette.
 curve('Cheek tuft upper.'+label,[(sg*.91,fronty(sg*.91,3.95),3.95),(sg*1.10,-.20,3.955),(sg*1.215,-.11,3.88)],.033,purple,[1.3,1,.08])
 curve('Cheek tuft lower.'+label,[(sg*1.015,-.20,3.875),(sg*1.17,-.13,3.84),(sg*1.19,-.07,3.765)],.025,purple,[1.2,1,.08])
# Larger oval pupils, like the supplied design; eyes sit within the narrowed forehead.
for sg,label in [(-1,'L'),(1,'R')]:
 eye=ell('Eye.'+label,(sg*.365,-.523,4.045),(.282,.117,.340),black)
 eye.rotation_euler[1]=sg*math.radians(-10)
 ell('Pupil.'+label,(sg*.365,-.638,4.055),(.098,.019,.137),white,48,32)
''' +s[end:]
s=s.replace("-.763,-.64,black,.015", "-.708,-.59,black,.015")
# Replace forehead seam with a tiny rosy tongue in the deep mouth, matching the reference expression.
a=s.index('# Small central head seam,');b=s.index('# Group objects',a)
s=s[:a]+'''tongue=mat('10 • tongue',(.92,.16,.24),.65)
for sg in [-1,1]:ell('Tongue lobe '+str(sg),(sg*.075,-.20,2.995),(.115,.065,.040),tongue,48,24)
''' +s[b:]
s=s.replace("ref.name='REFERENCE • official CatNap • source in README'", "ref.name='REFERENCE • official CatNap • source in README'\nref2=bpy.data.images.load(ROOT+'/work/model-reference/teepublic-catnap.jpg');ref2.pack();ref2.name='REFERENCE • user supplied TeePublic design'")
s=s.replace("for cam in cams:\n sc.camera=cam", "for cam in cams:\n sc.camera=cam")
s=s.replace("print('CATNAP_MODEL_COMPLETE',flush=True)", """# Head close-up for this round of review.
da=bpy.data.cameras.new('Head close-up');da.type='ORTHO';da.ortho_scale=2.95;cam=bpy.data.objects.new('Head close-up',da);studio.objects.link(cam);cam.location=(0,-12,3.95);aim(cam,(0,0,3.93));sc.camera=cam;sc.render.resolution_x=1200;sc.render.resolution_y=1100;sc.render.filepath=OUT+'/Head-front.png';bpy.ops.render.render(write_still=True)
cam.location=(6,-12,4.8);aim(cam,(0,0,3.93));sc.render.filepath=OUT+'/Head-three-quarter.png';bpy.ops.render.render(write_still=True)
sc.camera=cams[1];sc.render.resolution_x=1000;sc.render.resolution_y=1200;bpy.ops.wm.save_as_mainfile(filepath=OUT+'/CatNap-shape-v02.blend')
print('CATNAP_MODEL_COMPLETE',flush=True)""")
Path('work/catnap-model/build-v02.py').write_text(s)
Path('outputs/CatNap-3D-v02').mkdir(exist_ok=True)
