from PIL import Image,ImageChops,ImageFont,ImageDraw
from pathlib import Path
root=Path('/Users/kunruiwang/Documents/Codex/2026-10-17/ni')
ref=Image.open(root/'work/model-reference/official-catnap.png').convert('RGBA')
model=Image.open(root/'outputs/CatNap-3D-v04/Front.png').convert('RGB')
bg=model.getpixel((0,0));diff=ImageChops.difference(model,Image.new('RGB',model.size,bg)).convert('L');mask=diff.point(lambda v:255 if v>12 else 0)
model=model.crop(mask.getbbox());ref=ref.crop(ref.getchannel('A').getbbox())
canvas=Image.new('RGB',(1320,1200),bg)
for x,im in [(0,ref),(660,model)]:
 scale=min(560/im.width,1050/im.height);im=im.resize((round(im.width*scale),round(im.height*scale)),Image.Resampling.LANCZOS)
 pos=(x+(660-im.width)//2,95+(1050-im.height)//2)
 if im.mode=='RGBA':canvas.paste(im,pos,im.getchannel('A'))
 else:canvas.paste(im,pos)
try:font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',30)
except OSError:font=ImageFont.load_default()
draw=ImageDraw.Draw(canvas)
for label,x in [('Official reference',0),('Model v04',660)]:
 width=draw.textbbox((0,0),label,font=font)[2];draw.text((x+(660-width)//2,28),label,font=font,fill=(238,238,240))
canvas.save(root/'outputs/CatNap-3D-v04/Reference-comparison.png')
