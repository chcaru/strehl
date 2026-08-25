"""Self-measured lateral CA, per stack, from the bracket itself.

The transfer objection is the only thing keeping the shipped lateral-CA
correction off by default: a coefficient fitted on `tweezers-cpl` recovered 95.0%
of the in-sample reduction on `bee-3-cpl`, but the reverse direction recovered
54.1% against a registered 60% bar, and fact 52 stands as the warning against
transferring a scalar fitted on one scene. A coefficient measured on the stack
being rendered is not a transferred coefficient, so the objection does not apply
to it. This script measures that coefficient.

WHY MANY FRAMES. Commissioning on a single frame left only 60 tiles above the
structure gate, and the blue arm was not flat across the gate ladder -- it ran
from +61 ppm to +188 ppm, which by project rule 5 means the answer was a property
of the threshold rather than of the optics. A focus bracket fixes this for free:
every tile is in focus in *some* frame, so scanning the bracket and taking each
tile at its own best-focus frame turns a 60-tile fit into one that uses most of
the field. Nothing is averaged across depth; each tile is measured once, in the
frame where it is sharpest.

WHY NO REGISTRATION. Every comparison is between two channels inside a single
frame, so inter-frame drift cancels identically and none is estimated. Project
rule 6 is respected: the only sub-pixel resampling anywhere in this module
manufactures synthetic doses for commissioning and never touches a measured
quantity.

OUTPUTS, per stack:
  * eps_R and eps_B, raw and null-corrected, with bootstrap CIs over tiles;
  * the G1-vs-G2 null fitted identically and reported in the same rows (rule 3);
  * the gate ladder, so the reader can see whether the answer is a property of
    the threshold;
  * eps in radial bins, so a higher-order radial term would be visible rather
    than absorbed into the linear coefficient;
  * eps per frame, to check that defocus does not move the estimate.
"""

import argparse
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import lateral

TILE = 160
MARGIN = 40
GATE = 2e5
GATES = [0.0, 2e4, 5e4, 1e5, 2e5, 4e5, 8e5]
N_FRAMES = 24
ARMS = ("R", "G2", "B")
PPM = 1e6

_CTX = {}


def _init(stack, tile, margin):
    _CTX["stack"] = stack
    _CTX["tile"] = tile
    _CTX["margin"] = margin


def _one_frame(args):
    """Decode one frame and return per-tile structure and displacements."""
    path, = args
    cfa = common.read_cfa(path)
    planes = common.planes_of(cfa)
    tile = _CTX["tile"]
    tiles = lateral.tile_corners(planes["G1"].shape, tile, _CTX["margin"])
    disp, struct = lateral.measure_frame(planes, tiles, tile, arms=ARMS)
    s = np.array([struct[t] for t in tiles], np.float64)
    d = {a: np.array([disp[(t[0], t[1], a)] for t in tiles], np.float64)
         for a in ARMS}
    return s, d


def scan(stack, tile=TILE, margin=MARGIN, n_frames=N_FRAMES, workers=8):
    fs = common.frames(stack)
    idx = np.unique(np.linspace(0, len(fs) - 1, n_frames).round().astype(int))
    sel = [fs[i] for i in idx]
    cfa0 = common.read_cfa(sel[0])
    sensel_shape = cfa0.shape
    shape = common.planes_of(cfa0)["G1"].shape
    tiles = lateral.tile_corners(shape, tile, margin)
    del cfa0
    print(f"{stack}: {len(fs)} frames, scanning {len(sel)}; "
          f"plane {shape}, {len(tiles)} tiles of {tile} px")
    with ProcessPoolExecutor(max_workers=workers, initializer=_init,
                             initargs=(stack, tile, margin)) as ex:
        res = list(ex.map(_one_frame, [(p,) for p in sel]))
    S = np.stack([r[0] for r in res])                       # (F, T)
    D = {a: np.stack([r[1][a] for r in res]) for a in ARMS}  # (F, T, 2)
    return dict(stack=stack, frame_idx=idx, tiles=tiles, tile=tile,
                sensel_shape=sensel_shape, plane_shape=shape, S=S, D=D)


