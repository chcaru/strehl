"""M113-spectral S3: per-window measurement for every stack, then all bars.

Persists per-window displacements so that the radial-sampling rival (ORCH's
rival 4) can be tested WITHOUT re-rendering: if eps(r) is flat within a stack,
then which radii the windows happen to occupy cannot move the fitted eps, and a
between-stack difference cannot be a sampling artefact. The same arrays give the
common-radial-band control, in which every stack is refitted using only windows
in 0.30 <= r/r_max <= 0.70, so all stacks are compared on the same annulus.
"""
import json, os, sys
import numpy as np

CA_SRC = r"C:\dev\blog\death-of-software\projects\strehl\experiments\M113-ca\src"
sys.path.insert(0, CA_SRC)
import c4_globalfit as c4g                       # noqa: E402
from c4_globalfit import cs, fit_eps, EPS_R      # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from s2_measure import paths, measure_ch, FOCUS  # noqa: E402

ROOT = r"C:\dev\strehl-out\M113-spectral"
NPZ = os.path.join(ROOT, "windows.npz")

def fit_band(m, cx, cy, hd, lo, hi):
    if len(m) == 0:
        return float("nan"), 0
    r = np.hypot(m[:, 0] - cx, m[:, 1] - cy) / hd
    s = (r >= lo) & (r <= hi)
    if s.sum() < 20:
        return float("nan"), int(s.sum())
    eps, tx, ty, n, rms = fit_eps(m[s], cx, cy)
    return eps, n

def collect():
    c4g.STEP = 100
    store = {}
    names = [n for n in FOCUS if all(os.path.exists(q) for q in paths(n))]
    names.sort(key=lambda n: FOCUS[n])
    for name in names:
        poff, pon = paths(name)
        off, W, H = cs.load_tiff_u16(poff)
        on, _, _ = cs.load_tiff_u16(pon)
        cx, cy = W / 2.0, H / 2.0
        ws = c4g.grid(off, W, H)
        for ch, cn in ((0, "R"), (2, "B")):
            for arm, img in (("off", off), ("on", on)):
                store["%s|%s|%s" % (name, cn, arm)] = measure_ch(img, ws, ch, cx, cy)
        store["%s|geom" % name] = np.array([W, H, cx, cy, float(np.hypot(cx, cy))])
        print("  measured %s (%d windows)" % (name, len(ws)), flush=True)
        del off, on
    np.savez_compressed(NPZ, **store)
    return store, names

