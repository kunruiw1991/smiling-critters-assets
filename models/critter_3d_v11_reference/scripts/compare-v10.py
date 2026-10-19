from PIL import Image,ImageDraw,ImageFont
from pathlib import Path
r=Path('/Users/kunruiwang/Documents/Codex/2026-10-17/ni');out=r/'outputs/CatNap-3D-v10'
W=600
ref=Image.open(r/'work/model-reference/official-catnap.png').convert('RGBA').crop((640,610,850,820)).resize((W,W),Image.Resampling.LANCZOS)
# Fixed official pixels to model coordinates, projected by the same orthographic camera.
a=1000/.95*210/W/258
c=500+1000/.95*(640-750)/258
f=500-1000/.95*(2.76+(595-610)/258-2.35)
images=[ref]
for p in [r/'work/catnap-model/v09-pendant.png',out/'Pendant-front.png']:
 im=Image.open(p).convert('RGBA');images.append(im.transform((W,W),Image.Transform.AFFINE,(a,0,c,0,a,f),Image.Resampling.BICUBIC))
canvas=Image.new('RGB',(1840,700),(239,236,246));d=ImageDraw.Draw(canvas)
font=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',25)
for i,(im,label) in enumerate(zip(images,['OFFICIAL REFERENCE','v09 / BEFORE','v10 / REVISED'])):
 x=10+i*610;canvas.paste(im,(x,70),im);d.text((x+15,24),label,fill=(45,34,62),font=font)
canvas.save(out/'Moon-comparison.png')
