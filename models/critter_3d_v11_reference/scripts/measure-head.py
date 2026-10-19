from PIL import Image
import numpy as np
from collections import deque
a=np.asarray(Image.open('work/model-reference/official-catnap.png').convert('RGBA')).astype(float)
r,g,b,alpha=[a[:,:,i] for i in range(4)]
gray=(alpha>220)&(g>r*.55)&(g>b*.50)&(np.maximum.reduce([r,g,b])<220)
def cc(mask):
 seen=np.zeros(mask.shape,bool);out=[]
 for yy,xx in zip(*np.nonzero(mask)):
  if seen[yy,xx]:continue
  q=deque([(yy,xx)]);seen[yy,xx]=1;coords=[]
  while q:
   y,x=q.popleft();coords.append((y,x))
   for dy,dx in [(1,0),(-1,0),(0,1),(0,-1)]:
    v,u=y+dy,x+dx
    if 0<=v<mask.shape[0] and 0<=u<mask.shape[1] and mask[v,u] and not seen[v,u]:seen[v,u]=1;q.append((v,u))
  if len(coords)>100:
   ps=np.array(coords);out.append((len(coords),tuple(ps.min(0)),tuple(ps.max(0))))
 return sorted(out,reverse=True)
mask=gray[130:305,550:950];print('Eye-region grayscale components (offset x550 y130):',cc(mask)[:5])
for x in range(500,1001,25):
 ys=np.where(gray[270:590,x])[0]+270
 ys=ys[(ys>=300) | (abs(x-750)>80)]
 if len(ys):print('Mouth x',x,'top-bottom',int(ys.min()),int(ys.max()))
for y in [110,120,140,170,200,240,270,300,350,400,450,500,540,560,580,590]:
 xs=np.where(alpha[y,430:1070]>220)[0]+430
 if len(xs):print('Silhouette y',y,'x',int(xs.min()),int(xs.max()))
