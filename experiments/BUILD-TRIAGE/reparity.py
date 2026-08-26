"""Do the three near-parity subjects survive WITHOUT the retracted clamp excuse?

ORCH retracted the hull-clamp cost: it is ~3.1% overall and, at every octave
where detail lives, removes LESS than the noise already present (0.10-0.42 sigma).
My report used "inside the 8.6-18.9% clamp handicap" to explain the only three
ORCH-site ratios below parity.  That explanation is now void, so the ratios must
stand on their own or not at all.

This re-reads stored JSON.  It runs no renders and re-measures nothing.
"""
import json
import os
import sys

OUT = r"C:\dev\strehl-out\BUILD-TRIAGE\compare"


def main() -> int:
    subs = sys.argv[1:] or ["109MSDCF", "119MSDCF", "lead-1-cpl", "bee-3-cpl"]
    for s in subs:
        p = os.path.join(OUT, s + ".orch.json")
        if not os.path.exists(p):
            print(f"== {s}: no stored comparison")
            continue
        d = json.load(open(p))
        v = d["sites"]["ORCH-BEST"]
        print(f"== {s}   ncc={v.get('ncc')}  reliable={v.get('reliable')}  "
              f"caution={v.get('caution')}  why={v.get('why_unreliable')}")
        for b in ("low", "mid", "high"):
            z = v.get(b)
            if not isinstance(z, dict):
                continue
            sm, sf = z.get("sig_merge_dn", 0.0), z.get("sig_frame_corr_dn", 0.0)
            nm, nf = z.get("noise_merge_dn", 0.0), z.get("noise_frame_dn", 0.0)
            snr_m = sm / nm if nm else float("nan")
            snr_f = sf / nf if nf else float("nan")
            print(f"   {b:5s} raw={z.get('ratio_raw'):.4f} "
                  f"corr={z.get('ratio_corr'):.4f} "
                  f"gather={z.get('gather_cost'):.4f}   "
                  f"sig m/f = {sm:8.0f} /{sf:8.0f}   "
                  f"SNR m/f = {snr_m:6.2f} /{snr_f:6.2f}")
    print("\nratio_corr already has the alignment-gather cost removed, so these "
          "need no\nfurther correction. The clamp was never in them; it was an "
          "excuse applied after.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
