"""M92 S1 -- build and cache the half-merge cells.

Decodes each stack ONCE and scatters every frame to every ROI, instead of
M57's one-decode-per-frame-per-ROI.  The loader is the only new I/O in this
milestone and it is asserted equal to `m57lib.load_cube` on one ROI before any
cell is written.

Emits, per stack:
  out/cache/cells_<stack>_<grid>.npz    half-merges at gate 0.50 and 0.99
  out/cache/cells_<stack>_m57.npz       M57 S7's own three cells (RC control)

Nothing here computes dsig.  Nothing here is a result.
"""
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m92lib as M92  # noqa: E402
import m57lib as K    # noqa: E402


def loader_control(files, xy, g):
    """Rule 20 -- the new loader must be able to disagree with M57's.

    Builds one ROI both ways and requires bit-equality of the resulting
    half-merges.  A loader that silently transposed, mis-strided the CFA quad
    or dropped the black level would fail here.
    """
    x, y = xy
    ref = K.load_cube(files, (x, y, M92.ROI_N, M92.ROI_N), pad=M92.PAD)
    plane0 = M92.quad_plane(files[0])
    mine = np.empty_like(ref)
    for i, f in enumerate(files):
        p = M92.quad_plane(f) if i else plane0
        mine[i] = p[y - M92.PAD:y + M92.ROI_N + M92.PAD,
                    x - M92.PAD:x + M92.ROI_N + M92.PAD]
    dmax = float(np.abs(ref - mine).max())
    fine, coarse, reg = K.L1.focus_fields(ref, g, M92.RN_E_FOCUS)
    ia, ib = K.splits(len(files))["parity"]
    ra, _ = K.merge_subset(ref, coarse, reg, ia, pad=M92.PAD)
    f2, c2, r2 = K.L1.focus_fields(mine, g, M92.RN_E_FOCUS)
    ma, _ = K.merge_subset(mine, c2, r2, ia, pad=M92.PAD)
    return dmax, float(np.abs(ra - ma).max())


