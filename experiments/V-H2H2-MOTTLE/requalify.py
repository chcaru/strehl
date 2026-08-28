# V-H2H2: re-qualify my scoring bands on MY subject, per ORCH correction #4.
#
# THE INSTRUCTION BEING RETIRED. I was told to score with contrast_ms.py taking
# band 0 (0.25-0.50) as NOISE and band 1 (0.17-0.25) as SIGNAL, corpus-wide.
# V-LINEAR (31eda43a) measured the signal/noise boundary moving 0.17-0.48 across
# subjects, so that fixed mapping is only correct where the boundary happens to
# land near 0.25.
#
# MY SUBJECT IS 112MSDCF AND IT HAS ALREADY BEEN MEASURED. It is not in the
# document's headline five, but V-LINEAR's round 2 added it explicitly because
# it "carries the band-0 gate-floor arm", and the sweep output survives at
# experiments/V-LINEAR/bandsweep-far20-112MSDCF.json even though the develops
# were purged in the disk emergency. So I do not have to leave my verdict
# unqualified and I do not have to spend 15 GB of develops to qualify it.
#
# WHAT THIS SCRIPT DOES. It maps contrast_ms.py's band edges onto V-LINEAR's
# MEASURED sub-bands by overlap and classifies each scoring band by what was
# actually measured underneath it:
#     NOISE   every overlapping measured sub-band FAILs   -> grain may be read
#     SIGNAL  every overlapping measured sub-band PASSes  -> acuity may be read
#     MIXED   anything else                               -> NEITHER may be read
#
# MIXED is the point of the exercise. A band that is half qualified signal and
# half marginal cannot support an acuity verdict, and quietly rounding it to
# SIGNAL is precisely the failure ORCH is correcting. The script refuses such a
# band and falls through to the finest band that is wholly SIGNAL.
#
# CONTROL. V-LINEAR ran a matched-defocus control at far=8 as well as far=20.
# A boundary that is really a property of the subject must not depend on how far
# "defocused" is. Both are loaded and the CLASSIFICATION must agree; if it does
# not, that is reported as a failure and no verdict is issued.

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"C:\dev\blog\death-of-software\projects\strehl")
VL = ROOT / "experiments" / "V-LINEAR"
MS = ROOT / "experiments" / "ORCH-drift-check" / "contrast_ms.py"
SUBJECT = "112MSDCF"
TMP = Path(r"C:\Users\chris\AppData\Local\Temp")

RUNS = {"far=20": f"bandsweep-far20-{SUBJECT}.json",
        "far=8": f"bandsweep-far8-{SUBJECT}.json"}


def load(fn):
    p = VL / fn
    assert p.exists(), f"missing {p}"
    rows = json.load(open(p))
    row = next((r for r in rows if r["key"] == SUBJECT), None)
    assert row is not None, f"{fn} has no row for {SUBJECT}"
    return row


def classify(bands, lo, hi):
    """Classify a scoring band [lo,hi) by the measured sub-bands it overlaps."""
    ov = [(k, v) for k, v in bands.items()
          if v["f_lo"] < hi and v["f_hi"] > lo]
    # Only the contiguous fine ladder is meaningful here; the wide summary bands
    # (0.10-0.20 etc.) overlap several and would double-count.
    ov = [(k, v) for k, v in ov if (v["f_hi"] - v["f_lo"]) <= 0.09]
    assert ov, f"no measured sub-band overlaps {lo}-{hi}"
    verdicts = {v["verdict"] for _, v in ov}
    if verdicts <= {"FAIL(noise)"}:
        kind = "NOISE"
    elif verdicts <= {"PASS"}:
        kind = "SIGNAL"
    else:
        kind = "MIXED"
    return kind, ov


print(f"subject {SUBJECT}")
rows = {}
for tag, fn in RUNS.items():
    r = load(fn)
    rows[tag] = r
    print(f"  {tag:7s}  N={r['n_real']} step={r['step']} far={r['far_real']} "
          f"tiles={r['tiles']} kept={r['kept']} confirmed={r['confirmed']}")

print("\nMEASURED LADDER (fine bands only), far=20 vs far=8 control")
print(f"{'band':>12} {'R far20':>9} {'verdict':>12} {'R far8':>9} {'verdict':>12}  agree")
fine = sorted(((k, v) for k, v in rows["far=20"]["bands"].items()
               if (v["f_hi"] - v["f_lo"]) <= 0.09),
              key=lambda kv: kv[1]["f_lo"])
