"""M101 script 08 - the deciding measurement, computed from the winner map.

Consumes script 07's election and answers section 2 of the commission:

  D2  H_value    fraction of elected output pixels whose gathered sample sits on
                 a defective sensor site
      H_support  fraction whose winning frame carries a defect anywhere in the
                 29x29 focus support that decided the pixel (SUPPORT_RADIUS=14)
  D3  enrichment does a defect coordinate win its own election more often than
                 chance, against three separate nulls
  D4  trail      geometric trail length from the sidecar (exact, no decode) and
                 the elected subset of it

Nulls carried beside every number:
  shift        defect map rolled by an even offset - preserves CFA phase and
               every spatial statistic, destroys correspondence
  random       uniform random coordinates, matched in count
  permuted     the winner map held fixed, the frame index of each event
               permuted - destroys the defect-frame pairing, preserves both
               marginals
  brightness   the shift control resampled to match the elected-luma
               distribution at the real defect sites

Reads  : C:\\dev\\strehl-out\\M101\\election-*.npz, defectmap-*.npz, M86 sidecar
Writes : C:\\dev\\strehl-out\\M101\\08-deciding-<stack>-<arm>.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.ndimage import maximum_filter

import importlib.util
_spec = importlib.util.spec_from_file_location(
    "e07", Path(__file__).with_name("07-election.py"))
_e07 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_e07)
parse_warpmap = _e07.parse_warpmap

OUT = Path(r"C:\dev\strehl-out\M101")
REPO = Path(r"C:\dev\blog\death-of-software\projects\strehl")
PLANES = ["R", "G1", "G2", "B"]
SHIFT = (64, 64)
SUPPORT_RADIUS = 14
SEED = 101
B8_BAR = 1.5


def load_defects(shape_out):
    dm = np.load(OUT / "defectmap-final.npz")
    amp = np.load(OUT / "defectmap-amp.npz")
    H, W = shape_out
    out = {}
    for pk in PLANES:
        sh = tuple(dm[f"shape_{pk}"])
        m = np.unpackbits(dm[f"{pk}-defect"],
                          count=sh[0] * sh[1]).astype(bool).reshape(sh)
        a = amp[f"{pk}-amp_e"]
        full = np.zeros((H, W), dtype=bool)
        fa = np.zeros((H, W), dtype=np.float32)
        full[:sh[0], :sh[1]] = m[:H, :W]          # rawpy 3514 are rawler's leading cols
        fa[:sh[0], :sh[1]] = a[:H, :W]
        out[pk] = (full, fa)
    return out


def fwd(sim, x, y, cx, cy):
    a, b = sim
    px, py = x - cx, y - cy
    return (a.real * px - a.imag * py + b.real + cx,
            a.imag * px + a.real * py + b.imag + cy)


def inv(sim, x, y, cx, cy):
    a, b = sim
    z = (complex(x - cx, y - cy) - b) / a
    return z.real + cx, z.imag + cy


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stack", default="bee-3-cpl")
    ap.add_argument("--arm", default="warped")
    ap.add_argument("--warpmap", default=str(
        REPO / "experiments/M86-alignment/out/warpmap-bee-3-cpl.txt"))
    a = ap.parse_args()

    z = np.load(OUT / f"election-{a.stack}-{a.arm}.npz")
    win = z["winner"].astype(np.int32)
    luma = z["luma"]
    meta = json.loads(str(z["meta"][0]))
    H, W = win.shape
    cx, cy = W * 0.5, H * 0.5
    hdr, warps = parse_warpmap(Path(a.warpmap))
    if a.arm == "identity":
        warps = {k: (complex(1, 0), complex(0, 0)) for k in warps}
    nf = meta["n_frames"]
    rng = np.random.default_rng(SEED)

    dm = load_defects((H, W))
    any_defect = np.zeros((H, W), dtype=bool)
    for pk in PLANES:
        any_defect |= dm[pk][0]
    green_defect = dm["G1"][0] | dm["G2"][0]
    shifted = np.roll(any_defect, SHIFT, axis=(0, 1))
    randmask = np.zeros(H * W, dtype=bool)
    randmask[rng.choice(H * W, int(any_defect.sum()), replace=False)] = True
    randmask = randmask.reshape(H, W)

    res = {"meta": meta, "n_defect_sites": int(any_defect.sum()),
           "n_green_defect_sites": int(green_defect.sum()),
           "shift": list(SHIFT), "D2": {}, "D3": {}, "D4": {}}

    # ---------- D2: where did each elected sample come from? ----------
    dil = maximum_filter(any_defect.astype(np.uint8), size=2 * SUPPORT_RADIUS + 1) > 0
    hits = {k: 0 for k in ("any", "green", "shift", "random", "support", "support_shift")}
    dil_shift = np.roll(dil, SHIFT, axis=(0, 1))
    covered = 0
    for k in range(nf):
        sel = win == k
        n = int(sel.sum())
        if not n:
            continue
        yy, xx = np.nonzero(sel)
        sim = warps.get(k)
        if sim is None:
            continue
        qx, qy = fwd(sim, xx.astype(np.float64), yy.astype(np.float64), cx, cy)
        ix = np.clip(np.rint(qx).astype(np.int32), 0, W - 1)
        iy = np.clip(np.rint(qy).astype(np.int32), 0, H - 1)
        covered += n
        hits["any"] += int(any_defect[iy, ix].sum())
        hits["green"] += int(green_defect[iy, ix].sum())
        hits["shift"] += int(shifted[iy, ix].sum())
        hits["random"] += int(randmask[iy, ix].sum())
        hits["support"] += int(dil[iy, ix].sum())
        hits["support_shift"] += int(dil_shift[iy, ix].sum())
    tot = float(covered)
    res["D2"] = {
        "n_output_px": int(H * W), "n_attributed": covered,
        "H_value_any_defect": hits["any"] / tot,
        "H_value_green_defect": hits["green"] / tot,
        "H_value_shift_control": hits["shift"] / tot,
        "H_value_random_control": hits["random"] / tot,
        "H_support": hits["support"] / tot,
        "H_support_shift_control": hits["support_shift"] / tot,
        "counts": hits,
        "defect_density": float(any_defect.sum() / (H * W)),
    }
    print(f"D2 H_value = {res['D2']['H_value_any_defect']:.3e} "
          f"(shift {res['D2']['H_value_shift_control']:.3e}, "
          f"random {res['D2']['H_value_random_control']:.3e})", flush=True)
    print(f"   H_support = {res['D2']['H_support']:.4f} "
          f"(shift {res['D2']['H_support_shift_control']:.4f})", flush=True)

    # ---------- D3 + D4: per (defect, frame) events ----------
    sy, sx = np.nonzero(any_defect)
    keep = rng.choice(sy.size, min(sy.size, 4000), replace=False)
    sy, sx = sy[keep], sx[keep]
    ry = (sy + SHIFT[0]) % H
    rx = (sx + SHIFT[1]) % W
    uy = rng.integers(0, H, size=sy.size)
    ux = rng.integers(0, W, size=sx.size)

    def events(py, px):
        hit = np.zeros(py.size, dtype=np.int32)
        vis = np.zeros(py.size, dtype=np.int32)
        allx = np.empty((nf, py.size), dtype=np.float32)
        ally = np.empty((nf, py.size), dtype=np.float32)
        allx[:] = np.nan
        for k in range(nf):
            sim = warps.get(k)
            if sim is None:
                continue
            a_, b_ = sim
            zc = (px - cx) + 1j * (py - cy)
            zz = (zc - b_) / a_
            qx, qy = zz.real + cx, zz.imag + cy
            allx[k], ally[k] = qx, qy
            ok = (qx >= 0) & (qx < W) & (qy >= 0) & (qy < H)
            ix = np.clip(np.rint(qx).astype(np.int32), 0, W - 1)
            iy = np.clip(np.rint(qy).astype(np.int32), 0, H - 1)
            vis += ok
            hit += ok & (win[iy, ix] == k)
        return hit, vis, allx, ally

    h_d, v_d, tx, ty = events(sy.astype(np.float64), sx.astype(np.float64))
    h_s, v_s, _, _ = events(ry.astype(np.float64), rx.astype(np.float64))
    h_u, v_u, _, _ = events(uy.astype(np.float64), ux.astype(np.float64))

    # permutation null: same winner map, frame labels permuted
    perm = rng.permutation(nf)
    h_p = np.zeros(sy.size, dtype=np.int32)
    for k in range(nf):
        sim = warps.get(k)
        if sim is None:
            continue
        zc = (sx - cx) + 1j * (sy - cy)
        zz = (zc - sim[1]) / sim[0]
        qx, qy = zz.real + cx, zz.imag + cy
        ok = (qx >= 0) & (qx < W) & (qy >= 0) & (qy < H)
        ix = np.clip(np.rint(qx).astype(np.int32), 0, W - 1)
        iy = np.clip(np.rint(qy).astype(np.int32), 0, H - 1)
        h_p += ok & (win[iy, ix] == perm[k])

    def rate(h, v):
        n, d = int(h.sum()), int(v.sum())
        p = n / d if d else float("nan")
        return {"hits": n, "visible_events": d, "rate": p,
                "sem": float(np.sqrt(p * (1 - p) / d)) if d else None}

    rd, rs, ru, rp = rate(h_d, v_d), rate(h_s, v_s), rate(h_u, v_u), rate(h_p, v_d)
    res["D3"] = {"n_sites_sampled": int(sy.size), "defect": rd, "shift_null": rs,
                 "random_null": ru, "permuted_null": rp,
                 "enrichment_vs_shift": rd["rate"] / rs["rate"] if rs["rate"] else None,
                 "enrichment_vs_random": rd["rate"] / ru["rate"] if ru["rate"] else None,
                 "enrichment_vs_permuted": rd["rate"] / rp["rate"] if rp["rate"] else None,
                 "uniform_chance_1_over_nf": 1.0 / nf, "B8_bar": B8_BAR}
    res["D3"]["B8_pass"] = bool(all(
        (res["D3"][f"enrichment_vs_{n}"] or 0) >= B8_BAR
        for n in ("shift", "random", "permuted")))
    print(f"D3 defect {rd['rate']:.5f} +/- {rd['sem']:.5f} | shift {rs['rate']:.5f} "
          f"| random {ru['rate']:.5f} | permuted {rp['rate']:.5f} "
          f"=> {res['D3']['enrichment_vs_shift']:.3f}x", flush=True)

    # matched-brightness control: bin shift sites by elected luma
    lb = np.array([0, 500, 1000, 2000, 4000, 8000, 1e9])
    ld = luma[np.clip(np.rint(ty[0]).astype(int), 0, H - 1),
              np.clip(np.rint(tx[0]).astype(int), 0, W - 1)]
    ls = luma[ry, rx]
    strata = []
    for i in range(len(lb) - 1):
        md = (ld >= lb[i]) & (ld < lb[i + 1])
        ms = (ls >= lb[i]) & (ls < lb[i + 1])
        if md.sum() < 30 or ms.sum() < 30:
            continue
        a_, b_ = rate(h_d[md], v_d[md]), rate(h_s[ms], v_s[ms])
        strata.append({"luma_dn": [float(lb[i]), float(lb[i + 1]) if lb[i+1] < 1e8 else None],
                       "n_defect": int(md.sum()), "n_shift": int(ms.sum()),
                       "defect_rate": a_["rate"], "shift_rate": b_["rate"],
                       "enrichment": a_["rate"] / b_["rate"] if b_["rate"] else None})
    res["D3"]["brightness_matched_strata"] = strata

    # ---------- D4: trails ----------
    d = np.sqrt((tx - tx[0]) ** 2 + (ty - ty[0]) ** 2)
    geo = np.nanmax(d, axis=0)
    res["D4"] = {
        "geometric_trail_px_p50": float(np.nanmedian(geo)),
        "geometric_trail_px_p90": float(np.nanpercentile(geo, 90)),
        "geometric_trail_px_max": float(np.nanmax(geo)),
        "elected_trail_px_mean": float(h_d.mean()),
        "elected_trail_px_p50": float(np.median(h_d)),
        "elected_trail_px_p90": float(np.percentile(h_d, 90)),
        "elected_trail_px_max": int(h_d.max()),
        "elected_trail_shift_null_mean": float(h_s.mean()),
        "visible_frames_mean": float(v_d.mean()),
        "frac_sites_with_zero_elected": float((h_d == 0).mean()),
        "frac_shift_with_zero_elected": float((h_s == 0).mean()),
    }
    print(f"D4 geometric trail p50={res['D4']['geometric_trail_px_p50']:.1f} px "
          f"max={res['D4']['geometric_trail_px_max']:.1f} px | elected "
          f"mean={res['D4']['elected_trail_px_mean']:.3f} px "
          f"(shift null {res['D4']['elected_trail_shift_null_mean']:.3f})", flush=True)

    with open(OUT / f"08-deciding-{a.stack}-{a.arm}.json", "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    print(f"wrote 08-deciding-{a.stack}-{a.arm}.json", flush=True)


if __name__ == "__main__":
    main()
