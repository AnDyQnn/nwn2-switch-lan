#!/usr/bin/env python3
"""NWN2 EE (Switch) live debugging helper for the Atmosphere gdbstub.

Finds the running NWN2 process on the console, reads the nwmain base address
(ASLR changes it on every launch) and starts gdb with "silent" breakpoints that
only print registers and continue. The game keeps running and you get a log of
what gets called.

  python nwn2dbg.py procs                      list processes on the console
  python nwn2dbg.py base                       print NWN2 pid and nwmain base
  python nwn2dbg.py trace [-b bps.txt] [-o log.txt] [--tag SRV]
                                               attach and log breakpoint hits

Options (or environment variables):
  --target HOST:PORT   gdbstub address       (NWN2DBG_TARGET, default 127.0.0.1:22225)
  --gdb PATH           aarch64-none-elf-gdb   (NWN2DBG_GDB, default: from PATH)

bps file: one breakpoint per line, "<offset in main> <label>", '#' starts a comment.
Offsets are for build 3554C29951DDA41FE0AF61D3888DC3BB019764CA (update v65536).
To stop: Ctrl+C in gdb, then `detach` and `quit`, so the breakpoints are removed.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def gdb_batch(gdb, target, *cmds):
    args = [gdb, '-nx', '-batch', '-ex', f'target extended-remote {target}']
    for c in cmds:
        args += ['-ex', c]
    return subprocess.run(args, capture_output=True, text=True, timeout=120).stdout


def find_pid(gdb, target):
    out = gdb_batch(gdb, target, 'info os processes')
    for line in out.splitlines():
        m = re.match(r'\s*(\d+)\s+NWN2_EE', line)
        if m:
            return int(m.group(1))
    sys.exit('NWN2_EE is not running (start the game first)')


def find_base(gdb, target, pid):
    out = gdb_batch(gdb, target, f'attach {pid}', 'monitor get info', 'detach')
    m = re.search(r'(0x[0-9a-fA-F]+)\s*-\s*0x[0-9a-fA-F]+\s+nwmain', out)
    if not m:
        sys.exit('could not read nwmain base:\n' + out)
    return int(m.group(1), 16)


def load_bps(path):
    bps = []
    for line in open(path, encoding='utf-8'):
        line = line.split('#', 1)[0].strip()
        if line:
            off, _, label = line.partition(' ')
            bps.append((int(off, 16), label.strip() or off))
    return bps


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['procs', 'base', 'trace'])
    ap.add_argument('--target', default=os.environ.get('NWN2DBG_TARGET', '127.0.0.1:22225'))
    ap.add_argument('--gdb', default=os.environ.get('NWN2DBG_GDB') or shutil.which('aarch64-none-elf-gdb')
                    or 'aarch64-none-elf-gdb')
    ap.add_argument('-b', '--bps', default=os.path.join(HERE, 'bps_nwn2_lan.txt'))
    ap.add_argument('-o', '--log', default='nwn2dbg_log.txt')
    ap.add_argument('--tag', default='', help='prefix for log lines, e.g. SRV / CLI when tracing two consoles')
    a = ap.parse_args()

    if a.cmd == 'procs':
        print(gdb_batch(a.gdb, a.target, 'info os processes'))
        return
    pid = find_pid(a.gdb, a.target)
    base = find_base(a.gdb, a.target, pid)
    print(f'NWN2_EE pid={pid} nwmain base={base:#x}')
    if a.cmd == 'base':
        return

    bps = load_bps(a.bps)
    tag = (a.tag + ' ') if a.tag else ''
    lines = ['set pagination off', 'set confirm off',
             f'set logging file {a.log}', 'set logging overwrite on', 'set logging enabled on',
             f'target extended-remote {a.target}', f'attach {pid}']
    for off, label in bps:
        lines += [f'break *{base + off:#x}', 'commands', 'silent',
                  f'printf "{tag}HIT {label} x0=%lx x1=%lx x2=%lx x3=%lx x4=%lx lr=main+%lx\\n", '
                  f'$x0, $x1, $x2, $x3, $x4, $x30-{base:#x}',
                  'continue', 'end']
    lines.append('continue')
    with tempfile.NamedTemporaryFile('w', suffix='.gdb', delete=False, newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print(f'{len(bps)} breakpoints armed, log: {a.log}. Stop: Ctrl+C, then `detach`, `quit`.')
    subprocess.run([a.gdb, '-nx', '-x', f.name])


if __name__ == '__main__':
    main()
