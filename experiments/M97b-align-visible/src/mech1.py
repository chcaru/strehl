"""R1 -- does edge doubling RAISE or LOWER Tenengrad? Synthetic, truth known.

The orchestrator's ARGUED mechanism for the anti-correlation is that
misregistration doubles edges, and "a doubled edge has two gradients where a
correct one has a single sharper gradient", so gradient energy goes up.

Tenengrad sums the SQUARE of the gradient. Squaring is convex, so splitting a
fixed total rise across more pixels must lower the sum. I predicted in PREREG2
that doubling gives ~0.5x, i.e. the mechanism is falsified. This measures it on
a synthetic edge where the answer is not in dispute.

Also measures the two rival hypotheses on the same wiring, so the falsification
is not merely destructive:
  M-noise -- independent per-pixel noise, as when neighbouring output pixels
             elect different frames.
  M-seam  -- an abrupt switch between two frames' renditions of the same edge.
"""

import json
import sys

import numpy as np


def tenengrad(g):
    gx = np.zeros_like(g)
    gy = np.zeros_like(g)
    gx[:, 1:-1] = g[:, 2:] - g[:, :-2]
    gy[1:-1, :] = g[2:, :] - g[:-2, :]
    return float((gx * gx + gy * gy).mean())


def grad_mag(g):
    gx = np.zeros_like(g)
    gy = np.zeros_like(g)
    gx[:, 1:-1] = g[:, 2:] - g[:, :-2]
    gy[1:-1, :] = g[2:, :] - g[:-2, :]
    return np.sqrt(gx * gx + gy * gy)


def gauss1d(x, sigma):
    r = int(np.ceil(4 * sigma))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    return np.apply_along_axis(lambda m: np.convolve(m, k, mode="same"), 1, x)


def step(n, h, x0):
    """Ideal step of height h at column x0."""
    img = np.zeros((n, n), np.float64)
    img[:, int(round(x0)):] = h
    return img


def main():
    rng = np.random.default_rng(97)
    N, H = 256, 1000.0
    out = {}

    single = step(N, H, N // 2)
    # Doubled: the same total rise delivered as two half-steps 6 px apart, which
    # is what averaging two frames misregistered by 6 px produces.
    doubled = 0.5 * step(N, H, N // 2 - 3) + 0.5 * step(N, H, N // 2 + 3)
    # Blurred: the same total rise spread smoothly.
    blurred = gauss1d(single, 2.0)

    for name, img in (("single", single), ("doubled", doubled),
                      ("blurred_sigma2", blurred)):
        gm = grad_mag(img)
        row = img[N // 2]
        out[name] = {
            "tenengrad": tenengrad(img),
            "peak_grad": float(gm.max()),
            "integrated_grad_across_profile": float(
                np.abs(np.diff(row)).sum()),
            "total_rise": float(row[-1] - row[0]),
        }

    # Rival hypotheses, measured on the same wiring so the comparison is fair.
    flat = np.full((N, N), H / 2)
    out["flat"] = {"tenengrad": tenengrad(flat)}
    for sd in (1.0, 4.0, 16.0):
        out["flat_plus_noise_sd%g" % sd] = {
            "tenengrad": tenengrad(flat + rng.normal(0, sd, (N, N)))}

    # M-seam: a vertical discontinuity where the elected frame switches, with
    # the two frames differing by a small brightness/position offset.
    seam = single.copy()
    seam[N // 2:, :] = gauss1d(step(N, H, N // 2 + 4), 0.8)[N // 2:, :]
    out["seam"] = {"tenengrad": tenengrad(seam)}

    b = out["single"]["tenengrad"]
    print("%-24s %14s %12s %12s" % ("case", "tenengrad", "vs single", "peak|g|"))
    for k, v in out.items():
        t = v["tenengrad"]
        pk = v.get("peak_grad")
        print("%-24s %14.2f %12.4f %12s" % (
            k, t, t / b, ("%.1f" % pk) if pk is not None else "-"))

    r = out["doubled"]["tenengrad"] / b
    print()
    print("R1 VERDICT")
    print("  doubled / single tenengrad = %.4f" % r)
    if r > 1.0:
        print("  -> doubling RAISES tenengrad. Orchestrator's mechanism CONFIRMED.")
    elif r <= 0.9:
        print("  -> doubling LOWERS tenengrad by more than 10%%.")
        print("     Orchestrator's doubling mechanism FALSIFIED (I predicted ~0.5x).")
    else:
        print("  -> inconclusive band (0.9 < r <= 1.0).")
    print("  integrated |grad| across the profile is CONSERVED under doubling:")
    print("     single %.1f   doubled %.1f   blurred %.1f" % (
        out["single"]["integrated_grad_across_profile"],
        out["doubled"]["integrated_grad_across_profile"],
        out["blurred_sigma2"]["integrated_grad_across_profile"]))
    print("  so integrated |grad| cannot distinguish them either -- only the")
    print("  PEAK falls: %.1f -> %.1f -> %.1f" % (
        out["single"]["peak_grad"], out["doubled"]["peak_grad"],
        out["blurred_sigma2"]["peak_grad"]))

    json.dump(out, open(sys.argv[1], "w"), indent=1)
    print("\nwrote", sys.argv[1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
