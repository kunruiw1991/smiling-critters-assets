from pathlib import Path
s=Path('work/catnap-model/build-v06.py').read_text().replace('v06','v07')
s=s.replace('(4.24,.75,.49),(4.37,.63,.38),(4.48,.45,.27),(4.56,.25,.15),(4.605,.02,.025)', '(4.24,.75,.53),(4.37,.65,.42),(4.48,.50,.30),(4.56,.33,.19),(4.59,.20,.115),(4.605,.02,.025)')
# Model the muzzle volume in the head surface itself, before ear union and the mouth opening.
needle="faces=[]\nfor i in range(len(ringdata)-1):"
s=s.replace(needle,"""# Broad padded muzzle and cheek volume; these are displacements of the skull, not added rings.
def facial_volume(x,z):
 return .092*math.exp(-((x/.31)**2+((z-3.99)/.21)**2))+ .045*math.exp(-(((abs(x)-.79)/.24)**2+((z-3.98)/.26)**2))
verts=[(x,y-facial_volume(x,z)*max(0,min(1,(.035-y)/.18)),z) for x,y,z in verts]
"""+needle)
a=s.index('head.data.materials.append(inside)',s.index('cutter=polyextrude'));b=s.index('# Official toy uses round black button eyes',a)
s=s[:a]+'''# Round the cut into the existing head shell. No separate lip tube is created.
mo=head.modifiers.new('Continuous rounded mouth opening','REMESH');mo.mode='VOXEL';mo.voxel_size=.009;mo.use_smooth_shade=True;bpy.ops.object.modifier_apply(modifier=mo.name)
# Limit smoothing to the mouth region, keeping the revised ear contour intact.
vg=head.vertex_groups.new(name='Mouth cloth rollover')
for v in head.data.vertices:
 x,y,z=v.co
 if z<4.10 and y<.08:vg.add([v.index],1.0,'REPLACE')
mo=head.modifiers.new('Broad soft cloth transition','SMOOTH');mo.vertex_group=vg.name;mo.factor=.72;mo.iterations=22;bpy.ops.object.modifier_apply(modifier=mo.name)
head.data.materials.append(inside)
for face in head.data.polygons:
 face.use_smooth=True
 c=face.center
 face.material_index=0
 for tree,indices in ear_surfaces:
  co,no,idx,dist=tree.find_nearest(c)
  if idx is not None and dist<.04 and indices[idx]==1:face.material_index=1
 if c.y>-.025 and c.y<.02 and 2.82<c.z<4.01 and abs(c.x)<1.03:face.material_index=len(head.data.materials)-1
head_tree=BVHTree.FromPolygons([v.co for v in head.data.vertices],[list(f.vertices) for f in head.data.polygons])
def analyticfront(x,z):
 w,d=prof(z);return .035-d*sqrt(max(.025,1-(x/max(.01,w))**2))-facial_volume(x,z)
def fronty(x,z):
 loc,normal,idx,dist=head_tree.ray_cast(Vector((x,-2,z)),Vector((0,1,0)),4)
 return loc.y if loc is not None else analyticfront(x,z)
# Smooth recessed bowl: the black material begins inside the rounded cloth edge.
verts=[];N=len(outline);fractions=[.995,.975,.93,.85,.72,.56,.38,.20,.06]
for f in fractions:
 for x,z in outline:
  xx=x*f;zz=3.40+(z-3.40)*f
  edge=analyticfront(x,z)
  yy=edge*(f*f)+(-.012)*(1-f*f)+.018*f
  verts.append((xx,yy,zz))
faces=[]
for r in range(len(fractions)-1):
 for i in range(N):faces.append((r*N+i,r*N+(i+1)%N,(r+1)*N+(i+1)%N,(r+1)*N+i))
# Triangular fan cap avoids expensive high-valence subdivision.
verts.append((0,-.012,3.40));ci=len(verts)-1
for i in range(N):faces.append(((len(fractions)-1)*N+i,(len(fractions)-1)*N+(i+1)%N,ci))
me=bpy.data.meshes.new('Continuous curved mouth bowl');me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new('Mouth • smoothly recessed lining',me);model.objects.link(o);me.materials.append(inside)
for p in me.polygons:p.use_smooth=True
sub=o.modifiers.new('Smooth cavity surface','SUBSURF');sub.levels=1
'''+s[b:]
a=s.index('# Official toy uses round black button eyes');b=s.index('# Fine central cloth seam',a)
s=s[:a]+'''# Fitted domed eyes: perimeter follows the actual forehead instead of intersecting a sphere.
def fitted_eye(sg,label):
 cx=sg*.338;cz=4.205;N=96;vs=[];rs=[.015,.15,.30,.45,.60,.72,.82,.90,.96,1.0]
 for r in rs:
  for j in range(N):
   a=j/N*2*pi;x=cx+.225*r*cos(a);z=cz+.222*r*sin(a)
   y=fronty(x,z)-.004-.105*sqrt(max(0,1-r*r));vs.append((x,y,z))
 fs=[]
 for k in range(len(rs)-1):
  for j in range(N):fs.append((k*N+j,k*N+(j+1)%N,(k+1)*N+(j+1)%N,(k+1)*N+j))
 fs.append(tuple(reversed(range(N))))
 # Recessed back ring gives the button real thickness without a floating edge.
 off=len(vs)
 for j in range(N):
  x,y,z=vs[(len(rs)-1)*N+j];vs.append((x,y+.025,z))
 for j in range(N):fs.append(((len(rs)-1)*N+j,(len(rs)-1)*N+(j+1)%N,off+(j+1)%N,off+j))
 fs.append(tuple(range(off,off+N)))
 me=bpy.data.meshes.new('Fitted eye dome');me.from_pydata(vs,[],fs);me.update();ob=bpy.data.objects.new('Eye.'+label+' • skin-fitted dome',me);model.objects.link(ob);me.materials.append(black)
 for f in me.polygons:f.use_smooth=True
 bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob;bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT')
for sg,label in [(-1,'L'),(1,'R')]:fitted_eye(sg,label)
# A padded triangular nose seated into the central muzzle, with its lower point touching the grin apex.
nose=polyextrude('Nose • seated rounded triangle',catmull([(-.13,4.033),(.13,4.033),(.092,3.983),(0,3.901),(-.092,3.983)],6),-.77,-.64,black,.020)
'''+s[b:]
s=s.replace('location=(0,-.036,3.29)','location=(0,-.130,3.29)').replace('location=(x,-.036,3.29+z)','location=(x,-.130,3.29+z)').replace('location=(0,-.059,3.29)','location=(0,-.153,3.29)')
s=s.replace("('Ear-root',(5,-10,5.1),(.45,0,4.35),1.8)","('Connections',(5,-10,4.45),(.20,0,3.94),1.80),('Head-side',(12,0,3.9),(0,0,3.9),2.7)")
s=s.replace('for cam in [headcams[0],headcams[2]]:','for cam in [headcams[0],headcams[1]]:')
# Defer export until after quick visual QA.
a=s.index('bpy.ops.export_scene.gltf(');b=s.index('\n',a);export=s[a:b];s=s[:a]+s[b:]
idx=s.index('sc.render.resolution_x=1200');s=s[:idx]+export+'\n'+s[idx:]
Path('work/catnap-model/build-v07.py').write_text(s)
Path('work/catnap-model/verify-v07.py').write_text(Path('work/catnap-model/verify-v06.py').read_text().replace('v06','v07'))
