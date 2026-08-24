"""N2b closed-form check.

The label-swap control is only a power control if it predicts a NUMBER, not
just a direction.  Swapping the data of the R site and the G1 site permutes
which per-channel focus index lands in which slot, so the post-swap medians are
fully determined by the pre-swap ones with NO free parameters:

  pre-swap, writing everything relative to true green:
      k_R  = kG + dR      k_G1 = kG      k_G2 = kG      k_B = kG + dB

  post-swap the R site carries green data and the G1 site carries red data:
      k_R' = kG           k_G1' = kG + dR    k_G2' = kG    k_B' = kG + dB

  so, with kG' = mean(k_G1', k_G2') = kG + dR/2:
      dR'   = k_R' - kG'          = -dR/2
      dB'   = k_B' - kG'          = dB - dR/2
      null' = k_G1' - k_G2'       = dR          <-- the SIGNAL moves into the NULL

If instead the instrument were measuring the lattice site rather than the
wavelength, none of these would move.
"""
import sys, os, json

sys.path.insert(0, os.path.dirname(__file__))
from common import OUT, dump


def rows(name):
    d = json.load(open(os.path.join(OUT, "json", name)))
    return d["data"] if isinstance(d, dict) else d


if __name__ == "__main__":
    base = [x for x in rows("e3_argmax.json") if x["stack"] == "tweezers-cpl"][0]
    sw = [x for x in rows("e3_controls_n2b.json")
          if x.get("control") == "N2b_label_swap_power"][0]

    dR, dB = base["median_dR"], base["median_dB"]
    pred = {"dR": -dR / 2.0, "dB": dB - dR / 2.0, "null": dR}
    meas = {"dR": sw["median_dR"], "dB": sw["median_dB"], "null": sw["median_null"]}

    print(f"pre-swap:  dR = {dR:+.4f}   dB = {dB:+.4f}   null = {base['median_null']:+.4f}")
    print("\n  quantity   predicted   measured    |error| (frames)")
    worst = 0.0
    for k in ("dR", "dB", "null"):
        e = abs(pred[k] - meas[k]); worst = max(worst, e)
        print(f"  {k:8s}   {pred[k]:+9.4f}   {meas[k]:+9.4f}   {e:.4f}")
    ok = worst <= 0.02
    print(f"\n  worst error {worst:.4f} frames, bar 0.02 -> {'PASS' if ok else 'FAIL'}")
    print("  The signal follows the DATA through the lattice, not the SITE.")
    dump("e3_n2b_closedform", [{"predicted": pred, "measured": meas,
                                "worst_abs_error_frames": worst,
                                "bar": 0.02, "pass": bool(ok)}])
