"""Read colour metadata OUT OF a PNG, by parsing chunks -- never by inference.

ORCH's requirement, verbatim: "Read the profile out of the file itself -- do not
infer it from the CLI flags that were passed."  And the commissioning bar it set:
"a profile reader that returns 'sRGB' for a file with no profile at all is the
same failure -- give it a file you have stripped and require it to report
*absent*, not a default."

That bar is the reason this file parses raw chunks instead of asking PIL.
PIL's Image.info exposes 'icc_profile' only when iCCP is present, but several
imaging stacks silently substitute a default sRGB profile for a file carrying
only the 1-byte sRGB *chunk* (which is a rendering-intent flag, NOT a profile)
or nothing at all.  A reader that cannot tell those three states apart cannot
answer the question that was asked, so this one keeps them separate by
construction:

    ICCP     an actual embedded profile, bytes recovered and hashed
    SRGB     the sRGB chunk: a 1-byte intent flag, no profile, no tone curve
    ABSENT   neither: the file states nothing and a consumer will guess

PNG layout: 8-byte signature, then [len:4][type:4][data:len][crc:4] repeating.
"""

import binascii
import hashlib
import struct
import sys
import zlib
from pathlib import Path

SIG = b"\x89PNG\r\n\x1a\n"

COLOR_TYPE = {0: "gray", 2: "rgb", 3: "palette", 4: "gray+a", 6: "rgba"}
INTENT = {0: "perceptual", 1: "relative-colorimetric", 2: "saturation",
          3: "absolute-colorimetric"}


def chunks(raw: bytes):
    """Yield (type, data) and verify each CRC.

    The CRC is checked because a truncated or edited file that still *parses*
    would otherwise be read as authoritative.  A corrupt chunk is reported, not
    skipped silently.
    """
    if raw[:8] != SIG:
        raise ValueError("not a PNG (bad signature)")
    off = 8
    while off + 8 <= len(raw):
        (ln,) = struct.unpack(">I", raw[off:off + 4])
        typ = raw[off + 4:off + 8]
        data = raw[off + 8:off + 8 + ln]
        (crc,) = struct.unpack(">I", raw[off + 8 + ln:off + 12 + ln])
        ok = binascii.crc32(typ + data) & 0xFFFFFFFF == crc
        yield typ.decode("latin-1"), data, ok
        off += 12 + ln
        if typ == b"IEND":
            break


def icc_header(p: bytes) -> dict:
    """Pull the fields of the 128-byte ICC header that decide what a profile IS."""
    if len(p) < 132:
        return {"error": f"profile too short ({len(p)} bytes)"}
    out = {
        "size": struct.unpack(">I", p[0:4])[0],
        "class": p[12:16].decode("latin-1"),
        "space": p[16:20].decode("latin-1"),
        "pcs": p[20:24].decode("latin-1"),
        "acsp": p[36:40].decode("latin-1"),
        "intent": struct.unpack(">I", p[64:68])[0],
    }
    (ntags,) = struct.unpack(">I", p[128:132])
    tags = {}
    for i in range(ntags):
        b = 132 + 12 * i
        if b + 12 > len(p):
            break
        sig = p[b:b + 4].decode("latin-1")
        o, n = struct.unpack(">II", p[b + 4:b + 12])
        tags[sig] = (o, n)
    out["tags"] = tags
    if "desc" in tags:
        o, n = tags["desc"]
        blob = p[o:o + n]
        if blob[:4] == b"desc":
            (dl,) = struct.unpack(">I", blob[8:12])
            out["desc"] = blob[12:12 + dl].rstrip(b"\x00").decode("latin-1")
        elif blob[:4] == b"mluc":
            (nrec,) = struct.unpack(">I", blob[8:12])
            if nrec:
                sl, so = struct.unpack(">II", blob[20:28])
                out["desc"] = blob[so:so + sl].decode("utf-16-be").rstrip("\x00")
    return out


def probe(path: Path) -> dict:
    raw = path.read_bytes()
    r = {"file": path.name, "bytes": len(raw), "bad_crc": [],
         "state": "ABSENT", "icc": None, "srgb_intent": None,
         "gama": None, "chrm": False, "phys": None}
    for typ, data, ok in chunks(raw):
        if not ok:
            r["bad_crc"].append(typ)
        if typ == "IHDR":
            w, h, depth, ctype = struct.unpack(">IIBB", data[:10])
            r.update(width=w, height=h, depth=depth,
                     ctype=COLOR_TYPE.get(ctype, str(ctype)))
        elif typ == "iCCP":
            z = data.index(b"\x00")
            r["profile_name"] = data[:z].decode("latin-1")
            prof = zlib.decompress(data[z + 2:])
            r["state"] = "ICCP"
            r["icc"] = icc_header(prof)
            r["icc"]["md5"] = hashlib.md5(prof).hexdigest()[:12]
            r["icc"]["stored_bytes"] = len(prof)
        elif typ == "sRGB":
            r["srgb_intent"] = data[0]
            if r["state"] == "ABSENT":
                r["state"] = "SRGB"
        elif typ == "gAMA":
            r["gama"] = struct.unpack(">I", data)[0] / 100000.0
        elif typ == "cHRM":
            r["chrm"] = True
        elif typ == "pHYs":
            x, y, unit = struct.unpack(">IIB", data)
            r["phys"] = (x, y, unit)
    return r


def dpi_of(r) -> str:
    """pHYs is pixels-per-METRE when unit==1, and unitless (aspect only) when 0."""
    if not r["phys"]:
        return "-"
    x, y, unit = r["phys"]
    if unit != 1:
        return f"aspect {x}:{y} (no physical unit)"
    return f"{x * 0.0254:.1f}x{y * 0.0254:.1f} dpi"


def main():
    args = [a for a in sys.argv[1:]]
    paths = []
    for a in args:
        p = Path(a)
        paths.extend(sorted(p.glob("*.png")) if p.is_dir() else [p])
    if not paths:
        print("usage: png_probe.py <dir-or-files...>")
        return 2

    rows = [probe(p) for p in paths]
    print(f"{'file':<34}{'depth':>6}{'type':>7}  {'state':<7}"
          f"{'profile':<26}{'md5':<14}{'dpi':<22}")
    print("-" * 118)
    for r in rows:
        d = r["icc"] or {}
        desc = d.get("desc", "-") if r["icc"] else (
            f"sRGB chunk intent={INTENT.get(r['srgb_intent'], '?')}"
            if r["state"] == "SRGB" else "-")
        print(f"{r['file']:<34}{r['depth']:>6}{r['ctype']:>7}  {r['state']:<7}"
              f"{desc[:25]:<26}{d.get('md5', '-'):<14}{dpi_of(r):<22}")
        if r["bad_crc"]:
            print(f"    !! CRC FAILED on chunks: {r['bad_crc']}")

    print()
    n = len(rows)
    for st in ("ICCP", "SRGB", "ABSENT"):
        k = [r for r in rows if r["state"] == st]
        print(f"  {st:<8} {len(k):>3}/{n}")
    # Every input must land in exactly one bucket: a file that is merely skipped
    # must never be able to read as a file that passed.
    assert sum(len([r for r in rows if r['state'] == s])
               for s in ("ICCP", "SRGB", "ABSENT")) == n, "states do not partition"
    md5s = sorted({r["icc"]["md5"] for r in rows if r["icc"]})
    print(f"  distinct embedded profiles: {len(md5s)} {md5s}")
    depths = sorted({r["depth"] for r in rows})
    print(f"  distinct bit depths: {depths}")
    dpis = sorted({dpi_of(r) for r in rows})
    print(f"  distinct pHYs: {dpis}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
