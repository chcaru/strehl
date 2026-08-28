"""Corpus-scale test of ORCH's two banner claims, at n=26 rather than n=1.

ORCH measured one subject (`leaf-2-cpl`) at HEAD and drew two conclusions:

  1. every `x white` entry is ABOVE 1.0, so the measured floor is HIGHER than
     the white-noise constant and the landed gatefloor fix makes the gate
     STRICTER, not looser -- the reverse of what was relayed to four lanes;
  2. `averaged` reads 54.4% at level 0 and 0.0% at levels 1-6, so above the
     finest band no coefficient is ever gated and the merge is, by the banner's
     own stated criterion, a naive pyramid stacker there.

Both are structural claims about the merge, and a structural claim measured on
one subject is a hypothesis. The 26 logs from the DEF-2f858c62 arm already carry
this banner, so the corpus answer costs no render at all.

WHY THIS ARM IS A VALID TEST OF A CLAIM MADE AT HEAD
Pin 2f858c62 contains 78fed9a1 (the gatefloor fix) -- verified by ancestry in
section 13.1 -- and its provenance records STREHL_GATE_FLOOR unset with the
built-in default ON. Section 13.1 further established that the two commits
between this pin and HEAD are bit-identical on the render path across three
subjects, 296,808,192 samples, max|d| = 0. So this arm IS HEAD behaviour, and
reading it is a reproduction on a DIFFERENT BINARY than ORCH's, which is a
stronger test than re-running the same one.

A PRECISION CAVEAT THAT MUST NOT BE GLOSSED
The banner prints one decimal place. "0.0%" is therefore any value below 0.05%,
not necessarily zero. "The gate never fires above level 0" and "the gate fires
on fewer than 1 coefficient in 2000" are different statements and only the
second is supported by this text. Both sustain ORCH's conclusion, but the
distinction is recorded rather than smoothed over.
"""
import json
import re
import sys
from pathlib import Path

import numpy as np

ARM = Path(r"D:\strehl-out\BUILD-OUTPUT\BUILD-RECERT\arms\DEF-2f858c62")
OUT = Path(r"D:\strehl-out\BUILD-OUTPUT\BUILD-RECERT\logs\bannercensus.json")

RE_XWHITE = re.compile(r"x white\s*:\s*([0-9.\s]+)")
RE_FLOOR = re.compile(r"measured floor\s*:\s*([0-9.\s]+)")
RE_AVG = re.compile(r"^averaged\s*:\s*(.+)$", re.M)
RE_GATE = re.compile(r"noise gate\s*:\s*([0-9.]+)\s*x")
RE_BANDS = re.compile(r"bands\s*:\s*(\d+) Laplacian")
RE_FRAMES = re.compile(r"^frames\s*:\s*(\d+) from", re.M)
RE_GAIN = re.compile(r"band noise gain\s*:\s*([0-9.\s]+)")

rows = []
for log in sorted(ARM.glob("*.log")):
    t = log.read_text(encoding="utf-8", errors="replace")
    subject = log.name.split("--")[0]
    m_x, m_f, m_a = RE_XWHITE.search(t), RE_FLOOR.search(t), RE_AVG.search(t)
    if not (m_x and m_f and m_a):
        rows.append({"subject": subject, "state": "NO BANNER"})
        continue
    xw = [float(v) for v in m_x.group(1).split()]
    fl = [float(v) for v in m_f.group(1).split()]
    av = [float(v.rstrip("%")) for v in m_a.group(1).split()]
    gain = [float(v) for v in RE_GAIN.search(t).group(1).split()]
    rows.append({
        "subject": subject, "state": "OK",
        "frames": int(RE_FRAMES.search(t).group(1)),
        "bands": int(RE_BANDS.search(t).group(1)),
        "gate_k": float(RE_GATE.search(t).group(1)),
        "x_white": xw, "measured_floor": fl, "band_noise_gain": gain,
        "averaged_pct": av,
    })

ok = [r for r in rows if r["state"] == "OK"]
print(f"logs read: {len(rows)}   banner present: {len(ok)}\n")

# --------------------------------------------------------------------------
# CLAIM 1: every x-white entry is above 1.0
# --------------------------------------------------------------------------
print("CLAIM 1 -- measured floor vs the white-noise constant (x white)\n")
print(f"  {'subject':<38} {'frames':>6}  " + "  ".join(f"L{i}" .rjust(6) for i in range(4)))
n_entries = n_above = 0
for r in sorted(ok, key=lambda r: -max(r["x_white"])):
    n_entries += len(r["x_white"])
    n_above += sum(1 for v in r["x_white"] if v > 1.0)
    print(f"  {r['subject']:<38} {r['frames']:>6}  "
          + "  ".join(f"{v:6.4f}" for v in r["x_white"]))