def main():
    t0 = time.time()
    meta = {}
    print("=" * 78)
    print("M92 S1 -- build half-merge cells.  PREREGISTRATION sections 1, 3, 8.")
    print("=" * 78)

    for kind in ("disjoint", "overlap"):
        co = M92.grid(kind)
        dj = M92.footprints_disjoint(co)
        print(f"grid {kind:9s}: {len(co)} ROIs, padded footprints disjoint = {dj}")
        assert (kind == "disjoint") == dj, "grid geometry is not what was registered"

    for name, cfg in M92.STACKS.items():
        files = M92.stack_files(name)
        iso = cfg["iso"]
        g = K.gain_dn_per_e(iso)
        print("\n" + "=" * 78)
        print(f"{name}: {len(files)} frames, EXIF ISO {iso}, g = {g:.5f} DN/e-, "
              f"read noise {K.read_noise_e(iso):.4f} e-")

        if name == "112MSDCF":
            t = time.time()
            dm, dmerge = loader_control(files[:12], (1184, 608), g)
            print(f"  LOADER CONTROL vs m57lib.load_cube: max |cube diff| = "
                  f"{dm:.3e} DN, max |half-merge diff| = {dmerge:.3e} DN "
                  f"({time.time()-t:.0f}s)")
            assert dm == 0.0 and dmerge == 0.0, "loader differs from m57lib"

        t = time.time()
        cube = M92.load_full(files, progress=lambda i, n: print(
            f"    decoded {i}/{n} ({time.time()-t:.0f}s)", flush=True))
        print(f"  decoded {len(files)} frames in {time.time()-t:.0f}s, "
              f"plane {cube.shape[1:]}, {cube.nbytes/1e9:.2f} GB")

        smeta = dict(iso=iso, g=g, n_frames=len(files), plane=list(cube.shape[1:]))
        for kind in ("disjoint", "overlap"):
            co = M92.grid(kind)
            store, rows = {}, []
            t = time.time()
            for k, xy in enumerate(co):
                c = M92.cell_from_cube(cube, xy, g)
                for gt in (M92.GATE_SHIPPED, M92.GATE_SELECTOR):
                    tag = f"{k:02d}_{gt:.2f}"
                    store[tag + "_a"] = c[gt]["ma"]
                    store[tag + "_b"] = c[gt]["mb"]
                ma = c[M92.GATE_SHIPPED]["ma"]
                lvl = float(np.median(ma))
                ne = c[M92.GATE_SHIPPED]["n_eff"]
                sm, s1 = M92.merged_sigma(lvl, iso, ne)
                rows.append(dict(k=k, x=xy[0], y=xy[1], level=lvl,
                                 n_eff=ne, n_eff_099=c[M92.GATE_SELECTOR]["n_eff"],
                                 sigma1=s1, sigma_merged=sm,
                                 hp_sd=float(K.L1.hp_sd(ma))))
            np.savez_compressed(os.path.join(M92.CACHE, f"cells_{name}_{kind}.npz"),
                                **store)
            smeta[kind] = rows
            print(f"  {kind:9s}: {len(co)} cells in {time.time()-t:.0f}s   "
                  f"n_eff(0.50) {min(r['n_eff'] for r in rows):.2f}-"
                  f"{max(r['n_eff'] for r in rows):.2f}   "
                  f"n_eff(0.99) {min(r['n_eff_099'] for r in rows):.2f}-"
                  f"{max(r['n_eff_099'] for r in rows):.2f}   "
                  f"hp_sd {min(r['hp_sd'] for r in rows):.3f}-"
                  f"{max(r['hp_sd'] for r in rows):.3f}")

        # ---- M57's own cells, at M57's own operator settings, for the RC ----
        cells = [c for c in M92.M57_CELLS if c[0] == name]
        if cells:
            store, rows = {}, []
            for k, (sn, rn, xy, lo, hi) in enumerate(cells):
                assert (lo, hi) == (cfg["lo"], cfg["hi"])
                # M57 s5/s6/s7 used G = 1.14469 (ISO 500) for EVERY stack.
                c = M92.cell_from_cube(cube, xy, 1.14469,
                                       gates=(M92.GATE_SHIPPED,))
                store[f"{k:02d}_a"] = c[M92.GATE_SHIPPED]["ma"]
                store[f"{k:02d}_b"] = c[M92.GATE_SHIPPED]["mb"]
                ma = c[M92.GATE_SHIPPED]["ma"]
                lvl = float(np.median(ma))
                ne = c[M92.GATE_SHIPPED]["n_eff"]
                sm500, s1500 = M92.merged_sigma(lvl, 500, ne)
                smtrue, s1true = M92.merged_sigma(lvl, iso, ne)
                rows.append(dict(k=k, cell=f"{sn}/{rn}", x=xy[0], y=xy[1],
                                 level=lvl, n_eff=ne,
                                 sigma1_iso500=s1500, sigma_merged_iso500=sm500,
                                 sigma1_isotrue=s1true, sigma_merged_isotrue=smtrue,
                                 iso_true=iso))
                print(f"  M57 cell {sn}/{rn} @ ({xy[0]},{xy[1]}): level "
                      f"{lvl:.1f} DN  n_eff {ne:.3f}  sigma_merged "
                      f"ISO500 {sm500:.4f} DN  ISO{iso} {smtrue:.4f} DN  "
                      f"ratio {sm500/smtrue:.4f}x")
            np.savez_compressed(os.path.join(M92.CACHE, f"cells_{name}_m57.npz"),
                                **store)
            smeta["m57"] = rows
        meta[name] = smeta
        del cube

    with open(os.path.join(M92.OUT, "s1_cells.json"), "w") as fh:
        json.dump(meta, fh, indent=2, default=float)
    print(f"\nwrote out/s1_cells.json  ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
