#!/usr/bin/env python3
"""Sweep the MERGE-LIMITED threshold over BUILD-TRIAGE's own evidence.

Reads C:\dev\strehl-out\BUILD-TRIAGE (read-only) and re-runs the SHIPPED
classifier with BLUR_BAD_PX moved, so the robustness of MERGE-LIMITED = 0 is
measured rather than asserted.  Nothing under experiments/BUILD-TRIAGE is
edited; triage.BLUR_BAD_PX is rebound in this process only.
"""
from __future__ import annotations

import json
import os
import sys

BT = r"C:\dev\blog\death-of-software\projects\strehl\experiments\BUILD-TRIAGE"
sys.path.insert(0, BT)
import tri  # noqa: E402
import triage  # noqa: E402

tri.OUT = r"C:\dev\strehl-out\BUILD-TRIAGE"
tri.LIN = os.path.join(tri.OUT, "lin")


def worst_over_all_sites(sub):
    """Worst blur over EVERY site, and over the sites the gate keeps."""
    p = os.path.join(tri.OUT, "compare", sub + ".json")
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as fh:
        c = json.load(fh)
    rows = []
    for k, v in c["sites"].items():
        e = v["edge"]
        rows.append({
            "site": k, "blur": e["blur_equiv_px"], "ratio": e["ratio"],
            "deficit": e["deficit_dnpx"], "merge": e["merge_dnpx"],
            "frame_corr": e["frame_corr_dnpx"],
            "snr_merge": e["merge_dnpx"] / e["noise_merge_dn"] if e["noise_merge_dn"] else float("inf"),
            "snr_frame": e["frame_dnpx"] / e["noise_frame_dn"] if e["noise_frame_dn"] else float("inf"),
            "reliable": v.get("reliable", True),
            "weak": triage.classify.__globals__ and None,
        })
    return rows


def main() -> int:
    subs = tri.SUBJECTS
    ev = {s: triage.load(s) for s in subs}
    base = {s: triage.classify(s, ev[s]) for s in subs}

    print("=" * 112)
    print("A. PER-SUBJECT WORST DEFICIT, ordered (usable sites only, as the "
          "classifier sees them)")
    print("=" * 112)
    print(f"{'subject':<38} {'verdict as shipped':<32} {'worst px':>9} "
          f"{'site':<12} {'ratio':>7} {'deficit DN/px':>13}")
    rows = []
    for s in subs:
        e = base[s]["evidence"]
        wb = e.get("worst_blur_px")
        site = e.get("worst_site")
        d = None
        r = None
        if site:
            with open(os.path.join(tri.OUT, "compare", s + ".json"), encoding="utf-8") as fh:
                c = json.load(fh)
            d = c["sites"][site]["edge"]["deficit_dnpx"]
            r = c["sites"][site]["edge"]["ratio"]
        rows.append((wb if wb is not None else -1.0, s, base[s]["verdict"], wb, site, r, d))
    for wbk, s, v, wb, site, r, d in sorted(rows, reverse=True):
        print(f"{s:<38} {v:<32} "
              f"{('n/a' if wb is None else f'{wb:8.3f}'):>9} {str(site):<12} "
              f"{('n/a' if r is None else f'{r:7.4f}'):>7} "
              f"{('n/a' if d is None else f'{d:+13.1f}'):>13}")

    print()
    print("=" * 112)
    print("B. THRESHOLD SWEEP -- shipped classifier, BLUR_BAD_PX rebound")
    print("=" * 112)
    orig = triage.BLUR_BAD_PX
    print(f"{'BLUR_BAD_PX':>12} {'MERGE-LIMITED':>14}  {'first subjects to flip'}")
    for t in [0.90, 0.80, 0.75, 0.74, 0.70, 0.65, 0.64, 0.60, 0.50, 0.49, 0.45,
              0.40, 0.39, 0.35, 0.30]:
        triage.BLUR_BAD_PX = t
        rs = {s: triage.classify(s, ev[s]) for s in subs}
        ml = [s for s in subs if rs[s]["verdict"] == "MERGE-LIMITED"]
        print(f"{t:>12.2f} {len(ml):>14}  {', '.join(ml) if ml else '-'}")
    triage.BLUR_BAD_PX = orig

    print()
    print("=" * 112)
    print("C. EVERY SITE IN THE CORPUS, including the ones the gate dropped")
    print("=" * 112)
    print(f"{'subject':<36} {'site':<12} {'blur':>6} {'ratio':>7} "
          f"{'merge':>9} {'frmcorr':>9} {'SNRm':>6} {'SNRf':>6} {'kept':>5}  note")
    dropped_big = []
    for s in subs:
        p = os.path.join(tri.OUT, "compare", s + ".json")
        if not os.path.exists(p):
            print(f"{s:<36} (no compare json)")
            continue
        with open(p, encoding="utf-8") as fh:
            c = json.load(fh)
        for k, v in c["sites"].items():
            e = v["edge"]
            snm = e["merge_dnpx"] / e["noise_merge_dn"] if e["noise_merge_dn"] else float("inf")
            snf = e["frame_dnpx"] / e["noise_frame_dn"] if e["noise_frame_dn"] else float("inf")
            kept = (k != "FLAT" and v.get("reliable", True)
                    and not _weak(v))
            note = []
            if not v.get("reliable", True):
                note.append("UNRELIABLE")
            if k == "FLAT":
                note.append("FLAT (never votes)")
            if v.get("caution"):
                note.append("; ".join(v["caution"])[:70])
            print(f"{s:<36} {k:<12} {e['blur_equiv_px']:>6.2f} {e['ratio']:>7.4f} "
                  f"{e['merge_dnpx']:>9.1f} {e['frame_corr_dnpx']:>9.1f} "
                  f"{snm:>6.2f} {snf:>6.2f} {str(kept):>5}  {' | '.join(note)}")
            if not kept and k != "FLAT" and e["blur_equiv_px"] >= 0.80:
                dropped_big.append((s, k, e["blur_equiv_px"], snm, snf))
    print()
    print("D. SITES THAT WOULD HAVE VOTED MERGE-LIMITED BUT WERE DROPPED")
    for s, k, b, snm, snf in dropped_big:
        print(f"   {s:<36} {k:<12} blur={b:.2f} px  SNR merge={snm:.2f} "
              f"frame={snf:.2f}  (gate needs >= 4.00 on both when ratio<1)")
    if not dropped_big:
        print("   none")
    return 0


def _weak(v):
    """Reproduce triage.weak() exactly (it is a closure, so it is re-stated)."""
    if any("not clear of" in c for c in v.get("caution", [])):
        return True
    e = v.get("edge") or {}
    m, f = e.get("merge_dnpx", 0.0), e.get("frame_corr_dnpx", 0.0)
    nm, nf = e.get("noise_merge_dn", 0.0), e.get("noise_frame_dn", 0.0)
    if nm > 0 and m < 4.0 * nm:
        return True
    if e.get("ratio", 1.0) < 1.0 and nf > 0 and f < 4.0 * nf:
        return True
    return False


if __name__ == "__main__":
    raise SystemExit(main())
