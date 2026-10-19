from PIL import Image,ImageDraw,ImageFont
from pathlib import Path
R=Path('/Users/kunruiwang/Documents/Codex/2026-10-17/ni');out=R/'outputs/CatNap-3D-v06';S=1100
ref=Image.open(R/'work/model-reference/official-catnap.png').convert('RGBA').crop((445,0,1055,610)).resize((S,S),Image.Resampling.LANCZOS)
def aligned(path):
 im=Image.open(path).convert('RGBA');x0=600+((445-750)/258)*1200/2.7;y0=600-(2.76+595/258-3.9)*1200/2.7;k=(610/S)/258*1200/2.7
 return im.transform((S,S),Image.Transform.AFFINE,(k,0,x0,0,k,y0),Image.Resampling.BICUBIC)
def bg(im):
 a=Image.new('RGBA',im.size,(52,55,64,255));a.alpha_composite(im);return a.convert('RGB')
font=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',27)
def title(im,label):
 a=Image.new('RGB',(im.width,im.height+75),(28,31,38));a.paste(im,(0,75));ImageDraw.Draw(a).text((20,22),label,font=font,fill='white');return a
new=aligned(out/'Head-front.png');old=aligned(R/'outputs/CatNap-3D-v05/Head-front.png')
a=Image.new('RGB',(S*2,S+75));a.paste(title(bg(ref),'Official CatNap'),(0,0));a.paste(title(bg(new),'Blender v06 - fixed scale'),(S,0));a.save(out/'Head-comparison.png')
box=(570,0,1010,470);W,H=550,588
sheet=Image.new('RGB',(W*3,H+75))
for j,(im,label) in enumerate([(ref,'Official reference'),(old,'v05 - previous'),(new,'v06 - convex edge')]):
 panel=bg(im).crop(box).resize((W,H),Image.Resampling.LANCZOS);sheet.paste(title(panel,label),(j*W,0))
sheet.save(out/'Ear-comparison.png')
title(Image.blend(bg(ref),bg(new),.5),'50% reference / 50% v06 - fixed scale').save(out/'Head-overlay.png')