def main():
    if os.path.exists(NPZ):
        z = np.load(NPZ); store = {k: z[k] for k in z.files}
        names = sorted({k.split("|")[0] for k in store if "|geom" in k}, key=lambda n: FOCUS[n])
        print("loaded cached per-window data for %d stacks" % len(names))
    else:
        store, names = collect()

    rows = {}
    for name in names:
        W, H, cx, cy, hd = store["%s|geom" % name]
        c = {"focus_m": FOCUS[name]}
        for cn in ("R", "B"):
            for arm in ("off", "on"):
                m = store["%s|%s|%s" % (name, cn, arm)]
                eps, tx, ty, n, rms = fit_eps(m, cx, cy)
                c["eps_%s_%s" % (cn, arm)] = eps
                c["n_%s_%s" % (cn, arm)] = n
            c["needed_%s" % cn] = -c["eps_%s_off" % cn]
            c["applied_%s" % cn] = c["eps_%s_on" % cn] - c["eps_%s_off" % cn]
        c["transfer"] = c["applied_R"] / (-EPS_R)
        c["ratio_BR"] = c["needed_B"] / c["needed_R"]
        band, nb = fit_band(store["%s|R|off" % name], cx, cy, hd, 0.30, 0.70)
        c["needed_R_band"] = -band; c["n_band"] = nb
        rows[name] = c

    with open(os.path.join(ROOT, "s2_measure.json")) as fh:
        col = json.load(fh)
    for n in rows:
        if n in col:
            rows[n]["RG"] = col[n]["RG"]; rows[n]["BG"] = col[n]["BG"]

    print("\n" + "=" * 122)
    print("%-28s %6s %9s %9s %9s %8s %9s %8s %7s" %
          ("stack", "focus", "needed_R", "needed_B", "ratioB/R", "transfer", "band0.3-0.7", "R/G", "B/G"))
    print("=" * 122)
    keep = []
    for n in names:
        c = rows[n]
        ok = 0.90 <= c["transfer"] <= 1.02
        if ok:
            keep.append(n)
        print("%-28s %6.4f %9.1f %9.1f %9.4f %8.4f %9.1f %8.4f %7.4f %s"
              % (n, c["focus_m"], c["needed_R"] * 1e6, c["needed_B"] * 1e6, c["ratio_BR"],
                 c["transfer"], c["needed_R_band"] * 1e6, c.get("RG", float("nan")),
                 c.get("BG", float("nan")), "" if ok else " <-- S0 FAIL, EXCLUDED"))
    print("=" * 122)
    print("S0: %d of %d stacks inside the [0.90, 1.02] transfer band" % (len(keep), len(names)))

    def nd(n):
        return rows[n]["needed_R"] * 1e6

    print("\n" + "-" * 78)
    print("S1 replicate bound (same subject, same focus distance)")
    if "bee-2-cpl" in rows and "bee-3-cpl" in rows:
        d = abs(nd("bee-2-cpl") - nd("bee-3-cpl"))
        print("  |bee-2 - bee-3| = %.1f ppm   bar 60 ppm -> %s" % (d, "PASS" if d <= 60 else "FAIL"))

    print("\n" + "-" * 78)
    print("S2 THE CRUX: bee-1 shares couch's focus distance and bee-3's subject")
    if "bee-1-cpl" in rows:
        beemean = np.mean([nd(n) for n in ("bee-2-cpl", "bee-3-cpl") if n in rows])
        db, dc = abs(nd("bee-1-cpl") - beemean), abs(nd("bee-1-cpl") - nd("couch-fibers-cpl"))
        print("  bee-1 = %.1f ppm ; bee mean = %.1f ; couch = %.1f" % (nd("bee-1-cpl"), beemean, nd("couch-fibers-cpl")))
        print("  |bee-1 - bee mean| = %.1f ppm ; |bee-1 - couch| = %.1f ppm" % (db, dc))
        if db <= 60 < dc:
            print("  -> tracks SUBJECT. Magnification REFUTED as the explanation.")
        elif dc <= 60 < db:
            print("  -> tracks FOCUS DISTANCE. Spectral REFUTED; magnification explains it.")
        else:
            print("  -> UNDETERMINED")

    print("\n" + "-" * 78)
    print("S3 constant-magnification group (all at focus 0.2841 m)")
    grp = [n for n in keep if abs(rows[n]["focus_m"] - 0.2841) < 1e-9]
    if len(grp) >= 2:
        v = [nd(n) for n in grp]
        print("  %s" % ", ".join("%s=%.1f" % (n, nd(n)) for n in grp))
        print("  range = %.1f ppm over %d stacks with magnification HELD FIXED" % (max(v) - min(v), len(grp)))
        print("  -> %s" % ("magnification alone explains it; SPECTRAL REFUTED" if max(v) - min(v) <= 60
                           else "a real scene-dependent effect survives at fixed magnification"))

    print("\n" + "-" * 78)
    print("S4 dispersion ratio needed_B/needed_R (a common scale factor cannot change it)")
    rr = np.array([rows[n]["ratio_BR"] for n in keep])
    vr = np.array([nd(n) for n in keep])
    cv = float(np.std(rr) / abs(np.mean(rr)))
    spread = float((vr.max() - vr.min()) / vr.mean())
    print("  ratio values: %s" % ", ".join("%.4f" % x for x in rr))
    print("  CV(ratio) = %.1f %% ; spread(needed_R) = %.1f %%" % (cv * 100, spread * 100))
    if cv < 0.10 and spread > 0.20:
        print("  -> COMMON SCALE. Not spectral.")
    else:
        print("  -> ratio is NOT invariant: no single multiplicative factor explains both channels.")
    print("  sign check: needed_R > 0 and needed_B < 0 means red under- and blue over-magnified")
    print("              relative to green, i.e. a monotone spread with wavelength.")

    print("\n" + "-" * 78)
    print("S6 rank correlation of needed_R against scene colour and against focus")
    try:
        from scipy.stats import spearmanr
        for lab, key in (("R/G", "RG"), ("B/G", "BG"), ("focus_m", "focus_m")):
            x = [rows[n][key] for n in keep if key in rows[n]]
            y = [nd(n) for n in keep if key in rows[n]]
            if len(x) >= 4:
                rho, pv = spearmanr(x, y)
                print("  needed_R vs %-8s : rho = %+.3f  p = %.4f  (n=%d)" % (lab, rho, pv, len(x)))
    except Exception as ex:
        print("  scipy unavailable: %s" % ex)

    print("\n" + "-" * 78)
    print("RIVAL 4 -- radial sampling. Full-field vs common band 0.30-0.70 r_max")
    for n in keep:
        c = rows[n]
        print("  %-28s full %8.1f   band %8.1f   delta %6.1f ppm (n=%d)"
              % (n, c["needed_R"] * 1e6, c["needed_R_band"] * 1e6,
                 (c["needed_R_band"] - c["needed_R"]) * 1e6, c["n_band"]))

    with open(os.path.join(ROOT, "s3_analyse.json"), "w") as fh:
        json.dump(rows, fh, indent=2)
    print("\nwrote s3_analyse.json")

if __name__ == "__main__":
    main()