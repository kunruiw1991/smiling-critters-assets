from pathlib import Path
p=Path('work/catnap-model/build-v08.py');s=p.read_text().replace('(.29,.16,.17,sg*.44','(.29,.10,.115,sg*.44').replace('(.34,.275,.25,sg*.44','(.34,.225,.22,sg*.44').replace('(.45,.345,.29,sg*.44','(.45,.33,.28,sg*.44')
a=s.index('controls=[');b=s.index('end=centers[-1].copy()',a)
s=s[:a]+'''# Clamped cubic spline with continuous second derivatives.
knots=list(map(Vector,[(0,.36,1.60),(-.90,.29,1.08),(-1.32,.08,.34),(-1.05,-.22,-.10),(-.22,-.30,-.20),(.60,-.28,-.27),(1.10,-.25,-.62)]))
h=[(knots[i+1]-knots[i]).length for i in range(len(knots)-1)];K=len(knots)
lo=[0.0]*K;diag=[0.0]*K;up=[0.0]*K;rhs=[Vector((0,0,0)) for _ in range(K)]
d0=Vector((-.65,.04,-.10)).normalized();dn=Vector((-.05,0,-.29)).normalized()
diag[0]=2*h[0];up[0]=h[0];rhs[0]=6*((knots[1]-knots[0])/h[0]-d0)
for i in range(1,K-1):
 lo[i]=h[i-1];diag[i]=2*(h[i-1]+h[i]);up[i]=h[i];rhs[i]=6*((knots[i+1]-knots[i])/h[i]-(knots[i]-knots[i-1])/h[i-1])
lo[-1]=h[-1];diag[-1]=2*h[-1];rhs[-1]=6*(dn-(knots[-1]-knots[-2])/h[-1])
for i in range(1,K):
 w=lo[i]/diag[i-1];diag[i]-=w*up[i-1];rhs[i]-=w*rhs[i-1]
M=[Vector((0,0,0)) for _ in range(K)];M[-1]=rhs[-1]/diag[-1]
for i in range(K-2,-1,-1):M[i]=(rhs[i]-up[i]*M[i+1])/diag[i]
centers=[];tangents=[];radii=[];length=sum(h);walk=0
for i,H in enumerate(h):
 for j in range(24+(i==len(h)-1)):
  t=j/24;a=1-t;b=t
  co=a*knots[i]+b*knots[i+1]+((a*a*a-a)*M[i]+(b*b*b-b)*M[i+1])*(H*H/6)
  tangent=(knots[i+1]-knots[i])/H+((-3*a*a+1)*M[i]+(3*b*b-1)*M[i+1])*(H/6)
  centers.append(co);tangents.append(tangent.normalized());u=(walk+t*H)/length;radii.append(.15-.03*u*u)
 walk+=H
'''+s[b:]
p.write_text(s)
