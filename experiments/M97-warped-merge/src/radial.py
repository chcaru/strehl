"""Does correcting the solve's gain make the PHOTOGRAPH better?

The two renders compared here differ in exactly one thing: the scalar gain
applied to every placement in the sidecar. Same frames, same gate, same
resampler, same cover scale k=0.9974, same code path. So any difference is
registration and nothing else.

A scale misregistration has a built-in spatial control, and it is the reason
this test can be trusted: the error is ZERO at the image centre and grows
linearly with radius. So the centre is a null region and the corners are the
treatment region, WITHIN THE SAME PAIR OF IMAGES. If correcting the gain
sharpens the corners and leaves the centre alone, that is registration. If it
changes both equally, it is something else -- exposure, tone, a global
resample -- and the result must not be claimed as registration.

Metric is local gradient energy on the green channel, measured in annular
bands by radius, ratio treatment/control.
"""

import json
import sys

import numpy as np
import tifffile


def grad_energy(a: np.ndarray) -> np.ndarray:
    gy = np.diff(a, axis=0)[:, :-1]
    gx = np.diff(a, axis=1)[:-1, :]
    return gy * gy + gx * gx


def main(argv: list[str]) -> int:
    out_json, ctrl_p, treat_p = argv[1], argv[2], argv[3]
    ctrl = tifffile.imread(ctrl_p)
    treat = tifffile.imread(treat_p)
    assert ctrl.shape == treat.shape, (ctrl.shape, treat.shape)
    assert ctrl.dtype == np.uint16 and treat.dtype == np.uint16

    g_c = ctrl[:, :, 1].astype(np.float64)
    g_t = treat[:, :, 1].astype(np.float64)
    print(f"shape {ctrl.shape}  ctrl mean {g_c.mean():.1f}  treat mean {g_t.mean():.1f}")

    # Guard: a global brightness change would masquerade as a sharpness change.
    ratio_mean = g_t.mean() / g_c.mean()
    print(f"global green mean ratio {ratio_mean:.5f} "
          f"({'OK, tone matched' if abs(ratio_mean - 1) < 0.02 else 'WARNING: tone differs'})")

    e_c, e_t = grad_energy(g_c), grad_energy(g_t)
    h, w = e_c.shape
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.hypot(yy - (h - 1) / 2.0, xx - (w - 1) / 2.0)
    r_max = r.max()

    # Tile so each band's ratio is a median over many independent tiles rather
    # than one number dominated by the brightest few pixels.
    T = 128
    ny, nx = h // T, w // T
    ec = e_c[: ny * T, : nx * T].reshape(ny, T, nx, T).mean(axis=(1, 3))
    et = e_t[: ny * T, : nx * T].reshape(ny, T, nx, T).mean(axis=(1, 3))
    rt = r[: ny * T, : nx * T].reshape(ny, T, nx, T).mean(axis=(1, 3)) / r_max

    rows = []
    edges = [0.0, 0.2, 0.4, 0.6, 0.8, 1.01]
    print()
    print(f"{'radius band':>14} {'tiles':>6} {'ctrl energy':>13} {'ratio T/C':>10}")
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (rt >= lo) & (rt < hi) & (ec > 0)
        n = int(m.sum())
        if n == 0:
            continue
        ratio = float(np.median(et[m] / ec[m]))
        rows.append(dict(lo=lo, hi=hi, n=n, ctrl=float(np.median(ec[m])), ratio=ratio))
        print(f"  {lo:.1f}-{hi:.1f} r_max {n:>6} {np.median(ec[m]):>13.1f} {ratio:>10.4f}")

    inner = rows[0]["ratio"]
    outer = rows[-1]["ratio"]
    print()
    print(f"centre band  ratio {inner:.4f}")
    print(f"corner band  ratio {outer:.4f}")
    print(f"corner minus centre {outer - inner:+.4f}")
    print()
    if outer > inner + 0.01:
        print("CONSISTENT WITH A REGISTRATION WIN: the corners gained more than the centre,")
        print("which is the spatial signature a scale error must have.")
    elif abs(outer - inner) <= 0.01:
        print("NO RADIAL STRUCTURE: whatever changed, it changed centre and corner alike,")
        print("so it is NOT the registration. Do not claim a registration win.")
    else:
        print("CORNERS GOT WORSE relative to the centre -- opposite of the expected signature.")

    with open(out_json, "w", encoding="utf-8") as fh:
        json.dump(dict(control=ctrl_p, treatment=treat_p,
                       tone_ratio=ratio_mean, bands=rows), fh, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
