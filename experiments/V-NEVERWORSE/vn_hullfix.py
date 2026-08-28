"""Part D: does the r_max-relative fix reintroduce hull violations?

ORCH asked for this specifically, and framed it as "your 0 / 72 / 511 hull
violations at exponents 1 / 8 / 16". THOSE ARE NOT MY NUMBERS. They are quoted
verbatim from the `Hull` doc comment inside `pyramid.rs` and appear in
RESULT.md section 9 as a block quotation of the Rust source, attributed there.
This lane has never measured them. That attribution error is the same class as
the `n_eff` one and is corrected here by MEASURING the exponent sweep rather
than citing it, on our own frames, with our own counter.

WHY A HULL VIOLATION IS THE RIGHT PRICE TO CHARGE. Each band computes its own
weight field. A per-band convex combination is inside the per-band hull, but a
SUM of convex combinations taken under DIFFERENT weightings is not a convex
combination of the original pixels. So the reconstruction can land outside the
range spanned by the input frames at that pixel -- overshoot, which is ringing.
The shipping merge clips to that hull, so the violation count is invisible in
the delivered image; it is nonetheless the sharpest available measure of how
discontinuous the weight field is, and a discontinuous weight field is exactly
what a more aggressive selection law produces.

THE COUNTER IS COMMISSIONED IN BOTH DIRECTIONS.

  D1 IDENTITY. With `hull=True` the merge clips, so the count must be EXACTLY
     zero for every arm. This proves the counter reads the reconstruction it
     was handed rather than reporting a constant.
  D2 PLANTED DEGRADATION, KNOWN ANSWER. Push the reconstruction out of the
     hull by a known amount at a known number of pixels and require the
     counter to return that number exactly. A counter that cannot recover a
     planted count cannot be trusted with an unplanted one.
  D3 PLANTED IMPROVEMENT. Replace the reconstruction with the per-pixel mean
     of the frames, which is inside the hull by construction, and require
     exactly zero. A statistic that only rises under plants is half blind.
  D4 RESPONSIVENESS / NON-SHORT-CIRCUIT. The count must rise with the
     selection exponent across a sweep. This is the direction `pyramid.rs`
     claims, measured here instead of quoted.

Never writes to D:. Reads the cached RGB bundle only.
"""
import io
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vn_pyr as VP  # noqa: E402
from vn_plateau import BETA, SHIP  # noqa: E402

OUT = r"C:\dev\strehl-out\V-NEVERWORSE\dilute"
BDIR = r"C:\dev\strehl-out\V-NEVERWORSE\bundle"
NB = 7
# Reported at several tolerances so the headline cannot be tolerance-gamed.
# 0.0 is the raw predicate; 0.5 DN is half a code value at the 16-bit scale
# these frames are carried in.
TOLS = (0.0, 1e-6, 0.5, 1.0)


def load_rgb(subj):
    npz = os.path.join(BDIR, "%s.npz" % subj)
    js = os.path.join(BDIR, "%s.json" % subj)
    if not (os.path.exists(npz) and os.path.exists(js)):
        raise IOError("no RGB bundle for %s" % subj)
    d = np.load(npz)
    meta = json.load(io.open(js, encoding="utf-8"))
    keys = [k for k in d.files if k.startswith("b")]
    keys.sort(key=lambda x: int(x[1:]))
    return [d[k] for k in keys], meta


def hull_of(frames):
    lo = frames[0].astype(np.float64)
    hi = lo.copy()
    for f in frames[1:]:
        ff = f.astype(np.float64)
        np.minimum(lo, ff, out=lo)
        np.maximum(hi, ff, out=hi)
    return lo, hi


def count_violations(rec, lo, hi, tols=TOLS):
    out = {}
    for t in tols:
        below = rec < (lo - t)
        above = rec > (hi + t)
        out["%g" % t] = int(below.sum() + above.sum())
    over = np.maximum(np.maximum(lo - rec, rec - hi), 0.0)
    out["max_excursion_dn"] = float(over.max())
    out["px_total"] = int(rec.size)
    return out


