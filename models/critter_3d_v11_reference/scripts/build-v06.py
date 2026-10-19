import bpy, math, json, os
from mathutils import Vector
from mathutils.geometry import tessellate_polygon
from math import sin,cos,pi,sqrt
ROOT='/Users/kunruiwang/Documents/Codex/2026-10-17/ni'
OUT=ROOT+'/outputs/CatNap-3D-v06'
os.makedirs(OUT,exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
model=bpy.data.collections.new('CATNAP • shape review v06');bpy.context.scene.collection.children.link(model)
studio=bpy.data.collections.new('STUDIO • cameras and lighting');bpy.context.scene.collection.children.link(studio)
def move(obj,col=model):
 for c in list(obj.users_collection):c.objects.unlink(obj)
 col.objects.link(obj)
 return obj
def mat(name,color,rough=.6,metal=0,bump=False):
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
 n=m.node_tree.nodes;p=n.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
 if bump:
  tex=n.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=115;tex.inputs['Detail'].default_value=2
  b=n.new('ShaderNodeBump');b.inputs['Strength'].default_value=.12;b.inputs['Distance'].default_value=.012;m.node_tree.links.new(tex.outputs['Fac'],b.inputs['Height']);m.node_tree.links.new(b.outputs['Normal'],p.inputs['Normal']);p.inputs['Sheen Weight'].default_value=.22
 return m
purple=mat('01 • CatNap purple • temporary surface',(.235,.045,.46),.64,bump=True)
dark=mat('02 • paws and inner ears',(.115,.023,.23),.72,bump=True)
black=mat('03 • dark eye buttons',(.006,.004,.011),.28)
inside=mat('04 • mouth cavity • matte',(.003,.002,.004),.85)
inside.node_tree.nodes.get('Principled BSDF').inputs['Specular IOR Level'].default_value=.18
white=mat('05 • small white pupils',(.97,.95,1),.3)
gold=mat('06 • crescent pendant',(.93,.58,.07),.27,.7)
zipmat=mat('07 • zipper fabric',(.035,.015,.055),.8)
teeth=mat('08 • zipper teeth',(.15,.12,.19),.48,.3)
seammat=mat('09 • seam thread',(.47,.25,.65),.8)
def finish(o,m):
 if m:o.data.materials.append(m)
 if o.type=='MESH':
  for p in o.data.polygons:p.use_smooth=True
 move(o);return o
def ell(name,loc,scale,m,seg=64,rings=48):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=seg,ring_count=rings,location=loc);o=bpy.context.object;o.name=name;o.scale=scale;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);return finish(o,m)
def curve(name,pts,r,m,radii=None,cyclic=False):
 cu=bpy.data.curves.new(name,'CURVE');cu.dimensions='3D';cu.resolution_u=16;cu.bevel_depth=r;cu.bevel_resolution=5;cu.use_fill_caps=True;s=cu.splines.new('BEZIER');s.bezier_points.add(len(pts)-1)
 for i,(p,co) in enumerate(zip(s.bezier_points,pts)):
  p.co=co;p.handle_left_type='AUTO';p.handle_right_type='AUTO';p.radius=(radii[i] if radii else 1)
 s.use_cyclic_u=cyclic;o=bpy.data.objects.new(name,cu);model.objects.link(o);cu.materials.append(m);return o
def polyextrude(name,xz,yfront,yback,m,bevel=0):
 n=len(xz);v=[(x,yfront,z) for x,z in xz]+[(x,yback,z) for x,z in xz];faces=[]
 vectors=[Vector((x,z,0)) for x,z in xz];tris=tessellate_polygon([vectors]);lookup={tuple(v):i for i,v in enumerate(vectors)}
 for t in tris:
  ids=[p if isinstance(p,int) else lookup[tuple(p)] for p in t];faces.append(tuple(reversed(ids)));faces.append(tuple(i+n for i in ids))
 faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 me=bpy.data.meshes.new(name);me.from_pydata(v,[],faces);me.update();o=bpy.data.objects.new(name,me);model.objects.link(o)
 if m:me.materials.append(m)
 # Consistent closed-surface normals before boolean/bevel.
 bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o;bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT')
 if bevel:
  b=o.modifiers.new('soft sculpted edges','BEVEL');b.width=bevel;b.segments=4
  bpy.ops.object.modifier_apply(modifier=b.name)
 for p in me.polygons:p.use_smooth=True
 return o
