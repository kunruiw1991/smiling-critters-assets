from PIL import Image,ImageDraw,ImageFont
from pathlib import Path
ROOT=Path('/Users/kunruiwang/Documents/Codex/2026-10-17/ni');out=ROOT/'outputs/CatNap-3D-v05'
S=1100
ref=Image.open(ROOT/'work/model-reference/official-catnap.png').convert('RGBA').crop((445,0,1055,610)).resize((S,S),Image.Resampling.LANCZOS)
model=Image.open(out/'Head-front.png').convert('RGBA')
def mapping(u,v):
 rx=445+u*610/S;ry=v*610/S
 x=(rx-750)/258;z=2.76+(595-ry)/258
 return 600+x*1200/2.7,600-(z-3.9)*1200/2.7
x0,y0=mapping(0,0);x1,_=mapping(1,0);_,y1=mapping(0,1)
model=model.transform((S,S),Image.Transform.AFFINE,(x1-x0,0,x0,0,y1-y0,y0),Image.Resampling.BICUBIC)
def bg(im):
 a=Image.new('RGBA',im.size,(52,55,64,255));a.alpha_composite(im);return a.convert('RGB')
ref,model=bg(ref),bg(model)
font=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',32)
small=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',22)
def title(im,label):
 a=Image.new('RGB',(im.width,im.height+90),(28,31,38));a.paste(im,(0,90));d=ImageDraw.Draw(a);d.text((30,20),label,font=font,fill='white');return a
sheet=Image.new('RGB',(S*2,S+90));sheet.paste(title(ref,'Official CatNap reference'),(0,0));sheet.paste(title(model,'Blender model v05 - same scale'),(S,0));sheet.save(out/'Head-comparison.png')
a=title(Image.blend(ref,model,.5),'50% reference / 50% model - fixed scale');a.save(out/'Head-overlay.png')
