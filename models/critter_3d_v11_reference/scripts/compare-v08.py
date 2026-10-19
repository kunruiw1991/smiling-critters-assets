from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
R=Path('/Users/kunruiwang/Documents/Codex/2026-10-17/ni');O=R/'outputs/CatNap-3D-v08';S=1200
ref=Image.open(R/'work/model-reference/official-catnap.png').convert('RGBA')
k=4.1*258/S;ref=ref.transform((S,S),Image.Transform.AFFINE,(k,0,750-2.05*258,0,k,595-(1.05+2.05-2.76)*258),Image.Resampling.BICUBIC)
old=Image.open(R/'work/catnap-model/v07-body-front.png').convert('RGBA');new=Image.open(O/'Body-front.png').convert('RGBA')
def bg(im):
 a=Image.new('RGBA',im.size,(52,55,64,255));a.alpha_composite(im);return a.convert('RGB')
font=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',28)
W=700;sheet=Image.new('RGB',(3*W,W+70),(28,31,38));d=ImageDraw.Draw(sheet)
for i,(im,label) in enumerate([(ref,'Official reference'),(old,'v07 - previous body'),(new,'v08 - revised body')]):
 sheet.paste(bg(im).resize((W,W),Image.Resampling.LANCZOS),(i*W,70));d.text((i*W+20,20),label,font=font,fill='white')
sheet.save(O/'Body-comparison.png')