# Proportions measured against the official plush render: head including ears ~48% of ear-to-toe height.
# One continuous loft per cloth limb avoids separate human-like upper-arm/hand or leg/foot spheres.
def plush_loft(name,profile,mats,cuff=None,N=96):
 rows=[]
 for i in range(len(profile)-1):
  p0=Vector(profile[max(0,i-1)]);p1=Vector(profile[i]);p2=Vector(profile[i+1]);p3=Vector(profile[min(len(profile)-1,i+2)])
  for j in range(7):
   t=j/7;rows.append(tuple(.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t)))
 rows.append(profile[-1]);v=[]
 for z,w,d,cx,cy in rows:
  for k in range(N):
   t=k/N*2*pi;v.append((cx+max(.006,w)*cos(t),cy+max(.006,d)*sin(t),z))
 faces=[];bands=[]
 for r in range(len(rows)-1):
  for k in range(N):faces.append((r*N+k,r*N+(k+1)%N,(r+1)*N+(k+1)%N,(r+1)*N+k));bands.append(1 if cuff is not None and (rows[r][0]+rows[r+1][0])*.5<cuff else 0)
 faces.extend([tuple(reversed(range(N))),tuple(range((len(rows)-1)*N,len(rows)*N))]);bands.extend([1 if cuff is not None else 0,0])
 me=bpy.data.meshes.new(name);me.from_pydata(v,[],faces);me.update();ob=bpy.data.objects.new(name,me);model.objects.link(ob)
 for m in mats:me.materials.append(m)
 for p,idx in zip(me.polygons,bands):p.use_smooth=True;p.material_index=idx
 bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob;bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT')
 return ob
body_profile=[(1.40,.07,.10),(1.44,.34,.24),(1.52,.50,.34),(1.70,.575,.405),(1.90,.60,.43),(2.10,.56,.415),(2.32,.46,.35),(2.50,.43,.30),(2.62,.36,.27),(2.72,.27,.24),(2.80,.17,.21),(2.83,.08,.14)]
body=plush_loft('Torso • official-reference cloth silhouette',[(z,w,d,0,0) for z,w,d in body_profile],[purple])
def bodyfront(z):
 for i in range(len(body_profile)-1):
  a,b=body_profile[i],body_profile[i+1]
  if z<=b[0]:
   f=max(0,min(1,(z-a[0])/(b[0]-a[0])));return -(a[2]*(1-f)+b[2]*f)-.015
 return -.12
for sg,label in [(-1,'L'),(1,'R')]:
 legp=[(.20,.018,.020,sg*.39,-.07),(.25,.15,.16,sg*.39,-.075),(.34,.28,.275,sg*.39,-.05),(.52,.34,.29,sg*.39,-.01),(.78,.30,.275,sg*.34,.005),(1.05,.235,.245,sg*.285,.01),(1.30,.195,.225,sg*.26,.015),(1.46,.12,.17,sg*.245,.02),(1.52,.02,.05,sg*.24,.02)]
 plush_loft('Leg.'+label+' • seamless rounded cloth leg',legp,[purple,dark],.56)
 armp=[(1.38,.018,.022,sg*1.05,-.055),(1.43,.115,.13,sg*1.03,-.06),(1.54,.19,.195,sg*.98,-.055),(1.72,.215,.205,sg*.88,-.04),(1.95,.205,.20,sg*.74,-.02),(2.20,.19,.185,sg*.59,0),(2.42,.16,.16,sg*.47,.01),(2.59,.10,.12,sg*.35,.015),(2.65,.025,.045,sg*.32,.015)]
 plush_loft('Arm.'+label+' • seamless soft toy arm',armp,[purple,dark],1.73)