def build_weights(frames, var0, law, exponent, sharpen, theta, nb=NB):
    """Per-band weight stacks under either law, from the same band energies.

    The two laws are given IDENTICAL excess and floor fields; they differ only
    in how those are turned into weights. That is the whole point -- the arms
    must differ only in the variable under test, and here that is enforced by
    construction because both are computed inside one loop from one `excess`.
    """
    varp = VP.gauss_pyr(var0, nb)
    laps = [VP.lap_pyr(f[:, :, 1].astype(np.float64), nb)[0] for f in frames]
    n = len(frames)
    W = []
    for k in range(nb):
        p = VP.exponent_at(k, nb, exponent, sharpen)
        floor = SHIP["gate"] * BETA[k] * np.maximum(varp[k], 0.0)
        ex = [np.maximum(VP.smooth5(laps[i][k] ** 2) - floor, 0.0)
              for i in range(n)]
        if law == "ship":
            ws = [VP.select_weight(ex[i], floor, p) for i in range(n)]
        elif law == "rmax":
            r = [ex[i] / np.maximum(floor, 1.0) / VP.SNR_REF for i in range(n)]
            rmax = r[0].copy()
            for i in range(1, n):
                np.maximum(rmax, r[i], out=rmax)
            ws = []
            for i in range(n):
                eff = np.maximum(r[i] - theta * rmax, 0.0)
                ws.append(np.where(eff > 0.0, eff ** p, 0.0))
        else:
            raise ValueError(law)
        W.append(np.stack(ws))
    return W


def arm(frames, var0, law, exponent, theta, sharpen=None, hull=False, nb=NB):
    sharpen = SHIP["sharpen"] if sharpen is None else sharpen
    W = build_weights(frames, var0, law, exponent, sharpen, theta, nb=nb)
    cfg = dict(SHIP, exponent=exponent, sharpen=sharpen, hull=hull)
    rec, _ = VP.merge(frames, cfg, BETA, var0, nb=nb, fixedW=W)
    del W
    return rec


def winner_agreement(W):
    """How often adjacent bands elect the SAME frame at the same place.

    A hull violation requires the bands to disagree, so this is the quantity
    that should explain the violation count's shape. Compared on the coarser
    band's grid by subsampling the finer band's winner field at stride 2,
    which is a SAMPLE of the finer field rather than a resampling of it --
    interpolating a categorical winner index would invent frames that never
    won anywhere. Pixels where nothing was admitted in either band are
    excluded and counted, because an abstention is not an agreement.
    """
    frac, wt = [], []
    for k in range(len(W) - 1):
        a = W[k].argmax(axis=0)
        b = W[k + 1].argmax(axis=0)
        liva = W[k].sum(axis=0) > 0.0
        livb = W[k + 1].sum(axis=0) > 0.0
        h, w = b.shape
        a = a[::2, ::2][:h, :w]
        liva = liva[::2, ::2][:h, :w]
        m = liva & livb[:a.shape[0], :a.shape[1]]
        if not m.any():
            continue
        frac.append(float((a[m] == b[:a.shape[0], :a.shape[1]][m]).mean()))
        wt.append(int(m.sum()))
    if not frac:
        return float("nan")
    return float(sum(f * n for f, n in zip(frac, wt)) / sum(wt))


