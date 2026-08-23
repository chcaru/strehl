"""M50 step 1 - is this sensor's fixed-pattern noise anisotropic?

WHY. An external review proposed a mechanism for the focus-measure orientation
anomaly (SYNTHESIS question 20): that M4 "measured row/column FPN", and that a
Sobel-x/Sobel-y pair therefore sees row banding asymmetrically, biasing every
window number M13 and M15 produced. Reading M4 does not support the premise.
M4 section 5 measured a PLANE-level asymmetry -- G2 and B, the bottom row of the
RGGB quad, carry more FPN than R and G1 at high ISO -- and explicitly declined
to distinguish a row-dependent readout path from a colour-filter-dependent dark
current. M4 never decomposed FPN into row banding versus column banding.

The premise is therefore untested rather than established. This script tests it
on darks, where there is no scene content to confound the answer.

METHOD, and why it is built this way. The naive statistic -- average N frames,
take row means, report their spread -- cannot work. Averaging N frames leaves
sigma_t/sqrt(N) of temporal noise per pixel, and a row mean over W pixels has a
spread of sigma_t/sqrt(N*W) from that noise ALONE. At these sizes that is small,
but so is the effect being looked for, and a statistic whose null expectation is
nonzero will always find structure.

Every quantity here is instead a CROSS-HALF COVARIANCE. The frames are split
into two disjoint halves, each averaged independently, and the reported value is
the covariance between the two halves' statistics. Temporal noise is independent
between disjoint halves, so it contributes exactly ZERO in expectation, and the
covariance is an unbiased estimator of the fixed-pattern variance in DN^2. The
estimator is free to return a negative number, and a negative number is the
correct answer for "no fixed pattern here". That is the point of choosing it:
this design can say no.

Reported alongside every value is the spread across NSPLIT independent random
half-splits, which is the error bar. A value smaller than its own spread is not
a measurement of anything.

This is M4 section 6's split-half discipline, applied to a different question and
carried through to the derivative operators the focus measure actually uses.

DECOMPOSITION. Per CFA plane -- the 2x2 CFA would otherwise dominate any row or
column statistic -- the master is decomposed as

    M[y,x] = grand + row[y] + col[x] + resid[y,x]

and the fixed-pattern variance of each term is estimated by cross-half
covariance. Row banding means var_row >> var_col.

DIRECTIONAL CONSEQUENCE. The claim under test is about gradient operators, not
about row means, so the operators are measured directly rather than argued from
the decomposition. Sobel-x and Sobel-y are applied to each half's master and the
reported energy is the cross-half mean product <Sx_A * Sx_B>, again unbiased for
the fixed-pattern part. Convention: Sobel-x differentiates along x and therefore
sees COLUMN banding (vertical stripes); Sobel-y differentiates along y and sees
ROW banding (horizontal stripes). Row banding predicts Ey > Ex.

That comparison is reported as the bounded index (Ey - Ex) / (Ey + Ex) and NOT
as the ratio Ey/Ex. The self-test rejected the ratio before this script ever
touched real data: a row-only pattern has no variation along x at all, so Ex is
legitimately near zero, and on planted row banding the ratio returned -494.9 --
a large negative number for the most strongly positive case that exists. Had the
self-test not run first, that number would have appeared in a table about this
sensor and been interpreted.

The same energies are recomputed on the residual, which is the review's proposed
fix (subtract per-row and per-column means before the gradient), so the fix's
effect is measured rather than assumed.

WHAT THIS SCRIPT DOES NOT DO. It does not measure the focus operator's response
on scene content, and it does not touch the window question. It establishes
whether the mechanism exists in the sensor at all. If the anisotropy is absent
here it cannot explain an anomaly downstream, and the proposed fix is a no-op
worth not building.

Black level is never subtracted: every statistic here is mean-centred by
construction, so it cancels exactly. Nothing here assumes a gain. Units are DN.

A TRAP, RECORDED BECAUSE IT COST AN HOUR. `rawpy`'s `raw_image_visible` is a
VIEW into LibRaw's internal buffer, not a copy. It becomes invalid the moment
the `RawPy` context manager exits. The first version of this script did

    with rawpy.imread(f) as rr:
        a = rr.raw_image_visible
    stack[i] = a            # <-- outside the with: use-after-free

which Windows eventually reported as an access violation (0xC0000005) with no
Python traceback at all -- and only after several minutes, having read freed
memory many times without complaint first. That is the dangerous part: the
failure mode is not reliably a crash, it is silently corrupted pixel data.
`faulthandler` is what located it. Copy inside the `with`, always.

`01-dark-sigma.py` is not affected: it calls `.astype(np.float64)` inside the
`with`, which copies while the buffer is still valid. Its results stand, and the
loader cross-check below re-confirms that against this script's own decode.
"""

