"""Re-verify the delivered master bytes and fold the print-tag evidence into MANIFEST.txt.

Two jobs, in this order:

1.  Re-hash every master named in MANIFEST.txt and compare against the SHA256
    recorded at render time.  This folder has demonstrably been written to by
    another lane after my run finished, so "the bytes I delivered are still the
    bytes I rendered" is a claim that has to be re-established, not assumed.

2.  Insert the print-critical tag evidence (ICC 34675, XResolution/YResolution,
    ResolutionUnit, Software) per subject, from TAGS.json as produced by
    tagcheck.py -- which reads the file's own bytes via BUILD-OUTPUT's IFD
    parser and self-commissions against a known-defective file first.

Anything in the folder that MANIFEST.txt does not name is listed in a trailer as
foreign.  It is not deleted: deleting another lane's output without being asked
is what destroyed the ORCH-FAITHFUL baseline tonight.
"""

import hashlib
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

BUF = 8 << 20


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            b = fh.read(BUF)
            if not b:
                break
            h.update(b)
    return h.hexdigest().upper()


def main(argv):
    dest = Path(argv[0])
    man = dest / "MANIFEST.txt"
    tags = {t["subject"]: t for t in json.loads((dest / "TAGS.json").read_text(encoding="utf-8"))}

    text = man.read_text(encoding="utf-8", errors="replace")
    shutil.copy2(man, Path(sys.argv[0]).with_name("MANIFEST.before-tags.txt"))

    blocks = text.split("\n\n")
    named, out, mismatched, missing_tag = set(), [], [], []

    for blk in blocks:
        lines = blk.rstrip("\n").split("\n")
        subj = None
        for ln in lines:
            if ln.startswith("subject   :"):
                subj = ln.split(":", 1)[1].strip()
        if subj is None:
            out.append(blk)
            continue
        named.add(subj)
        rec = {}
        for ln in lines:
            if ":" in ln:
                k, v = ln.split(":", 1)
                rec[k.strip()] = v.strip()

        f = dest / (subj + ".tiff")
        got = sha256(f) if f.exists() else "MISSING"
        want = rec.get("out SHA256", "")
        state = "unchanged since render" if got == want else "*** CHANGED ***"
        if got != want:
            mismatched.append((subj, want, got))

        t = tags.get(subj)
        if t is None:
            missing_tag.append(subj)
            new = lines
        else:
            if not (t["icc_present"] and t["icc_len"] == 2716
                    and t["xres"] == [300, 1] and t["yres"] == [300, 1] and t["unit"] == 2):
                missing_tag.append(subj)
            icc = ("34675 present, %d B, TIFF type %s, sRGB TRC" % (t["icc_len"], t["icc_type"])
                   if t["icc_present"] else "34675 ABSENT  *** NOT A PRINT FILE ***")
            new = []
            for ln in lines:
                new.append(ln)
                if ln.startswith("bytes     :"):
                    new.append("recheck   : %s" % state)
                    new.append("ICCProfile: %s" % icc)
                    new.append("resolution: X %d/%d  Y %d/%d  unit %d (%s)"
                               % (t["xres"][0], t["xres"][1], t["yres"][0], t["yres"][1],
                                  t["unit"], t["unit_name"]))
                    new.append("software  : %s" % t["software"])
        out.append("\n".join(new))

    foreign = sorted(p.stem for p in dest.glob("*.tiff") if p.stem not in named)
    trailer = [
        "",
        "=== print-tag verification (added %s)" % datetime.now().astimezone().isoformat(timespec="seconds"),
        "reader        : experiments/BUILD-OUTPUT/tiff_tags.py (BUILD-OUTPUT), driven by",
        "                experiments/DELIVER-V6/tagcheck.py -- raw IFD bytes, not tifffile/PIL.",
        "commissioned  : C:\\dev\\strehl-out\\marker.tif (rendered 2026-08-23, predates the ICC",
        "                fix 96b7e119) reads ICC ABSENT, XResolution 1/1, ResolutionUnit none.",
        "                The reader can see the defect, so a clean read means something.",
        "                NOTE: the brief asked me to commission against an ORCH-FAITHFUL master.",
        "                Those files were deleted from disk by another process at 02:53 tonight;",
        "                marker.tif is the substitute and carries the identical defect signature.",
        "result        : %d/%d masters named here carry ICC 2716 B + 300/1 dpi + unit inch." % (
            len(named) - len(missing_tag), len(named)),
        "bytes recheck : %d/%d unchanged since render." % (len(named) - len(mismatched), len(named)),
        "",
        "foreign files in this folder (%d) -- NOT rendered by DELIVER-V6, not covered by any" % len(foreign),
        "record above, provenance unknown to me. Written 02:36-02:47, after my run ended at",
        "02:15. They carry Software 'strehl 0.0.0 (6af834dac08d)', i.e. my pinned commit, and",
        "they pass the same tag check -- but I did not render them and cannot attest to their",
        "invocation. Left in place deliberately rather than deleted:",
    ] + ["  %s" % s for s in foreign]

    man.write_text("\n\n".join(out).rstrip("\n") + "\n" + "\n".join(trailer) + "\n", encoding="utf-8")

    print("subjects in manifest : %d" % len(named))
    print("bytes unchanged      : %d" % (len(named) - len(mismatched)))
    for s, w, g in mismatched:
        print("  *** %s want %s got %s" % (s, w, g))
    print("tag check failures   : %d %s" % (len(missing_tag), missing_tag or ""))
    print("foreign tiffs        : %d %s" % (len(foreign), foreign))
    return 1 if (mismatched or missing_tag) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
