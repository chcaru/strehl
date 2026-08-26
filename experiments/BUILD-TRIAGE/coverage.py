"""BUILD-TRIAGE: the coverage instrument.

Prior art (docs/captures-needed.md Sec 23) established that the fraction of
pixels electing the first or last rung of the bracket -- `boundary %` -- is NOT
by itself a coverage statistic.  On `flowers-cpl` those pixels turned out to be
thin curved ribbons tracing petal edges, concentrated in the HIGHEST-contrast
decile, and the "reshoot wider" advice was withdrawn.  A pixel can elect the
end of the bracket because the true optimum lies outside it (a real coverage
gap, reshoot) or because it sits on an occlusion edge where no frame ever holds
a coherent focus (geometry, no reshoot will help).

So this module measures the boundary set and then applies Sec 23's two
discriminators to split those cases:

  MORPHOLOGY   a genuine gap fills a contiguous REGION; occlusion draws thin
               CONTOURS.  Measured as erosion survival: the fraction of
               boundary pixels still standing after a binary erosion by a
               disk of radius EROSION_R.  A ribbon of half-width < R vanishes.

  CONTRAST     a genuine gap sits where there is little to focus ON, so it
               concentrates in LOW-contrast deciles; occlusion rides edges and
               concentrates in HIGH-contrast deciles.  Measured as the ratio of
               the top-decile election rate to the bottom-decile rate, against
               a shuffled-map null that must come back at ~1.0.

Everything numeric here is computed on the ELECTION MAP, which is an index into
filename order -- it is not a photometric quantity at all, so no tone curve can
touch it.  The contrast field it is ranked against comes from the CAMERA-LINEAR
render (`lin/`), never from the `--srgb` SHIP-V1 masters.

Usage:  python coverage.py [subject ...]        (default: all with a map)
        python coverage.py --commission          (self-tests only)
"""

from __future__ import annotations

import glob
import json
import os
import sys

import numpy as np
import scipy.ndimage as ndi

import tri

COVER = os.path.join(tri.OUT, "cover")

# A boundary ribbon on a petal edge is a few plane-pixels wide.  A bracket that
# genuinely ran out of depth leaves a patch far larger than that.  R = 4 plane
# px = 8 px at master scale.
EROSION_R = 4
# Local-contrast window on the plane grid, in pixels.
CONTRAST_WIN = 9


# --------------------------------------------------------------------------
# primitives
# --------------------------------------------------------------------------
def disk(r: int) -> np.ndarray:
    y, x = np.ogrid[-r : r + 1, -r : r + 1]
    return (y * y + x * x) <= r * r


def frame_count(subject: str) -> int:
    """N from the source directory, because the election map stores indices in
    FILENAME ORDER and max(idx)+1 undercounts whenever the last rung never
    wins -- which is precisely the case we are trying to detect."""
    d = os.path.join(r"D:\personal\macro", subject)
    # Windows globs are case-INSENSITIVE, so *.ARW and *.arw return the same
    # files and a naive sum double-counts.  Dedupe on the casefolded path.
    seen: set[str] = set()
    for ext in ("ARW", "arw", "tif", "tiff", "TIF", "TIFF"):
        for p in glob.glob(os.path.join(d, f"*.{ext}")):
            seen.add(os.path.normcase(p))
    n = len(seen)
    assert n > 1, f"{subject}: found {n} source frames in {d}"
    return n


def local_contrast(lum: np.ndarray, win: int = CONTRAST_WIN) -> np.ndarray:
    """Local RELATIVE contrast: local std divided by local mean.

    The absolute local std in DN is the obvious choice and it is wrong here,
    for the reason this project keeps rediscovering -- it compares across a
    transformation.  Local std scales with illumination, so a dark but richly
    detailed object ranks BELOW a bright smooth one.  That is not a hypothetical:
    on `flower-bud-with-background-fern-cpl` the background fern is manifestly a
    detailed object sitting entirely beyond the far end of the bracket, yet an
    absolute-contrast ranking put its boundary pixels at 0.90x chance -- i.e. it
    reported the fern as carrying LESS detail than average, purely because the
    fern is dark.  Dividing by the local mean makes the measure invariant to
    illumination, which is the property a "does this pixel carry detail" test
    has to have.

    The denominator is floored at 2% of the frame's 99th percentile so that
    near-black regions, where the ratio is dominated by read noise, cannot
    manufacture unbounded contrast.
    """
    f = lum.astype(np.float32)
    m = ndi.uniform_filter(f, win)
    m2 = ndi.uniform_filter(f * f, win)
    sd = np.sqrt(np.maximum(m2 - m * m, 0.0))
    floor = 0.02 * float(np.percentile(f, 99))
    return sd / np.maximum(m, floor)