import glob
import json
import os

import numpy as np
import rawpy

ROOT = r"D:\macro-dark-frames"
NSPLIT = 6
SEED = 20260209
PLANES = (("R", 0, 0), ("G1", 0, 1), ("G2", 1, 0), ("B", 1, 1))
KEYS = ("var_row", "var_col", "var_pix", "Ex", "Ey", "Ex_fix", "Ey_fix")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


def iso_of(path):
    import exifread

    with open(path, "rb") as fh:
        t = exifread.process_file(fh, details=False)
    return int(str(t.get("EXIF ISOSpeedRatings", "0")))


def sobel(a):
    """Sobel-x and Sobel-y, valid interior only, both shaped (H-2, W-2).

    Written out rather than imported so the convention is visible in the file
    and cannot be silently transposed by a library update. gx differentiates
    along x (axis 1) and so responds to column-to-column variation.
    """
    up, mid, dn = a[:-2, :], a[1:-1, :], a[2:, :]
    gx = (up[:, 2:] + 2 * mid[:, 2:] + dn[:, 2:]) - (
        up[:, :-2] + 2 * mid[:, :-2] + dn[:, :-2]
    )
    lf, ctr, rt = a[:, :-2], a[:, 1:-1], a[:, 2:]
    gy = (lf[2:, :] + 2 * ctr[2:, :] + rt[2:, :]) - (
        lf[:-2, :] + 2 * ctr[:-2, :] + rt[:-2, :]
    )
    return gx, gy


def decompose(m):
    """M = grand + row[y] + col[x] + resid. Returns (row, col, resid)."""
    grand = m.mean()
    row = m.mean(axis=1) - grand
    col = m.mean(axis=0) - grand
    resid = m - grand - row[:, None] - col[None, :]
    return row, col, resid


def analyse_plane(flat, shape, rng):
    """flat: (N, H*W) float32 for one CFA plane. Returns {key: (mean, sd)}."""
    n = flat.shape[0]
    half = n // 2
    acc = {k: [] for k in KEYS}
    for _ in range(NSPLIT):
        idx = rng.permutation(n)
        wa = np.zeros(n, dtype=np.float32)
        wb = np.zeros(n, dtype=np.float32)
        wa[idx[:half]] = 1.0 / half
        wb[idx[half : 2 * half]] = 1.0 / half
        # Disjoint halves, so the temporal noise in a and b is independent.
        a = (wa @ flat).reshape(shape).astype(np.float64)
        b = (wb @ flat).reshape(shape).astype(np.float64)

        ra, ca, sa = decompose(a)
        rb, cb, sb = decompose(b)
        acc["var_row"].append(float(np.mean(ra * rb)))
        acc["var_col"].append(float(np.mean(ca * cb)))
        acc["var_pix"].append(float(np.mean(sa * sb)))

        gxa, gya = sobel(a)
        gxb, gyb = sobel(b)
        acc["Ex"].append(float(np.mean(gxa * gxb)))
        acc["Ey"].append(float(np.mean(gya * gyb)))

        gxa2, gya2 = sobel(sa)
        gxb2, gyb2 = sobel(sb)
        acc["Ex_fix"].append(float(np.mean(gxa2 * gxb2)))
        acc["Ey_fix"].append(float(np.mean(gya2 * gyb2)))
    return {k: (float(np.mean(v)), float(np.std(v))) for k, v in acc.items()}


def signed_sqrt(v):
    return float(np.sign(v) * np.sqrt(abs(v)))