body_objects=set(o.name for o in model.objects)
# Reference-driven silhouette: compact crown, wide smile cheeks, tapered rounded chin.
profile=[(2.76,.015,.10),(2.78,.18,.20),(2.82,.37,.31),(2.90,.55,.40),(2.98,.65,.46),(3.13,.82,.53),(3.32,.97,.59),(3.52,1.065,.65),(3.71,1.108,.67),(3.90,1.095,.65),(4.02,1.045,.62),(4.12,.89,.56),(4.24,.75,.49),(4.37,.63,.38),(4.48,.45,.27),(4.56,.25,.15),(4.605,.02,.025)]
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
me=bpy.data.meshes.new('CatNap reference silhouette loft');me.from_pydata(verts,[],faces);me.update();head=bpy.data.objects.new('Head • reference traced crown and fused ear roots',me);model.objects.link(head);me.materials.append(purple)
for p in me.polygons:p.use_smooth=True
bpy.ops.object.select_all(action='DESELECT');head.select_set(True);bpy.context.view_layer.objects.active=head;bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT')
def catmull(points,n=8):
 arr=[]
 for i in range(len(points)):
  p0=Vector(points[(i-1)%len(points)]);p1=Vector(points[i]);p2=Vector(points[(i+1)%len(points)]);p3=Vector(points[(i+2)%len(points)])
  for j in range(n):
   t=j/n;v=.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t);arr.append(tuple(v))
 return arr
ear_dark=mat('11 • recessed dark-purple inner ear',(.038,.006,.09),.90)
def ear_shell(name,outline,cx,cz,material):
 points=catmull(outline,3);N=len(points);verts=[]
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

# Convex cubic silhouette: no inward kink on either side of the pointed ear.
def cubic2(a,b,c,d,n=4):
 return [tuple((1-t)**3*a[k]+3*(1-t)**2*t*b[k]+3*(1-t)*t*t*c[k]+t**3*d[k] for k in range(2)) for t in [j/n for j in range(n)]]
ear_outline=[]
for segment in [((.22,4.45),(.29,4.67),(.51,4.93),(.645,4.99)),((.645,4.99),(.672,5.002),(.695,5.004),(.712,4.982)),((.712,4.982),(.797,4.872),(.88,4.45),(.845,4.14)),((.845,4.14),(.62,4.10),(.37,4.23),(.22,4.45))]:
 ear_outline+=cubic2(*segment)
ears=[]
for sg,label in [(-1,'L'),(1,'R')]:
 points=[(sg*x,z) for x,z in ear_outline]
 ob=ear_shell('Ear.'+label,points,sg*.605,4.54,purple)
 bpy.context.view_layer.objects.active=ob
 for mo in list(ob.modifiers):bpy.ops.object.modifier_apply(modifier=mo.name)
 ears.append(ob)
from mathutils.bvhtree import BVHTree
ear_surfaces=[]
for ob in ears:
 ear_surfaces.append((BVHTree.FromPolygons([v.co for v in ob.data.vertices],[list(f.vertices) for f in ob.data.polygons]),[f.material_index for f in ob.data.polygons]))
