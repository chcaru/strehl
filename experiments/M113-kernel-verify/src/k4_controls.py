"""M113 K4 - control-power audit of `crates/strehl-cli/examples/m95-lanczos.rs`.

Rule 20: for each control, write down the input that would make it FAIL, and
check that such an input exists. A control that cannot fail is not evidence.

C1 interpolating at phase 0        published max|w - delta| = 2.301e-8
C2 partition of unity              published max|sum(w) - 1| = 2.384e-7
C3 support vanishes at window edge  published w[0] at phase 1 = 0.000e0
C4 discrimination vs Catmull-Rom    published lanczos3 0.6466, catmullrom 0.4488

Everything below reimplements the example's arithmetic in float32 to match, then
asks what each control would have caught.
"""
import json
import os

import numpy as np

F32 = np.float32
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")
PI = F32(np.pi)
TAU = F32(2.0 * np.pi)


def l3_patch(x):
    """The example's l3(), including BOTH of its early returns."""
    x = F32(x)
    if abs(x) < F32(1e-6):
        return F32(1.0)
    if abs(x) >= F32(3.0):
        return F32(0.0)
    px = PI * x
    return F32(3.0) * (np.sin(px) * np.sin(px / F32(3.0))) / (px * px)


def l3_patch_noclamp(x):
    """The same, with the `>= 3.0` guard REMOVED. Everything else identical."""
    x = F32(x)
    if abs(x) < F32(1e-6):
        return F32(1.0)
    px = PI * x
    return F32(3.0) * (np.sin(px) * np.sin(px / F32(3.0))) / (px * px)


def weights_patch(f, fn=l3_patch, normalise=True):
    w = np.array([fn(F32(f) - F32(i - 2)) for i in range(6)], dtype=np.float32)
    s = w.sum(dtype=np.float32)
    if normalise and abs(s) > F32(1e-12):
        w = (w / s).astype(np.float32)
    return w


def sinc64(x):
    return 1.0 if abs(x) < 1e-12 else np.sin(np.pi * x) / (np.pi * x)


def weights_landed(f):
    """crates/strehl-core/src/align.rs::lanczos3_weights -- f64, sinc(t)*sinc(t/3),
    NO |x|>=3 clamp, centre guard 1e-12 inside sinc()."""
    w = np.array([sinc64(f - (i - 2.0)) * sinc64((f - (i - 2.0)) / 3.0) for i in range(6)])
    return (w / w.sum()).astype(np.float32)


def cr_w(f):
    f = F32(f); f2 = f * f; f3 = f2 * f
    return np.array([F32(-0.5) * f3 + f2 - F32(0.5) * f,
                     F32(1.5) * f3 - F32(2.5) * f2 + F32(1.0),
                     F32(-1.5) * f3 + F32(2.0) * f2 + F32(0.5) * f,
                     F32(0.5) * f3 - F32(0.5) * f2], dtype=np.float32)


def recon(wfun, offs, freq, phase):
    """The example's C4 statistic, verbatim in structure."""
    w = wfun(phase)
    num = F32(0.0); den = F32(0.0)
    for k in range(-40, 40):
        want = np.cos(TAU * F32(freq) * F32(k + phase), dtype=np.float32)
        got = np.float32(sum(w[j] * np.cos(TAU * F32(freq) * F32(k + offs[j]), dtype=np.float32)
                             for j in range(len(w))))
        num = np.float32(num + got * want); den = np.float32(den + want * want)
    return float(num / den)


def sharpen(wfun, offs, a):
    """wfun convolved with the 3-tap sharpener [-a, 1+2a, -a]: a deliberately
    RINGY kernel whose passband gain EXCEEDS 1. Support grows by one each side."""
    lo, hi = min(offs) - 1, max(offs) + 1
    newoffs = list(range(lo, hi + 1))

    def f(phase):
        w = wfun(phase)
        out = np.zeros(len(newoffs), dtype=np.float32)
        for j, o in enumerate(offs):
            for d, c in ((-1, -a), (0, 1 + 2 * a), (1, -a)):
                out[newoffs.index(o + d)] += np.float32(w[j] * c)
        return out
    return f, newoffs


