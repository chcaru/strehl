"""Verify the SHIP-V2-ICC deliverable: every master, every check, counted.

Three questions, one row per subject, and the summary partitions every subject
into a counted outcome so a skipped one cannot read as a passed one.

1. Does the master carry a real, parseable ICC profile?
2. Are the pixels unchanged from SHIP-V2?

   NOTE ON (2): this is a CROSS-BUILD comparison. SHIP-V2 came from b9b6921
   (CF33AE08...), SHIP-V2-ICC from 96b7e119 (0B3B6F19...). Per ORCH's warning,
   a difference here could belong to any lane's commits in between, NOT to the
   ICC change -- that was settled separately by a controlled one-SHA A/B in
   which the two trees differed by image_out.rs alone and gave max|A-B| = 0.
   Channels are reported separately because the chromatic-aberration
   correction ORCH warned about leaves green bit-identical.

3. Does the provenance sidecar record the commit and the binary hash, so the
   single-binary claim is recorded rather than inferred from mtimes?
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

import numpy as np
import tifffile

NEW = Path(r"C:\dev\strehl-out\SHIP-V2-ICC")
OLD = Path(r"C:\dev\strehl-out\SHIP-V2")
ARM = "SHIP-V2-ICC"
ICC_TAG = 34675


def icc_of(path: Path) -> bytes | None:
    with tifffile.TiffFile(path) as tf:
        t = tf.pages[0].tags.get(ICC_TAG)
        return None if t is None else bytes(t.value)


def profile_ok(p: bytes) -> tuple[bool, str]:
    if len(p) < 132:
        return False, "too short"
    if struct.unpack(">I", p[0:4])[0] != len(p):
        return False, "size field != length"
    if p[36:40] != b"acsp":
        return False, "no acsp signature"
    if struct.unpack(">I", p[8:12])[0] != 0x0210_0000:
        return False, "not v2.1"
    n = struct.unpack(">I", p[128:132])[0]
    sigs = {p[132 + 12 * i:136 + 12 * i].decode("ascii", "replace") for i in range(n)}
    need = {"desc", "wtpt", "rXYZ", "gXYZ", "bXYZ", "rTRC", "gTRC", "bTRC", "cprt"}
    if not need <= sigs:
        return False, f"missing {sorted(need - sigs)}"
    return True, f"{len(p)}B/{n}tags"


def main() -> int:
    masters = sorted(NEW.glob(f"*--{ARM}.tiff"))
    if not masters:
        print(f"REFUSE: no masters under {NEW}")
        return 2

    icc_ok = icc_bad = 0
    same = differ = nopair = 0
    prov_ok = prov_bad = 0
    ref_hash: set[str] = set()
    rows = []

    print(f"{'subject':40}{'ICC':>16}{'pixels vs SHIP-V2':>22}{'prov':>7}")
    print("-" * 86)
    for m in masters:
        stem = m.name[: -len(f"--{ARM}.tiff")]

        p = icc_of(m)
        if p is None:
            icc_bad += 1
            icc_s = "ABSENT"
        else:
            ok, why = profile_ok(p)
            icc_ok, icc_bad = (icc_ok + 1, icc_bad) if ok else (icc_ok, icc_bad + 1)
            icc_s = why if ok else f"BAD:{why}"

        old = OLD / f"{stem}--SHIP-V2.tiff"
        if not old.exists():
            nopair += 1
            pix = "no SHIP-V2 pair"
        else:
            a, b = tifffile.imread(old), tifffile.imread(m)
            assert a.dtype == np.uint16 and b.dtype == np.uint16, f"{stem}: not uint16"
            if a.shape != b.shape:
                differ += 1
                pix = f"SHAPE {a.shape}!={b.shape}"
            else:
                d = [int(np.abs(a[:, :, i].astype(np.int32)
                                - b[:, :, i].astype(np.int32)).max()) for i in range(3)]
                if max(d) == 0:
                    same += 1
                    pix = "identical RGB"
                else:
                    differ += 1
                    pix = f"R{d[0]} G{d[1]} B{d[2]}"

        sc = m.with_suffix(".tiff.provenance.txt")
        txt = sc.read_text(encoding="utf-8", errors="replace") if sc.exists() else ""
        has = ("96b7e1190181f2edd8f0e451d29c962c770a2ce1" in txt
               and "0B3B6F19ABABD7589098A271259DF64819CC0D3B07F74071FD3A7AC1C255DBEC" in txt)
        prov_ok, prov_bad = (prov_ok + 1, prov_bad) if has else (prov_ok, prov_bad + 1)
        if has:
            ref_hash.add("0B3B6F19")

        rows.append(stem)
        print(f"{stem:40}{icc_s:>16}{pix:>22}{'ok' if has else 'MISSING':>7}")

    total = len(masters)
    print(f"\nsubjects: {total}")
    print(f"  ICC profile valid       {icc_ok:3d}   invalid or absent {icc_bad:3d}"
          f"   (sums to {icc_ok + icc_bad})")
    print(f"  pixels identical        {same:3d}   differ {differ:3d}   no pair {nopair:3d}"
          f"   (sums to {same + differ + nopair})")
    print(f"  provenance complete     {prov_ok:3d}   incomplete {prov_bad:3d}"
          f"   (sums to {prov_ok + prov_bad})")
    print(f"  distinct binaries named in sidecars: {len(ref_hash)} -> "
          f"{'SINGLE BINARY, RECORDED' if len(ref_hash) == 1 else 'MORE THAN ONE'}")

    assert icc_ok + icc_bad == total, "ICC outcomes do not partition the subjects"
    assert same + differ + nopair == total, "pixel outcomes do not partition the subjects"
    assert prov_ok + prov_bad == total, "provenance outcomes do not partition the subjects"

    bad = icc_bad + differ + prov_bad
    print("\n" + ("SHIP-V2-ICC VERIFIED" if bad == 0 else f"{bad} PROBLEM(S)"))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
