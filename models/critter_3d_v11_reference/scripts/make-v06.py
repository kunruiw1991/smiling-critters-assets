from pathlib import Path
p=Path('work/catnap-model/build-v05.py').read_text().replace('v05','v06')
a=p.index('ears=[]');b=p.index(' bpy.context.view_layer.objects.active=ob',a)
p=p[:a]+'''# Convex cubic silhouette: no inward kink on either side of the pointed ear.
def cubic2(a,b,c,d,n=12):
 return [tuple((1-t)**3*a[k]+3*(1-t)**2*t*b[k]+3*(1-t)*t*t*c[k]+t**3*d[k] for k in range(2)) for t in [j/n for j in range(n)]]
ear_outline=[]
for segment in [((.22,4.45),(.29,4.67),(.51,4.93),(.645,4.99)),((.645,4.99),(.665,5.012),(.690,5.012),(.708,4.985)),((.708,4.985),(.83,4.90),(.88,4.45),(.845,4.14)),((.845,4.14),(.62,4.10),(.37,4.23),(.22,4.45))]:
 ear_outline+=cubic2(*segment)
ears=[]
for sg,label in [(-1,'L'),(1,'R')]:
 points=[(sg*x,z) for x,z in ear_outline]
 ob=ear_shell('Ear.'+label,points,sg*.605,4.54,purple)
'''+p[b:]
# This revision concentrates renders on the ears/head; previous body design is preserved.
a=p.index('for cam in cams[:2]:',p.index("if os.environ.get('CATNAP_PREVIEW')"))
b=p.index('sc.render.resolution_x=1200',a);p=p[:a]+p[b:]
Path('work/catnap-model/build-v06.py').write_text(p)
Path('work/catnap-model/verify-v06.py').write_text(Path('work/catnap-model/verify-v05.py').read_text().replace('v05','v06'))
