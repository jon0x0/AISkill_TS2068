"""Original RGB artwork and hardware-constrained Sierra Lite error diffusion.

Diffusion stencil: right 1/2, down-left 1/4, down 1/4. First project RGB
onto each legal ink/paper pair, then diffuse the scalar ink-coverage error.
Moving bands use one pair per scanline so pixel shifts preserve their colors.
"""
from PIL import Image

PALETTE=[(0,0,0),(0,0,205),(205,0,0),(205,0,205),(0,205,0),(0,205,205),(205,205,0),(205,205,205),
         (0,0,0),(0,0,255),(255,0,0),(255,0,255),(0,255,0),(0,255,255),(255,255,0),(255,255,255)]
PAIRS=[(bright*8+p,bright*8+i) for bright in range(2) for p in range(8) for i in range(p+1,8)]
def mix(a,b,t): return tuple(int(x+(y-x)*t) for x,y in zip(a,b))
def gradient(stops,y):
    for (y0,c0),(y1,c1) in zip(stops,stops[1:]):
        if y<=y1:return mix(c0,c1,max(0,(y-y0)/(y1-y0)))
    return stops[-1][1]
def dist(a,b):return sum((x-y)**2 for x,y in zip(a,b))
def quantize(im, row_pairs=None, allowed_pairs=None, serpentine=False, pair_filter=None):
    w,h=im.size; src=list(im.getdata()); buf=[0.0]*(w*h)
    bits=[];attrs=[]
    for y in range(h):
        ar=[]
        for cell in range(w//8):
            if row_pairs is not None:paper,ink=row_pairs[y]
            else:
                samples=src[y*w+cell*8:y*w+cell*8+8]
                # Fit the line between two legal colors, so intermediate RGB
                # colors are represented by spatial mixtures, not hard bands.
                def score(pair):
                    p,q=[PALETTE[k] for k in pair];v=[b-a for a,b in zip(p,q)];den=sum(t*t for t in v)
                    total=0
                    for rgb in samples:
                        t=max(0,min(1,sum((a-b)*c for a,b,c in zip(rgb,p,v))/den))
                        total+=sum((rgb[j]-p[j]-t*v[j])**2 for j in range(3))
                    return total
                candidates=allowed_pairs or PAIRS
                if pair_filter:candidates=pair_filter(samples,candidates)
                paper,ink=min(candidates,key=score)
            ar.append((64 if ink>=8 else 0)+((paper&7)<<3)+(ink&7))
            p,q=[PALETTE[c] for c in (paper,ink)]
            v=[b-a for a,b in zip(p,q)];den=sum(t*t for t in v)
            for x in range(cell*8,cell*8+8):
                rgb=src[y*w+x]
                buf[y*w+x]=max(0,min(1,sum((a-b)*c for a,b,c in zip(rgb,p,v))/den))
        attrs.append(ar)
    for y in range(h):
        row=[0]*w
        direction=-1 if serpentine and y&1 else 1
        for x in (range(w-1,-1,-1) if direction<0 else range(w)):
            coverage=buf[y*w+x];bit=int(coverage>=.5);row[x]=bit
            err=coverage-bit
            for dx,dy,f in [(direction,0,.5),(-direction,1,.25),(0,1,.25)]:
                xx,yy=x+dx,y+dy
                if 0<=xx<w and yy<h:buf[yy*w+xx]+=err*f
        bits.append(row)
    return bits,attrs

