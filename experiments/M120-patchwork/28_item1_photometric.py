"""M120 step 28 -- ORCH item 1: is IDEALISED per-frame level removal better than
the shipped `--photometric` fit on bee-3-cpl, and by how much?

THE TENSION ORCH RECORDED:
  M120 : idealised removal of measured level drift  -> 60.9% of the effect
  M122 : shipped --photometric fit, B12 = 1.0638    -> 6.4% WORSE

Different metric, different ROI, idealised-vs-fitted. They need not agree. This
puts all arms on ONE footing so the comparison means something:

  A0        M122's default render                    (shipped)
  A1        M122's --photometric render              (the fitted correction)
  IDEAL     the same election, with per-frame level  (idealised removal)
            offsets removed exactly, re-merged

scored with ONE metric (M120's Q) on ONE ROI, and additionally on 12 windows so
the window-choice axis is visible separately from the arm axis.

Q = lapRMS(arm) / max over single input frames, bound 1.284 (M120 section 7).

Readers: tifffile + dtype assert on every .tif (fact 1615).
Geometry is VALIDATED before any arm is compared; mismatch is reported, not
worked around.
"""
import json
import numpy as np
import tifffile
from scipy import ndimage as ndi
from pathlib import Path

M122 = Path(r"C:\dev\strehl-out\M122\measure")
M93 = Path(r"C:\dev\strehl-out\M93-out")
C = Path(r"C:\dev\blog\death-of-software\projects\strehl\experiments\M87-occlusion\cache")
OUT = Path(r"C:\dev\strehl-out\M120")
BOX = (1178, 1922, 278, 1422)
ROI = (476, 604, 442, 570)
UNIT = np.sqrt(2.0) * 0.015214
WIN = 96


def rd(p):
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, (p, a.dtype)
    return a


def lap_rms(a):
    return float(np.sqrt((ndi.laplace(np.asarray(a, np.float64)) ** 2).mean()))


def ncc(a, b):
    a = a - a.mean()
    b = b - b.mean()
    return float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum()))