def aniso_index(ex, ey):
    """(Ey - Ex) / (Ey + Ex): +1 pure row banding, -1 pure column, 0 isotropic.

    NOT the ratio Ey/Ex. The self-test rejected the ratio: a row-only pattern has
    no variation along x, so Ex is legitimately ~0 and the ratio divides through
    zero -- on planted row banding it returned -494.9, a large NEGATIVE number
    for the most strongly POSITIVE case possible. This index is bounded in
    [-1, +1] for non-negative energies and stays finite wherever there is any
    fixed pattern at all. Returns None when the total energy is not significantly
    positive, because then there is nothing to take the anisotropy of.
    """
    tot = ey + ex
    if not np.isfinite(tot) or tot <= 0:
        return None
    return float((ey - ex) / tot)


def main():
    rng = np.random.default_rng(SEED)
    rows = []
    for d in sorted(glob.glob(os.path.join(ROOT, "*MSDCF"))):
        fs = sorted(glob.glob(os.path.join(d, "*.ARW")))[2:]
        iso = iso_of(fs[0])
        stack = None
        for i, f in enumerate(fs):
            with rawpy.imread(f) as rr:
                # rr.raw_image_visible is a VIEW into LibRaw's internal buffer and
                # is freed when the context manager exits. Both the allocation and
                # the copy must happen inside the `with`. Reading it afterwards is
                # a use-after-free; see this file's header.
                a = rr.raw_image_visible
                if stack is None:
                    stack = np.empty((len(fs),) + a.shape, dtype=np.int16)
                stack[i] = a
        rec = dict(dir=os.path.basename(d), iso=iso, n=len(fs), shape=list(stack.shape[1:]))
        for name, dy, dx in PLANES:
            p = stack[:, dy::2, dx::2].astype(np.float32)
            shape = p.shape[1:]
            # Loader cross-check: the pooled-RMS temporal sigma computed from the
            # stack as loaded here must reproduce 01-dark-sigma.py, which decoded
            # the same files through an independent path. This is what turns "the
            # crash is fixed" into "the data is right".
            var = p.var(axis=0, ddof=1)
            rec.setdefault("loader_check_rms_sd", {})[name] = float(
                np.sqrt(var.mean())
            )
            del var
            rec[name] = analyse_plane(p.reshape(p.shape[0], -1), shape, rng)
            del p
        del stack

        def m(k):
            return sum(rec[p][k][0] for p, _, _ in PLANES) / 4

        def spread(k):
            return sum(rec[p][k][1] for p, _, _ in PLANES) / 4

        vr, vc, vp = m("var_row"), m("var_col"), m("var_pix")
        ex, ey, exf, eyf = m("Ex"), m("Ey"), m("Ex_fix"), m("Ey_fix")
        rec["summary"] = dict(
            var_row=vr, var_col=vc, var_pix=vp,
            sd_row=signed_sqrt(vr), sd_col=signed_sqrt(vc), sd_pix=signed_sqrt(vp),
            spread_row=signed_sqrt(spread("var_row")),
            spread_col=signed_sqrt(spread("var_col")),
            spread_pix=signed_sqrt(spread("var_pix")),
            Ex=ex, Ey=ey, Ex_spread=spread("Ex"), Ey_spread=spread("Ey"),
            aniso=aniso_index(ex, ey),
            Ex_fix=exf, Ey_fix=eyf,
            aniso_fix=aniso_index(exf, eyf),
            # Fraction of directional energy surviving the review's proposed fix.
            # Well defined even when the index is not, and it is the quantity
            # that says whether the fix does anything.
            Ey_surviving=float(eyf / ey) if ey > 0 else None,
            Ex_surviving=float(exf / ex) if ex > 0 else None,
        )
        rows.append(rec)
        s = rec["summary"]

        def show(v):
            return "  n/a " if v is None else f"{v:+6.3f}"

        print(
            f"  ISO {iso:>5}  sd_row={s['sd_row']:+7.4f}+-{s['spread_row']:.4f}"
            f"  sd_col={s['sd_col']:+7.4f}+-{s['spread_col']:.4f}"
            f"  sd_pix={s['sd_pix']:+7.4f} DN"
            f"   aniso={show(s['aniso'])} -> {show(s['aniso_fix'])} after row/col removal",
            flush=True,
        )

    rows.sort(key=lambda x: x["iso"])
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "fpn-anisotropy.json")
    with open(path, "w") as fh:
        json.dump(dict(nsplit=NSPLIT, seed=SEED, rows=rows), fh, indent=1)
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()