bpy.ops.object.select_all(action='DESELECT')
for ob in [head]+ears:ob.select_set(True)
bpy.context.view_layer.objects.active=head;bpy.ops.object.join()
mo=head.modifiers.new('Continuous plush ear roots','REMESH');mo.mode='VOXEL';mo.voxel_size=.012;mo.use_smooth_shade=True;bpy.ops.object.modifier_apply(modifier=mo.name)
mo=head.modifiers.new('Soft root transition','SMOOTH');mo.factor=.65;mo.iterations=7;bpy.ops.object.modifier_apply(modifier=mo.name)
# Voxel union resets material indices; transfer the ear-bowl assignment back from source surfaces.
for face in head.data.polygons:
 c=face.center
 best=(100,0)
 for tree,indices in ear_surfaces:
  co,no,idx,dist=tree.find_nearest(c)
  if idx is not None and dist<best[0]:best=(dist,indices[idx])
 if best[0]<.035 and best[1]==1:face.material_index=1
# Trace the official frontal grin, preserving raised corners and central scallop.
pixels=[(525,266),(550,268),(585,288),(625,307),(665,317),(700,317),(730,309),(750,302),(770,309),(800,317),(835,317),(875,307),(915,288),(950,268),(975,266),(999,285),(1010,320),(1012,355),(1000,395),(978,441),(950,477),(915,515),(875,542),(835,562),(790,572),(750,575),(710,572),(665,562),(625,542),(585,515),(550,477),(522,441),(500,395),(488,355),(490,320),(501,285)]
ctrl=[((x-750)/258,2.76+(595-y)/258) for x,y in pixels]
outline=catmull(ctrl)
cutter=polyextrude('TEMP • mouth subtraction',outline,-1.1,-.005,None)
bpy.context.view_layer.objects.active=head;mod=head.modifiers.new('True hollow grin','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)
head.data.materials.append(inside)
for face in head.data.polygons:
 if all(abs(head.data.vertices[i].co.y+.005)<.0001 for i in face.vertices):face.material_index=len(head.data.materials)-1
for p in head.data.polygons:p.use_smooth=True
# A curved, deep black lining inside the actual mouth, not a flat decal.
def fronty(x,z):
 w,d=prof(z);return .035-d*sqrt(max(.04,1-(x/max(.01,w))**2))-.014
verts=[];N=len(outline)
for ring,f in enumerate([1,.80,.48,.12]):
 for x,z in outline:
  xx=x*f;zz=3.35+(z-3.35)*f
  yy=fronty(x,z) if ring==0 else [-9,-.040,-.015,-.008][ring]
  verts.append((xx,yy,zz))
faces=[]
for r in range(3):
 for i in range(N):faces.append((r*N+i,r*N+(i+1)%N,(r+1)*N+(i+1)%N,(r+1)*N+i))
faces.append(tuple(range(3*N,4*N)))
me=bpy.data.meshes.new('Mouth curved lining');me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new('Mouth • deep curved black interior',me);model.objects.link(o);me.materials.append(inside)
for p in me.polygons:p.use_smooth=True
sub=o.modifiers.new('Smooth cavity bowl','SUBSURF');sub.levels=2
curve('Smile rim • continuous sculpted lip',[(x,fronty(x,z)-.005,z) for x,z in outline],.032,purple,cyclic=True)
# Official toy uses round black button eyes, without cartoon white pupils.
for sg,label in [(-1,'L'),(1,'R')]:
 eye=ell('Eye.'+label,(sg*.338,fronty(sg*.338,4.205)-.095,4.205),(.232,.072,.228),black)
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
for face in plate.data.polygons:face.use_smooth=False
bpy.ops.mesh.primitive_torus_add(major_segments=96,minor_segments=12,major_radius=.214,minor_radius=.009,location=(0,-.059,3.29),rotation=(pi/2,0,0));finish(bpy.context.object,speaker).name='Mouth • speaker rim'
for ob in model.objects:
 if ob.name not in body_objects:ob.location.z+=0
# Long low S-shaped tail following the official reference. Explicit handles control tangent flow.
cu=bpy.data.curves.new('Tail • explicit tangent S spline','CURVE');cu.dimensions='3D';cu.resolution_u=48;cu.bevel_depth=.145;cu.bevel_resolution=8;cu.use_fill_caps=True
sp=cu.splines.new('BEZIER');sp.bezier_points.add(3)
tailpoints=[((-.38,.30,1.40),(-.18,.25,1.44),(-.94,.43,1.29),1.05),((-1.32,.06,.35),(-1.28,.31,.82),(-1.36,-.19,-.12),1.0),((-.18,-.40,-.17),(-.90,-.42,-.22),(.44,-.38,-.12),.95),((1.05,-.30,-.69),(1.18,-.35,-.29),(1.00,-.28,-.84),.72)]
for bp,(co,hl,hr,r) in zip(sp.bezier_points,tailpoints):bp.co=co;bp.handle_left_type='FREE';bp.handle_right_type='FREE';bp.handle_left=hl;bp.handle_right=hr;bp.radius=r
ob=bpy.data.objects.new('Tail • long flowing S curve',cu);model.objects.link(ob);cu.materials.append(purple)
ell('Tail • softly rounded tapered tip',(1.05,-.30,-.69),(.1044,.1044,.1044),purple,32,24)
# Zipper follows the actual torso surface.
curve('Zipper • surface fitted dark tape',[(0,bodyfront(z),z) for z in [2.62,2.45,2.25,2.00,1.75,1.51,1.46]],.025,zipmat)
for i in range(27):
 z=1.49+i*.039;yy=bodyfront(z)-.006
 bpy.ops.mesh.primitive_cube_add(size=1,location=((-.012 if i%2 else .012),yy,z));ob=bpy.context.object;ob.name='Zipper tooth %02d'%i;ob.scale=(.019,.014,.012);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);finish(ob,teeth);be=ob.modifiers.new('rounded tooth','BEVEL');be.width=.004;be.segments=2
