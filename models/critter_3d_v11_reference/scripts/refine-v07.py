from pathlib import Path
p=Path('work/catnap-model/build-v07.py');s=p.read_text()
s=s.replace("(.006,.004,.011),.28)","(.006,.004,.011),.38)")
needle='# Round the cut into the existing head shell. No separate lip tube is created.'
s=s.replace(needle,needle+"\nmo=head.modifiers.new('Rolled cloth opening fillet','BEVEL');mo.width=.045;mo.segments=5;mo.limit_method='ANGLE';mo.angle_limit=.6;mo.use_clamp_overlap=False;bpy.ops.object.modifier_apply(modifier=mo.name)")
s=s.replace('mo.iterations=22','mo.iterations=12')
s=s.replace('head.data.materials.append(inside)\nfor face', '''head.data.materials.append(inside)
def in_mouth(x,z):
 inside_poly=False
 for i,(ax,az) in enumerate(outline):
  bx,bz=outline[(i+1)%len(outline)]
  if (az>z)!=(bz>z) and x<(bx-ax)*(z-az)/(bz-az)+ax:inside_poly=not inside_poly
 return inside_poly
for face''')
s=s.replace("if c.y>-.025 and c.y<.02 and 2.82<c.z<4.01 and abs(c.x)<1.03:","if -.025<c.y<.02 and face.normal.y<-.65 and in_mouth(c.x,c.z):")
s=s.replace('yy=edge*(f*f)+(-.012)*(1-f*f)+.018*f','yy=edge*(f*f)+(-.012)*(1-f*f)+.065*f**6')
s=s.replace("y=fronty(x,z)-.004-.105*sqrt(max(0,1-r*r));vs.append((x,y,z))", """base=fronty(cx,cz)
   dx=(fronty(cx+.01,cz)-fronty(cx-.01,cz))/.02;dz=(fronty(cx,cz+.01)-fronty(cx,cz-.01))/.02
   tangent=base+dx*(x-cx)+dz*(z-cz)
   blend=max(0,min(1,(r-.80)/.20));blend=blend*blend*(3-2*blend)
   y=tangent*(1-blend)+fronty(x,z)*blend-.003-.155*sqrt(max(0,1-r*r));vs.append((x,y,z))""")
a=s.index("nose=polyextrude('Nose");b=s.index('# Fine central cloth seam',a)
s=s[:a]+'''nose_outline=catmull([(-.13,4.031),(0,4.044),(.13,4.031),(.09,3.980),(0,3.901),(-.09,3.980)],8)
vs=[];N=len(nose_outline);rs=[.015,.20,.40,.60,.78,.90,.97,1.0]
for r in rs:
 for x,z in nose_outline:
  xx=x*r;zz=3.989+(z-3.989)*r
  # Every perimeter point is seated on the head; the padded center projects gently forward.
  yy=analyticfront(xx,zz)-.004-.055*sqrt(max(0,1-r*r))
  vs.append((xx,yy,zz))
fs=[tuple(reversed(range(N)))]
for k in range(len(rs)-1):
 for j in range(N):fs.append((k*N+j,k*N+(j+1)%N,(k+1)*N+(j+1)%N,(k+1)*N+j))
off=len(vs)
for x,y,z in vs[(len(rs)-1)*N:]:vs.append((x,y+.045,z))
for j in range(N):fs.append(((len(rs)-1)*N+j,(len(rs)-1)*N+(j+1)%N,off+(j+1)%N,off+j))
fs.append(tuple(range(off,off+N)))
me=bpy.data.meshes.new('Soft triangular nose volume');me.from_pydata(vs,[],fs);me.update();nose=bpy.data.objects.new('Nose • flush seated padded triangle',me);model.objects.link(nose);me.materials.append(black)
for f in me.polygons:f.use_smooth=True
bpy.ops.object.select_all(action='DESELECT');nose.select_set(True);bpy.context.view_layer.objects.active=nose;bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT')
'''+s[b:]
p.write_text(s)
