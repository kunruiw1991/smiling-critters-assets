from pathlib import Path
s=Path('work/catnap-model/build-v03.py').read_text().replace('/outputs/CatNap-3D-v03','/outputs/CatNap-3D-v04').replace('shape review v03','shape review v04').replace('shape-v03','shape-v04')
a=s.index('# Chubby plush proportions:');b=s.index('# Reference-driven silhouette:',a)
s=s[:a]+'''# Proportions measured against the official plush render: head including ears ~48% of ear-to-toe height.
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
body_profile=[(1.40,.07,.10),(1.44,.34,.24),(1.52,.50,.34),(1.70,.575,.405),(1.90,.60,.43),(2.10,.56,.415),(2.32,.46,.35),(2.50,.37,.28),(2.62,.27,.22),(2.70,.14,.16),(2.73,.07,.09)]
body=plush_loft('Torso • official-reference cloth silhouette',[(z,w,d,0,0) for z,w,d in body_profile],[purple])
def bodyfront(z):
 for i in range(len(body_profile)-1):
  a,b=body_profile[i],body_profile[i+1]
  if z<=b[0]:
   f=max(0,min(1,(z-a[0])/(b[0]-a[0])));return -(a[2]*(1-f)+b[2]*f)-.015
 return -.12
for sg,label in [(-1,'L'),(1,'R')]:
 legp=[(.20,.018,.020,sg*.34,-.07),(.25,.13,.16,sg*.34,-.075),(.34,.245,.275,sg*.34,-.05),(.52,.285,.29,sg*.33,-.01),(.78,.275,.275,sg*.31,.005),(1.05,.235,.245,sg*.285,.01),(1.30,.195,.225,sg*.26,.015),(1.46,.12,.17,sg*.245,.02),(1.52,.02,.05,sg*.24,.02)]
 plush_loft('Leg.'+label+' • seamless rounded cloth leg',legp,[purple,dark],.56)
 armp=[(1.38,.018,.022,sg*.96,-.055),(1.43,.115,.13,sg*.94,-.06),(1.54,.19,.195,sg*.87,-.055),(1.72,.215,.205,sg*.78,-.04),(1.95,.205,.20,sg*.675,-.02),(2.20,.19,.185,sg*.55,0),(2.42,.16,.16,sg*.44,.01),(2.59,.10,.12,sg*.35,.015),(2.65,.025,.045,sg*.32,.015)]
 plush_loft('Arm.'+label+' • seamless soft toy arm',armp,[purple,dark],1.73)
body_objects=set(o.name for o in model.objects)
''' +s[b:]
s=s.replace('ob.location.z-=.73','ob.location.z+=0')
a=s.index('# Signature tail.');b=s.index('# Recessed front zipper',a)
s=s[:a]+'''# Long low S-shaped tail following the official reference. Explicit handles control tangent flow.
cu=bpy.data.curves.new('Tail • explicit tangent S spline','CURVE');cu.dimensions='3D';cu.resolution_u=48;cu.bevel_depth=.145;cu.bevel_resolution=8;cu.use_fill_caps=True
sp=cu.splines.new('BEZIER');sp.bezier_points.add(3)
tailpoints=[((-0.18,.34,1.53),(-.01,.28,1.57),(-.72,.48,1.47),1.05),((-1.38,.04,.62),(-1.36,.28,.93),(-1.40,-.20,.31),1.0),((-.15,-.52,.39),(-.80,-.50,.35),(.42,-.54,.43),.88),((1.30,-.48,.29),(1.0,-.53,.50),(1.45,-.455,.185),.30)]
for bp,(co,hl,hr,r) in zip(sp.bezier_points,tailpoints):bp.co=co;bp.handle_left_type='FREE';bp.handle_right_type='FREE';bp.handle_left=hl;bp.handle_right=hr;bp.radius=r
ob=bpy.data.objects.new('Tail • long flowing S curve',cu);model.objects.link(ob);cu.materials.append(purple)
ell('Tail • softly rounded tapered tip',(1.30,-.48,.29),(.044,.044,.044),purple,32,24)
''' +s[b:]
a=s.index('# Recessed front zipper');b=s.index('# Actual concave crescent',a)
s=s[:a]+'''# Zipper follows the actual torso surface.
curve('Zipper • surface fitted dark tape',[(0,bodyfront(z),z) for z in [2.62,2.45,2.25,2.00,1.75,1.51,1.46]],.025,zipmat)
for i in range(27):
 z=1.49+i*.039;yy=bodyfront(z)-.006
 bpy.ops.mesh.primitive_cube_add(size=1,location=((-.012 if i%2 else .012),yy,z));ob=bpy.context.object;ob.name='Zipper tooth %02d'%i;ob.scale=(.019,.014,.012);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);finish(ob,teeth);be=ob.modifiers.new('rounded tooth','BEVEL');be.width=.004;be.segments=2
''' +s[b:]
s=s.replace('1.58+R*sin(t)','2.25+R*sin(t)').replace('1.58+r*sin(t)','2.25+r*sin(t)')
s=s.replace('moonpts,-.685,-.605,gold,.022','moonpts,-.53,-.45,gold,.022')
s=s.replace('location=(0,-.605,1.89)','location=(0,-.45,2.56)')
s=s.replace("[(0,-.39,1.88),(0,-.49,1.91),(0,-.605,1.89)]", "[(0,bodyfront(2.61),2.61),(0,-.34,2.59),(0,-.45,2.56)]")
s=s.replace('(sg*.075,-.20,2.265)','(sg*.075,-.20,2.995)')
s=s.replace('(0,.02,2.04),(.20,.22,.13)','(0,.025,2.72),(.18,.21,.12)')
s=s.replace("('Front',(0,-12,2.38),4.85),('Three-quarter',(7,-11,3.5),5.1),('Side',(12,0,2.38),4.85),('Back',(0,12,2.38),4.85)","('Front',(0,-12,2.65),5.8),('Three-quarter',(6,-12,3.5),6.0),('Side',(12,0,2.65),5.8),('Back',(0,12,2.65),5.8)")
s=s.replace('aim(o,(.25,0,2.25))','aim(o,(0,0,2.65))')
s=s.replace('cam.location=(0,-12,3.22);aim(cam,(0,0,3.20))','cam.location=(0,-12,3.95);aim(cam,(0,0,3.93))').replace('cam.location=(6,-12,4.07);aim(cam,(0,0,3.20))','cam.location=(6,-12,4.8);aim(cam,(0,0,3.93))')
# Preview uses the same geometry and cameras, only a smaller temporary render.
s=s.replace('for cam in cams:\n sc.camera=cam',"""if os.environ.get('CATNAP_PREVIEW')=='1':
 sc.cycles.samples=16;sc.render.resolution_x=750;sc.render.resolution_y=900
 for cam in cams[:2]:
  sc.camera=cam;sc.render.filepath=ROOT+'/work/catnap-model/v04-preview-'+cam.name+'.png';bpy.ops.render.render(write_still=True)
 print('PREVIEW_COMPLETE',flush=True);bpy.ops.wm.quit_blender()
for cam in cams:
 sc.camera=cam""")
Path('work/catnap-model/build-v04.py').write_text(s)
Path('outputs/CatNap-3D-v04').mkdir(exist_ok=True)
v=Path('work/catnap-model/verify-v03.py').read_text().replace('CatNap-3D-v03','CatNap-3D-v04').replace('shape-v03','shape-v04').replace('shape review v03','shape review v04')
Path('work/catnap-model/verify-v04.py').write_text(v)