# Actual concave crescent, open to the right, with thickness and bevel.
R=.27;r=.233;d=.145;xx=(R*R-r*r+d*d)/(2*d);zz=sqrt(R*R-xx*xx);a=math.atan2(zz,xx);b=math.atan2(-zz,xx-d)
moonpts=[]
for i in range(65):
 t=a+(2*pi-2*a)*i/64;moonpts.append((R*cos(t),2.25+R*sin(t)))
for i in range(65):
 t=b+(-2*pi-2*b)*i/64;moonpts.append((d+r*cos(t),2.25+r*sin(t)))
polyextrude('Pendant • solid gold crescent',moonpts,-.53,-.45,gold,.022)
# Pendant bail.
bpy.ops.mesh.primitive_torus_add(major_segments=40,minor_segments=12,location=(0,-.45,2.56),rotation=(pi/2,0,0),major_radius=.045,minor_radius=.014);finish(bpy.context.object,gold).name='Pendant • bail'
curve('Pendant • short attachment',[(0,bodyfront(2.61),2.61),(0,-.34,2.59),(0,-.45,2.56)],.013,gold)
# Neck transition is integrated into the continuous torso loft.
# Group objects under one clear root, retaining every mesh/spline editable.
root=bpy.data.objects.new('CATNAP_ROOT • unrigged shape draft',None);model.objects.link(root)
for o in list(model.objects):
 if o!=root:o.parent=root
# Studio: neutral lighting for silhouette approval.
floor=mat('Studio neutral floor',(.19,.205,.23),.85)
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,.20));o=bpy.context.object;o.name='Studio floor';move(o,studio);o.data.materials.append(floor);o.hide_render=True
def aim(o,point):o.rotation_euler=(Vector(point)-o.location).to_track_quat('-Z','Y').to_euler()
def area(name,loc,power,size,color):
 da=bpy.data.lights.new(name,'AREA');da.energy=power;da.shape='DISK';da.size=size;da.color=color;o=bpy.data.objects.new(name,da);studio.objects.link(o);o.location=loc;aim(o,(0,0,2.6))
