"""Link the bundled ROM-independent TSPico driver with sjasmplus (no ROMs)."""
import argparse
from pathlib import Path
import shutil
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend', choices=('legacy', 'modern'), required=True)
    parser.add_argument('--stream', action='store_true', help='modern sequential reader')
    parser.add_argument('--origin', type=lambda n: int(n, 0), default=0x1000)
    parser.add_argument('--workspace', type=lambda n: int(n, 0), default=0x7800)
    parser.add_argument('--assembler', default=shutil.which('sjasmplus'))
    parser.add_argument('--out', type=Path, required=True, help='output directory')
    args = parser.parse_args()
    if args.backend == 'legacy' and args.stream:
        parser.error('legacy backend has no raw-file streaming module')
    if not args.assembler:
        parser.error('install sjasmplus or pass --assembler PATH')
    if not (0 <= args.origin <= 0xffff and 0 <= args.workspace <= 0xfc00):
        parser.error('origin/workspace must fit the Z80 address space')
    source = Path(__file__).resolve().parents[1]/'assets/z80'
    output = args.out.resolve()
    output.mkdir(parents=True, exist_ok=True)
    names = ['layout.inc'] + (['tpi_legacy.asm', 'files_legacy.asm'] if args.backend == 'legacy'
                              else ['tpi.asm', 'files.asm'])
    if args.stream:
        names.append('stream.asm')
    lines = [f'        DEFINE WORK_BASE ${args.workspace:04x}', f'        org ${args.origin:04x}']
    lines += [f'        include "{(source/name).as_posix()}"' for name in names]
    lines += ['library_end:', '        assert library_end <= $10000']
    wrapper = output/'library.asm'
    wrapper.write_text('\n'.join(lines)+'\n', encoding='utf-8')
    subprocess.run([args.assembler, '--nologo', '--msg=war',
                    '--raw='+str(output/'library.bin'),
                    '--sym='+str(output/'library.sym'),
                    '--lst='+str(output/'library.lst'), str(wrapper)], check=True)
    print(f'{args.backend}{"+stream" if args.stream else ""}: '
          f'{(output/"library.bin").stat().st_size} ROM bytes at ${args.origin:04X}')
    print('Reserve documented RAM areas; workspace selection does not relocate stream/reply scratch.')


if __name__ == '__main__':
    main()