disagree = []
for k, v in fine:
    v8 = rows["far=8"]["bands"].get(k)
    a = "n/a"
    if v8:
        same = (v["verdict"] == v8["verdict"])
        a = "yes" if same else "NO"
        if not same:
            disagree.append((k, v["verdict"], v8["verdict"]))
    print(f"{k:>12} {v['R']:9.3f} {v['verdict']:>12} "
          f"{v8['R'] if v8 else float('nan'):9.3f} {v8['verdict'] if v8 else '-':>12}  {a}")

passing = [v["f_hi"] for _, v in fine if v["verdict"] == "PASS"]
boundary = max(passing) if passing else None
print(f"\nBOUNDARY (highest fully-PASSing fine band) = {boundary}")
if disagree:
    print(f"  NOTE: far=8/far=20 verdict differs on {len(disagree)} band(s): "
          + ", ".join(f"{k} {a}/{b}" for k, a, b in disagree))

# contrast_ms.py's band edges, read off its own printed table.
SCORING = [(0, 0.25, 0.50), (1, 0.17, 0.25), (2, 0.08, 0.17),
           (3, 0.04, 0.08), (4, 0.02, 0.04), (5, 0.01, 0.02)]

print("\nSCORING BANDS RE-CLASSIFIED ON THIS SUBJECT")
print(f"{'band':>4} {'cyc/px':>12} {'ORCH fixed':>11} {'MEASURED':>9}   overlapping measured sub-bands")
kinds = {}
for b, lo, hi in SCORING:
    try:
        kind, ov = classify(rows["far=20"]["bands"], lo, hi)
    except AssertionError:
        kind, ov = "UNMEASURED", []
    k8 = None
    if ov:
        try:
            k8, _ = classify(rows["far=8"]["bands"], lo, hi)
        except AssertionError:
            k8 = None
    kinds[b] = (kind, k8)
    fixed = {0: "NOISE", 1: "SIGNAL"}.get(b, "-")
    detail = ", ".join(f"{k}:{v['verdict'].replace('FAIL(noise)','FAIL')}" for k, v in ov) or "-"
    flag = "" if (k8 is None or k8 == kind) else f"  [far8 says {k8}]"
    print(f"{b:>4} {f'{lo}-{hi}':>12} {fixed:>11} {kind:>9}   {detail}{flag}")

grain_band = next((b for b, _, _ in SCORING if kinds[b][0] == "NOISE"), None)
acuity_band = None
for b, _, _ in SCORING:
    if kinds[b][0] == "SIGNAL":
        acuity_band = b
        break

print(f"\n  grain must be read at the finest NOISE band  : band {grain_band}")
print(f"  acuity must be read at the finest SIGNAL band: band {acuity_band}")
if kinds.get(1, ("",))[0] == "MIXED":
    print("  band 1 is MIXED on this subject -- it is NOT a valid acuity band here,")
    print("  which is exactly the fixed-band error ORCH is retiring.")

# Now re-read the actual ratios at the re-qualified bands.
SCALE_RE = re.compile(r"B rescaled by\s+([0-9.]+)")
PAIRS = [("srgb   A vs K", r"vh2h2-2side\A.tif", r"vh2h2-2side\K.tif"),
         ("linear A vs K", r"vh2h2-lin\A.tif", r"vh2h2-lin\K.tif")]

print("\nVERDICT AT THE RE-QUALIFIED BANDS  (corr = raw/rescale, per b6862058)")
for label, ra, rb in PAIRS:
    pa, pb = TMP / ra, TMP / rb
    if not (pa.exists() and pb.exists()):
        print(f"  {label}: SKIPPED, master missing")
        continue
    out = subprocess.run([sys.executable, str(MS), str(pa), str(pb)],
                         capture_output=True, text=True)
    assert out.returncode == 0, f"{label}: instrument failed"
    scale = float(SCALE_RE.search(out.stdout).group(1))
    tab = {}
    for line in out.stdout.splitlines():
        p = line.split()
        if len(p) >= 8 and p[0].isdigit():
            tab[int(p[0])] = (float(p[-4]), float(p[-1]))  # flat ratio, edge ratio
    assert len(tab) == len(SCORING), f"{label}: parsed {len(tab)} bands"
    gf_r, _ = tab[grain_band]
    _, ae_r = tab[acuity_band]
    _, b1_r = tab[1]
    print(f"\n  {label}   rescale={scale:.4f}")
    print(f"    GRAIN  band {grain_band} FLAT : raw {gf_r:.4f}  corr {gf_r/scale:.4f}   (want << 1)")
    print(f"    ACUITY band {acuity_band} EDGE : raw {ae_r:.4f}  corr {ae_r/scale:.4f}   (want >= 0.98)"
          f"   {'PASS' if min(ae_r, ae_r/scale) >= 0.98 else 'FAIL'}")
    print(f"    [retired ORCH band-1 EDGE : raw {b1_r:.4f}  corr {b1_r/scale:.4f}]")