def best_frame_rows(sc, arm, gate, topk=3):
    """One row per tile, taken at that tile's own best-focus frame(s).

    `topk` frames are combined by median rather than the single argmax, so a
    tile does not rest on one realisation; `spread` records how far they
    disagreed and is carried as a per-tile quality number.
    """
    S, D = sc["S"], sc["D"][arm]
    tiles, tile = sc["tiles"], sc["tile"]
    ly, lx = lateral.lattice_offset(arm)
    order = np.argsort(-S, axis=0)
    u, d, s, spread, bf = [], [], [], [], []
    for j, (y, x) in enumerate(tiles):
        pick = order[:topk, j]
        if S[pick[0], j] < gate:
            continue
        v = D[pick, j, :]
        u.append(lateral.field_position(y, x, tile, "G1", sc["sensel_shape"]))
        d.append((float(np.median(v[:, 0])) - ly, float(np.median(v[:, 1])) - lx))
        s.append(float(S[pick[0], j]))
        spread.append(float(np.max(np.abs(v - np.median(v, axis=0)))))
        bf.append(int(pick[0]))
    return (np.array(u, float), np.array(d, float), np.array(s, float),
            np.array(spread, float), np.array(bf, int))


def summarise(u, d, label, radial_only=False):
    f = lateral.boot_fit(u, d, radial_only=radial_only, robust=True)
    fo = lateral.fit_model(u, d, radial_only=radial_only, robust=False)
    p = lateral.perm_p(u, d, radial_only=radial_only, robust=True, n_perm=1000)
    r = np.hypot(u[:, 0], u[:, 1])
    return {
        "label": label, "n": int(len(u)),
        "eps": -f["eps"], "eps_lo": -f["eps_hi"], "eps_hi": -f["eps_lo"],
        "eps_se": f["eps_se"], "eps_ols": -fo["eps"],
        "ty": -f["ty"], "tx": -f["tx"], "ty_se": f["ty_se"], "tx_se": f["tx_se"],
        "rms": f["rms"], "r2": f["r2"], "perm_p": p,
        "r_min": float(r.min()), "r_max": float(r.max()),
        "r_med": float(np.median(r)),
    }


def radial_bins(u, d, nbin=4):
    """Local radial scale per annulus. A pure radial scale predicts it flat.

    `eps_local = (d . rhat) / r` is the obvious statistic and it is WRONG on its
    own: a constant translation T contributes (T . rhat)/r, which diverges as
    1/r and manufactures a fake higher-order term at small radius. The first
    version of this diagnostic did exactly that and reported R running from
    -820 ppm at r=504 to -633 ppm at r=1565 on `tweezers-cpl`, which is entirely
    accounted for by the fitted T of (-0.196, +0.035) plane px.

    So both are returned, in the same rows (rule 3): `eps_raw` with nothing
    removed, and `eps_detrans` after subtracting the globally fitted translation.
    Only the second answers the question about higher-order radial structure.
    """
    f = lateral.fit_model(u, d, robust=True)
    T = np.array([f["ty"], f["tx"]])
    r = np.hypot(u[:, 0], u[:, 1])
    rhat = u / np.maximum(r, 1e-9)[:, None]
    proj_raw = np.sum(d * rhat, axis=1)
    proj_det = np.sum((d - T) * rhat, axis=1)
    edges = np.quantile(r, np.linspace(0, 1, nbin + 1))
    rows = []
    for k in range(nbin):
        lo, hi = edges[k], edges[k + 1]
        sel = (r >= lo) & ((r <= hi) if k == nbin - 1 else (r < hi))
        if sel.sum() < 8:
            continue
        rows.append({
            "r_lo": float(lo), "r_hi": float(hi), "n": int(sel.sum()),
            "r_med": float(np.median(r[sel])),
            "eps_raw": float(-np.median(proj_raw[sel] / r[sel])),
            "eps_detrans": float(-np.median(proj_det[sel] / r[sel])),
            "disp_med": float(np.median(proj_det[sel])),
        })
    return rows


