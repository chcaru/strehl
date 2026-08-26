"""Per-pair registration peaks, parsed from the run logs.

The residual false positives in BOTH subjects trace to the same cause: pairs
whose phase-correlation peak is low. bee-1-cpl's two H2 candidates come from
k=264 (peak 0.759) and k=297 (peak 0.660), the worst-registered frames in its
stack; flowers-cpl's worst comes from k=155 (peak 0.642). A frame that cannot be
registered cannot be compared, because the tile extracted from it is not the same
patch of scene as the merge tile. Gating on that is a statement about the
INSTRUMENT, not about detail, so it is applied to both arms of both subjects
identically and every number is reported gated AND ungated.
"""
import re
from pathlib import Path
import numpy as np

OUT = Path(r"C:\dev\strehl-out\V-BESTFRAME")
HDR = re.compile(r"^(\S+): (\d+) frames on disk, probing (\d+) ADJACENT PAIRS")
ROW = re.compile(r"^\s+k=\s*(\d+)/(\d+)\s+\S+\s+s=([\d.]+)/([\d.]+)\s+peak=([\d.]+)/([\d.]+)")


def _decode(path):
    """PowerShell's `*>>` writes UTF-16LE with a BOM. Decoding that as UTF-8
    yields NUL-interleaved garbage that matches no regex, so a gate reading it
    silently passes everything -- indistinguishable from a gate that found
    nothing to remove. Detect the BOM instead of assuming an encoding."""
    b = path.read_bytes()
    if b[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return b.decode("utf-16", errors="ignore")
    return b.decode("utf-8-sig", errors="ignore")


def all_peaks():
    out = {}
    for lg in sorted(OUT.glob("*.log")):
        subj = None
        for line in _decode(lg).splitlines():
            m = HDR.match(line)
            if m:
                subj = m.group(1); out.setdefault(subj, {}); continue
            m = ROW.match(line)
            if m and subj:
                out[subj][int(m.group(1))] = (float(m.group(5)), float(m.group(6)),
                                              float(m.group(3)))
    return out


def peaks_for(subj, anchors):
    d = all_peaks().get(subj, {})
    return np.array([min(d[int(k)][0], d[int(k)][1]) if int(k) in d else np.nan
                     for k in anchors])


if __name__ == "__main__":
    for s, d in sorted(all_peaks().items()):
        ks = sorted(d)
        print(f"{s:38s} {len(ks):2d} pairs  peak min {min(min(d[k][:2]) for k in ks):.3f} "
              f"max {max(max(d[k][:2]) for k in ks):.3f}  "
              f"below 0.80: {sum(1 for k in ks if min(d[k][:2]) < 0.80)}")