def main():
    A0 = rd(M122 / "bee-3-cpl__A0.tif")
    A1 = rd(M122 / "bee-3-cpl__A1.tif")
    print(f"A0 {A0.shape} {A0.dtype}   A1 {A1.shape} {A1.dtype}")
    assert A0.shape == A1.shape

    g4 = rd(M93 / "armM4-gate4-binlin.tif")
    print(f"M93 gate4 {g4.shape}")
    if A0.shape != g4.shape:
        print("!! GEOMETRY MISMATCH between M122 arms and M93 arms -- reporting, not "
              "working around")
        return

    a0 = A0[BOX[0]:BOX[1], BOX[2]:BOX[3], 1].astype(np.float64)
    a1 = A1[BOX[0]:BOX[1], BOX[2]:BOX[3], 1].astype(np.float64)
    m93 = g4[BOX[0]:BOX[1], BOX[2]:BOX[3], 1].astype(np.float64)

    print("\nGEOMETRY VALIDATION (must pass before any arm is compared):")
    print(f"  NCC(A0, M93 gate4)  = {ncc(a0, m93):.6f}")
    print(f"  NCC(A0, A1)         = {ncc(a0, a1):.6f}")
    if ncc(a0, m93) < 0.99:
        print("  !! A0 is not the same render as M93 gate4; they are different builds.")
        print("     Comparing A0 vs A1 remains valid (same run, same warp). Proceeding")
        print("     with A0/A1/IDEAL only, and NOT mixing in M93 numbers.")

    luma = np.load(C / "bee3-leg-luma.npy", mmap_mode="r")
    field = np.load(C / "bee3-leg-field.npy", mmap_mode="r")
    K, H, W = luma.shape
    bg = np.load(OUT / "m1_bg_mask.npy")
    fmax = np.load(OUT / "m9_fmax.npy")

    # ---- per-frame level offsets, measured on pure background (idealised) ----
    print("\nmeasuring per-frame levels on pure background ...")
    lev = np.array([float(np.asarray(luma[k], np.float32)[bg].mean()) for k in range(K)])
    ref = lev.mean()
    pp = 100 * (lev.max() - lev.min()) / ref
    print(f"  per-frame background level: {lev.min():.1f} .. {lev.max():.1f} "
          f"(mean {ref:.1f}), peak-to-peak {pp:.2f}%")

    # ---- merge under gate 4, with and without idealised level removal ----
    thr = fmax - 4.0 * UNIT
    num_raw = np.zeros((H, W), np.float64)
    num_fix = np.zeros((H, W), np.float64)
    den = np.zeros((H, W), np.float64)
    for k in range(K):
        adm = np.asarray(field[k], np.float32) >= thr
        f = np.asarray(luma[k], np.float32).astype(np.float64)
        num_raw += adm * f
        num_fix += adm * (f * (ref / lev[k]))
        den += adm
    den = np.maximum(den, 1)
    raw = num_raw / den
    ideal = num_fix / den
    print(f"  replication n_eff on ROI = {den[ROI[0]:ROI[1], ROI[2]:ROI[3]].mean():.1f} "
          f"(pipeline 166.8)")

    # denominator: noisiest single input frame, same pixels
    def denom(sl):
        return max(lap_rms(np.asarray(luma[k], np.float32)[sl]) for k in range(0, K, 12))

    print("\n" + "=" * 74)
    print("ONE METRIC, ONE ROI -- Q = lapRMS(arm) / max over single frames")
    print("=" * 74)
    sl = (slice(ROI[0], ROI[1]), slice(ROI[2], ROI[3]))
    d = denom(sl)
    gain = float(np.median(raw[sl]) / np.median(np.asarray(luma[K // 2], np.float32)[sl]))
    rows = {}
    for tag, arr, sc in (("A0  M122 default", a0[sl], 1.0),
                         ("A1  M122 --photometric", a1[sl], 1.0),
                         ("RAW  my replication, gate 4", raw[sl], gain),
                         ("IDEAL  level removed exactly", ideal[sl], gain)):
        q = lap_rms(arr) / (d * sc)
        rows[tag] = q
        print(f"  {tag:32}  lapRMS {lap_rms(arr):9.2f}   Q {q:7.3f}"
              f"   {'OVER' if q > 1.284 else 'under'} bound 1.284")

    qa0, qa1 = rows["A0  M122 default"], rows["A1  M122 --photometric"]
    qr, qi = rows["RAW  my replication, gate 4"], rows["IDEAL  level removed exactly"]
    print(f"\n  --photometric vs default   : Q {qa0:.3f} -> {qa1:.3f} "
          f"= {100*(qa1-qa0)/qa0:+.1f}%")
    print(f"  IDEALISED vs my raw arm    : Q {qr:.3f} -> {qi:.3f} "
          f"= {100*(qi-qr)/qr:+.1f}%")
    print(f"  excess over bound removed by idealised removal: "
          f"{100*(1-(qi-1.284)/(qr-1.284)):.1f}%" if qr > 1.284 else "")

    # ---- 12 windows, to separate the window-choice axis ----
    print("\n" + "=" * 74)
    print("SAME ARMS, 12 RULE-CHOSEN BACKGROUND WINDOWS (window axis isolated)")
    print("=" * 74)
    wins = [r for r in json.load(open("m6_localisation.json"))["rows"]][:12]
    acc = {k: [] for k in ("A0", "A1", "RAW", "IDEAL")}
    for r in wins:
        s = (slice(r["y"], r["y"] + WIN), slice(r["x"], r["x"] + WIN))
        dd = denom(s)
        acc["A0"].append(lap_rms(a0[s]) / dd)
        acc["A1"].append(lap_rms(a1[s]) / dd)
        acc["RAW"].append(lap_rms(raw[s]) / (dd * gain))
        acc["IDEAL"].append(lap_rms(ideal[s]) / (dd * gain))
    for k, v in acc.items():
        v = np.array(v)
        print(f"  {k:6} median Q {np.median(v):7.3f}   worst {v.max():7.3f}   "
              f"over bound {int((v>1.284).sum())}/12")
    r_ph = np.median(acc["A1"]) / np.median(acc["A0"])
    r_id = np.median(acc["IDEAL"]) / np.median(acc["RAW"])
    print(f"\n  ratio --photometric / default  = {r_ph:.4f}   "
          f"({'HARM' if r_ph > 1 else 'benefit'})")
    print(f"  ratio idealised / raw          = {r_id:.4f}   "
          f"({'HARM' if r_id > 1 else 'benefit'})")
    print(f"\n  M122 reported B12 = 1.0638 for --photometric on this stack.")
    print(f"  This run, on M120's metric and windows, gets {r_ph:.4f}.")

    json.dump(dict(roi=rows, windows={k: np.array(v).tolist() for k, v in acc.items()},
                   ratio_photometric=float(r_ph), ratio_idealised=float(r_id),
                   drift_pp_pct=float(pp), ncc_a0_m93=ncc(a0, m93)),
              open("m12_item1.json", "w"), indent=1)
    print("\nwrote m12_item1.json")


if __name__ == "__main__":
    main()
