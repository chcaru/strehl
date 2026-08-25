"""M87 / 102 -- robustness of the 100/101 result to REGION and CHANNEL.

100/101 measured s25's veil depth on ROI_LEG, green channel, and found the
veiled band invariant to the gate (near band spans 0.0673% across a 55.3x
change in n_eff; pinned-reference ladder range 0.0572 pp against a predicted
19.79 pp).  That is one crop and one channel.  A result that only holds on the
population it was tuned on is not a result.

Three robustness arms, all with the mask FROZEN on the gate-4.00 arm:

  A1  ROI_LEG, mean-RGB instead of green  -- channel robustness.
  A2  the BLOB region ORCH filed as the flagship figure, green -- region
      robustness, and it is the region ORCH most cares about.
  A3  the BLOB region, mean-RGB.

Registered before running: the claim under test is "the NEAR band is invariant
to the gate".  For each arm I report the near-band span across the ladder as a
percentage, and the pinned-reference range in pp.  Registered bar, applied to
EVERY arm independently:

    B22-ROBUST      near-band span < 0.5% AND pinned range < 3.00 pp on all
                    three arms
    B22-MIXED       the bars hold on some arms and not others
    B22-REFUTED     near-band span >= 0.5% or pinned range >= 3.00 pp on the
                    majority of arms

A registered falsifier that matters: if A2 or A3 fails while A1 passes, the
ROI_LEG result does not generalise to the region ORCH filed, and I must say so
rather than lead with ROI_LEG.

C-RING-POP: every reported band must be populated.  I print the pixel count of
    the near band and the far band on every arm and every region, and any band
    under 200 px is reported as NaN by construction rather than silently
    averaged over nothing.

READ-ONLY: D:\\personal\\macro and ORCH's pinned TIFFs.  Provenance as 100.
"""
import json
import pathlib
import sys

import numpy as np
import tifffile
from scipy.ndimage import distance_transform_edt

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m87lib as L  # noqa: E402

GATE = pathlib.Path(r"C:\dev\strehl-out\ORCH-gate")
DATA = pathlib.Path(__file__).resolve().parents[1] / "data"
ARMS = ["4.00", "2.00", "0.7078", "0.00"]
VEIL = (2, 22)
FAR = (80, 120)
M = L.WINDOW_RADIUS + L.REGULARISER_RADIUS + 1
BIN = 2

# (name, y0, y1, x0, x1) in BINNED coordinates, inner region excluding margin M.
REGIONS = {
    "ROI_LEG": L.ROIS["ROI_LEG"],
    # ORCH's BLOB figure is (x=700,y=3150) 1100x900 in UNBINNED arm coords;
    # binned that is x 350..900, y 1575..2025.  Widened to populate d<=120.
    "BLOB": (1500, 2100, 250, 1000),
}


def _np(o):
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    raise TypeError(repr(o))


