from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
R=Path('/Users/kunruiwang/Documents/Codex/2026-10-17/ni');O=R/'outputs/CatNap-3D-v09';S=1200
ref=Image.open(R/'work/model-reference/official-catnap.png').convert('RGBA');k=4.1*258/S
ref=ref.transform((S,S),Image.Transform.AFFINE,(k,0,750-2.05*258,0,k,595-(1.05+2.05-2.76)*258),Image.Resampling.BICUBIC)
old=Image.open(R/'outputs/CatNap-3D-v08/Body-front.png').convert('RGBA');new=Image.open(O/'Body-front.png').convert('RGBA')
def panel(im):
 a=Image.new('RGBA',im.size,(52,55,64,255));a.alpha_composite(im);return a.convert('RGB').crop((680,890,1120,1180)).resize((660,435),Image.Resampling.LANCZOS)
a=Image.new('RGB',(1980,505),(28,31,38));d=ImageDraw.Draw(a);font=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',28)
for i,(im,label) in enumerate([(ref,'Official reference'),(old,'v08 - previous'),(new,'v09 - fuller rounded tip')]):
 a.paste(panel(im),(660*i,70));d.text((660*i+20,20),label,font=font,fill='white')
a.save(O/'Tail-comparison.png')
