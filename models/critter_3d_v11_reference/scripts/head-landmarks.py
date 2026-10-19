from PIL import Image,ImageDraw,ImageFont
import numpy as np
from collections import deque
im=Image.open('work/model-reference/official-catnap.png').convert('RGBA');a=np.asarray(im).astype(float);rgb=a[:,:,:3];mx=rgb.max(2);mn=rgb.min(2)
mask=(a[:,:,3]>220)&((mx-mn)<np.maximum(25,mx*.5))&(mx<200)
mask[:260,:]=0;mask[590:,:]=0;mask[:,:470]=0;mask[:,1030:]=0
seen=np.zeros(mask.shape,bool);best=[]
for yy,xx in zip(*np.nonzero(mask)):
 if seen[yy,xx]:continue
 q=deque([(yy,xx)]);seen[yy,xx]=1;pts=[]
 while q:
  y,x=q.popleft();pts.append((y,x))
  for dy,dx in [(1,0),(-1,0),(0,1),(0,-1)]:
   v,u=y+dy,x+dx
   if 0<=v<1500 and 0<=u<1500 and mask[v,u] and not seen[v,u]:seen[v,u]=1;q.append((v,u))
 if len(pts)>len(best):best=pts
p=np.asarray(best);print('Mouth component',len(best),'bbox',p.min(0),p.max(0))
for x in range(500,1001,25):
 ys=p[p[:,1]==x,0]
 if len(ys):print(x,int(ys.min()),int(ys.max()))
# Technical inspection only: preserve original artwork and overlay a coordinate grid.
crop=Image.new('RGBA',(640,620),(65,69,76,255));crop.alpha_composite(im.crop((430,0,1070,620)))
ov=Image.new('RGBA',crop.size);d=ImageDraw.Draw(ov)
for x in range(450,1051,50):
 xx=x-430;d.line((xx,0,xx,620),fill=(245,245,245,70),width=1);d.text((xx+2,2),str(x),fill=(255,255,255,240))
for y in range(50,601,50):d.line((0,y,640,y),fill=(245,245,245,70),width=1);d.text((2,y+2),str(y),fill=(255,255,255,240))
Image.alpha_composite(crop,ov).resize((1280,1240)).save('work/catnap-model/reference-head-grid.png')