allx = np.array([v for r in ok for v in r["x_white"]])
print(f"\n  entries {n_entries}   above 1.0: {n_above}   below 1.0: {n_entries - n_above}")
print(f"  min {allx.min():.4f}   median {np.median(allx):.4f}   max {allx.max():.4f}")
per_level = [np.array([r["x_white"][i] for r in ok if len(r["x_white"]) > i])
             for i in range(4)]
for i, v in enumerate(per_level):
    print(f"  level {i}: n={len(v):2d}  min {v.min():.4f}  median {v.median() if hasattr(v,'median') else np.median(v):.4f}  max {v.max():.4f}")
CLAIM1 = n_above == n_entries
print(f"\n  ORCH's claim 'every entry ABOVE 1.0' holds on all 26: "
      f"{'CONFIRMED' if CLAIM1 else 'REFUTED'}")

# --------------------------------------------------------------------------
# CLAIM 2: the gate does not fire above level 0
# --------------------------------------------------------------------------
print("\n\nCLAIM 2 -- fraction of coefficients the gate averaged, per level\n")
nlev = max(len(r["averaged_pct"]) for r in ok)
print(f"  {'subject':<38} " + "  ".join(f"L{i}".rjust(6) for i in range(nlev - 1)) + "   base")
for r in sorted(ok, key=lambda r: -r["averaged_pct"][0]):
    a = r["averaged_pct"]
    print(f"  {r['subject']:<38} " + "  ".join(f"{v:6.1f}" for v in a))
mid = np.array([[r["averaged_pct"][i] for i in range(1, nlev - 1)] for r in ok])
lvl0 = np.array([r["averaged_pct"][0] for r in ok])
base = np.array([r["averaged_pct"][-1] for r in ok])
print(f"\n  level 0 : min {lvl0.min():5.1f}%  median {np.median(lvl0):5.1f}%  max {lvl0.max():5.1f}%")
print(f"  L1..L{nlev-2}  : min {mid.min():5.1f}%  median {np.median(mid):5.1f}%  max {mid.max():5.1f}%"
      f"   ({mid.size} cells over {len(ok)} subjects)")
print(f"  base    : min {base.min():5.1f}%  median {np.median(base):5.1f}%  max {base.max():5.1f}%")
nonzero = int((mid > 0.0).sum())
CLAIM2 = nonzero == 0
print(f"\n  cells above L0 printing anything but 0.0%: {nonzero} of {mid.size}")
print(f"  ORCH's claim 'the gate is inert above level 0' holds on all 26: "
      f"{'CONFIRMED' if CLAIM2 else 'REFUTED'}")
print("  CAVEAT: the banner prints one decimal, so 0.0% means < 0.05%, not")
print("          exactly zero. The claim supported is 'fires on fewer than 1")
print("          coefficient in 2000', which sustains the conclusion either way.")

# --------------------------------------------------------------------------
# The mechanism the two claims share: the floor is compared against band power
# that falls by ~an order of magnitude per level, so k=2.0 is a different
# demand at every scale. Print what the gate is actually asking for.
# --------------------------------------------------------------------------
print("\n\nWHY -- what the gate demands at each level, in units of band power\n")
g = np.array([r["band_noise_gain"] for r in ok])
f = np.array([r["measured_floor"] for r in ok])
k = np.array([r["gate_k"] for r in ok])
print(f"  gate k: {sorted(set(k.tolist()))}")
print(f"  {'level':>5}  {'median band noise gain':>22}  {'median measured floor':>21}  {'ratio to L0':>11}")
for i in range(g.shape[1]):
    fl = f"{np.median(f[:, i]):21.4f}" if i < f.shape[1] else " " * 17 + "(white)"
    print(f"  {i:>5}  {np.median(g[:, i]):22.4f}  {fl}  "
          f"{np.median(g[:, i]) / np.median(g[:, 0]):11.5f}")

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(rows, indent=1), encoding="utf-8")
print(f"\nwrote {OUT}")

print(f"\n{'CLAIM 1 CONFIRMED' if CLAIM1 else 'CLAIM 1 REFUTED'}   "
      f"{'CLAIM 2 CONFIRMED' if CLAIM2 else 'CLAIM 2 REFUTED'}   "
      f"on {len(ok)}/26 subjects, binary A058F737 (not ORCH's AAAF8666)")
sys.exit(0)