def decile_rates(mask: np.ndarray, contrast: np.ndarray) -> list[float]:
    """Election rate WITHIN each contrast decile.  Deciles carry equal pixel
    counts by construction, so this is interchangeable with the distribution
    of boundary pixels across deciles -- Sec 23 phrases it the first way."""
    order = np.argsort(contrast, axis=None, kind="stable")
    edges = np.linspace(0, order.size, 11).astype(np.int64)
    flat = mask.reshape(-1)
    out = []
    for i in range(10):
        sel = order[edges[i] : edges[i + 1]]
        out.append(float(flat[sel].mean()))
    return out


def tail_split(rates: list[float]) -> tuple[float, float]:
    """Share of the boundary set sitting in the bottom-three versus top-three
    deciles.  Bounded on [0,1] and defined even when a decile is empty, which
    the bare top/bottom ratio is not: an empty bottom decile sends that ratio
    to infinity and an empty top decile sends it to zero, and both happen on
    real subjects here."""
    tot = sum(rates)
    if tot <= 0:
        return 0.0, 0.0
    return sum(rates[:3]) / tot, sum(rates[7:]) / tot


def ratio_guarded(rates: list[float]) -> float:
    """Top/bottom decile ratio, with a half-pixel pseudo-count so an empty
    decile cannot manufacture a 1e9.  Capped for printing at 999."""
    eps = 0.5 / max(len(rates), 1)
    r = (rates[9] + eps) / (rates[0] + eps)
    return float(min(r, 999.0))


def detail_gap(rates: list[float]) -> float:
    """THE actionable coverage number, in percent.

    Raw `boundary %` counts every pixel that elected an end of the bracket,
    and on this corpus that is dominated by featureless backdrop: on
    `flower-bud-alone-cpl` the bud is a smooth fully-spanned depth map while
    7.6% of the frame elects frame 0 purely because a blown white background
    gives the argmax nothing to lock onto.  Electing an end where there is no
    detail costs nothing and no reshoot can fix it.

    So restrict the rate to pixels that carry resolvable detail -- the top
    three contrast deciles -- and read it as: of the pixels that actually hold
    detail, what fraction did the bracket never bring into focus?  On the
    print-worthy reference `bee-3-cpl` this is ~0.0; on `flowers-cpl` it is
    two orders of magnitude larger.
    """
    return 100.0 * float(np.mean(rates[7:]))


def morphology(mask: np.ndarray, r: int = EROSION_R) -> dict:
    """Erosion survival plus the largest surviving blob."""
    n = int(mask.sum())
    if n == 0:
        return {"survival": 0.0, "n_blobs": 0, "largest_px": 0, "bbox": None,
                "centroid": None}
    er = ndi.binary_erosion(mask, structure=disk(r), border_value=0)
    surv = float(er.sum()) / float(n)
    lab, nlab = ndi.label(er)
    if nlab == 0:
        return {"survival": surv, "n_blobs": 0, "largest_px": 0, "bbox": None,
                "centroid": None}
    sizes = np.bincount(lab.reshape(-1), minlength=nlab + 1)[1:]
    k = int(np.argmax(sizes)) + 1
    sl = ndi.find_objects(lab)[k - 1]
    cy, cx = ndi.center_of_mass((lab == k).astype(np.float32))
    return {
        "survival": surv,
        "n_blobs": int(nlab),
        "largest_px": int(sizes.max()),
        "bbox": [int(sl[0].start), int(sl[0].stop),
                 int(sl[1].start), int(sl[1].stop)],
        "centroid": [float(cy), float(cx)],
    }


def where(cy: float, cx: float, h: int, w: int) -> str:
    v = "upper" if cy < h / 3 else ("lower" if cy > 2 * h / 3 else "centre")
    z = "left" if cx < w / 3 else ("right" if cx > 2 * w / 3 else "centre")
    if v == "centre" and z == "centre":
        return "centre"
    if v == "centre":
        return z
    if z == "centre":
        return v
    return f"{v}-{z}"


