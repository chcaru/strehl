"""Corpus-wide test of ORCH's mechanism, using the binary's own admission record.

ORCH aimed the hypothesis at `softgate.rs`. That module did not run: every one
of the 26 masters carries STREHL_SOFT_GATE = (unset), and the switch's own
documentation says None -- the top-hat Gate -- "must remain the default". The
Gaussian kernel, WEIGHT_FLOOR and z = 4.7096 are all unexecuted for SHIP-V4.

But the hypothesis survives being re-aimed, and the shipping binary already
reports the quantity it needs. The default `stack` path is a Laplacian pyramid
merge whose per-coefficient weight is (band power above the noise floor)^exp,
with a noise gate at 2.00x the modelled band-noise power; below it no frame may
win and the merge averages. The binary prints, per level, the fraction of
coefficients where that happened:

    averaged : 26.1% 4.7% 0.0% 0.0% 0.0% 0.0% 0.0% 100.0%

That IS ORCH's admission decision, per coefficient, already measured, for every
subject in the corpus.

The prediction. If mottle comes from a spatially varying mixture of "averaged"
(noise down by sqrt(n)) and "selected" (single-frame noise), then a level that
averaged 0% is uniform, a level that averaged 100% is uniform, and the mottle
is worst in between. The natural summary is the mixedness 4p(1-p), which is 0
at both extremes and 1 at p = 0.5. A subject whose coarse levels sit near p=0.5
should read blotchier than one whose levels are pinned at either end.

The coarse levels are the ones that matter, and their scale is not a guess:
the master is 7032 px wide, so a coefficient at coarse level j spans about
7032 / (width >> j) px. Levels 0 and 1 land at roughly 125 px and 63 px, inside
the 50-400 px band `orch_blotch` measures. That is why this is the right place
to look and the fine levels are not.
"""
import io
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vn_lib as L  # noqa: E402

PROV = r"C:\dev\strehl-out\acceptance\SHIP-V4"
OUT = r"C:\dev\strehl-out\V-NEVERWORSE\mech"
AVG = re.compile(r"^\s*\|\s*averaged\s*:\s*(.+)$", re.M)
BANDS = re.compile(r"^\s*\|\s*bands\s*:\s*(\d+) Laplacian levels", re.M)
FRAMES = re.compile(r"^\s*frames\s*:\s*(\d+)\s*$", re.M)
SOFT = re.compile(r"STREHL_SOFT_GATE\s*=\s*\(([^)]*)\)")


def read_prov(path):
    t = io.open(path, encoding="utf-8", errors="replace").read()
    m = AVG.search(t)
    if not m:
        return None
    pct = [float(v) / 100.0 for v in re.findall(r"([\d.]+)%", m.group(1))]
    b = BANDS.search(t)
    f = FRAMES.search(t)
    s = SOFT.search(t)
    return dict(avg=pct, bands=int(b.group(1)) if b else None,
                frames=int(f.group(1)) if f else None,
                soft=s.group(1) if s else "MISSING")


def mixedness(p):
    return 4.0 * p * (1.0 - p)


def gather():
    rows = {}
    miss = []
    for fn in sorted(os.listdir(PROV)):
        if not fn.endswith(".provenance.txt"):
            continue
        subj = fn.split("--SHIP-V4")[0]
        r = read_prov(os.path.join(PROV, fn))
        if r is None or not r["avg"]:
            miss.append(subj)
            continue
        rows[subj] = r
    return rows, miss


def main():
    rows, miss = gather()
    print("")
    print("THE SHIPPING ADMISSION RECORD  (from the binary's own self-report)")
    print("")
    soft = {}
    for s, r in rows.items():
        soft.setdefault(r["soft"], []).append(s)
    for k, v in sorted(soft.items()):
        print("  STREHL_SOFT_GATE = (%s) on %d subjects" % (k, len(v)))
    print("")
    print("  %-22s %6s %6s  %7s %7s   %7s" %
          ("subject", "frames", "bands", "avg L0", "avg L1", "mix L0"))
    for s in sorted(rows):
        r = rows[s]
        a = r["avg"]
        print("  %-22s %6d %6d  %6.1f%% %6.1f%%   %6.3f"
              % (s, r["frames"] or -1, r["bands"] or -1,
                 100 * a[0], 100 * a[1] if len(a) > 1 else -1,
                 mixedness(a[0])))
    print("")
    print("  examined %d + missing %d = %d provenance files"
          % (len(rows), len(miss), len(rows) + len(miss)))
    if miss:
        print("  missing: %s" % ", ".join(miss))
    os.makedirs(OUT, exist_ok=True)
    L.jdump({s: dict(avg=r["avg"], frames=r["frames"], bands=r["bands"],
                     soft=r["soft"]) for s, r in rows.items()},
            os.path.join(OUT, "admission.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
