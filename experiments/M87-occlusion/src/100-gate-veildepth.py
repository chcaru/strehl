"""M87 / 100 -- ORCH's causal test, run in the statistic ORCH's prediction is
stated in.  Does the s25 veil depth V depend on --gate?

================================================================================
WHY THIS IS NOT THE SAME TEST AS s33
================================================================================
s33 measured V_s33 = peak BRIGHT ring residual / contrast, on the BLOB region,
and found it near-invariant to the gate.  ORCH's prediction is stated in a
DIFFERENT statistic -- s25's veil DEPTH,

    V = ( median profile over d in [2,22] - median profile over d in [80,120] )
        / median profile over d in [80,120]                      (70-veil.py)

-- a signed DARKENING, on ROI_LEG, in linear DN.  A statistic measuring the
absence of darkening and a statistic measuring a bright hump are not the same
quantity and s33 does not settle ORCH's claim.  So I compute s25's V.

================================================================================
WHAT ORCH PREDICTED, AND THE THING THAT ALREADY REFUTES IT
================================================================================
ORCH: "at gate 0.00 the merge is one frame per pixel, so it cannot remove a
veil by combination and should read close to your single-frame -26.47%.  At
gate 4.00 the flat background averages heavily and should read close to your
merge value of -6.68%."

That reads -6.68% as a gate-4 number.  It is not.  Verified at source twice:

  * docs/research/M87-occlusion.md s25.7 tabulates the row as
    "| gate-0 merge | -6.6810% |"
  * 70-veil.py prints it as "merge (gate 0)" and computes it on
    cache/bee3-leg-sel.npy, the gate-0 elected merge.

So 74.76% of the veil was ALREADY removed at n_eff = 1, with zero averaging.
And s25's C-RANDV is the control that isolates why: a uniformly random
per-pixel election has the SAME per-pixel mixture structure and an
UNINFORMATIVE selector, and reads -25.8547%, inside the single-frame range --
no removal at all.  s25 states the conclusion directly: "A per-pixel mixture as
such does nothing -- it is this election."

s25 therefore already ran ORCH's causal experiment in a stronger form: it
varied selector INFORMATIVENESS with averaging held at zero, which isolates the
selector, whereas the gate ladder varies averaging with the selector held
informative.  Together the two complete a 2x2.  This script fills the missing
cell: informative selector at n_eff = 55.

================================================================================
PREREGISTRATION -- written before any number below was seen.
================================================================================
Predicted swing if ORCH is right: V goes from -6.68% to -26.47%, a change of
-19.79 percentage points (pp).  Registered branches on dV = V(0.00) - V(4.00),
in pp, SIGNED.  Four branches, because a bar with no reversal branch is how I
and ORCH have each already produced a wrong verdict this milestone:

  B19-ORCH-CONFIRMED   dV <= -9.90 pp   (at least half the predicted swing,
                                         in the predicted direction)
  B19-PARTIAL          -9.90 < dV <= -3.00 pp
  B19-FLAT             |dV| < 3.00 pp    (15% of the predicted swing; averaging
                                         does not drive veil removal)
  B19-REVERSED         dV >= +3.00 pp    (gate 0 LESS veiled -- opposite sign)

Registered secondary: the RANK of the arms.  If averaging drives removal, V
must be monotone in the gate.  I report Spearman rho over the four arms and
treat non-monotonicity as evidence against an averaging mechanism regardless of
which branch dV lands in.

================================================================================
CONTROLS
================================================================================
C-DRIFT-FORM  ORCH's hazard 1, and I must not assume my way past it.  V is a
    ratio, so it is EXACTLY invariant to g -> a*g and NOT invariant to
    g -> g + b.  Whether ORCH's 2.14% far-field fall is a hazard therefore
    depends entirely on its FORM.  I discriminate empirically: if the drift is
    multiplicative the dark subject level falls by the same PERCENT as the far
    level; if additive it falls by the same absolute DN.  Reported, not assumed.

C-MULT   scale an arm by 0.9786 (ORCH's 2.14%).  V must be unchanged to
    < 1e-12.  This is algebraically exact, so it is a test of my code.

C-ADD    subtract a constant of 2.14% of the far level.  V MUST change.  A
    control that cannot move is not evidence of immunity, it is evidence of a
    dead instrument -- so this arm proves V is responsive to the hazard it is
    claimed to survive, and quantifies it.

C-FROZEN R1: masks derived once on the gate-4.00 arm and applied unchanged to
    all four.  I additionally recompute with per-arm masks and report the
    difference, so the reader can see whether freezing changed the verdict.

C-POS    plant a known extra veil -- multiply the 2-22 px band by 0.90 on the
    gate-4.00 arm -- and require V to move by the planted amount with
    CALIBRATION, not merely in the right direction.

READ-ONLY: D:\\personal\\macro, and ORCH's pinned TIFFs in
C:\\dev\\strehl-out\\ORCH-gate (read only; this script writes nothing there).

PROVENANCE (rule 47).  Operands are ORCH's four pinned renders:
  strehl stack D:\\personal\\macro\\bee-3-cpl --gate <G> --srgb --exposure=1.54
    --out C:\\dev\\strehl-out\\ORCH-gate\\pin-bee-3-cpl-gate-<G>.tif
  env: STREHL_WARPMAP=C:\\dev\\strehl-out\\ORCH-kernel\\bee-3-cpl-catmull-rom-warpmap.txt
       STREHL_ALIGN unset, STREHL_FIX_HALO unset
  one shared solved sidecar: reference frame 149, 299 placed / 0 refused.
  gate-4.00 arm sha256 E400A63AA9F6AB1F1957940D7BD9D4965D67E01F6F0E1A0A7ABC30D8E7F17112
"""
import hashlib
import json
import pathlib
import sys
import time

