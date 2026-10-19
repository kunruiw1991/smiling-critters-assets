from pathlib import Path
p=Path('work/catnap-model/build-v02.py');s=p.read_text()
a=s.index("for sg,label in [(-1,'L'),(1,'R')]:\n points=")
s=s[:a]+'''def inset_patch(name,patch,ear_outline,cx,cz):
 edge=catmull(ear_outline,6);outline=catmull(patch,6);N=len(outline);pcx=sum(p[0] for p in outline)/N;pcz=sum(p[1] for p in outline)/N
 def cross(a,b):return a[0]*b[1]-a[1]*b[0]
 def front_surface(x,z):
  ray=(x-cx,z-cz);hits=[]
  for i in range(len(edge)):
   a=edge[i];b=edge[(i+1)%len(edge)];seg=(b[0]-a[0],b[1]-a[1]);den=cross(ray,seg)
   if abs(den)<1e-10:continue
   ac=(a[0]-cx,a[1]-cz);t=cross(ac,seg)/den;u=cross(ac,ray)/den
   if t>0 and 0<=u<=1:hits.append(t)
  f=1/min(hits) if hits else .5
  return .025-.14*f*f-.018
 verts=[]
 for r in [.01,.25,.5,.75,1]:
  for x,z in outline:
   xx=pcx+(x-pcx)*r;zz=pcz+(z-pcz)*r;verts.append((xx,front_surface(xx,zz),zz))
 faces=[tuple(reversed(range(N)))]
 for i in range(4):
  for j in range(N):faces.append((i*N+j,i*N+(j+1)%N,(i+1)*N+(j+1)%N,(i+1)*N+j))
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();ob=bpy.data.objects.new(name,me);model.objects.link(ob);me.materials.append(dark)
 for f in me.polygons:f.use_smooth=True
 su=ob.modifiers.new('Conforming inner-ear surface','SUBSURF');su.levels=1
 return ob
''' +s[a:]
s=s.replace("polyextrude('Ear inset.'+label,catmull(patch,6),-.155,-.105,dark,.015)","inset_patch('Ear inset.'+label+' • fitted surface',patch,points,sg*.73,4.50)")
s=s.replace("# Group objects under one clear root", "ell('Neck • joins head and torso',(0,.025,2.70),(.21,.23,.16),purple)\n# Group objects under one clear root")
p.write_text(s)
