r"""M112 Phase 0 -- how much high-band power does cropping instead of enlarging recover?

THIS FILE CONTAINS NO SHARPNESS ARITHMETIC OF ITS OWN.

It imports M95's committed harness (`experiments/M95-coverage/src/x8_fix.py`) and
its instrument (`m95cov.py`) and calls them. The gather, the Catmull-Rom taps,
the band-matched `band_ratio` and the `arm()` cost are executed **verbatim from
M95's committed source**; the only things this driver changes are the values of
two module-level *input* constants that M95 hard-coded:

    x8_fix.MAP      -- which warp sidecar to read   (was one fixed path)
    x8_fix.K_COVER  -- the coverage factor          (was the literal 0.9315)

That is deliberate. Discipline 716 and fact 1442: before building a control,
grep for one. A copy of the arithmetic could drift from the original; an import
cannot. Control C0 asserts the imported source is byte-identical to git HEAD.

Outputs land in experiments/M112-real-pixels/out/ and never touch M95's files.
Reads are read-only; nothing under D:\ is opened at all.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
M95SRC = REPO / "experiments" / "M95-coverage" / "src"
OUT = HERE.parents[1] / "out"

sys.path.insert(0, str(M95SRC))
import m95cov as M          # noqa: E402  M95's instrument, verbatim
import x8_fix as X          # noqa: E402  M95's harness, verbatim

# ------------------------------------------------------------------ inputs

BASE = Path(r"C:\dev\strehl-out\M95-resample\single-noalign.tif")

SIDECARS = {
    # the shipped 299-frame solve, reference 149 -- byte-identical in three
    # independent milestones (M106 snapshot, ORCH-gallery3, M107-chroma)
    "bee299": Path(r"C:\dev\strehl-out\M106\warpmap-corpus-snapshot.txt"),
    # an independent copy of the same digest, to prove the input is stable
    "bee299b": Path(r"C:\dev\strehl-out\ORCH-gallery3\bee-3-cpl-warpmap.txt"),
    # the quarantined 8-frame sidecar the fact-1419 re-run could have read
    "bee8": Path(r"C:\dev\strehl-out\ORCH-quarantine-sidecars\bee-3-cpl--warpmap.txt"),
}

K_BEE = 0.9315      # fit_to_cover on bee-3-cpl (facts 1289, 1400; M98 MEASURED)
K_NULLQ = 0.9974    # the brief's "k is already ~1" stack (M97, identity sidecar)


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def sidecar_meta(p):
    head = {}
    for line in Path(p).read_text(encoding="utf-8").splitlines():
        for key in ("stack-name", "stack-digest", "frames", "reference",
                    "resampler", "strategy"):
            if line.startswith(key + " "):
                head[key] = line.split(None, 1)[1].strip()
    head["sha256"] = sha256(p)
    head["path"] = str(p)
    return head


# ------------------------------------------------------- C0: arithmetic check

def c0_arithmetic_unchanged():
    """The imported harness and instrument must match git HEAD byte for byte.

    This is what lets every number below be attributed to M95's arithmetic
    rather than to a copy of it that may have drifted.
    """
    res = {}
    for rel in ("experiments/M95-coverage/src/x8_fix.py",
                "experiments/M95-coverage/src/m95cov.py"):
        blob = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=REPO,
                              capture_output=True).stdout
        disk = (REPO / rel).read_bytes()
        # git may normalise line endings on checkout; compare canonically
        same = blob.replace(b"\r\n", b"\n") == disk.replace(b"\r\n", b"\n")
        res[rel] = {"matches_head": bool(same),
                    "sha256_disk": hashlib.sha256(disk).hexdigest()}
    return res


# ------------------------------------------------------------------- arms

IDENT = [(0, 1.0, 0.0, 0.0, 0.0)]


def cost(img, tiles, warps, use_cover, snap=False):
    c, st = X.arm(img, tiles, warps, use_cover=use_cover, snap=snap)
    if len(c) == 0:
        return {"cost_dex": None, "sem": None, "n": 0, "mean_step": None}
    return {"cost_dex": float(c.mean()),
            "sem": float(c.std(ddof=1) / np.sqrt(len(c))),
            "n": int(len(c)),
            "mean_step": float(st.mean())}


def main():
    if not BASE.exists():
        sys.exit(f"missing base image {BASE}")

    img = M.load_luma(BASE)
    tiles = M.pick_tiles(img)

    res = {
        "base": {"path": str(BASE), "shape": [int(img.shape[1]), int(img.shape[0])],
                 "sha256": sha256(BASE)},
        "roi": {"n_tiles": len(tiles), "tile": M.TILE, "pad": M.PAD,
                "tiles": [[int(y), int(x)] for y, x in tiles]},
        "band": {"high_cyc_px": list(M.BAND), "low_cyc_px": list(M.LOWBAND),
                 "band_matched": True},
        "C0_arithmetic": c0_arithmetic_unchanged(),
        "sidecars": {},
        "arms": {},
    }

    print(f"base   : {BASE.name}  {img.shape[1]}x{img.shape[0]}")
    print(f"ROI    : {len(tiles)} tiles of {M.TILE}px, >= {M.PAD}px inside every border")
    print(f"band   : high {M.BAND} cyc/px over low {M.LOWBAND} cyc/px, band-matched\n")

    print("--- C0: is the imported arithmetic identical to git HEAD? ---")
    for k, v in res["C0_arithmetic"].items():
        print(f"  {'OK ' if v['matches_head'] else 'DIFF'}  {k}")
    if not all(v["matches_head"] for v in res["C0_arithmetic"].values()):
        print("\nC0 FAILED -- the harness on disk is not the committed one. Stopping.")
        (OUT / "p0.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
        return 2

    # -------------------------------------------------- K1 / K4 true nulls
    print("\n--- controls whose true value is ZERO by construction ---")
    X.K_COVER = K_BEE
    k1 = cost(img, tiles, IDENT, use_cover=False)
    k4 = cost(img, tiles, [(0, 1.0, 0.0, 7.0, -3.0)], use_cover=False)
    res["arms"]["K1_identity_nocover"] = k1
    res["arms"]["K4_integer_shift"] = k4
    print(f"  K1  identity warp, no coverage   {k1['cost_dex']:+.6f} dex"
          f"   {'PASS' if abs(k1['cost_dex']) < 0.005 else 'FAIL'}")
    print(f"  K4  integer shift, unit scale    {k4['cost_dex']:+.6f} dex"
          f"   {'PASS' if abs(k4['cost_dex']) < 0.005 else 'FAIL'}")
    if abs(k1["cost_dex"]) >= 0.005:
        print("\nK1 FAILED -- reporting no arm numbers.")
        (OUT / "p0.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
        return 1

    # ------------------------------------------- the decision arms, per sidecar
    for tag, path in SIDECARS.items():
        if not path.exists():
            print(f"\n[{tag}] MISSING {path}")
            continue
        meta = sidecar_meta(path)
        res["sidecars"][tag] = meta
        X.MAP = path
        X.MAP_ALT = path
        X.K_COVER = K_BEE
        plane, rows, src = X.read_warps()
        idx = np.linspace(0, len(rows) - 1, X.NFRAMES).round().astype(int)
        warps24 = [rows[i] for i in idx]

        print(f"\n=== {tag}: {meta['stack-name']}  frames={meta['frames']} "
              f"reference={meta['reference']}  sha={meta['sha256'][:16]} ===")
        print(f"    {len(rows)} placed rows, plane {plane[0]}x{plane[1]}")

        block = {}
        for name, uc, sn, desc in (
            ("NOW", True, False, f"real warp + coverage k={K_BEE}"),
            ("FIX", False, False, "real warp, coverage removed (k=1)"),
            ("SNAP", False, True, "integer translation, unit scale"),
        ):
            block[name] = cost(img, tiles, warps24, use_cover=uc, snap=sn)
            block[name]["what"] = desc

        # all placed frames, not M95's 24-frame subsample (rule 24: re-choose)
        block["NOW_all"] = cost(img, tiles, rows, use_cover=True)
        block["FIX_all"] = cost(img, tiles, rows, use_cover=False)

        # the reference frame alone -- its warp is exact identity, so under FIX
        # it should become a true no-op
        ref_i = int(meta.get("reference", -1))
        ref_rows = [r for r in rows if r[0] == ref_i]
        if ref_rows:
            block["REFONLY_NOW"] = cost(img, tiles, ref_rows, use_cover=True)
            block["REFONLY_FIX"] = cost(img, tiles, ref_rows, use_cover=False)
            block["reference_warp"] = {"idx": ref_i, "a_re": ref_rows[0][1],
                                       "a_im": ref_rows[0][2],
                                       "b_re": ref_rows[0][3],
                                       "b_im": ref_rows[0][4]}

        print(f"    {'arm':<10} {'cost (dex)':>12} {'sem':>8} {'n':>6} {'step':>9}  what")
        for name in ("NOW", "FIX", "SNAP", "NOW_all", "FIX_all",
                     "REFONLY_NOW", "REFONLY_FIX"):
            if name in block and block[name].get("cost_dex") is not None:
                b = block[name]
                print(f"    {name:<10} {b['cost_dex']:>+12.4f} {b['sem']:>8.4f} "
                      f"{b['n']:>6} {b['mean_step']:>9.5f}  {b.get('what','')}")

        block["recovery_dex"] = block["NOW"]["cost_dex"] - block["FIX"]["cost_dex"]
        block["recovery_dex_all"] = (block["NOW_all"]["cost_dex"]
                                     - block["FIX_all"]["cost_dex"])
        if "REFONLY_NOW" in block:
            block["recovery_dex_reference_frame"] = (
                block["REFONLY_NOW"]["cost_dex"] - block["REFONLY_FIX"]["cost_dex"])
        block["ships_bar_0p10"] = bool(block["recovery_dex"] > 0.10)
        block["dead_bar_0p03"] = bool(block["recovery_dex"] < 0.03)
        print(f"    recovery (24-frame subsample) : {block['recovery_dex']:+.4f} dex")
        print(f"    recovery (ALL placed frames)  : {block['recovery_dex_all']:+.4f} dex")
        if "recovery_dex_reference_frame" in block:
            print(f"    recovery (reference frame only): "
                  f"{block['recovery_dex_reference_frame']:+.4f} dex")
        print(f"    registered SHIPS (> +0.10)    : {block['ships_bar_0p10']}")
        print(f"    registered DEAD  (< +0.03)    : {block['dead_bar_0p03']}")
        res["arms"][tag] = block

    # ------------------------------------- NULLQ: the brief's proposed null
    print("\n=== NULLQ: the brief's null -- a stack where fit_to_cover already "
          "returns k ~ 1.0 ===")
    print("    identity sidecar, so arm 2 (k=1) is an exact no-op.")
    nq = {}
    for kc in (K_NULLQ, K_BEE):
        X.K_COVER = kc
        nq[f"k={kc}"] = cost(img, tiles, IDENT, use_cover=True)
        print(f"    arm1  k={kc:<7} {nq[f'k={kc}']['cost_dex']:>+9.4f} dex")
    X.K_COVER = K_BEE
    nq["k=1.0"] = cost(img, tiles, IDENT, use_cover=False)
    print(f"    arm2  k=1.0     {nq['k=1.0']['cost_dex']:>+9.4f} dex  (exact no-op)")
    nq["brief_null_difference_dex"] = (nq[f"k={K_NULLQ}"]["cost_dex"]
                                       - nq["k=1.0"]["cost_dex"])
    nq["brief_null_fires"] = bool(abs(nq["brief_null_difference_dex"]) > 0.005)
    print(f"    difference      {nq['brief_null_difference_dex']:>+9.4f} dex"
          f"   -> null FIRES: {nq['brief_null_fires']}")
    res["arms"]["NULLQ"] = nq

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "p0.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT / 'p0.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