def commission(frames, var0):
    res, ok = {}, True
    lo, hi = hull_of(frames)

    # D1 IDENTITY: with the clip on, the count is exactly zero.
    rec = arm(frames, var0, "ship", SHIP["exponent"], 0.0, hull=True)
    res["D1_hull_on"] = count_violations(rec, lo, hi)
    if res["D1_hull_on"]["0"] != 0:
        ok = False

    # D2 PLANTED DEGRADATION WITH A KNOWN ANSWER: push exactly `want` pixels
    # a known distance above the hull and require that exact count back.
    rng = np.random.default_rng(11)
    bad = rec.copy()
    flat = bad.reshape(-1)
    want = 1234
    idx = rng.choice(flat.size, size=want, replace=False)
    flat[idx] = hi.reshape(-1)[idx] + 7.5
    got = count_violations(bad, lo, hi)
    res["D2_planted"] = dict(planted=want, counted=got["0"],
                             max_excursion_dn=got["max_excursion_dn"])
    if got["0"] != want or abs(got["max_excursion_dn"] - 7.5) > 1e-9:
        ok = False
    del bad, rec

    # D3 PLANTED IMPROVEMENT: the per-pixel mean is inside the hull by
    # construction, so a working counter must return exactly zero on it.
    mean = np.mean([f.astype(np.float64) for f in frames], axis=0)
    res["D3_mean_inside"] = count_violations(mean, lo, hi)
    if res["D3_mean_inside"]["0"] != 0:
        ok = False
    del mean

    # D4 RESPONSIVENESS: the counter must respond to the selection exponent.
    #
    # MEASURED FAILURE THAT SHAPED THIS. The first version required the COUNT
    # to rise monotonically, which is the direction `pyramid.rs`'s doc comment
    # claims. It does not. Measured on coffee-bubbles at a flat ladder the
    # count runs 10662 / 57117 / 75582 / 65757 at exponents 1 / 4 / 8 / 16 --
    # it peaks and then FALLS. The severity is monotone over the same sweep
    # (440.663 / 566.463 / 711.468 / 755.033 DN), so the counter is responding;
    # it is the count that is non-monotone, and D5 tests why rather than
    # asserting it. The gate is therefore on max excursion, with the count
    # recorded. Note this does not contradict the Rust comment's 0 / 72 / 511:
    # those are three orders of magnitude smaller than anything measured here,
    # so they are a different image, predicate or scale, and this lane cannot
    # reproduce them and does not claim to.
    sweep = []
    for e in (1.0, 4.0, 8.0, 16.0):
        W = build_weights(frames, var0, "ship", e, 1.0, 0.0)
        cfg = dict(SHIP, exponent=e, sharpen=1.0, hull=False)
        r, _ = VP.merge(frames, cfg, BETA, var0, nb=NB, fixedW=W)
        c = count_violations(r, lo, hi)
        sweep.append(dict(exponent=e, viol=c["0"],
                          max_excursion_dn=c["max_excursion_dn"],
                          band_agreement=winner_agreement(W)))
        del r, W
    res["D4_exponent_sweep"] = sweep
    x = [s["max_excursion_dn"] for s in sweep]
    if not all(x[i] < x[i + 1] for i in range(len(x) - 1)):
        ok = False

    # D5 EXPLAINING THE NON-MONOTONE COUNT.
    #
    # MEASURED FAILURE THAT SHAPED THIS. The first version predicted that as
    # the exponent rises the bands converge on a common winner, and tested it
    # by measuring adjacent-band winner AGREEMENT. That control was inert by
    # construction: `argmax(r**p) == argmax(r)` for any p > 0, so the winner's
    # IDENTITY cannot move with the exponent at all. It duly read 0.2845,
    # 0.2845, 0.2845, 0.2840 across a 16x sweep and the hypothesis was refuted
    # by a statistic that could not have supported it either. That is the same
    # family as the identity control that short-circuited at `s == 1`: a
    # control keyed on a quantity the variable under test cannot change.
    #
    # The replacement is a convergence prediction the exponent CAN move. As
    # p rises the weight field approaches a hard argmax, so the violation
    # count must approach the count of the exact winner-take-all merge. If
    # p = 16 is nearer that limit than p = 4 is, an interior maximum in the
    # count is a real property of the merge and not a defect in the counter.
    Wa = build_weights(frames, var0, "ship", 8.0, 1.0, 0.0)
    for k in range(len(Wa)):
        hot = np.zeros_like(Wa[k])
        np.put_along_axis(hot, Wa[k].argmax(axis=0)[None], 1.0, axis=0)
        Wa[k] = np.where(Wa[k].sum(axis=0)[None] > 0.0, hot, 0.0)
    cfg = dict(SHIP, exponent=8.0, sharpen=1.0, hull=False)
    ra, _ = VP.merge(frames, cfg, BETA, var0, nb=NB, fixedW=Wa)
    lim = count_violations(ra, lo, hi)["0"]
    del ra, Wa
    d4 = res["D4_exponent_sweep"]
    d = {s["exponent"]: abs(s["viol"] - lim) for s in d4}
    counts = [s["viol"] for s in d4]
    res["D5_converges_to_argmax"] = dict(
        argmax_limit=lim, distance=d,
        # The gate. Hard winner-take-all is the MOST band-disagreeing case
        # available, so it must produce more overshoot than any finite
        # exponent. That is a prediction with a sign and it is checkable.
        argmax_is_maximal=bool(lim > max(counts)),
        # Reported, NOT gated, and NOT explained. The count does not approach
        # the limit monotonically -- p = 8 lands nearer it than p = 16 does.
        # This lane has no account of that and says so rather than inventing
        # one; the severity IS monotone, which is what D4 gates on.
        monotone_toward_limit=bool(
            d[1.0] > d[4.0] > d[8.0] > d[16.0]),
        band_disagreement=1.0 - d4[0]["band_agreement"],
        agreement_is_exponent_invariant=bool(
            max(abs(s["band_agreement"] - d4[0]["band_agreement"])
                for s in d4) < 0.01))
    if not res["D5_converges_to_argmax"]["argmax_is_maximal"]:
        ok = False

    res["ok"] = ok
    return res, lo, hi