import numpy as np
from scipy.ndimage import distance_transform_edt

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m87lib as L  # noqa: E402

GATE = pathlib.Path(r"C:\dev\strehl-out\ORCH-gate")
HERE = pathlib.Path(__file__).resolve().parents[1]
CACHE = HERE / "cache"
DATA = HERE / "data"
ARMS = ["4.00", "2.00", "0.7078", "0.00"]

# s25 / 70-veil.py constants, reused verbatim so the numbers are commensurable.
VEIL = (2, 22)
FAR = (80, 120)
M = L.WINDOW_RADIUS + L.REGULARISER_RADIUS + 1          # 22
ROI_Y0, ROI_Y1, ROI_X0, ROI_X1 = L.ROIS["ROI_LEG"]      # binned coords
BIN = 2                                                  # arms are unbinned

# s25 anchors, quoted from docs/research/M87-occlusion.md s25.7 (percent).
S25_MERGE_GATE0 = -6.6810
S25_FRAME_MEAN = -26.4668
S25_RANDOM = -25.8547
PREDICTED_SWING = S25_MERGE_GATE0 - S25_FRAME_MEAN       # ORCH's -19.79 pp


def _np(o):
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(repr(o))


def srgb_to_linear(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def load_arm(gate, channel="green"):
    """Crop ROI_LEG (with s25's margin) at 2x, linearise, bin 2x2 -> s25 space."""
    import tifffile
    y0 = (ROI_Y0 - M) * BIN
    y1 = (ROI_Y1 + M) * BIN
    x0 = (ROI_X0 - M) * BIN
    x1 = (ROI_X1 + M) * BIN
    a = tifffile.imread(GATE / f"pin-bee-3-cpl-gate-{gate}.tif")
    sub = a[y0:y1, x0:x1, :].astype(np.float64) / 65535.0
    del a
    lin = srgb_to_linear(sub)
    if channel == "green":
        v = lin[:, :, 1]
    else:
        v = lin.mean(axis=2)
    n_clip = int((sub >= 1.0).sum())
    del sub, lin
    h, w = v.shape
    v = v.reshape(h // BIN, BIN, w // BIN, BIN).mean(axis=(1, 3))
    return v * 65535.0, n_clip


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 22), b""):
            h.update(blk)
    return h.hexdigest().upper()