def srgb_to_linear(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def load(gate, region, channel):
    y0b, y1b, x0b, x1b = REGIONS[region]
    y0, y1 = (y0b - M) * BIN, (y1b + M) * BIN
    x0, x1 = (x0b - M) * BIN, (x1b + M) * BIN
    a = tifffile.imread(GATE / f"pin-bee-3-cpl-gate-{gate}.tif")
    sub = a[y0:y1, x0:x1, :].astype(np.float64) / 65535.0
    del a
    lin = srgb_to_linear(sub)
    v = lin[:, :, 1] if channel == "green" else lin.mean(axis=2)
    del sub, lin
    h, w = v.shape
    return v.reshape(h // BIN, BIN, w // BIN, BIN).mean(axis=(1, 3)) * 65535.0


class Geom:
    def __init__(self, ref, region):
        y0b, y1b, x0b, x1b = REGIONS[region]
        self.fmask, _ = L.foreground_mask(ref)
        dd = np.rint(distance_transform_edt(~self.fmask)).astype(np.int32)
        inner = np.zeros_like(dd, bool)
        inner[M:M + (y1b - y0b), M:M + (x1b - x0b)] = True
        self.valid = (~self.fmask) & inner
        self.dd = dd
        dv = dd[self.valid]
        self.order = np.argsort(dv, kind="stable")
        self.edges = np.searchsorted(dv[self.order], np.arange(0, 202))

    def bandpop(self, lo, hi):
        return int(((self.dd >= lo) & (self.dd <= hi) & self.valid).sum())

    def near_far(self, img):
        v = img[self.valid][self.order]
        p = np.full(201, np.nan)
        for d in range(201):
            a, b = self.edges[d], self.edges[d + 1]
            if b - a >= 200:
                p[d] = np.median(v[a:b])
        near = np.nanmedian(p[VEIL[0]:VEIL[1] + 1])
        far = np.nanmedian(p[FAR[0]:FAR[1] + 1])
        return float(near), float(far)


def main():
    rep = {"arms": {}, "bars": {}}
    plan = [("A1", "ROI_LEG", "mean"), ("A2", "BLOB", "green"),
            ("A3", "BLOB", "mean")]
    verdicts = {}
    for tag, region, channel in plan:
        print(f"\n=== {tag}: region {region}, channel {channel} ===")
        imgs = {g: load(g, region, channel) for g in ARMS}
        G = Geom(imgs["4.00"], region)
        npop, fpop = G.bandpop(*VEIL), G.bandpop(*FAR)
        print(f"  frozen mask subject {100 * G.fmask.mean():.2f}%   "
              f"near band {npop} px   far band {fpop} px")
        if npop < 200 or fpop < 200:
            print("  C-RING-POP: FAIL -- a band is underpopulated, arm void")
            verdicts[tag] = "VOID"
            rep["arms"][tag] = {"region": region, "channel": channel,
                                "void": True, "near_px": npop, "far_px": fpop}
            continue
        near, far, V = {}, {}, {}
        for g in ARMS:
            near[g], far[g] = G.near_far(imgs[g])
            V[g] = 100.0 * (near[g] / far[g] - 1.0)
        f0 = far["4.00"]
        vpin = {g: 100.0 * (near[g] - f0) / f0 for g in ARMS}
        nspan = 100.0 * (max(near.values()) / min(near.values()) - 1)
        fspan = 100.0 * (max(far.values()) / min(far.values()) - 1)
        rng = max(vpin.values()) - min(vpin.values())
        print(f"  {'gate':>8}  {'near DN':>10}  {'far DN':>10}  "
              f"{'V raw %':>9}  {'V pin %':>9}")
        for g in ARMS:
            print(f"  {g:>8}  {near[g]:>10.1f}  {far[g]:>10.1f}  "
                  f"{V[g]:>+9.4f}  {vpin[g]:>+9.4f}")
        ok = nspan < 0.5 and rng < 3.00
        print(f"  near span {nspan:.4f}%   far span {fspan:.4f}%   "
              f"ratio {fspan / max(nspan, 1e-12):.1f}x")
        print(f"  pinned range {rng:.4f} pp   bars: near<0.5% and range<3.00pp"
              f"  -> {'PASS' if ok else 'FAIL'}")
        verdicts[tag] = "PASS" if ok else "FAIL"
        rep["arms"][tag] = {"region": region, "channel": channel, "void": False,
                            "near_px": npop, "far_px": fpop,
                            "near": near, "far": far, "V_raw": V,
                            "V_pinned": vpin, "near_span_pct": nspan,
                            "far_span_pct": fspan, "pinned_range_pp": rng,
                            "pass": bool(ok)}
        del imgs

    live = [v for v in verdicts.values() if v != "VOID"]
    if live and all(v == "PASS" for v in live):
        b22 = "B22-ROBUST"
    elif live and all(v == "FAIL" for v in live):
        b22 = "B22-REFUTED"
    else:
        b22 = "B22-MIXED"
    print(f"\n=== B22 -> {b22}   ({verdicts}) ===")
    rep["bars"]["B22"] = {"branch": b22, "verdicts": verdicts}
    with open(DATA / "102-robust.json", "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1, default=_np)
    print(f"wrote {DATA / '102-robust.json'}")


if __name__ == "__main__":
    main()
