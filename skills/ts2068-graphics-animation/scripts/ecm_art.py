"""Convert RGBA art or RGB gradients into TS2068 ECM planes (Pillow required)."""
from pathlib import Path
import argparse,json,hashlib
from PIL import Image
from sierra_lite import PALETTE,PAIRS,quantize,gradient

def offset(y):
    return ((y&192)<<5)+((y&7)<<8)+((y&56)<<2)

def pack(bits,attrs):
    bitmap=bytearray(6144);colors=bytearray(6144)
    for y,(row,ar) in enumerate(zip(bits,attrs)):
        for x,a in enumerate(ar):
            bitmap[offset(y)+x]=sum(row[x*8+b]<<(7-b) for b in range(8))
            colors[offset(y)+x]=a
    return bytes(bitmap),bytes(colors)

def decode(bitmap,attrs):
    im=Image.new('RGB',(256,192));pixels=[]
    for y in range(192):
        for x in range(256):
            i=offset(y)+x//8;a=attrs[i]
            c=(a&7) if bitmap[i]&(128>>(x&7)) else ((a>>3)&7)
            pixels.append(PALETTE[c+(8 if a&64 else 0)])
    im.putdata(pixels);return im

def fit_rows(im):
    # Avoid per-cell palette borders; fit each complete scanline to one pair.
    pairs=[]
    for y in range(im.height):
        samples=[im.getpixel((x,y)) for x in range(im.width)]
        def error(pair):
            p,q=[PALETTE[c] for c in pair];v=[b-a for a,b in zip(p,q)];den=sum(a*a for a in v)
            total=0
            for rgb in samples:
                t=max(0,min(1,sum((a-b)*c for a,b,c in zip(rgb,p,v))/den))
                total+=sum((rgb[k]-p[k]-t*v[k])**2 for k in range(3))
            return total
        pairs.append(min(PAIRS,key=error))
    return pairs

def convert(rgba,background,mode='row',phase_step=0,threshold=100):
    w,h=rgba.size
    if not (8<=w<=256 and w%8==0 and 1<=h<=192):raise ValueError('Width must be 8..256 in multiples of 8; height 1..192')
    if background.size!=rgba.size:raise ValueError('Background must match the target dimensions')
    if not 0<=threshold<=255:raise ValueError('Alpha threshold must be 0..255')
    if mode not in ('row','cell'):raise ValueError('Unknown palette mode')
    if phase_step not in (0,1,2):raise ValueError('Phase step must be 0, 1 or 2')
    if phase_step and mode!='row':raise ValueError('Fine phases require coherent row palettes')
    rgba=rgba.convert('RGBA');im=Image.alpha_composite(background.convert('RGBA'),rgba).convert('RGB')
    bits,attrs=quantize(im,row_pairs=fit_rows(im) if mode=='row' else None,serpentine=True)
    mask=[[int(rgba.getpixel((x,y))[3]<threshold) for x in range(w)] for y in range(h)]
    phases=[]
    for shift in range(0,8,phase_step or 8):
        rotate=lambda rows:[row[shift:]+row[:shift] for row in rows]
        bitmap,colors=pack(rotate(bits),attrs)
        active_mask,_=pack(rotate(mask),[[0]*(w//8) for _ in range(h)])
        preserve=bytearray([255])*6144
        for y in range(h):preserve[offset(y):offset(y)+w//8]=active_mask[offset(y):offset(y)+w//8]
        phases.append((shift,bitmap,colors,bytes(preserve)))
    return im,phases

def hex_color(s):
    s=s.removeprefix('#')
    if len(s)!=6:raise ValueError('Expected RRGGBB')
    return tuple(bytes.fromhex(s))

def make_gradient(width,height,stops):
    if len(stops)<2 or any(stops[i][0]>=stops[i+1][0] for i in range(len(stops)-1)):
        raise ValueError('At least two strictly increasing gradient stops are required')
    im=Image.new('RGBA',(width,height))
    for y in range(height):
        color=gradient(stops,y)+(255,)
        for x in range(width):im.putpixel((x,y),color)
    return im

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    for name in ('convert','gradient'):
        q=sub.add_parser(name);q.add_argument('--out',required=True,type=Path)
        q.add_argument('--width',type=int,default=256);q.add_argument('--height',type=int,default=192)
        q.add_argument('--palette-mode',choices=['row','cell'],default='row')
        q.add_argument('--phase-step',type=int,choices=[0,1,2],default=0,help='0=static, 1=eight phases, 2=four phases')
        q.add_argument('--alpha-threshold',type=int,default=100)
        if name=='convert':
            q.add_argument('image',type=Path);q.add_argument('--background',type=Path)
            q.add_argument('--background-color',default='000000',help='RRGGBB, used when no background image is given')
        else:q.add_argument('--stop',action='append',required=True,help='Y:RRGGBB, in increasing Y order')
    a=p.parse_args()
    if not (8<=a.width<=256 and a.width%8==0 and 1<=a.height<=192):p.error('Invalid ECM dimensions')
    size=(a.width,a.height);source_hash=None
    if a.command=='convert':
        source_hash=hashlib.sha256(a.image.read_bytes()).hexdigest()
        # Pillow's premultiplied RGBa avoids hidden RGB contaminating alpha edges.
        im=Image.open(a.image).convert('RGBA').convert('RGBa').resize(size,Image.Resampling.LANCZOS).convert('RGBA')
        bg=Image.open(a.background).convert('RGBA').resize(size,Image.Resampling.LANCZOS) if a.background else Image.new('RGBA',size,hex_color(a.background_color)+(255,))
        if bg.getchannel('A').getextrema()!=(255,255):p.error('Background must be opaque')
    else:
        stops=[(int(s.split(':',1)[0]),hex_color(s.split(':',1)[1])) for s in a.stop]
        im=make_gradient(*size,stops);bg=Image.new('RGBA',size,(0,0,0,255))
    composite,phases=convert(im,bg,a.palette_mode,a.phase_step,a.alpha_threshold)
    a.out.mkdir(parents=True,exist_ok=True);composite.save(a.out/'source-composite.png')
    manifest={'width':a.width,'height':a.height,'layout':'Spectrum nonlinear scanlines, 6144 bytes per plane',
              'palette_mode':a.palette_mode,'phase_step':a.phase_step,'mask':'1 preserves background; 0 replaces',
              'alpha_threshold':a.alpha_threshold,'source_sha256':source_hash,'phases':[]}
    for shift,bitmap,attrs,mask in phases:
        stem=f'phase-{shift}';files={}
        for suffix,data in [('bitmap',bitmap),('attrs',attrs),('mask',mask)]:
            name=f'{stem}.{suffix}.bin';(a.out/name).write_bytes(data);files[name]=hashlib.sha256(data).hexdigest()
        decode(bitmap,attrs).save(a.out/f'{stem}.png');manifest['phases'].append({'pixels':shift,'sha256':files})
    (a.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(f'Exported {len(phases)} ECM phase(s) to {a.out}')
if __name__=='__main__':main()