def main():
    subj = sys.argv[1] if len(sys.argv) > 1 else "coffee-bubbles"
    thetas = [float(x) for x in sys.argv[2:]] or [0.25, 0.5, 0.75]
    frames, meta = load_rgb(subj)
    print("PART D: %s, %d frames, shape %s, range %.1f..%.1f DN"
          % (subj, len(frames), frames[0].shape,
             float(min(f.min() for f in frames)),
             float(max(f.max() for f in frames))))
    var0, read2, gph = VP.fit_variance(frames[0][:, :, 1].astype(np.float64))
    print("  variance model: read^2 %.4g  gain/DN %.4g" % (read2, gph))

    print("\nCOMMISSIONING THE HULL COUNTER (both directions)")
    c, lo, hi = commission(frames, var0)
    print("  D1 hull=True  -> %d violations (must be 0)" % c["D1_hull_on"]["0"])
    print("  D2 planted %d -> counted %d, max excursion %.6f DN (want 7.5)"
          % (c["D2_planted"]["planted"], c["D2_planted"]["counted"],
             c["D2_planted"]["max_excursion_dn"]))
    print("  D3 plain mean -> %d violations (must be 0)"
          % c["D3_mean_inside"]["0"])
    print("  D4 exponent sweep (flat ladder, sharpen=1.0):")
    for s in c["D4_exponent_sweep"]:
        print("       exponent %5.1f  violations %8d  max excursion %10.3f DN"
              "  adjacent-band winner agreement %.4f"
              % (s["exponent"], s["viol"], s["max_excursion_dn"],
                 s["band_agreement"]))
    print("  D5 argmax limit %d violations (maximal: %s); distance from it "
          "%s; monotone toward it: %s (reported, not gated, not explained).  "
          "Adjacent-band winner DISAGREEMENT %.4f (exponent-invariant: %s -- "
          "argmax(r^p) == argmax(r), so this measures the structural band "
          "disagreement that makes overshoot possible, not the exponent)"
          % (c["D5_converges_to_argmax"]["argmax_limit"],
             c["D5_converges_to_argmax"]["argmax_is_maximal"],
             {k: int(v) for k, v in
              sorted(c["D5_converges_to_argmax"]["distance"].items())},
             c["D5_converges_to_argmax"]["monotone_toward_limit"],
             c["D5_converges_to_argmax"]["band_disagreement"],
             c["D5_converges_to_argmax"]["agreement_is_exponent_invariant"]))
    print("  commissioning ok: %s" % c["ok"])
    if not c["ok"]:
        print("\nREFUSED: hull counter failed commissioning; nothing reported")
        return 1

    rows = []
    print("\nTHE PRICE OF THE FIX (shipping ladder, hull clip OFF so the "
          "overshoot is visible)")
    print("  %-22s %10s %10s %10s %10s %12s"
          % ("arm", "viol@0", "viol@1e-6", "viol@0.5", "viol@1.0",
             "max_exc_DN"))
    for law, th in [("ship", 0.0)] + [("rmax", t) for t in thetas]:
        rec = arm(frames, var0, law, SHIP["exponent"], th, hull=False)
        cv = count_violations(rec, lo, hi)
        del rec
        name = "shipping" if law == "ship" else "rmax theta=%.2f" % th
        rows.append(dict(law=law, theta=th, name=name, **cv))
        print("  %-22s %10d %10d %10d %10d %12.3f"
              % (name, cv["0"], cv["1e-06"], cv["0.5"], cv["1"],
                 cv["max_excursion_dn"]))
    base = rows[0]
    for r in rows[1:]:
        r["rel_to_shipping"] = (r["0"] / base["0"]) if base["0"] else None
        print("  %-22s violations x%.4f of shipping"
              % (r["name"], r["rel_to_shipping"])
              if r["rel_to_shipping"] is not None else
              "  %-22s shipping had zero; ratio undefined" % r["name"])

    p = os.path.join(OUT, "hullfix-%s.json" % subj)
    json.dump(dict(subject=subj, n=len(frames), commission=c, arms=rows,
                   tols=list(TOLS), source=meta.get("source", "rgb-bundle")),
              io.open(p, "w", encoding="utf-8"), default=float)
    print("\nwrote %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
