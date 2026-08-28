"""Commission png_probe.py.  The load-bearing arm is a PLANTED profile.

png_probe reported ABSENT on 26/26 delivered files.  A reader with a broken
iCCP branch reports exactly that, on every file, forever.  So the arm that
decides whether the 26/26 means anything is not the strip -- it is the PLANT:
build a file that certainly HAS a profile and require the reader to find it,
name it, and hash it.  A strip-only suite cannot separate "no profiles present"
from "reader is blind to profiles", because both give ABSENT.

Arms:
  1 PLANT iCCP    -> must read ICCP, right md5, right desc   (potency)
  2 PLANT sRGB    -> must read SRGB, NOT ICCP, NOT ABSENT    (the middle state)
  3 PLANT pHYs    -> must read the planted DPI               (potency, item 4)
  4 STRIP iCCP    -> must read ABSENT, not a default         (ORCH's bar)
  5 CORRUPT crc   -> must report the bad chunk, not swallow it
"""

import binascii
import hashlib
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from png_probe import probe, dpi_of, SIG  # noqa: E402

TMP = Path(r"D:\strehl-out\BUILD-OUTPUT\scratch\commission")
WIN_SRGB = Path(r"C:\Windows\System32\spool\drivers\color\sRGB Color Space Profile.icm")


def split(raw):
    out, off = [], 8
    while off + 8 <= len(raw):
        (ln,) = struct.unpack(">I", raw[off:off + 4])
        typ = raw[off + 4:off + 8]
        out.append((typ, raw[off + 8:off + 8 + ln]))
        off += 12 + ln
        if typ == b"IEND":
            break
    return out


def build(parts):
    o = bytearray(SIG)
    for typ, data in parts:
        o += struct.pack(">I", len(data)) + typ + data
        o += struct.pack(">I", binascii.crc32(typ + data) & 0xFFFFFFFF)
    return bytes(o)


def insert_after_ihdr(parts, typ, data):
    i = next(k for k, (t, _) in enumerate(parts) if t == b"IHDR")
    return parts[:i + 1] + [(typ, data)] + parts[i + 1:]


def main():
    src = Path(sys.argv[1])
    TMP.mkdir(parents=True, exist_ok=True)
    parts = split(src.read_bytes())
    prof = WIN_SRGB.read_bytes()
    want_md5 = hashlib.md5(prof).hexdigest()[:12]
    fails = []

    def check(name, cond, got):
        print(f"  {'PASS' if cond else 'FAIL':<5} {name:<44} {got}")
        if not cond:
            fails.append(name)

    print(f"planted profile: {WIN_SRGB.name}  {len(prof)} bytes  md5 {want_md5}")
    print()

    # --- ARM 1: plant a real ICC profile -------------------------------------
    icc_data = b"planted\x00\x00" + zlib.compress(prof, 9)
    p1 = TMP / "arm1_planted_iccp.png"
    p1.write_bytes(build(insert_after_ihdr(parts, b"iCCP", icc_data)))
    r1 = probe(p1)
    check("ARM1 plant iCCP -> state ICCP", r1["state"] == "ICCP", r1["state"])
    check("ARM1 recovers the exact profile bytes",
          r1["icc"] and r1["icc"]["md5"] == want_md5,
          (r1["icc"] or {}).get("md5"))
    check("ARM1 reads the profile description",
          bool((r1["icc"] or {}).get("desc")), (r1["icc"] or {}).get("desc"))
    check("ARM1 reads the declared colour space",
          (r1["icc"] or {}).get("space", "").strip() == "RGB",
          (r1["icc"] or {}).get("space"))

    # --- ARM 2: plant only the sRGB *chunk* (a flag, not a profile) ----------
    p2 = TMP / "arm2_planted_srgb_chunk.png"
    p2.write_bytes(build(insert_after_ihdr(parts, b"sRGB", bytes([0]))))
    r2 = probe(p2)
    check("ARM2 sRGB chunk -> SRGB, distinct from ICCP",
          r2["state"] == "SRGB" and r2["icc"] is None, r2["state"])

    # --- ARM 3: plant pHYs at a known DPI ------------------------------------
    ppm = 11811  # 300 dpi = 300/0.0254 px/m
    p3 = TMP / "arm3_planted_phys.png"
    p3.write_bytes(build(insert_after_ihdr(parts, b"pHYs",
                                           struct.pack(">IIB", ppm, ppm, 1))))
    r3 = probe(p3)
    check("ARM3 plant pHYs 300dpi -> reads ~300",
          r3["phys"] is not None and abs(r3["phys"][0] * 0.0254 - 300) < 0.5,
          dpi_of(r3))

    # --- ARM 4: strip it back out again -------------------------------------
    p4 = TMP / "arm4_stripped.png"
    p4.write_bytes(build([(t, d) for t, d in split(p1.read_bytes())
                          if t != b"iCCP"]))
    r4 = probe(p4)
    check("ARM4 strip iCCP -> ABSENT, no default substituted",
          r4["state"] == "ABSENT" and r4["icc"] is None, r4["state"])

    # --- ARM 5: corrupt a CRC ------------------------------------------------
    b5 = bytearray(p1.read_bytes())
    b5[-1] ^= 0xFF
    p5 = TMP / "arm5_bad_crc.png"
    p5.write_bytes(bytes(b5))
    r5 = probe(p5)
    check("ARM5 corrupt CRC -> reported, not swallowed",
          len(r5["bad_crc"]) > 0, r5["bad_crc"])

    print()
    if fails:
        print(f"COMMISSIONING: FAIL -- {len(fails)} arm(s): {fails}")
        return 1
    print("COMMISSIONING: PASS -- the reader finds a profile when one is there,")
    print("  reports ABSENT when it is not, and does not conflate the two.")
    print("  Therefore ABSENT on 26/26 delivered files is a fact about the files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
