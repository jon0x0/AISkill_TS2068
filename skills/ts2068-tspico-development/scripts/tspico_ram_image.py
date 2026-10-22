"""Prepare a stock TSPico multi-block TAP, or rebuild one from TPSAVE chunks."""
import argparse
import hashlib
from pathlib import Path
import struct

SIZE=327680
PAGE=8192
MAGIC=b'CPMRAM1\0\0\x0a\x28\x20'

def magic(image):
    if len(image) not in (163840,327680):raise ValueError('expected 160KB or 320KB')
    return MAGIC[:9]+bytes((len(image)//32768,len(image)//8192,len(image)//10240))

def tap_code(name,data):
    header=bytes([3])+name.encode('ascii').ljust(10,b' ')+struct.pack('<HHH',len(data),0xa000,0x8000)
    out=bytearray()
    for flag,payload in [(0,header),(255,data)]:
        block=bytes([flag])+payload
        crc=0
        for byte in block: crc^=byte
        block+=bytes([crc]);out+=struct.pack('<H',len(block))+block
    return bytes(out)

def blocks(data):
    result=[];offset=0
    while offset<len(data):
        if offset+2>len(data): raise ValueError('truncated TAP length')
        length=struct.unpack_from('<H',data,offset)[0];offset+=2
        block=data[offset:offset+length];offset+=length
        if len(block)!=length or length<2: raise ValueError('truncated TAP block')
        crc=0
        for byte in block:crc^=byte
        if crc:raise ValueError('TAP checksum mismatch')
        result.append(block)
    return result

def decode_chunk(data,name):
    parts=blocks(data)
    if len(parts)!=2 or len(parts[0])!=19 or parts[0][0:2]!=b'\0\x03':raise ValueError('expected one TAP CODE chunk')
    if parts[0][2:12].rstrip()!=name.encode():raise ValueError('wrong chunk name/order')
    if struct.unpack_from('<H',parts[0],12)[0]!=PAGE or len(parts[1])!=PAGE+2 or parts[1][0]!=255:raise ValueError('wrong chunk size')
    return parts[1][1:-1]

def encode_image(image):
    magic(image)
    metadata=(magic(image)+bytes(4)+hashlib.sha256(image).digest()).ljust(128,b'\0')
    return tap_code('CPMRAM',metadata)+b''.join(tap_code(f'CPM{i:02}',image[i*PAGE:(i+1)*PAGE]) for i in range(len(image)//PAGE))

def encode_volumes(image):
    magic(image)
    result={}
    for volume in range(len(image)//40960):
        metadata=(magic(image)+bytes((volume,len(image)//40960,0,0))+hashlib.sha256(image).digest()).ljust(128,b'\0')
        result[f'CPM3200{volume}.TAP']=tap_code('CPMRAM',metadata)+b''.join(
            tap_code(f'CPM{i:02}',image[i*PAGE:(i+1)*PAGE]) for i in range(volume*5,volume*5+5))
    return result

def decode_image(data):
    parts=blocks(data)
    if len(parts) not in (42,82) or parts[1][0]!=255 or len(parts[1])!=130 or parts[1][1:13]!=magic(bytes(((len(parts)-2)//2)*PAGE)):
        raise ValueError('expected one complete 320KB CP/M TAP disk')
    return b''.join(decode_chunk(struct.pack('<H',len(parts[i]))+parts[i]+struct.pack('<H',len(parts[i+1]))+parts[i+1],f'CPM{(i-2)//2:02}') for i in range(2,len(parts),2))

def decode_volumes(folder):
    names={p.name.upper():p for p in folder.iterdir() if p.is_file()};pages=[];identity=None
    first=blocks(names['CPM32000.TAP'].read_bytes())
    count=first[1][14]
    if count not in (4,8):raise ValueError('invalid volume count')
    for volume in range(count):
        parts=blocks(names[f'CPM3200{volume}.TAP'].read_bytes())
        if len(parts)!=12 or len(parts[1])!=130 or parts[1][1:13]!=magic(bytes(count*40960)) or parts[1][13:15]!=bytes((volume,count)):
            raise ValueError('invalid boot volume metadata/order')
        if identity is None:identity=parts[1][17:49]
        elif identity!=parts[1][17:49]:raise ValueError('mixed disk identities')
        for i in range(5):
            h,d=parts[2+i*2:4+i*2]
            pages.append(decode_chunk(struct.pack('<H',len(h))+h+struct.pack('<H',len(d))+d,f'CPM{volume*5+i:02}'))
    return b''.join(pages)

def page_checksum(data):
    a=b=0
    for value in data:
        a=(a+value)%255;b=(b+a)%255
    return a|(b<<8)

def decode_saved_chunks(folder,kb=None):
    entries={p.name.upper():p for p in folder.iterdir() if p.is_file()}
    descriptor=None
    if 'CPMSTATE.TAP' in entries:
        parts=blocks(entries['CPMSTATE.TAP'].read_bytes())
        if len(parts)!=2 or len(parts[0])!=19 or parts[0][:2]!=b'\0\x03' or parts[0][2:12].rstrip()!=b'CPMSTATE' or parts[0][12:14]!=b'\x80\0' or len(parts[1])!=130 or parts[1][0]!=255:
            raise ValueError('invalid saved-disk descriptor')
        descriptor=parts[1][1:-1]
        if descriptor[:8]!=b'CPMSAV1\0' or descriptor[8]!=1 or descriptor[9] not in (5,10) or descriptor[10]!=descriptor[9]*4:
            raise ValueError('incomplete/invalid saved-disk descriptor')
        actual=descriptor[9]*32
        if kb is not None and kb!=actual:raise ValueError('requested geometry differs from saved disk')
        kb=actual
    if kb is None:kb=320
    pages=[]
    for i in range(kb//8):
        name=f'CPM{i:02}.TAP'
        if name not in entries:raise ValueError('missing saved page '+name)
        page=decode_chunk(entries[name].read_bytes(),f'CPM{i:02}')
        if descriptor is not None and page_checksum(page)!=int.from_bytes(descriptor[12+i*2:14+i*2],'little'):
            raise ValueError('mixed/corrupt saved page '+name)
        pages.append(page)
    return b''.join(pages)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    source=parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--image',type=Path)
    source.add_argument('--dsk',type=Path,help='160KB/320KB standard Fuse Oliger DSK')
    source.add_argument('--chunks',type=Path,help='directory containing CPM00.TAP through CPM39.TAP')
    parser.add_argument('--chunk-kb',type=int,choices=(160,320),help='old export geometry; new descriptors supply it automatically')
    source.add_argument('--tap',type=Path,help='one complete CP/M TAP disk to split/repack')
    source.add_argument('--boot-volumes',type=Path,help='directory containing CPM32000.TAP through CPM32007.TAP')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--raw-output',type=Path)
    parser.add_argument('--dsk-output',type=Path)
    parser.add_argument('--force',action='store_true')
    parser.add_argument('--volumes',type=Path,help='also write eight <45KB boot volumes into this directory')
    args=parser.parse_args()
    if args.output.exists() and not args.force:raise SystemExit('Output exists; use --force after preserving it')
    from oliger_image import decode_dsk,encode_dsk
    for target in (args.raw_output,args.dsk_output):
        if target and target.exists() and not args.force:raise SystemExit('Output exists; preserve it or use --force')
    if args.dsk:image=decode_dsk(args.dsk.read_bytes())
    elif args.image:image=args.image.read_bytes()
    elif args.tap:image=decode_image(args.tap.read_bytes())
    elif args.boot_volumes:image=decode_volumes(args.boot_volumes)
    else:
        image=decode_saved_chunks(args.chunks,args.chunk_kb)
    volumes=encode_volumes(image) if args.volumes else {}
    if args.volumes:
        for name in volumes:
            if (args.volumes/name).exists() and not args.force:raise SystemExit('Volume exists; use --force after preserving it')
    encoded=encode_image(image)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_bytes(encoded)
    if args.volumes:
        args.volumes.mkdir(parents=True,exist_ok=True)
        for name,data in volumes.items():(args.volumes/name).write_bytes(data)
    if args.raw_output:args.raw_output.write_bytes(image)
    if args.dsk_output:args.dsk_output.write_bytes(encode_dsk(image,len(image)//163840))
    print(f'{args.output}: {len(image)} bytes, SHA256 {hashlib.sha256(image).hexdigest()}')

if __name__=='__main__':main()
