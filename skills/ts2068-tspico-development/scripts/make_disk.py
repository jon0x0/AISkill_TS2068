"""Build a small CP/M 2.2 filesystem (1KB/2KB blocks, 8-bit allocation entries).

Files may span multiple logical extents, grouped by allocation block size. Fail instead of silently growing the image.
"""
def make_disk(files, size=49152, directory_entries=64, block_size=1024):
    if block_size not in (1024,2048) or size % block_size or not 0 < size//block_size <= 256:
        raise ValueError('unsupported block geometry')
    directory_bytes=directory_entries*32
    if directory_bytes % block_size:
        raise ValueError('directory must occupy whole allocation blocks')
    disk=bytearray(size)
    disk[:directory_bytes]=b'\xe5'*directory_bytes
    block=directory_bytes//block_size; slot=0; names=set(); manifest=[]
    for name,blob in files:
        name=name.upper(); parts=name.split('.')
        if len(parts)!=2 or not 1<=len(parts[0])<=8 or not 1<=len(parts[1])<=3 or name in names:
            raise ValueError(f'invalid/duplicate CP/M filename: {name}')
        names.add(name); allocations=[]
        # Pad text files with CP/M EOF and other files with zero to record size.
        padding=b'\x1a' if parts[1] in ('TXT','ASM','SUB') else b'\0'
        records=(len(blob)+127)//128
        blob=blob.ljust(records*128,padding)
        for extent,start in enumerate(range(0,max(1,len(blob)),16*block_size)):
            chunk=blob[start:start+16*block_size];count=(len(chunk)+block_size-1)//block_size
            if slot>=directory_entries or block+count>size//block_size:
                raise ValueError(f'disk full while adding {name}')
            entry=bytearray(32);entry[1:12]=f'{parts[0]:8}{parts[1]:3}'.encode('ascii')
            logical_extent=start//16384+max(0,len(chunk)-1)//16384
            entry[12]=logical_extent&31;entry[14]=logical_extent>>5;entry[15]=((len(chunk)-1)%16384)//128+1 if chunk else 0
            entry[16:16+count]=bytes(range(block,block+count))
            disk[slot*32:slot*32+32]=entry
            disk[block*block_size:block*block_size+len(chunk)]=chunk
            allocations.extend(range(block,block+count));block+=count;slot+=1
        manifest.append({'name':name,'records':records,'blocks':allocations})
    return bytes(disk),manifest,(size//block_size-block)*block_size