# --------------------------------------------------------------------------
# commissioning
# --------------------------------------------------------------------------
def commission() -> None:
    """An uncommissioned instrument and a null result look identical."""
    print("=== commissioning the coverage instrument ===")
    rng = np.random.default_rng(7)
    h = w = 600

    # -- positive control 1: morphology must separate a contour from a region.
    yy, xx = np.ogrid[:h, :w]
    rad = np.sqrt((yy - h / 2) ** 2 + (xx - w / 2) ** 2)
    ring = (np.abs(rad - 200) <= 1.5)              # 3 px wide contour
    n_ring = int(ring.sum())
    rr = np.sqrt(n_ring / np.pi)                    # filled disk, SAME area
    blob = rad <= rr
    s_ring = morphology(ring)["survival"]
    s_blob = morphology(blob)["survival"]
    print(f"  morphology  contour(3px wide, {n_ring} px) survival = {s_ring:.4f}")
    print(f"  morphology  region (equal area,  {int(blob.sum())} px) survival = {s_blob:.4f}")
    assert s_ring < 0.01, f"contour did not vanish under erosion: {s_ring}"
    assert s_blob > 0.30, f"equal-area region did not survive erosion: {s_blob}"
    print(f"  morphology  PASS  separation = {s_blob:.4f} vs {s_ring:.4f}")

    # -- null: a mask uncorrelated with contrast must give a flat decile ratio.
    contrast = ndi.uniform_filter(rng.random((h, w)).astype(np.float32), 9)
    shuf = np.zeros(h * w, bool)
    shuf[rng.choice(h * w, size=n_ring, replace=False)] = True
    r = decile_rates(shuf.reshape(h, w), contrast)
    ratio = r[9] / max(r[0], 1e-12)
    print(f"  contrast    NULL shuffled mask  top/bottom = {ratio:.3f}x "
          f"(expect ~1.0)")
    assert 0.5 < ratio < 2.0, f"null decile ratio is not flat: {ratio}"

    # -- positive control 2: a mask PLANTED on high contrast must be recovered.
    thr = np.quantile(contrast, 0.90)
    planted = contrast >= thr
    r = decile_rates(planted, contrast)
    ratio = r[9] / max(r[0], 1e-12)
    print(f"  contrast    PLANT top-decile mask top/bottom = {ratio:.1f}x "
          f"(expect >> 1)")
    assert ratio > 50, f"planted high-contrast mask not recovered: {ratio}"
    print("  contrast    PASS")
    print("=== commissioned ===\n")


# --------------------------------------------------------------------------
# per subject
# --------------------------------------------------------------------------
def logged_boundary(subject: str) -> float | None:
    """The binary's OWN printed boundary %, for the null check against ours."""
    p = os.path.join(COVER, f"{subject}.log")
    if not os.path.exists(p):
        return None
    raw = open(p, "rb").read()
    txt = raw.decode("utf-16-le" if raw[:2] == b"\xff\xfe" else "utf-8",
                     errors="replace")
    lines = txt.splitlines()
    for i, ln in enumerate(lines):
        if "boundary %" in ln:
            for nxt in lines[i + 1: i + 4]:
                f = nxt.split()
                if len(f) >= 5 and f[0].replace(".", "").isdigit():
                    return float(f[4].rstrip("%"))
    return None


