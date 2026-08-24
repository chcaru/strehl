"""M92 S4 -- reproduction control (RC).  Does this harness reproduce M57 S7?

Rule 20 in its strongest form: if this milestone cannot reproduce its parent's
published per-cell null scatter on the parent's own cells at the parent's own
settings, nothing else it reports means anything, and the milestone is void.

The control deliberately uses M57's OWN loader (`m57lib.load_cube`), M57's own
merge, M57's own hard-coded `ISO = 500 / G = 1.14469 / RN_E = 1.47`, and M57's
own 24-rep draw count, so the only thing that differs is the driver file.

Bar (PREREGISTRATION section 6): `sd(draws)` within a factor of 2 of M57 S7's
published value on every cell and level.  Failure voids the milestone.

It then re-runs the same three cells at each stack's TRUE EXIF ISO, and adds the
fourth cell -- `109MSDCF/flat`, S6's `n1_K1 dsig[1]` -- which is where the
0.34310 px bound this milestone was dispatched against actually came from.
"""
import glob
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m92lib as M92  # noqa: E402
import m57lib as K    # noqa: E402

PAD = 32
M57_G, M57_RN_E, M57_ISO = 1.14469, 1.47, 500
REPS = int(os.environ.get("M92_REPS", "128"))

# M57 S7 table 1, K1 dsig, sd(draws) at levels 1x / 2x / 3x.  `None` = M57
# reported "too few finite draws" at that level.
S7_PUBLISHED = {
    "109MSDCF/centre": (0.08230, 0.16370, 0.25592),
    "112MSDCF/flat": (0.05841, None, 0.09029),
    "112MSDCF/detail": (0.03054, 0.04334, 0.04898),
}

CELLS = [
    ("109MSDCF", "centre", (916, 1501, 512, 512), 0, 22, 160),
    ("112MSDCF", "flat", (2747, 32, 512, 512), 6, 68, 500),
    ("112MSDCF", "detail", (1671, 1373, 512, 512), 6, 68, 500),
    ("109MSDCF", "flat", (2747, 32, 512, 512), 0, 22, 160),   # source of 0.34310
]


def draws(ma, mb, rs1, sm, mult, reps, seed):
    rng = np.random.default_rng(seed)
    v, j = [], []
    for _ in range(reps):
        add = sm * mult
        aa = ma + rng.standard_normal(ma.shape).astype(np.float32) * add
        bb = mb + rng.standard_normal(mb.shape).astype(np.float32) * add
        d = K.dsig(rs1, K.RingStats(aa, bb))
        if np.isfinite(d["px"]):
            v.append(d["px"])
            j.append(d["se_px"])
    return np.array(v), np.array(j)


def main():
    t0 = time.time()
    lines = []

    def log(s=""):
        print(s, flush=True)
        lines.append(s)

    log("=" * 78)
    log(f"M92 S4 -- reproduction control against M57 S7.  {REPS} draws/level.")
    log("  M57's loader, M57's merge, M57's ISO 500 / G 1.14469 / RN_E 1.47.")
    log("  Bar: sd(draws) within a factor of 2 of S7's published value.")
    log("=" * 78)

    out, worst = {}, 0.0
    for sname, rname, roi, lo, hi, true_iso in CELLS:
        files = sorted(glob.glob(os.path.join(M92.ROOT, sname, "*.ARW")))[lo:hi]
        cube = K.load_cube(files, roi, pad=PAD)
        nf = cube.shape[0]
        fine, coarse, reg = K.L1.focus_fields(cube, M57_G, M57_RN_E)
        ia, ib = K.splits(nf)["parity"]
        ma, nea = K.merge_subset(cube, coarse, reg, ia, pad=PAD)
        mb, _ = K.merge_subset(cube, coarse, reg, ib, pad=PAD)
        del cube, fine, coarse, reg
        lvl = float(np.median(ma))
        rs1 = K.RingStats(ma, mb)
        key = f"{sname}/{rname}"

        def sigma(iso):
            s1 = float(np.sqrt(K.M.noise_var_dn(lvl, K.gain_dn_per_e(iso),
                                                K.read_noise_e(iso))))
            return s1 / np.sqrt(nea), s1

        sm500, s1_500 = sigma(M57_ISO)
        smtrue, s1_true = sigma(true_iso)
        log("\n" + "=" * 78)
        log(f"{key}   {nf} frames   n_eff(A) {nea:.3f}   level {lvl:.1f} DN"
            f"   ({time.time()-t0:.0f}s)")
        log(f"  merged sigma at M57's ISO 500 = {sm500:.4f} DN;"
            f" at TRUE EXIF ISO {true_iso} = {smtrue:.4f} DN"
            f"   ratio {sm500/smtrue:.4f}x")
        cell = {"n_frames": nf, "n_eff_a": float(nea), "level": lvl,
                "sigma_iso500": sm500, "sigma_true": smtrue,
                "true_iso": true_iso, "ratio": float(sm500 / smtrue),
                "levels": {}}
        pub = S7_PUBLISHED.get(key)
        log(f"  {'x sig':>6} {'iso':>5} {'mean px':>10} {'sd(draws)':>10}"
            f" {'S7 pub':>9} {'ratio':>7} {'jack':>8} {'sd/jack':>8}"
            f" {'finite':>8}")
        for mult in (1.0, 2.0, 3.0):
            for lab, sm, iso in (("M57", sm500, M57_ISO),
                                 ("true", smtrue, true_iso)):
                v, j = draws(ma, mb, rs1, sm, mult,
                             REPS, 920000 + int(mult * 10) + iso)
                if v.size < 3:
                    log(f"  {mult:6.1f} {lab:>5}   too few finite draws "
                        f"({v.size}/{REPS})")
                    cell["levels"][f"{lab}_{mult}"] = dict(n=int(v.size))
                    continue
                sd = float(v.std(ddof=1))
                mj = float(np.nanmedian(j))
                p = pub[int(mult) - 1] if (pub and lab == "M57") else None
                rat = (sd / p) if p else np.nan
                if p:
                    worst = max(worst, max(rat, 1.0 / rat))
                log(f"  {mult:6.1f} {lab:>5} {v.mean():+10.5f} {sd:10.5f}"
                    f" {(f'{p:9.5f}' if p else '        -')} "
                    f"{(f'{rat:7.3f}' if p else '      -')} {mj:8.5f}"
                    f" {sd/mj:8.2f} {v.size:5d}/{REPS}")
                cell["levels"][f"{lab}_{mult}"] = dict(
                    mean=float(v.mean()), sd=sd, jack=mj, n=int(v.size),
                    published=p, ratio=float(rat) if p else None,
                    sd_over_jack=float(sd / mj))
        out[key] = cell

    log("\n" + "=" * 78)
    log(f"RC bar: worst |sd / published| deviation factor = {worst:.3f}"
        f"   (bar is 2.000)  -> {'PASS' if worst < 2.0 else 'FAIL'}")
    log("=" * 78)
    with open(os.path.join(M92.OUT, "s4_reproduction.json"), "w") as fh:
        json.dump({"cells": out, "worst_factor": worst,
                   "passed": bool(worst < 2.0)}, fh, indent=2, default=float)
    with open(os.path.join(M92.OUT, "s4_reproduction.log"), "w",
              encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"\nwrote out/s4_reproduction.{{json,log}}  ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
