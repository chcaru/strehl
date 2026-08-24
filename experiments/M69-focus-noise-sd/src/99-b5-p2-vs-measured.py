"""M69 arm B5 -- reconciling two of my own committed numbers.

POST HOC. Not pre-registered. It exists because B3 measured the coarse field's
corpus rho_true span at 2.104x while M69's committed fact 13 reports 1.186x for
what its own text calls the same quantity.

Three candidate explanations, and this arm removes two of them by construction:

  region     -- REMOVED. Both use the SAME central 2048 raw-pixel crop
                (80-corpus-rho.py CROP = 2048; 20-a2's read_latent CROP = 2048).
  debias     -- REMOVED. rho_obs needs no debias at all, so the comparison is
                run on rho_obs only.
  estimator  -- the remaining difference: fact 13 evaluates the P2 PREDICTOR on
                the frame; B3 MEASURES the replicate SD of the shipped chain.

Frames: fact 13 averaged first/middle/last; this arm reports the middle frame
alone AND the same three-frame average, so frame choice is priced too.
"""

import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m69  # noqa: E402

a2 = __import__("importlib").import_module("20-a2-m66-replication")
p2m = __import__("importlib").import_module("40-p2-predictor")
bmod = __import__("importlib").import_module("97-b-fine-field")

CROP = a2.CROP
STACKS = bmod.STACKS


def crop_of(path):
    v = m69.raw_visible(path)
    y = (v.shape[0] - CROP) // 2
    x = (v.shape[1] - CROP) // 2
    y -= y % 2
    x -= x % 2
    return v[y : y + CROP, x : x + CROP].copy()


def p2_rho_obs(raw, iso):
    luma = m69.luma_from_raw(raw)
    sig = m69.green_luma_sigma(luma, iso)
    return float(m69.interior(p2m.p2(luma, sig)).mean() / m69.FOCUS_NOISE_SD)


def measured_rho_obs(raw, iso, radius, reg, c, nrep=a2.NREP_EXTRA, seed=777):
    sd_dn = a2.raw_noise_sd(raw, iso)
    rng = np.random.default_rng(seed)
    acc = None
    for _ in range(nrep):
        luma = m69.luma_from_raw(raw + sd_dn * rng.standard_normal(raw.shape))
        f = bmod.field(luma, radius, reg, sigma=m69.green_luma_sigma(luma, iso))
        if acc is None:
            acc = m69.Welford(f.shape)
        acc.push(f)
    return float(m69.interior(acc.sd(), bmod.inset_for(radius, reg)).mean() / c)


def main():
    m69.banner("M69 arm B5 -- P2 the PREDICTOR against the MEASURED chain (POST HOC)")
    m69.dump_constants()
    b = json.loads((m69.OUT / "97-b-fine-field.json").read_text(encoding="utf-8"))
    c_coarse = b["b1"]["coarse+reg"]["sd"]
    print(f"\n  Identical central {CROP}x{CROP} crop, coarse (shipped) field, rho_obs only.")
    print("  No debias is applied anywhere in this table, so the debias cannot")
    print("  contribute to any difference in it.\n")
    print(f"  {'stack':<16} {'ISO':>5} {'P2 mid':>8} {'P2 x3':>8} {'MEASURED':>9} "
          f"{'meas/P2':>8} {'fact 13 P2x3':>13}")
    print("  " + "-" * 74)
    committed = json.loads((m69.OUT / "80-corpus-rho.json").read_text(encoding="utf-8"))
    out = {}
    for st in STACKS:
        files = m69.stack_files(st)
        mid = files[len(files) // 2]
        iso = m69.iso_of(mid)
        raw_mid = crop_of(mid)
        p2_mid = p2_rho_obs(raw_mid, iso)
        p2_three = float(
            np.mean([p2_rho_obs(crop_of(p), m69.iso_of(p))
                     for p in (files[0], files[len(files) // 2], files[-1])])
        )
        meas = measured_rho_obs(raw_mid, iso, m69.WINDOW_RADIUS,
                                m69.REGULARISER_RADIUS, c_coarse)
        ratio = meas / p2_mid
        print(f"  {st:<16} {iso:>5.0f} {p2_mid:>8.4f} {p2_three:>8.4f} {meas:>9.4f} "
              f"{ratio:>8.3f} {committed[st]['rho_obs']:>13.4f}")
        out[st] = {"iso": iso, "p2_mid": p2_mid, "p2_three": p2_three,
                   "measured": meas, "meas_over_p2": ratio,
                   "committed_p2_three": committed[st]["rho_obs"]}

    p2v = [v["p2_mid"] for v in out.values()]
    mv = [v["measured"] for v in out.values()]
    rv = [v["meas_over_p2"] for v in out.values()]
    print(f"\n  P2 predicted  : min {min(p2v):.4f}  max {max(p2v):.4f}  "
          f"span {max(p2v) / min(p2v):.3f}x")
    print(f"  MEASURED      : min {min(mv):.4f}  max {max(mv):.4f}  "
          f"span {max(mv) / min(mv):.3f}x")
    print(f"  meas / P2     : min {min(rv):.3f}  max {max(rv):.3f}  "
          f"median {np.median(rv):.3f}  span {max(rv) / min(rv):.3f}x")

    # control: does P2-on-three-frames reproduce the committed fact 13 column?
    err = [abs(out[s]["p2_three"] / out[s]["committed_p2_three"] - 1.0) for s in STACKS]
    print(f"\n  K15 CONTROL -- P2 on the same three frames reproduces the committed")
    print(f"  80-corpus-rho.json rho_obs column: worst |error| {max(err):.2%}  bar 1%"
          f"  -> {'MET' if max(err) <= 0.01 else 'NOT MET'}")
    print("  If this is MET, the 2.104x-vs-1.186x gap is NOT a bug in either run;")
    print("  it is two different estimators of the same quantity disagreeing.")

    (m69.OUT / "99-b5.json").write_text(
        json.dumps({"rows": out, "k15_worst_err": max(err)}, indent=2), encoding="utf-8"
    )
    print("\n  wrote out/99-b5.json")


if __name__ == "__main__":
    main()
