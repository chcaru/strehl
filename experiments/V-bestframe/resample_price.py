"""Price the path-boundary handicap BUILD-SHARP raised, AT THIS INSTRUMENT'S BAND.

BUILD-SHARP 21.6 asks whether this survey's reference arm is warped or unwarped.
It is UNWARPED. bestframe.py's own module docstring says so in capitals:
"NEITHER SIDE IS EVER RESAMPLED FOR MEASUREMENT." So the merge pays the alignment
gather and the frame arm does not. The construction objection is CORRECT.

What remains is the magnitude, and that cannot be read off BUILD-SHARP's table.
It prices f = 0.25 / 0.35 / 0.50 cyc/px. The FINE band here is DoG(1.0, 2.0),
which peaks at f = 0.153 cyc/px -- BELOW every tabulated row -- and the loss is
steeply frequency dependent. Quoting the 0.35 row at this band would overstate
the handicap, which is the unsafe direction for a verifier arguing a deficit is
real. So price it here.

A. Identify the kernel by reproducing BUILD-SHARP 20.4's plant numbers EXACTLY.
   If this fails, everything after it is about the wrong interpolator.
B. Integrate that kernel against the actual DoG band weight and a natural-image
   spectrum, phase-averaged over the measured near-uniform phase.
"""
import numpy as np

TAPS = np.array([-1.0, 0.0, 1.0, 2.0])


def cr_weights(phi):
    """Catmull-Rom (Keys a = -0.5) weights for taps at offsets -1, 0, 1, 2."""
    p = np.asarray(phi, float)
    return np.stack([
        -0.5 * p**3 + 1.0 * p**2 - 0.5 * p,
         1.5 * p**3 - 2.5 * p**2 + 1.0,
        -1.5 * p**3 + 2.0 * p**2 + 0.5 * p,
         0.5 * p**3 - 0.5 * p**2,
    ], axis=0)


def cr_amp(f, phi):
    """|K(f, phi)| for one axis. f in cycles/px, may be an array."""
    f = np.atleast_1d(np.asarray(f, float))
    w = cr_weights(phi)                                  # (4,) or (4, m)
    ph = np.exp(2j * np.pi * np.multiply.outer(f, TAPS))  # (nf, 4)
    return np.abs(ph @ w)                                 # (nf,) or (nf, m)


def bilinear_amp(f, phi):
    f = np.atleast_1d(np.asarray(f, float))
    return np.abs((1 - phi) + phi * np.exp(2j * np.pi * f))


def dog_response(f, s1, s2):
    """Amplitude response of DoG(s1, s2) at radial frequency f."""
    return np.abs(np.exp(-2 * np.pi**2 * s1**2 * f**2) -
                  np.exp(-2 * np.pi**2 * s2**2 * f**2))


def main():
    print("=" * 78)
    print("A. KERNEL IDENTIFICATION -- reproduce BUILD-SHARP 20.4 plant, phi=0.5 both axes")
    print("=" * 78)
    exp = {0.25: 0.781250, 0.35: 0.402210, 0.50: 0.000000}
    ok = True
    for f, e in exp.items():
        cr = float(cr_amp(f, 0.5)[0]) ** 2
        bl = float(bilinear_amp(f, 0.5)[0]) ** 2
        hit = abs(cr - e) < 5e-6
        ok &= hit
        print(f"  f={f:.2f}  catmull-rom(2D) {cr:.6f}   bilinear(2D) {bl:.6f}   "
              f"BUILD-SHARP {e:.6f}   -> CR {'MATCH' if hit else 'MISS'}")
    print(f"  kernel identified as Catmull-Rom, 2-D = amplitude squared: "
          f"{'CONFIRMED' if ok else 'FAILED -- STOP'}")
    if not ok:
        raise SystemExit("kernel identification failed; do not trust anything below")

    print()
    print("  cross-check against BUILD-SHARP 20.3 'align (2-D)', phase-averaged")
    phis = (np.arange(2000) + 0.5) / 2000.0
    for f, e in ((0.25, 0.88986), (0.35, 0.69055), (0.50, 0.42096)):
        m = float(np.mean(cr_amp(f, phis)[0])) ** 2
        print(f"    f={f:.2f}  E_phi[|K|]^2 = {m:.5f}   BUILD-SHARP {e:.5f}   "
              f"delta {m - e:+.5f}")

    print()
    print("=" * 78)
    print("B. WHERE THIS INSTRUMENT ACTUALLY MEASURES")
    print("=" * 78)
    s1, s2 = 1.0, 2.0
    ff = np.linspace(1e-4, 0.5, 20000)
    H = dog_response(ff, s1, s2)
    fpk = float(ff[np.argmax(H)])
    u = np.log(s2**2 / s1**2) / (2 * np.pi**2 * (s2**2 - s1**2))
    print(f"  FINE = DoG({s1}, {s2}).  peak of |H| at f = {fpk:.4f} cyc/px "
          f"(closed form {np.sqrt(u):.4f})")
    c = np.cumsum(H**2 * ff)
    c /= c[-1]
    for q in (0.10, 0.50, 0.90):
        print(f"    power-weighted f{int(q*100):02d} = {float(np.interp(q, c, ff)):.4f} cyc/px")
    print(f"  BUILD-SHARP's lowest tabulated row is f = 0.25 -- ABOVE this band's "
          f"median. Their 0.35 figure is not the figure that applies here.")

    print()
    print("  band-integrated AMPLITUDE retention, 2-D, phase-averaged over uniform phase")
    print("  (natural-image spectrum S(f) ~ f^-alpha; alpha=0 is white, alpha=2 is typical)")
    print(f"    {'band':>16} {'alpha':>6} {'phi=0.5':>9} {'E_phi':>9} {'handicap 1/R':>13}")
    for name, (a1, a2) in (("FINE (1.0,2.0)", (1.0, 2.0)), ("MID (2.5,5.0)", (2.5, 5.0))):
        for alpha in (0.0, 2.0):
            # 2-D polar integration of |H|^2 * S * |K(fx)|^2 |K(fy)|^2
            n = 512
            fx = (np.arange(n) + 0.5) / (2 * n)          # 0..0.5
            FX, FY = np.meshgrid(fx, fx, indexing="ij")
            FR = np.hypot(FX, FY)
            m = FR <= 0.5
            Hs = dog_response(FR, a1, a2) ** 2
            S = np.where(FR > 0, FR, 1e-9) ** (-alpha)
            wgt = np.where(m, Hs * S, 0.0)
            kx5 = cr_amp(fx, 0.5) ** 2
            K5 = np.outer(kx5, kx5)
            r5 = np.sqrt((wgt * K5).sum() / wgt.sum())
            kxE = (cr_amp(fx, phis) ** 2).mean(axis=1)
            KE = np.outer(kxE, kxE)
            rE = np.sqrt((wgt * KE).sum() / wgt.sum())
            print(f"    {name:>16} {alpha:6.1f} {r5:9.4f} {rE:9.4f} {1.0/rE:13.4f}")

    print()
    print("  for contrast, the SAME integral at BUILD-SHARP's quoted single frequency:")
    for f in (0.25, 0.35):
        rE = float((cr_amp(f, phis) ** 2).mean()) ** 0.5
        print(f"    f={f:.2f} monochromatic  E_phi retention {rE**2:.4f} (2-D)  "
              f"handicap {1.0/rE**2:.3f}x")


if __name__ == "__main__":
    main()