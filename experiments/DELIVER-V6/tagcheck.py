"""Verify print-critical TIFF tags in the actual output bytes of the DELIVER-V6 masters.

Why this exists
---------------
The shipped gallery was found (by BUILD-OUTPUT) to carry no ICC profile and no
physical resolution: XResolution 1/1, ResolutionUnit "none", tag 34675 absent.
That is a delivery defect rather than a code defect -- the code at HEAD already
writes the profile -- so re-rendering is the fix.  This checks that the fix is
actually in the bytes I shipped, not merely in the source I built from.

Reuse, not reimplementation
---------------------------
The byte-level IFD parser is BUILD-OUTPUT's `experiments/BUILD-OUTPUT/tiff_tags.py`.
It is imported here rather than copied.  It parses the raw IFD deliberately:
`tifffile` normalises a missing resolution to (1, 1), which is indistinguishable
from a real 1/1, and PIL mis-reads 16-bit TIFFs.  A high-level reader cannot see
this defect at all.

Commissioning
-------------
The reader is commissioned on every run, against a file that is *known* to have
the defect, before any master is trusted.  A reader that cannot see the defect in
a file that has it would report every new file as clean.  If the commissioning
file does not come back ABSENT/none, this exits non-zero and checks nothing.
"""

import hashlib
import importlib.util
import json
import mmap
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
TAGGER = REPO / "experiments" / "BUILD-OUTPUT" / "tiff_tags.py"

_spec = importlib.util.spec_from_file_location("tiff_tags", TAGGER)
tiff_tags = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tiff_tags)

ICC = 34675
XRES, YRES, RESUNIT_TAG, SOFTWARE, DESC = 282, 283, 296, 305, 270

# What --srgb must produce.  The 2716-byte length is the sRGB-TRC profile the
# crate builds; --linear-srgb builds a 696-byte identity-TRC profile instead.
WANT_ICC_LEN = 2716
WANT_RES = (300, 1)
WANT_UNIT = 2  # inch


def probe(path):
    """Return the print-critical tags, read from the file's own bytes."""
    with open(path, "rb") as fh:
        buf = mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            e, entries = tiff_tags.read_ifd(buf)
            got = {}
            for tag, typ, cnt, data in entries:
                got[tag] = (typ, cnt, bytes(data))

            def rational(tag):
                if tag not in got:
                    return None
                _, _, d = got[tag]
                if len(d) < 8:
                    return None
                num, den = struct.unpack(e + "II", d[:8])
                return (num, den)

            def short(tag):
                if tag not in got:
                    return None
                _, _, d = got[tag]
                if len(d) < 2:
                    return None
                return struct.unpack(e + "H", d[:2])[0]

            def ascii_(tag):
                if tag not in got:
                    return None
                return got[tag][2].split(b"\0")[0].decode("ascii", "replace")

            icc = got.get(ICC)
            return {
                "icc_present": icc is not None,
                "icc_len": (icc[1] if icc else 0),
                "icc_type": (tiff_tags.TYPE_NAME.get(icc[0], str(icc[0])) if icc else None),
                "icc_sha256": (hashlib.sha256(icc[2][: icc[1]]).hexdigest() if icc else None),
                "xres": rational(XRES),
                "yres": rational(YRES),
                "unit": short(RESUNIT_TAG),
                "unit_name": tiff_tags.RESUNIT.get(short(RESUNIT_TAG), "?"),
                "software": ascii_(SOFTWARE),
                "desc": (ascii_(DESC) or "")[:60],
            }
        finally:
            buf.close()


def commission(path):
    """Prove the reader can see the defect in a file known to have it."""
    p = probe(path)
    ok = (not p["icc_present"]) and p["unit"] == 1 and p["xres"] == (1, 1)
    print("COMMISSIONING the reader against a file known to predate the fix:")
    print("  %s" % path)
    print("    ICC 34675      : %s" % ("PRESENT %d B" % p["icc_len"] if p["icc_present"] else "ABSENT"))
    print("    XResolution    : %s" % ("%d/%d" % p["xres"] if p["xres"] else "absent"))
    print("    ResolutionUnit : %s (%s)" % (p["unit"], p["unit_name"]))
    print("    -> reader %s see the defect\n" % ("CAN" if ok else "CANNOT"))
    return ok


def main(argv):
    ref = argv[0]
    masters = sorted(Path(argv[1]).glob("*.tiff"))
    if not commission(ref):
        print("REFUSING to check masters: the reader failed commissioning.")
        return 2
    if not masters:
        print("no masters found")
        return 2

    rows, bad = [], []
    for m in masters:
        p = probe(m)
        p["subject"] = m.stem
        p["bytes"] = m.stat().st_size
        p["ok"] = (
            p["icc_present"]
            and p["icc_len"] == WANT_ICC_LEN
            and p["xres"] == WANT_RES
            and p["yres"] == WANT_RES
            and p["unit"] == WANT_UNIT
        )
        rows.append(p)
        if not p["ok"]:
            bad.append(p)
        print(
            "%-34s ICC %-9s %-9s %7s %-5s %s"
            % (
                p["subject"],
                ("%d B" % p["icc_len"]) if p["icc_present"] else "ABSENT",
                p["icc_type"] or "-",
                ("%d/%d" % p["xres"]) if p["xres"] else "-",
                p["unit_name"],
                "ok" if p["ok"] else "**FAIL**",
            )
        )

    print("\n%d/%d masters carry ICC %d B + %d/%d dpi + unit inch"
          % (len(rows) - len(bad), len(rows), WANT_ICC_LEN, *WANT_RES))
    iccs = {r["icc_sha256"] for r in rows if r["icc_present"]}
    print("distinct embedded ICC payloads: %d %s"
          % (len(iccs), "(identical across all masters)" if len(iccs) == 1 else "(DIFFER)"))
    softs = {r["software"] for r in rows}
    print("distinct Software strings: %d -> %s" % (len(softs), sorted(softs)))
    (Path(argv[1]) / "TAGS.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