def analyse(subject: str) -> dict:
    idx_p = os.path.join(COVER, f"{subject}.idx.tiff")
    idx = tri.load16(idx_p).astype(np.int32)
    n = frame_count(subject)
    assert idx.max() <= n - 1, (
        f"{subject}: election index {idx.max()} exceeds N-1={n - 1}")

    near = idx == 0
    far = idx == n - 1
    mask = near | far
    tot = idx.size
    pct = 100.0 * mask.sum() / tot
    # NULL CHECK: our recomputation against the binary's own printed figure.
    logged = logged_boundary(subject)
    delta = None if logged is None else abs(pct - logged)

    lin = os.path.join(tri.LIN, f"{subject}.tiff")
    lum = tri.luma(tri.load16(lin))
    # Plane grid is exactly half the render in both axes; block-mean 2x2 so the
    # two overlay pixel-for-pixel with no interpolation.
    assert lum.shape[0] == 2 * idx.shape[0] and lum.shape[1] == 2 * idx.shape[1], (
        f"{subject}: render {lum.shape} is not 2x election map {idx.shape}")
    lum = lum.reshape(idx.shape[0], 2, idx.shape[1], 2).mean(axis=(1, 3))
    con = local_contrast(lum)

    rates = decile_rates(mask, con)
    ratio = ratio_guarded(rates)
    con_lo, con_hi = tail_split(rates)
    lrates = decile_rates(mask, lum)
    lratio = ratio_guarded(lrates)
    lum_lo, lum_hi = tail_split(lrates)
    rng = np.random.default_rng(11)
    shuf = np.zeros(tot, bool)
    if mask.sum():
        shuf[rng.choice(tot, size=int(mask.sum()), replace=False)] = True
    srates = decile_rates(shuf.reshape(idx.shape), con)
    sratio = ratio_guarded(srates)

    mor = morphology(mask)
    loc = None
    if mor["centroid"]:
        loc = where(mor["centroid"][0], mor["centroid"][1], *idx.shape)

    return {
        "subject": subject,
        "n_frames": n,
        "shape": list(idx.shape),
        "boundary_pct": round(pct, 4),
        "boundary_pct_logged": logged,
        "boundary_pct_delta": None if delta is None else round(delta, 4),
        # Deliberately labelled by the LITERAL end of filename order.  Which
        # physical end of the focus travel frame 0 sits at is a property of how
        # the bracket was shot and is NOT recoverable from the election map
        # alone, so this reports what was measured and nothing more.  It is
        # still the actionable half: "extend the bracket past frame 0".
        "end0_pct": round(100.0 * near.sum() / tot, 4),
        "endN_pct": round(100.0 * far.sum() / tot, 4),
        "decile_rates": [round(x, 6) for x in rates],
        "contrast_ratio": round(ratio, 4),
        "contrast_ratio_null": round(sratio, 4),
        "contrast_lo3": round(con_lo, 4),
        "contrast_hi3": round(con_hi, 4),
        "detail_gap_pct": round(detail_gap(rates), 4),
        "detail_gap_null": round(detail_gap(srates), 4),
        # Enrichment of the boundary set on detail-bearing pixels, against a
        # size-matched shuffled null.  >1 means the end-elections preferentially
        # land where there IS detail (a real loss); <1 means they land on
        # featureless ground (no reshoot can help).  Carrying the null per
        # subject is what makes the raw rate interpretable at all, because the
        # rate scales with boundary % and boundary % spans 0 to 35% here.
        "detail_enrichment": round(
            detail_gap(rates) / max(detail_gap(srates), 1e-9), 4),
        "luma_ratio": round(lratio, 4),
        "luma_lo3": round(lum_lo, 4),
        "luma_hi3": round(lum_hi, 4),
        "survival": round(mor["survival"], 4),
        "n_blobs": mor["n_blobs"],
        "largest_px": mor["largest_px"],
        "largest_frac": round(mor["largest_px"] / max(tot, 1) * 100, 4),
        "bbox_master": None if not mor["bbox"] else [x * 2 for x in mor["bbox"]],
        "centroid_master": None if not mor["centroid"]
        else [round(x * 2, 1) for x in mor["centroid"]],
        "location": loc,
    }


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--commission" in sys.argv:
        commission()
        if not args:
            return
    else:
        commission()

    subs = args or [s for s in tri.SUBJECTS
                    if os.path.exists(os.path.join(COVER, f"{s}.idx.tiff"))]
    rows = []
    hdr = (f"{'subject':<38} {'N':>4} {'bound%':>7} {'d(null)':>8} "
           f"{'end0%':>7} {'endN%':>7} {'DETAIL%':>8} {'dnull':>6} "
           f"{'surv':>6} {'conHi3':>7}")
    print(hdr)
    print("-" * len(hdr))
    for s in subs:
        try:
            r = analyse(s)
        except Exception as e:  # noqa: BLE001
            print(f"{s:<38} FAILED: {e}")
            continue
        rows.append(r)
        d = "n/a" if r["boundary_pct_delta"] is None else f"{r['boundary_pct_delta']:.4f}"
        print(f"{r['subject']:<38} {r['n_frames']:>4} {r['boundary_pct']:>7.3f} "
              f"{d:>8} {r['end0_pct']:>7.3f} {r['endN_pct']:>7.3f} "
              f"{r['detail_gap_pct']:>8.3f} {r['detail_gap_null']:>6.3f} "
              f"{r['survival']:>6.3f} {r['contrast_hi3']:>7.3f}")

    p = os.path.join(tri.OUT, "coverage.json")
    json.dump(rows, open(p, "w"), indent=1)
    print(f"\nwrote {p}  ({len(rows)} subjects)")


if __name__ == "__main__":
    main()