area('Key • large neutral softbox',(-3.8,-5,7),700,5,(1,.94,.88));area('Fill • frontal',(4,-4,4.6),500,4,(.90,.94,1));area('Separation',(2,3,6),800,4,(1,1,1))
world=bpy.data.worlds.new('Neutral studio') if not bpy.data.worlds else bpy.data.worlds[0];bpy.context.scene.world=world;world.use_nodes=True;world.node_tree.nodes.get('Background').inputs[0].default_value=(.16,.18,.22,1);world.node_tree.nodes.get('Background').inputs[1].default_value=.4
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.device='CPU';sc.cycles.samples=32;sc.cycles.use_denoising=True
sc.render.resolution_x=1000;sc.render.resolution_y=1200;sc.render.resolution_percentage=100;sc.view_settings.view_transform='AgX';sc.render.image_settings.file_format='PNG';sc.render.film_transparent=False
cams=[]
for name,loc,scale in [('Front',(0,-12,2.10),6.5),('Three-quarter',(6,-12,3.1),6.6),('Side',(12,0,2.10),6.5),('Back',(0,12,2.10),6.5)]:
 da=bpy.data.cameras.new(name);da.type='ORTHO';da.ortho_scale=scale;o=bpy.data.objects.new(name,da);studio.objects.link(o);o.location=loc;aim(o,(0,0,2.10));cams.append(o)
headcams=[]
for name,loc,target,scale in [('Head-front',(0,-12,3.9),(0,0,3.9),2.7),('Head-three-quarter',(6,-12,4.8),(0,0,3.9),2.8),('Ear-root',(5,-10,5.1),(.45,0,4.35),1.8)]:
 da=bpy.data.cameras.new(name);da.type='ORTHO';da.ortho_scale=scale;ob=bpy.data.objects.new(name,da);studio.objects.link(ob);ob.location=loc;aim(ob,target);headcams.append(ob)
sc.camera=cams[1]
# Embed the official reference inside the editable scene, but keep it out of exports/renders.
ref=bpy.data.images.load(ROOT+'/work/model-reference/official-catnap.png');ref.pack();ref.name='REFERENCE • official CatNap • source in README'
ref2=bpy.data.images.load(ROOT+'/work/model-reference/teepublic-catnap.jpg');ref2.pack();ref2.name='REFERENCE • user supplied TeePublic design'
ref3=bpy.data.images.load(ROOT+'/work/model-reference/official-catnap-icon.png');ref3.pack();ref3.name='REFERENCE • official CatNap page icon'
# Save original editable model; export only character objects.
bpy.ops.wm.save_as_mainfile(filepath=OUT+'/CatNap-shape-v06.blend')
bpy.ops.object.select_all(action='DESELECT')
for o in model.objects:o.select_set(True)
bpy.context.view_layer.objects.active=head
bpy.ops.export_scene.gltf(filepath=OUT+'/CatNap-shape-v06.glb',export_format='GLB',use_selection=True,export_apply=True,export_animations=False,export_cameras=False,export_lights=False)
if os.environ.get('CATNAP_PREVIEW')=='1':
 sc.cycles.samples=16;sc.render.resolution_x=800;sc.render.resolution_y=800;sc.render.film_transparent=True
 for cam in [headcams[0],headcams[2]]:
  sc.camera=cam;sc.render.filepath=ROOT+'/work/catnap-model/v06-preview-'+cam.name+'.png';bpy.ops.render.render(write_still=True)
 print('PREVIEW_COMPLETE',flush=True);raise SystemExit(0)
sc.render.resolution_x=1200;sc.render.resolution_y=1200;sc.render.film_transparent=True;sc.render.image_settings.color_mode='RGBA'
for cam in headcams:
 sc.camera=cam;sc.render.filepath=OUT+'/'+cam.name+'.png';bpy.ops.render.render(write_still=True)
sc.camera=headcams[1];bpy.ops.wm.save_as_mainfile(filepath=OUT+'/CatNap-shape-v06.blend')
print('CATNAP_MODEL_COMPLETE',flush=True)
