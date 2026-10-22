"""Create, list and copy files into TS2068 CP/M 160KB/320KB DSK/TAP/raw images."""
import argparse
import os
from pathlib import Path
import tempfile
from make_disk import make_disk
from oliger_image import encode_dsk, decode_dsk
from tspico_ram_image import encode_image, decode_image


def image_format(path):
    suffix = Path(path).suffix.lower()
    if suffix == '.dsk': return 'dsk'
    if suffix == '.tap': return 'tap'
    if suffix in ('.img', '.raw'): return 'raw'
    raise ValueError('use a .dsk, .tap, .img or .raw filename')


def decode(path):
    data = Path(path).read_bytes()
    kind = image_format(path)
    raw = decode_dsk(data) if kind == 'dsk' else decode_image(data) if kind == 'tap' else data
    if len(raw) not in (163840, 327680): raise ValueError('expected a TS2068 160KB/320KB disk')
    return raw


def encode(path, raw):
    kind = image_format(path)
    return encode_dsk(raw, len(raw)//163840) if kind == 'dsk' else encode_image(raw) if kind == 'tap' else raw


def read_files(raw):
    """Read the project's user-0, 128-entry, OFF=0 filesystem. Reject other layouts."""
    if len(raw) not in (163840,327680): raise ValueError('unsupported disk geometry')
    block_size = 1024 if len(raw) == 163840 else 2048
    exm = block_size//1024-1
    parts, attrs, used = {}, {}, set()
    for offset in range(0,4096,32):
        entry = raw[offset:offset+32]
        if entry[0] == 0xe5: continue
        if entry[0] != 0 or entry[13] or entry[14] > 63 or entry[12] > 31 or entry[15] > 128:
            raise ValueError('unsupported/corrupt directory (only project user-0 disks supported)')
        stem = bytes(c&127 for c in entry[1:9]).decode('ascii').rstrip()
        ext = bytes(c&127 for c in entry[9:12]).decode('ascii').rstrip()
        name = stem+'.'+ext
        if not stem or not ext or any(c not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!#$%&\'()-@^_`{}~' for c in stem+ext):
            raise ValueError('invalid CP/M filename: '+name)
        extent = entry[12]+32*entry[14]
        count = ((extent&exm)*128+entry[15])*128
        group = extent//(exm+1)
        if group in parts.setdefault(name,{}): raise ValueError('duplicate extent: '+name)
        blocks = [n for n in entry[16:32] if n]
        if len(blocks) != (count+block_size-1)//block_size: raise ValueError('invalid block count: '+name)
        for block in blocks:
            if block < 4096//block_size or block >= len(raw)//block_size or block in used:
                raise ValueError('invalid/shared allocation block')
            used.add(block)
        parts[name][group] = b''.join(raw[n*block_size:(n+1)*block_size] for n in blocks)[:count]
        previous = attrs.get(name,bytes(11))
        attrs[name] = bytes(old|(c&128) for old,c in zip(previous,entry[1:12]))
    files = {}
    for name, extents in parts.items():
        if sorted(extents) != list(range(len(extents))): raise ValueError('missing extent: '+name)
        ordered = [extents[i] for i in range(len(extents))]
        if any(len(data)!=16*block_size for data in ordered[:-1]): raise ValueError('short intermediate extent')
        files[name] = b''.join(ordered)
    return files, attrs


def add_files(raw, sources, replace=False):
    files, attrs = read_files(raw)
    added = set()
    for path in sources:
        path = Path(path); name = path.name.upper()
        pieces = name.split('.')
        if len(pieces)!=2 or not 1<=len(pieces[0])<=8 or not 1<=len(pieces[1])<=3 or any(c not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!#$%&\'()-@^_`{}~' for c in ''.join(pieces)):
            raise ValueError('use a CP/M 8.3 filename: '+name)
        if name in added: raise ValueError('duplicate input filename: '+name)
        if name in files and not replace: raise ValueError(name+' already exists; use --replace')
        files[name] = path.read_bytes(); attrs.pop(name,None); added.add(name)
    result, _, _ = make_disk(list(files.items()),len(raw),128,1024 if len(raw)==163840 else 2048)
    result = bytearray(result)
    for offset in range(0,4096,32):
        entry = result[offset:offset+32]
        if entry[0] == 0xe5: continue
        name = entry[1:9].decode().rstrip()+'.'+entry[9:12].decode().rstrip()
        if name in attrs:
            for i, attr in enumerate(attrs[name]): result[offset+1+i] |= attr
    return bytes(result)


def publish(path, data, replace=False):
    """Stage beside the destination; never leave a partially written disk image."""
    path = Path(path)
    if path.exists() and not replace: raise ValueError('output exists; use --force or choose another path')
    path.parent.mkdir(parents=True,exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name+'.',suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(descriptor,'wb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        if replace: os.replace(temporary,path)
        else: os.link(temporary,path); os.unlink(temporary)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command',required=True)
    create = commands.add_parser('create',help='create a new, empty formatted image')
    create.add_argument('image',type=Path);create.add_argument('--size',type=int,choices=(160,320),default=320)
    create.add_argument('--force',action='store_true')
    listing = commands.add_parser('list');listing.add_argument('image',type=Path)
    copy = commands.add_parser('put',help='copy host files into an image')
    copy.add_argument('image',type=Path);copy.add_argument('files',nargs='+',type=Path)
    copy.add_argument('--replace',action='store_true',help='replace an existing CP/M filename')
    copy.add_argument('--output',type=Path,help='write a new image instead of updating the source')
    args = parser.parse_args()
    try:
        if args.command == 'create':
            raw,_,_ = make_disk([],args.size*1024,128,1024 if args.size==160 else 2048)
            publish(args.image,encode(args.image,raw),args.force)
            print(f'{args.image}: empty {args.size}KB CP/M disk')
        elif args.command == 'list':
            files,_ = read_files(decode(args.image))
            for name,data in sorted(files.items()): print(f'{name:12} {len(data):7} bytes (CP/M records)')
            print(f'{len(files)} files')
        else:
            raw = add_files(decode(args.image),args.files,args.replace)
            output = args.output or args.image
            publish(output,encode(output,raw),args.output is None)
            print(f'{output}: copied {len(args.files)} files')
    except (ValueError,OSError,UnicodeError) as error:
        parser.exit(1,str(error)+'\n')


if __name__ == '__main__': main()