def step_overshoot(wfun, offs, phase=0.5):
    """Resample a unit step at `phase` and report peak overshoot beyond [0,1]."""
    n = 81
    src = np.concatenate([np.zeros(n // 2, dtype=np.float32), np.ones(n - n // 2, dtype=np.float32)])
    w = wfun(phase)
    out = []
    for i in range(8, n - 8):
        out.append(float(sum(w[j] * src[i + offs[j]] for j in range(len(w)))))
    out = np.array(out)
    return float(max(out.max() - 1.0, 0.0) + max(0.0 - out.min(), 0.0))


def band_gain_err(wfun, offs, phase=0.5, lo=0.30, hi=0.48):
    """Mean |gain - 1| across the metric band: distance from TRUTH, not gain."""
    fs = np.linspace(lo, hi, 19)
    return float(np.mean([abs(recon(wfun, offs, f, phase) - 1.0) for f in fs]))


def main():
    res = {}
    print("=" * 78)
    print("REPRODUCING THE EXAMPLE'S FOUR PUBLISHED READINGS (float32, same arithmetic)")
    w0 = weights_patch(0.0)
    c1 = float(np.max(np.abs(w0 - np.array([0, 0, 1, 0, 0, 0], dtype=np.float32))))
    worst = max(abs(float(weights_patch(i / 1000.0).sum(dtype=np.float32)) - 1.0)
                for i in range(1001))
    c3 = float(weights_patch(1.0)[0])
    g_l = recon(weights_patch, [-2, -1, 0, 1, 2, 3], 0.40, 0.5)
    g_c = recon(cr_w, [-1, 0, 1, 2], 0.40, 0.5)
    print(f"  C1 max|w - delta|      mine {c1:.3e}   published 2.301e-8")
    print(f"  C2 max|sum(w) - 1|     mine {worst:.3e}   published 2.384e-7")
    print(f"  C3 w[0] at phase 1     mine {c3:.3e}   published 0.000e0")
    print(f"  C4 lanczos3 {g_l:.4f} catmullrom {g_c:.4f}   published 0.6466 / 0.4488")
    res["repro"] = dict(c1=c1, c2=worst, c3=c3, c4_l3=g_l, c4_cr=g_c)

    print("\n" + "=" * 78)
    print("C2 POWER. The weights are normalised THREE LINES ABOVE the assertion.")
    un = max(abs(float(weights_patch(i / 1000.0, normalise=False).sum(dtype=np.float32)) - 1.0)
             for i in range(1001))
    print(f"  max|sum(w) - 1| WITHOUT the normalisation : {un:.3e}")
    print(f"  max|sum(w) - 1| WITH    the normalisation : {worst:.3e}   (bar 1e-6)")
    print(f"  the normaliser removes the defect C2 exists to detect, by {un/worst:.0f}x.")
    print(f"  What survives is f32 rounding of a 6-term sum: {worst:.3e} against a 1e-6 bar,")
    print(f"  i.e. C2 is passing with {1e-6/worst:.1f}x margin over FLOAT EPSILON, not over a kernel.")
    print("  VERDICT: no kernel reaching this assertion through this normaliser can fail it.")
    res["C2"] = dict(unnormalised=un, normalised=worst, ratio=un / worst)

    print("\n" + "=" * 78)
    print("C3 POWER. `l3()` returns EXACTLY 0.0 for |x| >= 3.0 by an early return.")
    print("  C3 evaluates w[0] at phase 1, i.e. l3(1 - (0 - 2)) = l3(3.0) -> that guard.")
    print(f"  with the guard    : {float(weights_patch(1.0)[0]):.3e}")
    print(f"  guard REMOVED     : {float(weights_patch(1.0, fn=l3_patch_noclamp)[0]):.3e}")
    print(f"  LANDED f64 code   : {float(weights_landed(1.0)[0]):.3e}   (align.rs has NO such guard)")
    print("  VERDICT: C3 asserts a `return 0.0` written six lines above it. Zero power.")
    res["C3"] = dict(guard=float(weights_patch(1.0)[0]),
                     noguard=float(weights_patch(1.0, fn=l3_patch_noclamp)[0]),
                     landed=float(weights_landed(1.0)[0]))

    print("\n" + "=" * 78)
    print("C4 POWER. C4 passes iff gain(lanczos3) > gain(catmull-rom). It is an ORDERING")
    print("on PASSBAND GAIN with NO UPPER BOUND, and the correct answer is gain == 1.")
    print("A kernel that overshoots scores HIGHER. That is the ringing direction, and it is")
    print("the exact failure mode align.rs's own doc-comment gives as why this is not default.")
    ladder = [("catmull-rom", cr_w, [-1, 0, 1, 2]),
              ("lanczos3 (patch)", weights_patch, [-2, -1, 0, 1, 2, 3]),
              ("lanczos3 (landed f64)", weights_landed, [-2, -1, 0, 1, 2, 3])]
    for a in (0.25, 0.5, 1.0):
        f, o = sharpen(cr_w, [-1, 0, 1, 2], a)
        ladder.append((f"catmull-rom + sharpen a={a}", f, o))
    print(f"\n  {'kernel':28s} {'C4 gain':>9s} {'C4 rank':>8s} {'mean|gain-1|':>13s} "
          f"{'step over/under':>16s}")
    rows = []
    for name, f, o in ladder:
        g = recon(f, o, 0.40, 0.5)
        rows.append((name, g, band_gain_err(f, o), step_overshoot(f, o)))
    order = {n: i + 1 for i, (n, _, _, _) in enumerate(sorted(rows, key=lambda r: -r[1]))}
    for name, g, e, s in rows:
        print(f"  {name:28s} {g:9.4f} {order[name]:8d} {e:13.4f} {s:16.4f}")
    best_c4 = max(rows, key=lambda r: r[1])
    best_truth = min(rows, key=lambda r: r[2])
    print(f"\n  C4 ranks FIRST      : {best_c4[0]}  (gain {best_c4[1]:.4f}, "
          f"step excursion {best_c4[3]:.4f})")
    print(f"  closest to TRUTH is : {best_truth[0]}  (mean|gain-1| {best_truth[2]:.4f})")
    if best_c4[0] != best_truth[0]:
        print("  ==> C4's winner is NOT the most accurate kernel. C4 is a gain contest.")
    res["C4"] = dict(rows=[dict(kernel=n, c4=g, mean_abs_gain_err=e, step_excursion=s)
                           for n, g, e, s in rows])

    print("\n" + "=" * 78)
    print("DOES THE EXAMPLE TEST THE CODE THAT SHIPPED?")
    print("  example  : lanczos3_weights(f: f32), 3*sin(px)sin(px/3)/(px*px), guards 1e-6 and >=3.0")
    print("  align.rs : lanczos3_weights(f: f64), sinc(t)*sinc(t/3), NO >=3.0 guard, 1e-12 in sinc()")
    print(f"  {'phase':>6s} {'max|w_patch - w_landed|':>26s}")
    worst_d = 0.0
    for i in range(0, 1001, 50):
        p = i / 1000.0
        d = float(np.max(np.abs(weights_patch(p).astype(np.float64) - weights_landed(p).astype(np.float64))))
        worst_d = max(worst_d, d)
        if i % 250 == 0:
            print(f"  {p:6.3f} {d:26.3e}")
    print(f"  worst over the phase sweep: {worst_d:.3e}")
    print("  The two agree numerically, but they are SEPARATE SOURCE. Nothing asserts they")
    print("  agree, so the example cannot fail in response to a change in align.rs.")
    res["shipped_vs_example"] = dict(max_weight_diff=worst_d)

    json.dump(res, open(os.path.join(OUT, "k4_controls.json"), "w"), indent=1)
    print(f"\nwrote {os.path.join(OUT, 'k4_controls.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
