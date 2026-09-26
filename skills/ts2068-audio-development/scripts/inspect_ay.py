"""Inspect ZXAYEMUL metadata/blocks without executing code. Standard library only."""
from pathlib import Path
import argparse,hashlib,json,struct

def inspect(data,song=None):
    def require(ok,message):
        if not ok:raise ValueError(message)
    def word(o):
        require(0<=o<=len(data)-2,'Truncated word');return struct.unpack_from('>H',data,o)[0]
    def pointer(o):
        value=word(o);p=o+(value-65536 if value>=32768 else value)
        require(0<=p<len(data),'Relative pointer outside file');return p
    def string(p):
        end=data.find(b'\0',p);require(end>=p,'Unterminated string');return data[p:end].decode('latin1')
    require(len(data)>=20 and data[:8]==b'ZXAYEMUL','Expected ZXAYEMUL header')
    count=data[16]+1;selected=data[17] if song is None else song
    require(0<=selected<count,'Song index out of range')
    table=pointer(18);require(table+count*4<=len(data),'Truncated song table')
    entry=table+selected*4;record=pointer(entry+2)
    require(record+14<=len(data),'Truncated song record')
    points=pointer(record+10);blocks_at=pointer(record+12);blocks=[]
    while word(blocks_at):
        address=word(blocks_at);length=word(blocks_at+2);source=pointer(blocks_at+4)
        require(address+length<=65536,'Block exceeds Z80 address space')
        require(source+length<=len(data),'Truncated block payload')
        blocks.append({'address':address,'length':length,'file_offset':source,'sha256':hashlib.sha256(data[source:source+length]).hexdigest()})
        blocks_at+=6
    return {'sha256':hashlib.sha256(data).hexdigest(),'file_version':data[8],'player_version':data[9],'author':string(pointer(12)),
            'misc':string(pointer(14)),'song':selected,'songs':count,'title':string(pointer(entry)),
            'length_ticks_50hz':word(record+4),'fade_ticks_50hz':word(record+6),
            'initial_register_high':data[record+8],'initial_register_low':data[record+9],
            'stack':word(points),'init':word(points+2),'interrupt':word(points+4),'blocks':blocks}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('file',type=Path)
    p.add_argument('--song',type=int);p.add_argument('--json',type=Path);p.add_argument('--extract',type=Path)
    a=p.parse_args();data=a.file.read_bytes();report=inspect(data,a.song)
    text=json.dumps(report,indent=2)+'\n'
    if a.json:a.json.parent.mkdir(parents=True,exist_ok=True);a.json.write_text(text,encoding='utf-8')
    if a.extract:
        a.extract.mkdir(parents=True,exist_ok=True)
        for i,b in enumerate(report['blocks']):
            (a.extract/f"block-{i:02d}-{b['address']:04x}.bin").write_bytes(data[b['file_offset']:b['file_offset']+b['length']])
    print(text,end='')
if __name__=='__main__':main()
