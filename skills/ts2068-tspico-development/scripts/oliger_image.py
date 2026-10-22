"""160KB/320KB CP/M media in a standard CPC DSK container understood by Fuse."""
CYLINDERS = 40
SECTORS = 16
SECTOR_BYTES = 256
DISK_BYTES = CYLINDERS * SECTORS * SECTOR_BYTES

def encode_dsk(raw, sides=1):
    if sides not in (1,2) or len(raw) != DISK_BYTES*sides:
        raise ValueError('expected 160KB per side of logical disk data')
    header = bytearray(256)
    header[:34] = b'MV - CPCEMU Disk-File\r\nDisk-Info\r\n'
    header[34:48] = b'CPM2068       '
    header[48:50] = bytes([CYLINDERS, sides])
    track_size = 256 + SECTORS * SECTOR_BYTES
    header[50:52] = track_size.to_bytes(2, 'little')
    result = bytearray(header)
    for track_index in range(CYLINDERS*sides):
        cylinder, head = divmod(track_index, sides)
        track = bytearray(256)
        track[:12] = b'Track-Info\r\n'
        track[16:24] = bytes([cylinder, head, 1, 2, 1, SECTORS, 0x2a, 0xe5])
        for sector in range(SECTORS):
            pos = 24 + sector * 8
            track[pos:pos+8] = bytes([cylinder, head, sector+1, 1, 0, 0, 0, 0])
        result += track
        start = track_index * SECTORS * SECTOR_BYTES
        result += raw[start:start + SECTORS * SECTOR_BYTES]
    return bytes(result)

def decode_dsk(data):
    if data[:34] != b'MV - CPCEMU Disk-File\r\nDisk-Info\r\n':
        raise ValueError('expected standard DSK')
    sides=data[49]
    if data[48] != 40 or sides not in (1,2):
        raise ValueError('expected single-sided 40-track disk')
    size = int.from_bytes(data[50:52], 'little')
    if size != 4352 or len(data) != 256 + 40 * sides * size:
        raise ValueError('invalid track size or truncated disk')
    raw = bytearray()
    for track_index in range(40*sides):
        cyl, head = divmod(track_index,sides)
        pos = 256 + track_index * size
        if data[pos:pos+12] != b'Track-Info\r\n' or data[pos+21] != 16:
            raise ValueError('invalid track')
        for sector in range(16):
            entry = data[pos+24+sector*8:pos+32+sector*8]
            if entry[:6] != bytes([cyl, head, sector+1, 1, 0, 0]):
                raise ValueError('invalid sector descriptor')
        raw += data[pos+256:pos+size]
    return bytes(raw)