class Geom:
    """Frozen population: mask, distance field, ring index. Built once."""

    def __init__(self, ref):
        self.fmask, _ = L.foreground_mask(ref)
        self.dd = np.rint(distance_transform_edt(~self.fmask)).astype(np.int32)
        inner = np.zeros_like(self.dd, bool)
        inner[M:M + (ROI_Y1 - ROI_Y0), M:M + (ROI_X1 - ROI_X0)] = True
        self.valid = (~self.fmask) & inner
        dv = self.dd[self.valid]
        self.order = np.argsort(dv, kind="stable")
        self.edges = np.searchsorted(dv[self.order], np.arange(0, 202))

    def prof(self, img):
        v = img[self.valid][self.order]
        out = np.full(201, np.nan)
        for d in range(201):
            a, b = self.edges[d], self.edges[d + 1]
            if b - a >= 200:
                out[d] = np.median(v[a:b])
        return out

    def V(self, img):
        p = self.prof(img)
        near = np.nanmedian(p[VEIL[0]:VEIL[1] + 1])
        far = np.nanmedian(p[FAR[0]:FAR[1] + 1])
        return float(100.0 * (near - far) / far), float(near), float(far)


def spearman(x, y):
    rx = np.argsort(np.argsort(np.asarray(x, float)))
    ry = np.argsort(np.argsort(np.asarray(y, float)))
    rx = rx - rx.mean()
    ry = ry - ry.mean()
    return float((rx * ry).sum() / np.sqrt((rx * rx).sum() * (ry * ry).sum()))