def run(stack, n_frames=N_FRAMES, workers=8):
    sc = scan(stack, n_frames=n_frames, workers=workers)
    half_diag = float(np.hypot(*sc["sensel_shape"]) / 4.0)
    out = {"stack": stack, "tile": sc["tile"], "gate": GATE,
           "n_frames_scanned": int(len(sc["frame_idx"])),
           "frame_idx": [int(i) for i in sc["frame_idx"]],
           "n_tiles_total": len(sc["tiles"]),
           "half_diag_plane_px": half_diag}

    # ---- gate ladder, all three arms in the same table (rule 3) ----------
    print(f"\n{'arm':>4} {'gate':>8} {'n':>5} {'r span':>17} {'eps ppm':>9} "
          f"{'CI lo':>9} {'CI hi':>9} {'null-corr':>10} {'rms px':>8} {'R2':>7} {'p':>7}")
    ladder = []
    for gate in GATES:
        row = {}
        for arm in ARMS:
            u, d, s, sp, bf = best_frame_rows(sc, arm, gate)
            if len(u) < 12:
                continue
            row[arm] = summarise(u, d, f"{arm}@{gate:.0f}")
        if "G2" not in row:
            continue
        null = row["G2"]["eps"]
        for arm in ARMS:
            if arm not in row:
                continue
            e = row[arm]
            e["gate"] = gate
            e["eps_null_corrected"] = e["eps"] - null
            print(f"{arm:>4} {gate:8.0f} {e['n']:5d} "
                  f"{e['r_min']:7.0f}..{e['r_max']:<8.0f} {e['eps']*PPM:9.2f} "
                  f"{e['eps_lo']*PPM:9.2f} {e['eps_hi']*PPM:9.2f} "
                  f"{e['eps_null_corrected']*PPM:10.2f} {e['rms']:8.4f} "
                  f"{e['r2']:7.4f} {e['perm_p']:7.4f}")
            ladder.append(e)
        print()
    out["ladder"] = ladder

    # ---- headline at the working gate ------------------------------------
    head = {}
    for arm in ARMS:
        u, d, s, sp, bf = best_frame_rows(sc, arm, GATE)
        h = summarise(u, d, arm)
        h["radial"] = radial_bins(u, d)
        h["spread_med"] = float(np.median(sp))
        h["spread_p90"] = float(np.percentile(sp, 90))
        h["best_frame_med"] = float(np.median(bf))
        head[arm] = h
        np.savez_compressed(
            os.path.join(common.OUT, "json", f"c1_{stack}_{arm}.npz"),
            u=u, d=d, s=s, spread=sp, best_frame=bf)
    null = head["G2"]["eps"]
    for arm in ARMS:
        head[arm]["eps_null_corrected"] = head[arm]["eps"] - null
    out["headline"] = head

    print(f"=== {stack}: headline at gate {GATE:.0f} ===")
    print(f"{'arm':>4} {'n':>5} {'eps ppm':>10} {'CI':>22} {'null-corr ppm':>14} "
          f"{'T (plane px)':>20} {'rms':>7} {'R2':>7} {'p':>7}")
    for arm in ARMS:
        h = head[arm]
        ci = f"[{h['eps_lo']*PPM:8.2f},{h['eps_hi']*PPM:8.2f}]"
        t = f"({h['ty']:+.3f},{h['tx']:+.3f})"
        print(f"{arm:>4} {h['n']:5d} {h['eps']*PPM:10.2f} {ci:>22} "
              f"{h['eps_null_corrected']*PPM:14.2f} {t:>20} {h['rms']:7.4f} "
              f"{h['r2']:7.4f} {h['perm_p']:7.4f}")

    print(f"\nradial bins (a pure radial scale predicts eps_detrans flat;")
    print(f"eps_raw carries a spurious 1/r term from the fitted translation):")
    for arm in ARMS:
        print(f"  {arm} raw     : " + "  ".join(
            f"r={b['r_med']:.0f}:{b['eps_raw']*PPM:+.0f}(n{b['n']})"
            for b in head[arm]["radial"]))
        print(f"  {arm} detrans : " + "  ".join(
            f"r={b['r_med']:.0f}:{b['eps_detrans']*PPM:+.0f}"
            for b in head[arm]["radial"]))

    # ---- eps per frame ---------------------------------------------------
    print(f"\neps per scanned frame (defocus must not move the estimate):")
    per_frame = {a: [] for a in ARMS}
    for fi in range(sc["S"].shape[0]):
        sel = sc["S"][fi] >= GATE
        if sel.sum() < 12:
            continue
        for arm in ARMS:
            ly, lx = lateral.lattice_offset(arm)
            u = np.array([lateral.field_position(y, x, sc["tile"], "G1",
                                                 sc["sensel_shape"])
                          for j, (y, x) in enumerate(sc["tiles"]) if sel[j]])
            d = sc["D"][arm][fi][sel] - np.array([ly, lx])
            per_frame[arm].append(
                {"frame": int(sc["frame_idx"][fi]), "n": int(sel.sum()),
                 "eps": -lateral.fit_model(u, d, robust=True)["eps"]})
    for arm in ARMS:
        vals = np.array([r["eps"] for r in per_frame[arm]])
        if len(vals):
            print(f"  {arm}: n_frames {len(vals)}  median {np.median(vals)*PPM:+8.2f} "
                  f"ppm  IQR {np.percentile(vals,75)*PPM - np.percentile(vals,25)*PPM:7.2f} "
                  f"ppm  range [{vals.min()*PPM:+.0f}, {vals.max()*PPM:+.0f}]")
    out["per_frame"] = per_frame

    common.dump(f"c1_lateral_{stack}", out)
    print(f"\nwrote c1_lateral_{stack}.json")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stacks", nargs="+")
    ap.add_argument("--frames", type=int, default=N_FRAMES)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    for st in a.stacks:
        run(st, n_frames=a.frames, workers=a.workers)
