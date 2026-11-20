"""Shared helpers for the stack-storage study (read-only on captures; scratch on C:).

Restores single ARWs from `.ARW.straw` archives with the product's own
`strehl-raw-archive restore`, finds the plain CFA strip of a Sony uncompressed
ARW by walking its TIFF IFDs, and exposes the strip as a numpy u16 array.
"""
import ctypes
import os
import pathlib
import struct
import subprocess
import sys

os.environ.setdefault('NUMBA_NUM_THREADS', '8')
os.environ.setdefault('OMP_NUM_THREADS', '8')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '8')
os.environ.setdefault('MKL_NUM_THREADS', '8')

import numpy as np  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
EXE = ROOT / 'target/release/strehl-raw-archive.exe'
SCRATCH = pathlib.Path(r'C:\strehl-scratch\storage-study')
CAPTURES = pathlib.Path('D:/StrehlCaptures')
SCARAB = 'stack-1794786793543-11226'
REPEAT_A = 'stack-1794687317465-11226'
REPEAT_B = 'stack-1794686724346-11226'
STACK107 = 'stack-1794689780304-11226'
BELOW_NORMAL = 0x00004000


def below_normal():
    """This process (and what it starts) at below-normal priority."""
    if sys.platform == 'win32':
        k = ctypes.windll.kernel32
        k.GetCurrentProcess.restype = ctypes.c_void_p
        k.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        k.SetPriorityClass(k.GetCurrentProcess(), BELOW_NORMAL)


def archive(run, frame):
    return CAPTURES / run / ('frame-%06d.ARW.straw' % frame)


def restore(run, frame):
    """The restored ARW of `frame` (1-based) of `run`, restoring it if absent."""
    out = SCRATCH / run
    out.mkdir(parents=True, exist_ok=True)
    arw = out / ('frame-%06d.ARW' % frame)
    if not arw.exists():
        r = subprocess.run([str(EXE), 'restore', str(archive(run, frame)), '--output-dir', str(out)],
                           capture_output=True, text=True,
                           creationflags=BELOW_NORMAL if sys.platform == 'win32' else 0)
        if r.returncode != 0:
            raise RuntimeError(r.stderr[-400:])
    return arw


def drop(run, frame):
    arw = SCRATCH / run / ('frame-%06d.ARW' % frame)
    if arw.exists():
        arw.unlink()


TYPE_SIZE = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 6: 1, 7: 1, 8: 2, 9: 4, 10: 8, 11: 4, 12: 8, 13: 4}


def ifd_entries(b, at):
    """(tag, type, count, value-or-offset bytes position, values) of the IFD at `at`, and the next IFD."""
    n = struct.unpack_from('<H', b, at)[0]
    out = []
    for i in range(n):
        e = at + 2 + 12 * i
        tag, ty, count = struct.unpack_from('<HHI', b, e)
        size = TYPE_SIZE.get(ty, 1) * count
        pos = e + 8 if size <= 4 else struct.unpack_from('<I', b, e + 8)[0]
        vals = None
        if ty in (3, 4) and count <= 16:
            vals = list(struct.unpack_from('<%d%s' % (count, 'H' if ty == 3 else 'I'), b, pos))
        out.append((tag, ty, count, pos, vals, size))
    nxt = struct.unpack_from('<I', b, at + 2 + 12 * n)[0]
    return out, nxt


def walk(b):
    """Every IFD reachable through the IFD chain, SubIFDs and the EXIF IFD: (name, offset, entries)."""
    assert b[:4] == b'II*\x00'
    first = struct.unpack_from('<I', b, 4)[0]
    todo = [('IFD0', first)]
    seen = set()
    found = []
    chain = 0
    while todo:
        name, at = todo.pop(0)
        if at in seen or at == 0 or at + 2 > len(b):
            continue
        seen.add(at)
        entries, nxt = ifd_entries(b, at)
        found.append((name, at, entries))
        for tag, ty, count, pos, vals, size in entries:
            if tag == 0x014a and vals:
                for i, v in enumerate(vals):
                    todo.append(('%s.Sub%d' % (name, i), v))
            if tag == 0x8769 and vals:
                todo.append((name + '.Exif', vals[0]))
        if nxt and name.startswith('IFD') and '.' not in name:
            chain += 1
            todo.append(('IFD%d' % chain, nxt))
    return found


def tags(entries):
    return {tag: (ty, count, pos, vals, size) for tag, ty, count, pos, vals, size in entries}


def layout(b):
    """The plain CFA strip: dict(offset, width, height, bits) from the IFD with CFA photometric (32803)."""
    for name, at, entries in walk(b):
        t = tags(entries)
        if 0x0106 in t and t[0x0106][3] == [32803] and 0x0111 in t:
            assert t[0x0103][3] == [1], 'not uncompressed'
            return dict(ifd=name, offset=t[0x0111][3][0], width=t[0x0100][3][0], height=t[0x0101][3][0],
                        bits=t[0x0102][3][0], bytes=t[0x0117][3][0])
    raise RuntimeError('no CFA strip')


def load(path):
    """(bytes of the file as a read-only memmap, strip layout, CFA as an (h, w) u16 view)."""
    b = np.memmap(path, dtype=np.uint8, mode='r')
    lay = layout(bytes(b[:1 << 20]) if len(b) > (1 << 20) else bytes(b))
    cfa = np.ndarray((lay['height'], lay['width']), dtype='<u2', buffer=b, offset=lay['offset'])
    return b, lay, cfa


def cfa_of(run, frame):
    """A private copy of the frame's CFA strip (h, w) u16."""
    b, lay, cfa = load(restore(run, frame))
    out = np.array(cfa)
    del cfa, b
    return out