def main():
    t0 = time.time()
    rep = {"provenance": {}, "arms": {}, "controls": {}, "bars": {}}

    rep["provenance"]["gate_4_sha256"] = sha256(
        GATE / "pin-bee-3-cpl-gate-4.00.tif")
    assert rep["provenance"]["gate_4_sha256"] == (
        "E400A63AA9F6AB1F1957940D7BD9D4965D67E01F6F0E1A0A7ABC30D8E7F17112"), \
        "gate-4.00 arm is not the render this milestone characterised"
    print(f"gate-4.00 sha256 verified: {rep['provenance']['gate_4_sha256'][:16]}...")

    imgs = {}
    for g in ARMS:
        imgs[g], nclip = load_arm(g)
        rep["arms"].setdefault(g, {})["n_clipped_subpixels"] = nclip
    print(f"loaded 4 arms in s25 space, shape {imgs['4.00'].shape} "
          f"(s25 cache is 744x1144)")

    # -------- frozen population, R1: derived ONCE on the gate-4.00 arm -----
    G = Geom(imgs["4.00"])
    subj_frac = float(G.fmask.mean())
    print(f"frozen mask: subject fraction {100 * subj_frac:.2f}%, "
          f"valid background px {int(G.valid.sum())}")
    rep["provenance"]["subject_fraction"] = subj_frac
    rep["provenance"]["valid_px"] = int(G.valid.sum())

    # registration diagnostic against s25's own cached merge (not a bar)
    sel0 = np.load(CACHE / "bee3-leg-sel.npy")
    if sel0.shape == imgs["4.00"].shape:
        m25, _ = L.foreground_mask(sel0)
        inter = float((m25 & G.fmask).sum())
        union = float((m25 | G.fmask).sum())
        rep["provenance"]["mask_iou_vs_s25"] = inter / max(union, 1.0)
        rep["provenance"]["s25_subject_fraction"] = float(m25.mean())
        print(f"registration vs s25's cached merge: mask IoU "
              f"{100 * inter / max(union, 1.0):.2f}%  "
              f"(s25 subject {100 * m25.mean():.2f}%)")

    # -------------------------------------------------------------- ladder
    print("\n=== s25 veil depth V across ORCH's gate ladder (frozen mask) ===")
    print(f"  {'gate':>8}  {'V %':>10}  {'near DN':>10}  {'far DN':>10}")
    Vs = {}
    for g in ARMS:
        v, near, far = G.V(imgs[g])
        Vs[g] = v
        rep["arms"][g].update({"V_pct": v, "near_dn": near, "far_dn": far})
        print(f"  {g:>8}  {v:>+10.4f}  {near:>10.1f}  {far:>10.1f}")

    dV = Vs["0.00"] - Vs["4.00"]
    gates = [float(g) for g in ARMS]
    rho = spearman(gates, [Vs[g] for g in ARMS])
    if dV <= -9.90:
        branch = "B19-ORCH-CONFIRMED"
    elif dV <= -3.00:
        branch = "B19-PARTIAL"
    elif abs(dV) < 3.00:
        branch = "B19-FLAT"
    else:
        branch = "B19-REVERSED"
    print(f"\n  dV = V(0.00) - V(4.00) = {dV:+.4f} pp")
    print(f"  ORCH predicted {PREDICTED_SWING:+.2f} pp "
          f"(from {S25_FRAME_MEAN:+.4f}% to {S25_MERGE_GATE0:+.4f}%)")
    print(f"  observed / predicted = {100 * dV / PREDICTED_SWING:.2f}%")
    print(f"  Spearman rho(gate, V) over 4 arms = {rho:+.4f}")
    print(f"  BRANCH -> {branch}")
    rep["bars"]["B19"] = {"dV_pp": dV, "predicted_pp": PREDICTED_SWING,
                          "frac_of_predicted": 100 * dV / PREDICTED_SWING,
                          "spearman_rho": rho, "branch": branch,
                          "V": {g: Vs[g] for g in ARMS}}

    # ------------------------------------------------- C-DRIFT-FORM
    print("\n=== C-DRIFT-FORM: is ORCH's 2.14% drift multiplicative or additive? ===")
    ref_far = rep["arms"]["4.00"]["far_dn"]
    ref_subj = float(np.median(imgs["4.00"][G.fmask]))
    rows = []
    for g in ARMS:
        far = rep["arms"][g]["far_dn"]
        sj = float(np.median(imgs[g][G.fmask]))
        rows.append({"gate": g, "far": far, "subj": sj,
                     "far_pct": 100 * (far / ref_far - 1),
                     "subj_pct": 100 * (sj / ref_subj - 1),
                     "far_dn_delta": far - ref_far,
                     "subj_dn_delta": sj - ref_subj})
        print(f"  gate {g:>7}  far {far:9.1f} ({rows[-1]['far_pct']:+6.3f}%, "
              f"{rows[-1]['far_dn_delta']:+8.1f} DN)   "
              f"subj {sj:9.1f} ({rows[-1]['subj_pct']:+6.3f}%, "
              f"{rows[-1]['subj_dn_delta']:+8.1f} DN)")
    last = rows[-1]
    mult_err = abs(last["subj_pct"] - last["far_pct"])
    add_err = abs(last["subj_dn_delta"] - last["far_dn_delta"])
    form = "MULTIPLICATIVE" if mult_err < abs(last["far_pct"]) * 0.5 else (
        "ADDITIVE" if add_err < abs(last["far_dn_delta"]) * 0.5 else "NEITHER")
    print(f"  gate 0.00 vs 4.00: percent mismatch {mult_err:.3f} pp, "
          f"absolute mismatch {add_err:.1f} DN  ->  {form}")
    rep["controls"]["C_DRIFT_FORM"] = {"rows": rows, "form": form,
                                       "mult_mismatch_pp": mult_err,
                                       "add_mismatch_dn": add_err}

    # ------------------------------------------------- C-MULT / C-ADD
    print("\n=== C-MULT (must be exact) / C-ADD (must move) ===")
    a = 1.0 - 0.0214
    v_mult, _, _ = G.V(imgs["4.00"] * a)
    mult_err2 = abs(v_mult - Vs["4.00"])
    b = -0.0214 * rep["arms"]["4.00"]["far_dn"]
    v_add, _, _ = G.V(imgs["4.00"] + b)
    add_delta = v_add - Vs["4.00"]
    print(f"  C-MULT  x{a:.4f}: V {Vs['4.00']:+.6f} -> {v_mult:+.6f}  "
          f"|dV| = {mult_err2:.3e}   bar < 1e-12  "
          f"-> {'PASS' if mult_err2 < 1e-12 else 'FAIL'}")
    print(f"  C-ADD   {b:+.1f} DN: V {Vs['4.00']:+.6f} -> {v_add:+.6f}  "
          f"dV = {add_delta:+.4f} pp  -> "
          f"{'responsive' if abs(add_delta) > 0.01 else 'DEAD INSTRUMENT'}")
    rep["controls"]["C_MULT"] = {"err": mult_err2, "pass": bool(mult_err2 < 1e-12)}
    rep["controls"]["C_ADD"] = {"dV_pp": add_delta, "b_dn": b,
                                "responsive": bool(abs(add_delta) > 0.01)}

    # ------------------------------------------------- C-FROZEN
    print("\n=== C-FROZEN: does freezing the mask change the verdict? ===")
    per_arm = {}
    for g in ARMS:
        Gg = Geom(imgs[g])
        per_arm[g] = Gg.V(imgs[g])[0]
    dV_free = per_arm["0.00"] - per_arm["4.00"]
    print(f"  {'gate':>8}  {'V frozen':>10}  {'V per-arm':>10}")
    for g in ARMS:
        print(f"  {g:>8}  {Vs[g]:>+10.4f}  {per_arm[g]:>+10.4f}")
    print(f"  dV frozen {dV:+.4f} pp   dV per-arm {dV_free:+.4f} pp")
    rep["controls"]["C_FROZEN"] = {"per_arm_V": per_arm, "dV_per_arm": dV_free,
                                   "dV_frozen": dV}

    # ------------------------------------------------- C-POS
    print("\n=== C-POS: plant a known veil, require calibration ===")
    planted = imgs["4.00"].copy()
    band = (G.dd >= VEIL[0]) & (G.dd <= VEIL[1]) & G.valid
    planted[band] *= 0.90
    v_pos, near_p, far_p = G.V(planted)
    near0 = rep["arms"]["4.00"]["near_dn"]
    far0 = rep["arms"]["4.00"]["far_dn"]
    expect = 100.0 * (0.90 * near0 - far0) / far0
    cal_err = abs(v_pos - expect)
    print(f"  planted x0.90 over d in [{VEIL[0]},{VEIL[1]}]")
    print(f"  V {Vs['4.00']:+.4f}% -> {v_pos:+.4f}%   expected {expect:+.4f}%"
          f"   |err| {cal_err:.4f} pp  -> "
          f"{'PASS' if cal_err < 0.5 else 'FAIL'}")
    rep["controls"]["C_POS"] = {"V_planted": v_pos, "V_expected": expect,
                                "err_pp": cal_err, "pass": bool(cal_err < 0.5)}

    rep["s25_anchors"] = {"merge_gate0": S25_MERGE_GATE0,
                          "frame_mean": S25_FRAME_MEAN,
                          "random_election": S25_RANDOM}
    rep["elapsed_s"] = round(time.time() - t0, 1)
    DATA.mkdir(parents=True, exist_ok=True)
    with open(DATA / "100-gate-veildepth.json", "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1, default=_np)
    print(f"\nwrote {DATA / '100-gate-veildepth.json'}  [{rep['elapsed_s']}s]")


if __name__ == "__main__":
    main()
