"""M5 — the primary measurement, and C2..C5.

Estimates the diffraction cutoff f_c from the radially averaged power spectrum
of a single-colour CFA sublattice, and from it the bellows factor

    (1 + m/p) = pitch / (lambda * f_c * N_marked)

Every stack yields an independent estimate of the same quantity. Their
agreement is the validation of the model.

Modes
-----
  exif    <dir>                 audit ISO / FNumber / focus across every frame
  measure <dir> --n <marked-N>  the measurement, with C3/C4/C5
  null    <dark-root>           C2: the same estimator on dark frames

Run `python m5_synthetic.py` (C1) before believing anything printed here.
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

import m5_lib as L

# ---------------------------------------------------------------------------
# ROI layout. Fixed geometric fractions of the active area, chosen before any
# spectrum was computed and identical for every stack and for the dark frames.
# Not selected on outcome. One centre ROI and four off-axis (C4).
# ---------------------------------------------------------------------------
ROI_FRACTIONS = [
    ("centre", 0.50, 0.50),
    ("upper-left", 0.30, 0.30),
    ("upper-right", 0.30, 0.70),
    ("lower-left", 0.70, 0.30),
    ("lower-right", 0.70, 0.70),
]
ROI_SIZE = 512  # lattice samples
TILE = 256
N_BEST = 5  # frames kept per ROI for the error bar


def set_geometry(roi_size=None, tile=None):
    global ROI_SIZE, TILE
    if roi_size:
        ROI_SIZE = roi_size
    if tile:
        TILE = tile


def roi_centres():
    out = []
    for name, fr, fc in ROI_FRACTIONS:
        rc = int(round(fr * L.ACTIVE_H)) & ~1
        cc = int(round(fc * L.ACTIVE_W)) & ~1
        out.append((name, rc, cc))
    return out


def frames(d):
    return sorted(
        os.path.join(d, f) for f in os.listdir(d) if f.lower().endswith(".arw")
    )


# ---------------------------------------------------------------------------
# EXIF audit — discovered, never assumed
# ---------------------------------------------------------------------------

EXIF_TAGS = ["ISO", "FNumber", "ExposureTime", "FocalLength", "LensModel",
             "LensSpec", "FocusPosition2", "FocusDistance2", "ImageStabilization",
             "SonyRawFileType", "Model"]


def exiftool_path():
    p = os.path.expandvars(
        r"%LOCALAPPDATA%\Programs\ExifTool\exiftool.exe")
    return p if os.path.exists(p) else "exiftool"


def exif_rows(d, limit=None):
    import subprocess

    fs = frames(d)
    if limit:
        fs = fs[:limit]
    cmd = [exiftool_path(), "-j", "-n"] + [f"-{t}" for t in EXIF_TAGS] + fs
    return json.loads(subprocess.run(cmd, capture_output=True, text=True).stdout)


def mode_exif(d):
    js = exif_rows(d)
    print(f"{d}  —  {len(js)} frames")
    for t in EXIF_TAGS:
        vals = sorted({str(r.get(t)) for r in js})
        if len(vals) == 1:
            print(f"   {t:22} {vals[0]}   (uniform over all {len(js)})")
        else:
            counts = {}
            for r in js:
                counts[str(r.get(t))] = counts.get(str(r.get(t)), 0) + 1
            pretty = ", ".join(f"{k}x{v}" for k, v in sorted(counts.items()))
            print(f"   {t:22} VARIES: {pretty}")


# ---------------------------------------------------------------------------
# Per-frame spectra
#
# Two selection policies, both reported:
#   "roi"   the prescribed method — one sharpest frame for the whole ROI.
#   "tile"  the sharpest frame chosen independently for each Welch tile.
#
# "tile" exists because a focus bracket has a depth of field of order 0.1 mm
# while a 512-sample ROI spans several mm of subject: in any single frame most
# of the ROI is defocused. Defocus cannot move the cutoff (the OTF support is
# set by the pupil; defocus only depresses MTF inside it), so a defocused
# mixture does not bias f_c upward — but it buries the signal near f_c and so
# biases the *detected* knee down. Choosing per tile recovers that SNR.
# Periodograms from different frames are averaged; pixel values never are.
# ---------------------------------------------------------------------------


def frame_spectra(path, lattices=L.LATTICES, windows=("hann",), sector="iso"):
    """All ROI x lattice x window radial spectra for one frame (policy "roi")."""
    a = L.load_active(path)
    out = {}
    for name, rc, cc in roi_centres():
        for lat in lattices:
            patch = L.crop_lattice(a, lat, rc, cc, ROI_SIZE)
            stats = {
                "mean": float(patch.mean()),
                "sd": float(patch.std()),
                "max_dn": float(patch.max()),
                "clipped": float(np.mean(patch >= L.WHITE_LEVEL - L.BLACK_LEVEL - 1)),
                "immerkaer": L.immerkaer_sigma(patch),
            }
            for win in windows:
                f, p, n = L.spectrum(patch, lat, tile=TILE, window=win, sector=sector)
                out[(name, lat, win)] = (f, p, n, stats)
    return out


class TileSelector:
    """Streams frames once, keeping the best-scoring tile periodogram per
    (ROI, lattice, tile position), plus a fixed-seed random-frame placebo."""

    def __init__(self, lattices, window, sector, seed=20260822):
        self.lattices, self.window, self.sector = lattices, window, sector
        self.rng = np.random.default_rng(seed)
        self.best = {}      # key -> (scores[ntiles], psd2[ntiles,t,t])
        self.placebo = {}   # key -> (u[ntiles],       psd2[ntiles,t,t])
        self.pick = {}      # key -> frame index chosen per tile
        self.stats = {}
        self.nframes = 0

    def add(self, path, frame_index):
        a = L.load_active(path)
        for name, rc, cc in roi_centres():
            for lat in self.lattices:
                patch = L.crop_lattice(a, lat, rc, cc, ROI_SIZE)
                ps = L.tile_psd2_stack(patch, TILE, self.window).astype(np.float32)
                sc = L.focus_score_2d(ps, L.band_masks(TILE, lat, self.sector))
                key = (name, lat)
                u = self.rng.random(len(sc))  # placebo lottery, drawn per frame
                if key not in self.best:
                    self.best[key] = [sc.copy(), ps.copy()]
                    self.placebo[key] = [u.copy(), ps.copy()]
                    self.pick[key] = np.full(len(sc), frame_index)
                    self.stats[key] = {
                        "mean": float(patch.mean()),
                        "clipped": float(np.mean(
                            patch >= L.WHITE_LEVEL - L.BLACK_LEVEL - 1)),
                        "immerkaer": L.immerkaer_sigma(patch),
                    }
                else:
                    bs, bp = self.best[key]
                    w = sc > bs
                    if w.any():
                        bp[w] = ps[w]
                        bs[w] = sc[w]
                        self.pick[key][w] = frame_index
                    pu, pp = self.placebo[key]
                    w2 = u > pu
                    if w2.any():
                        pp[w2] = ps[w2]
                        pu[w2] = u[w2]
        self.nframes += 1

    def spectrum(self, key, which="best"):
        src = self.best if which == "best" else self.placebo
        psd2 = src[key][1].mean(axis=0).astype(np.float64)
        return L.radial_psd(psd2, key[1], self.sector)

    def n_distinct(self, key):
        return len(np.unique(self.pick[key]))


# ---------------------------------------------------------------------------
# measure
# ---------------------------------------------------------------------------


def dark_reference(dark_dir, lattices, window, sector, max_frames=8):
    """Mean power spectrum of dark frames on the identical ROI/lattice/tiling
    geometry. Dark frames contain no optical signal but they are *not*
    spectrally white: they carry the row/column fixed-pattern noise M4
    measured. Subtracting this spectrum from a light frame's removes the FPN
    term (power spectra of independent components add) and leaves the optical
    signal plus a constant offset, so the knee is preserved."""
    fs = frames(dark_dir)[2:][:max_frames]  # skip stabilisation shots
    acc, cnt = {}, 0
    for path in fs:
        a = L.load_active(path)
        for name, rc, cc in roi_centres():
            for lat in lattices:
                patch = L.crop_lattice(a, lat, rc, cc, ROI_SIZE)
                f, p, n = L.spectrum(patch, lat, tile=TILE, window=window,
                                     sector=sector)
                key = (name, lat)
                if key not in acc:
                    acc[key] = [f, np.zeros_like(p), n, 0]
                acc[key][1] += p
                acc[key][3] += 1
        cnt += 1
    return {k: (v[0], v[1] / v[3], v[2]) for k, v in acc.items()}, len(fs)


CANDIDATES = {"B=2 (bare lens, p=1)": 2.0, "B=3 (brief, p=1)": 3.0,
              "B=5 (brief, p=0.5)": 5.0}


def mode_measure(d, n_marked, limit=None, sector="iso", windows=("hann",),
                 policies=("tile", "roi"), dark_dir=None):
    fs = frames(d)
    if limit:
        fs = fs[:limit]
    label = os.path.basename(os.path.normpath(d))
    print("=" * 110)
    print(f"MEASURE  {label}   marked f/{n_marked}   n={len(fs)} frames   "
          f"ROI {ROI_SIZE} lattice px   tile {TILE}   sector {sector}   "
          f"window {windows[0]}")
    print("=" * 110)
    print("Predicted cutoffs (sensor cyc/px) at lambda=550 nm:")
    for nm, B in CANDIDATES.items():
        fc = L.f_cutoff_sensor(n_marked * B)
        print(f"   {nm:<22} N_eff {n_marked*B:6.1f}   f_c {fc:.4f}   "
              f"({L.sensor_cyc_px_to_cyc_mm(fc):6.1f} cyc/mm)")
    print("Lattice reach (sensor cyc/px): " + "  ".join(
        f"{lat} {L.lattice_nyquist_sensor(lat):.4f}" for lat in L.LATTICES))

    t0 = time.time()
    sel = TileSelector(L.LATTICES, windows[0], sector)
    per_frame = [] if "roi" in policies else None
    for i, f in enumerate(fs):
        if "tile" in policies:
            sel.add(f, i)
        if per_frame is not None:
            per_frame.append(frame_spectra(f, windows=windows, sector=sector))
        if (i + 1) % 10 == 0 or i + 1 == len(fs):
            print(f"   ... {i+1}/{len(fs)} frames  ({time.time()-t0:.0f} s)")
    print()

    rois = [nm for nm, _, _ in roi_centres()]
    iso = _stack_iso(d)
    out = {"label": label, "n_marked": n_marked, "n_frames": len(fs),
           "sector": sector, "tile": TILE, "roi_size": ROI_SIZE, "iso": iso,
           "rows": []}

    # ---- primary table -------------------------------------------------
    print("--- PRIMARY: highest frequency carrying signal above the noise "
          "floor, and the bound it puts on B = (1+m/p) ---")
    print("    f_sig is a LOWER bound on f_c (C1: the crossing rule runs "
          "5-23% low), so B_max is an UPPER bound on B.")
    print(f"{'ROI':>12} {'lat':>4} {'pol':>7} {'reach':>6} {'dyn':>9} "
          f"{'kappa':>6} | {'f_sig':>7} {'B_max':>7} {'atReach':>8} | "
          f"{'fit f_c':>8} {'B_fit':>6} {'resid':>6} {'oob':>5} | "
          f"{'floorSD':>7} {'nfrm':>5}")
    for name in rois:
        for lat in L.LATTICES:
            for pol in policies:
                if pol == "tile":
                    f, p, n = sel.spectrum((name, lat), "best")
                    st = sel.stats[(name, lat)]
                    nfrm = sel.n_distinct((name, lat))
                else:
                    key = (name, lat, windows[0])
                    scores = [L.focus_score(*pf[key][:2]) for pf in per_frame]
                    bi = int(np.argmax(scores))
                    f, p, n, st = per_frame[bi][key]
                    nfrm = 1
                k = L.knee(f, p, n, TILE, ROI_SIZE, lat, windows[0], sector)
                m = L.knee_model_fit(f, p, n)
                reach = float(f[-1])
                at_reach = k["f_c"] is not None and k["f_c"] >= 0.97 * reach
                bmax = L.bellows_from_fc(k["f_c"], n_marked) if k["f_c"] else None
                bfit = (L.bellows_from_fc(m["f_c"], n_marked)
                        if m.get("f_c") and not m.get("above_reach") else None)
                sd_model = float(np.sqrt(L.noise_model_var(st["mean"], iso)["var"]))
                fr = float(np.sqrt(max(k["floor"], 0.0)) / sd_model)
                out["rows"].append({
                    "roi": name, "lat": lat, "policy": pol, "reach": reach,
                    "f_sig": k["f_c"], "b_max": bmax, "at_reach": at_reach,
                    "dyn": k["dynamic_range"], "kappa": k["kappa"],
                    "floor": k["floor"], "fit_fc": m.get("f_c"), "b_fit": bfit,
                    "resid": m.get("resid_rms"), "oob": bool(m.get("above_reach")),
                    "mean_dn": st["mean"], "immerkaer": st["immerkaer"],
                    "clipped": st["clipped"], "n_frames_used": nfrm,
                    "sd_model": sd_model, "floor_ratio_model": fr,
                })
                print(f"{name:>12} {lat:>4} {pol:>7} {reach:6.3f} "
                      f"{k['dynamic_range']:9.1f} {k['kappa']:6.3f} | "
                      f"{_f(k['f_c'])} {_f(bmax,7,3)} {str(at_reach):>8} | "
                      f"{_f(m.get('f_c'),8,4)} {_f(bfit,6,2)} "
                      f"{_f(m.get('resid_rms'),6,3)} "
                      f"{str(bool(m.get('above_reach'))):>5} | "
                      f"{np.sqrt(max(k['floor'],0)):7.2f} {nfrm:5d}")

    # ---- falsification of the candidates -------------------------------
    print("\n--- FALSIFICATION: two independent tests, both one-sided ---")
    print("    (a) signal ABOVE a candidate's predicted cutoff refutes it "
          "(there is no signal above f_c).")
    print("    (b) if a candidate predicts f_c above the lattice reach, then "
          "the top of the band must still")
    print("        carry optical signal. A floor that matches the "
          "photon-transfer model to better than")
    print("        FLOOR_CLEAN refutes it instead. Both directions use only "
          "measured quantities.")
    FLOOR_CLEAN = 1.15
    print(f"{'candidate':>22} {'f_c pred':>9} | " + " ".join(
        f"{lat:>18}" for lat in L.LATTICES))
    rows_tile = [r for r in out["rows"] if r["policy"] == policies[0]]
    for nm, B in CANDIDATES.items():
        fc_pred = L.f_cutoff_sensor(n_marked * B)
        cells = []
        for lat in L.LATTICES:
            rs = [r for r in rows_tile if r["lat"] == lat]
            gated = [r for r in rs if r["dyn"] >= L.DYN_GATE and r["f_sig"]]
            if not rs:
                cells.append(f"{'no data':>18}")
                continue
            reach = rs[0]["reach"]
            if fc_pred > reach:
                clean = [r for r in rs if r["floor_ratio_model"] < FLOOR_CLEAN]
                if clean:
                    cells.append(f"{'REFUTED(b) '+str(len(clean))+'/'+str(len(rs)):>18}")
                else:
                    cells.append(f"{'unreachable':>18}")
            else:
                over = [r for r in gated if r["f_sig"] > fc_pred]
                if over:
                    cells.append(f"{'REFUTED(a) '+str(len(over))+'/'+str(len(gated)):>18}")
                else:
                    cells.append(f"{'survives':>18}")
        print(f"{nm:>22} {fc_pred:9.4f} | " + " ".join(cells))

    # ---- placebo -------------------------------------------------------
    if "tile" in policies:
        print("\n--- Placebo: identical pipeline, tiles chosen by a fixed-seed "
              "lottery instead of by focus. Selecting on noise would show up "
              "here as an inflated floor or a knee. ---")
        print(f"{'ROI':>12} {'lat':>4} | {'best f_sig':>10} {'plac f_sig':>10} "
              f"| {'best floorSD':>12} {'plac floorSD':>12} | {'best dyn':>9} "
              f"{'plac dyn':>9}")
        for name in rois:
            for lat in L.LATTICES:
                f, p, n = sel.spectrum((name, lat), "best")
                kb = L.knee(f, p, n, TILE, ROI_SIZE, lat, windows[0], sector)
                f2, p2, n2 = sel.spectrum((name, lat), "placebo")
                kp = L.knee(f2, p2, n2, TILE, ROI_SIZE, lat, windows[0], sector)
                print(f"{name:>12} {lat:>4} | {_f(kb['f_c'],10,4)} "
                      f"{_f(kp['f_c'],10,4)} | "
                      f"{np.sqrt(max(kb['floor'],0)):12.2f} "
                      f"{np.sqrt(max(kp['floor'],0)):12.2f} | "
                      f"{kb['dynamic_range']:9.1f} {kp['dynamic_range']:9.1f}")

    # ---- C5 sublattice replicate ---------------------------------------
    print("\n--- C5: green sublattice replicate. G1 and G2 are disjoint sets "
          "of photosites sampling the same optics. ---")
    for pol in policies:
        for name in rois:
            a = _row(out, name, "G1", pol)
            b = _row(out, name, "G2", pol)
            if a and b and a["f_sig"] and b["f_sig"]:
                print(f"{name:>12} {pol:>7}  G1 {a['f_sig']:.4f}  "
                      f"G2 {b['f_sig']:.4f}  difference "
                      f"{100*(b['f_sig']/a['f_sig']-1):+6.2f}%   "
                      f"floorSD {np.sqrt(a['floor']):.2f} / "
                      f"{np.sqrt(b['floor']):.2f}")

    # ---- C4 ROI independence -------------------------------------------
    print("\n--- C4: ROI independence. Diffraction is near field-invariant; a "
          "strong field trend would mean aberration or an ROI artifact. ---")
    for pol in policies:
        for lat in L.LATTICES:
            v = [r["f_sig"] for r in out["rows"]
                 if r["lat"] == lat and r["policy"] == pol and r["f_sig"]]
            nr = [r for r in out["rows"]
                  if r["lat"] == lat and r["policy"] == pol and r["at_reach"]]
            if len(v) >= 2:
                v = np.array(v)
                bm = np.array([L.bellows_from_fc(x, n_marked) for x in v])
                print(f"   {lat} {pol:>7}: n={len(v)}  f_sig median "
                      f"{np.median(v):.4f}  min {v.min():.4f}  max {v.max():.4f}"
                      f"  (cv {100*v.std()/v.mean():4.1f}%)   B_max median "
                      f"{np.median(bm):.3f} [{bm.min():.3f}, {bm.max():.3f}]"
                      f"   at-reach {len(nr)}/{len(v)}")

    # ---- C2b: FPN contamination of the knee -----------------------------
    if dark_dir:
        print(f"\n--- C2b: FPN contamination. C2 showed the raw rule fires on "
              f"34% of dark cases, because darks are\n    not spectrally white "
              f"— they carry M4's row/column FPN. Here the matched-ISO dark "
              f"spectrum is\n    measured on the identical geometry and "
              f"subtracted, and f_sig recomputed. dark: {dark_dir} ---")
        dref, ndark = dark_reference(dark_dir, L.LATTICES, windows[0], sector)
        print(f"    {ndark} dark frames averaged.")
        bands = ((0.10, 0.15), (0.15, 0.20), (0.20, 0.25), (0.25, 0.35))
        hdr = " ".join(f"{f'{lo:.2f}-{hi:.2f}':>11}" for lo, hi in bands)
        print(f"{'ROI':>12} {'lat':>4} {'source':>7} | {hdr}  (median p/floor - 1)")
        for name in rois:
            for lat in L.LATTICES:
                f, p, n = sel.spectrum((name, lat), "best")
                k = L.knee(f, p, n, TILE, ROI_SIZE, lat, windows[0], sector)
                fe = L.band_excess(f, p, k["floor"], bands)
                fd, pd, nd = dref[(name, lat)]
                kd = L.knee(fd, pd, nd, TILE, ROI_SIZE, lat, windows[0], sector)
                de = L.band_excess(fd, pd, kd["floor"], bands)
                print(f"{name:>12} {lat:>4} {'light':>7} | " +
                      " ".join(f"{x:11.4f}" for x in fe))
                print(f"{'':>12} {'':>4} {'dark':>7} | " +
                      " ".join(f"{x:11.4f}" for x in de))
                # subtract the dark power spectrum and re-run the estimator
                psub = p - (pd - kd["floor"])
                ks = L.knee(f, psub, n, TILE, ROI_SIZE, lat, windows[0], sector)
                r = _row(out, name, lat, "tile")
                if r is not None:
                    r["f_sig_fpn_sub"] = ks["f_c"]
                delta = (100 * (ks["f_c"] / k["f_c"] - 1)
                         if (ks["f_c"] and k["f_c"]) else float("nan"))
                print(f"{'':>12} {'':>4} {'sub':>7} | f_sig {_f(k['f_c'])} -> "
                      f"{_f(ks['f_c'])}  ({delta:+.2f}%)   B_max "
                      f"{_f(L.bellows_from_fc(k['f_c'], n_marked) if k['f_c'] else None,6,3)}"
                      f" -> "
                      f"{_f(L.bellows_from_fc(ks['f_c'], n_marked) if ks['f_c'] else None,6,3)}")

    # ---- H4 noise cross-check ------------------------------------------
    print("\n--- H4: the high-frequency floor is a structure-free noise "
          "estimate. Compared against the project photon-transfer model. ---")
    iso = _stack_iso(d)
    print(f"{'ROI':>12} {'lat':>4} {'pol':>7} {'mean DN':>8} {'floorSD':>8} "
          f"{'model SD':>9} {'ratio':>6} {'Immerkaer':>10} {'ratio':>6}")
    for r in out["rows"]:
        mod = L.noise_model_var(r["mean_dn"], iso)
        sd_model = np.sqrt(mod["var"])
        sd_floor = np.sqrt(max(r["floor"], 0))
        r["sd_floor"] = sd_floor
        r["sd_model"] = sd_model
        print(f"{r['roi']:>12} {r['lat']:>4} {r['policy']:>7} "
              f"{r['mean_dn']:8.1f} {sd_floor:8.2f} {sd_model:9.2f} "
              f"{sd_floor/sd_model:6.3f} {r['immerkaer']:10.2f} "
              f"{r['immerkaer']/sd_model:6.3f}")

    # ---- SUMMARY --------------------------------------------------------
    print("\n" + "=" * 110)
    print(f"SUMMARY  {label}  f/{n_marked}  ISO {iso}  n={len(fs)} frames "
          f"(n=1 stack, n=1 camera, n=1 subject)")
    print("=" * 110)
    tiles = [r for r in out["rows"] if r["policy"] == "tile"]
    clean = [r for r in tiles if r["floor_ratio_model"] < 1.15
             and r["dyn"] >= L.DYN_GATE and r["f_sig"]]
    dirty = [r for r in tiles if r["floor_ratio_model"] >= 1.15]
    print(f"cases with a floor consistent with the photon-transfer model "
          f"(<1.15x): {len(clean)} of {len(tiles)}")
    if dirty:
        fr = [r["floor_ratio_model"] for r in dirty]
        print(f"cases with an inflated floor (no reachable noise floor, so the "
              f"knee is NOT a cutoff): {len(dirty)}, "
              f"ratio {min(fr):.2f}-{max(fr):.2f}x")
    if clean:
        best = min(clean, key=lambda r: r["b_max"])
        print(f"\nTIGHTEST VALID BOUND")
        print(f"   {best['roi']} / {best['lat']} / tile   dyn {best['dyn']:.0f}"
              f"   floor {best['floor_ratio_model']:.3f}x model")
        print(f"   f_sig  = {best['f_sig']:.4f} sensor cyc/px = "
              f"{L.sensor_cyc_px_to_cyc_mm(best['f_sig']):.1f} cyc/mm")
        print(f"   f_c   >= f_sig  (C1: crossing biased -8%; C1b on real "
              f"texture -14 to -40%)")
        print(f"   B     <= {best['b_max']:.3f}")
        for nm, B in CANDIDATES.items():
            verdict = "CONSISTENT" if B <= best["b_max"] + 1e-9 else "REFUTED"
            print(f"      {nm:<22} {verdict:>10}")
        reach = max(r["reach"] for r in clean)
        print(f"\n   Reverse bound: the floor matches the noise model at the "
              f"top of the band, so no signal is\n   detectable at the reach "
              f"{reach:.4f}. Taking f_c <~ reach gives "
              f"B >~ {L.bellows_from_fc(reach, n_marked):.3f}.")
    else:
        print("\nNO VALID BOUND from a detected knee at this aperture.")
    if dirty:
        reach = max(r["reach"] for r in dirty)
        print(f"\n   Out-of-band bound: power at the reach {reach:.4f} exceeds "
              f"the photon-transfer noise model on\n   {len(dirty)} case(s), so "
              f"f_c > {reach:.4f} and B < "
              f"{L.bellows_from_fc(reach, n_marked):.3f}. This uses no knee "
              f"detection at all.")

    print(f"\nCONSEQUENCES at B=3.0:")
    neff = n_marked * 3.0
    fc = L.f_cutoff_sensor(neff)
    print(f"   N_marked f/{n_marked} -> N_eff f/{neff:.1f};  f_c {fc:.4f} "
          f"sensor cyc/px = {L.sensor_cyc_px_to_cyc_mm(fc):.1f} cyc/mm")
    print(f"   Airy FWHM {L.airy_fwhm_um(neff):.2f} um = "
          f"{L.airy_fwhm_um(neff)/L.PITCH_UM:.2f} sensor px;  Nyquist "
          f"bandwidth used {min(fc/0.5, 1.0)*100:.1f}% "
          f"(area {min(fc/0.5,1.0)**2*100:.1f}%)")
    return out


def _row(out, roi, lat, pol):
    for r in out["rows"]:
        if r["roi"] == roi and r["lat"] == lat and r["policy"] == pol:
            return r
    return None


def _stack_iso(d):
    try:
        rows = exif_rows(d, limit=1)
        return int(float(rows[0].get("ISO", 100)))
    except Exception:
        return 100


def _f(x, w=7, d=4):
    return " " * w if x is None else f"{x:{w}.{d}f}"


# ---------------------------------------------------------------------------
# Spectrum dump — look at the shape rather than trusting a fitted number
# ---------------------------------------------------------------------------


def mode_dump(d, roi_name, lat, limit=None, window="hann", sector="iso"):
    fs = frames(d)
    if limit:
        fs = fs[:limit]
    rc, cc = [(r, c) for nm, r, c in roi_centres() if nm == roi_name][0]
    specs = []
    for path in fs:
        a = L.load_active(path)
        patch = L.crop_lattice(a, lat, rc, cc, ROI_SIZE)
        f, p, n = L.spectrum(patch, lat, tile=TILE, window=window, sector=sector)
        specs.append((f, p, n, L.focus_score(f, p), path, patch.mean()))
    best = int(np.argmax([s[3] for s in specs]))
    f, p, n, sc, path, mean = specs[best]
    print(f"{d}  ROI {roi_name} ({rc},{cc})  lattice {lat}  window {window}  "
          f"sector {sector}  ROI {ROI_SIZE} tile {TILE}")
    print(f"sharpest of {len(fs)}: index {best}  {os.path.basename(path)}  "
          f"mean {mean:.1f} DN")
    k = L.knee(f, p, n, TILE, ROI_SIZE, lat, window, sector)
    m = L.knee_model_fit(f, p, n)
    m2 = L.knee_model_fit(f, p, n, curvature=True)
    print(f"crossing f_c={_f(k['f_c'])}  floor sd={np.sqrt(max(k['floor'],0)):.2f} DN  "
          f"dyn={k['dynamic_range']:.1f}  kappa={k['kappa']:.3f}  "
          f"has_signal={k['has_signal']}")
    print(f"fit      f_c={_f(m.get('f_c'))}  alpha={_f(m.get('alpha'),6,2)}  "
          f"floor sd={np.sqrt(max(m.get('floor',0),0)):.2f}  "
          f"resid={m.get('resid_rms',float('nan')):.4f}  oob={m.get('above_reach')}")
    print(f"fit+curv f_c={_f(m2.get('f_c'))}  "
          f"resid={m2.get('resid_rms',float('nan')):.4f}")
    print(f"\n{'f(cyc/px)':>10} {'f(cyc/mm)':>10} {'power':>14} {'p/floor':>9} "
          f"{'nsamp':>7} {'log-slope':>10}")
    lp, lf = np.log(p), np.log(f)
    for i in range(len(f)):
        sl = ((lp[i + 1] - lp[i - 1]) / (lf[i + 1] - lf[i - 1])
              if 0 < i < len(f) - 1 else float("nan"))
        if i % max(1, len(f) // 40) == 0 or i >= len(f) - 5:
            print(f"{f[i]:10.4f} {L.sensor_cyc_px_to_cyc_mm(f[i]):10.2f} "
                  f"{p[i]:14.4f} {p[i]/max(k['floor'],1e-9):9.3f} {int(n[i]):7d} "
                  f"{sl:10.2f}")


# ---------------------------------------------------------------------------
# C2 — null control on dark frames
# ---------------------------------------------------------------------------


def mode_null(root, folders=None, sector="iso", window="hann"):
    print("=" * 110)
    print("C2  NULL CONTROL — the identical estimator on dark frames")
    print("=" * 110)
    print("Dark frames carry no optical signal, so there is no cutoff to find. "
          "The estimator\nmust report 'no signal' rather than a plausible-looking "
          "cutoff. Both selection\npolicies are exercised, because a "
          "selection-on-noise artifact would show up only\nin the 'tile' policy. "
          "First 2 frames of each folder discarded as stabilisation\nshots, "
          "following M4.\n")
    subs = folders or sorted(
        f for f in os.listdir(root) if os.path.isdir(os.path.join(root, f))
    )
    print(f"{'folder':>10} {'n':>3} {'ISO':>5} {'ROI':>12} {'lat':>4} {'pol':>5} "
          f"{'dyn':>7} {'kappa':>6} {'has_sig':>8} {'f_sig':>7} {'B_max':>7} "
          f"{'floorSD':>8} {'immerk':>7} {'mean':>7}")
    invented, total = 0, 0
    detail = []
    for sub in subs:
        d = os.path.join(root, sub)
        fs = frames(d)[2:]  # discard stabilisation shots
        if not fs:
            continue
        try:
            iso = int(float(exif_rows(d, limit=3)[-1].get("ISO", 0)))
        except Exception:
            iso = 0
        sel = TileSelector(("G1", "G2", "GQ"), window, sector)
        for i, f in enumerate(fs):
            sel.add(f, i)
        roi_specs = frame_spectra(fs[0], windows=(window,), sector=sector)
        for name, _, _ in roi_centres():
            for lat in L.LATTICES:
                for pol in ("tile", "roi"):
                    if pol == "tile":
                        f, p, n = sel.spectrum((name, lat), "best")
                        st = sel.stats[(name, lat)]
                    else:
                        f, p, n, st = roi_specs[(name, lat, window)]
                    k = L.knee(f, p, n, TILE, ROI_SIZE, lat, window, sector)
                    total += 1
                    if k["has_signal"] and k["f_c"]:
                        invented += 1
                    b = L.bellows_from_fc(k["f_c"], 11.0) if k["f_c"] else None
                    detail.append((sub, name, lat, pol, k))
                    print(f"{sub:>10} {len(fs):3d} {iso:5d} {name:>12} {lat:>4} "
                          f"{pol:>5} {k['dynamic_range']:7.2f} {k['kappa']:6.3f} "
                          f"{str(k['has_signal']):>8} {_f(k['f_c'])} "
                          f"{_f(b, 7, 2)} {np.sqrt(max(k['floor'],0)):8.3f} "
                          f"{st['immerkaer']:7.3f} {st['mean']:7.2f}")
    fired = sum(1 for *_, k in detail if k["f_c"] is not None)
    print(f"\nC2 VERDICT")
    print(f"   cases                                    {total}")
    print(f"   raw detections (any f_sig at all)        {fired} "
          f"({100*fired/max(total,1):.1f}%)")
    print(f"   detections that also passed the dynamic- {invented} "
          f"({100*invented/max(total,1):.1f}%)")
    print(f"   range gate, i.e. a claimed cutoff")
    print("   The estimator must claim ~0 cutoffs here. Any raw detection that "
          "the dynamic-range\n   gate catches is a near miss and is reported "
          "rather than hidden.")
    return {"total": total, "fired": fired, "invented": invented}


# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        raise SystemExit(2)
    mode, target = sys.argv[1], sys.argv[2]
    args = sys.argv[3:]

    def opt(flag, default=None, cast=str):
        return cast(args[args.index(flag) + 1]) if flag in args else default

    if mode == "exif":
        mode_exif(target)
    elif mode == "measure":
        set_geometry(opt("--roi", None, int), opt("--tile", None, int))
        sector = opt("--sector", "iso")
        wins = tuple(opt("--windows", "hann").split(","))
        mode_measure(target, opt("--n", 8.0, float), opt("--limit", None, int),
                     sector=sector, windows=wins, dark_dir=opt("--dark", None))
    elif mode == "dump":
        set_geometry(opt("--roi", None, int), opt("--tile", None, int))
        mode_dump(target, opt("--at", "centre"), opt("--lattice", "G1"),
                  opt("--limit", None, int), opt("--window", "hann"),
                  opt("--sector", "iso"))
    elif mode == "null":
        set_geometry(opt("--roi", None, int), opt("--tile", None, int))
        mode_null(target, opt("--folders", None, lambda s: s.split(",")))
    else:
        print(__doc__)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
