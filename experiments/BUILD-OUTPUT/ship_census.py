"""Census the SHIPPED 16-bit masters for the tags a print master must carry.

Uses the raw IFD reader from tiff_tags.py, not tifffile, for the reason recorded
there: tifffile reports resolution (1,1) whether the tag says 1/1 or the tag is
ABSENT, and "absent" is the exact state this census exists to find.

read_ifd returns (endian, [(tag, typ, count, data)]) with `data` ALREADY
dereferenced, so nothing here re-reads an offset.
"""

import hashlib
import mmap
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from tiff_tags import read_ifd  # noqa: E402

SRC = Path(r"C:\dev\strehl-out\acceptance\SHIP-V4")
UNIT = {0: "-", 1: "none", 2: "inch", 3: "cm"}


def icc_desc(blob: bytes) -> str:
    try:
        (nt,) = struct.unpack(">I", blob[128:132])
        for i in range(nt):
            b = 132 + 12 * i
            if blob[b:b + 4] == b"desc":
                o, n = struct.unpack(">II", blob[b + 4:b + 12])
                dl = struct.unpack(">I", blob[o + 8:o + 12])[0]
                return blob[o + 12:o + 12 + dl].rstrip(b"\x00").decode("latin-1")
    except Exception as ex:
        return f"<unparsed {ex}>"
    return "<no desc tag>"


def main():
    files = sorted(SRC.glob("*--SHIP-V4.tiff"))
    if not files:
        print(f"no masters under {SRC}")
        return 2
    print(f"{'master':<40}{'bits':>5}{'ICC':>5} {'icc-md5':<13}"
          f"{'profile description':<56}{'xres':>6}{'unit':>6}")
    print("-" * 132)
    prof, states, rows = {}, {"ICC": 0, "NO-ICC": 0}, []
    for f in files:
        with open(f, "rb") as fh:
            buf = mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)
            e, ents = read_ifd(buf)
            d = {t: (typ, cnt, bytes(data)) for t, typ, cnt, data in ents}
            buf.close()

        bits = struct.unpack(e + "H", d[258][2][:2])[0] if 258 in d else -1
        has_icc = 34675 in d
        md5, desc = "-", "-"
        if has_icc:
            blob = d[34675][2]
            md5 = hashlib.md5(blob).hexdigest()[:12]
            desc = icc_desc(blob)
            prof.setdefault((md5, desc), []).append(f.name)
        states["ICC" if has_icc else "NO-ICC"] += 1

        if 282 in d:
            n, dn = struct.unpack(e + "II", d[282][2][:8])
            xres = n / dn if dn else float("nan")
        else:
            xres = float("nan")
        unit = struct.unpack(e + "H", d[296][2][:2])[0] if 296 in d else 0

        name = f.name.replace("--SHIP-V4.tiff", "")
        rows.append((name, bits, has_icc, md5, desc, xres, unit))
        print(f"{name:<40}{bits:>5}{'yes' if has_icc else 'NO':>5} {md5:<13}"
              f"{desc[:54]:<56}{xres:>6.0f}{UNIT.get(unit, unit):>6}")

    n = len(rows)
    print()
    print(f"  masters                       : {n}")
    print(f"  with ICC                      : {states['ICC']}/{n}")
    print(f"  WITHOUT ICC                   : {states['NO-ICC']}/{n}")
    assert states["ICC"] + states["NO-ICC"] == n, "states do not partition"
    print(f"  distinct profiles embedded    : {len(prof)}")
    for (m, ds), names in sorted(prof.items(), key=lambda kv: -len(kv[1])):
        print(f"      {m}  x{len(names):<3} {ds}")
    print(f"  distinct bit depths           : {sorted({r[1] for r in rows})}")
    print(f"  distinct (xres, unit)         : "
          f"{sorted({(r[5], UNIT.get(r[6], r[6])) for r in rows})}")
    bad = [r[0] for r in rows if r[6] != 2 or r[5] != 300]
    print(f"  masters NOT at 300 dpi / inch : {len(bad)} {bad[:5]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
