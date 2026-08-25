"""M115 s02 -- validate the instrument BEFORE any headroom number is computed.

Rule 9: run the control FIRST, not as a closing check, because a metric that
fails it invalidates every number already computed with it.
Rule 20: for each control, the input that would make it FAIL is named, and such
an input exists.

  C5  external validation of the noise model      (rule 34: a plant that supplies
      its own constant cannot detect that constant being wrong)
  C4  noise-channel linearity                     (fails if the pipeline's
      weight sensitivity dominates the transfer)
  C3  GAIN INVARIANCE -- the control that decides whether "contrast gain" means
      anything at all.  Fails if the metric credits post-sharpening as signal.
  C1  the null: a REAL featureless capture through the same optics
  C2  planted known blur, monotone response and recovery ratio
  C7  sign convention, read off the estimator's own control
"""
import os, sys, json, glob, time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m115lib as L

FLAT_DIR = r"D:\personal\macro\flat-fields\flat-fields"
DF = 0.01
REPS = 3
SEED = 20260824


def banner(t):
    print("\n" + "=" * 78)
    print(t)
    print("=" * 78)


def spec_stats(rb, img, dlist):
    """P_O, P_noise, P_sig, SNR for one arm output and its noise-channel fields."""
    Po = rb.power(img)
    Pn = np.mean([rb.power(d) for d in dlist], axis=0)
    Ps = np.maximum(Po - Pn, 0.0)
    return Po, Pn, Ps, Ps / np.maximum(Pn, 1e-30)


# ------------------------------------------------------------------ C5
def c5_noise_model(log):
    banner("C5 -- external validation of the noise model (rule 34)")
    print("FAILS IF: the modelled sigma differs from a sigma measured on the data")
    print("by more than 15%.  Such an input exists -- M71 fact 1064 measured the")
    print("shipped model over-confident by up to -12.8% above S = 504 DN.\n")
    files = sorted(glob.glob(os.path.join(FLAT_DIR, "*.ARW")))
    iso = L.iso_of(files[0])
    g, rn_e = L.noise_params(iso)
    rows = []
    for a, b in [(0, 1), (2, 3), (4, 5), (6, 7), (8, 9)]:
        qa = L.quad_green_full(files[a])[1000:1000 + 384, 1600:1600 + 384]
        qb = L.quad_green_full(files[b])[1000:1000 + 384, 1600:1600 + 384]
        lvl = 0.5 * (qa.mean() + qb.mean())
        # a temporal sigma: two captures of ONE static scene, differenced.
        # rule 10: this is a TEMPORAL sigma and is compared only to the model.
        sig_meas = float((qa - qb).std() / np.sqrt(2.0))
        sig_model = float(np.sqrt(L.quad_var(lvl, g, rn_e)))
        rows.append((os.path.basename(files[a]), float(lvl), sig_meas, sig_model,
                     sig_meas / sig_model))
        print(f"  {os.path.basename(files[a])} vs {os.path.basename(files[b])}: "
              f"level {lvl:7.1f} DN   sigma_t measured {sig_meas:6.3f}   "
              f"model {sig_model:6.3f}   ratio {sig_meas/sig_model:6.4f}")
    r = np.array([x[4] for x in rows])
    ok = bool(np.all(np.abs(r - 1.0) <= 0.15))
    print(f"\n  C5: ratios {r.min():.4f}..{r.max():.4f}  -> {'PASS' if ok else 'FAIL'}")
    log["C5"] = dict(rows=rows, ratio_min=float(r.min()), ratio_max=float(r.max()),
                     passed=ok, iso=iso, g=g, rn_e=rn_e)
    return ok


# ------------------------------------------------------------- null cube
def null_cube(nframes, lo=0, log=None):
    """A REAL capture of a featureless scene through the same optics and sensor.
    M71 measured this corpus: PRNU kappa = 0.3096%, paper-fibre confound bounded
    at 0.09-0.14%.  At ~265 DN the PRNU term is ~0.8 DN against a modelled
    sigma of ~5.5, so the frames are featureless to within a few percent."""
    files = sorted(glob.glob(os.path.join(FLAT_DIR, "*.ARW")))[lo:lo + nframes]
    iso = L.iso_of(files[0])
    g, rn_e = L.noise_params(iso)
    B = 384
    cube = np.empty((len(files), B + 2 * L.PAD, B + 2 * L.PAD), np.float32)
    for i, f in enumerate(files):
        q = L.quad_green_full(f)
        cube[i] = q[1000 - L.PAD:1000 + B + L.PAD, 1600 - L.PAD:1600 + B + L.PAD]
    lvl = float(cube.mean())
    sd_s = float(cube[len(files) // 2].std())
    sig_t = float(np.sqrt(L.quad_var(lvl, g, rn_e)))
    print(f"  null cube: {len(files)} flat frames, ISO {iso}, level {lvl:.1f} DN, "
          f"sd_s {sd_s:.2f}, model sigma_t {sig_t:.2f}, sd_s/sigma_t = {sd_s/sig_t:.3f}")
    if log is not None:
        log["null_cube"] = dict(n=len(files), iso=iso, level=lvl, sd_s=sd_s,
                                sigma_t=sig_t, ratio=sd_s / sig_t,
                                first=os.path.basename(files[0]),
                                last=os.path.basename(files[-1]))
    return cube, g, rn_e, B


# ------------------------------------------------------------------ main
def main():
    t0 = time.time()
    log = {}
    ok5 = c5_noise_model(log)

    banner("C1 -- the null: every arm on a REAL featureless capture")
    print("FAILS IF: any arm reports mid-band signal power above the sampling")
    print("error of zero.  Such an input exists -- this cube contains no scene.\n")
    cube, g, rn_e, B = null_cube(24, 0, log)
    rb = L.RadialBins(B, DF)
    crop = L.crop_fn(L.PAD, B)
    fine, coarse, reg = L.focus_fields(cube, g, rn_e)
    s_null, fw_m, fw_mod = L.calibrate_s(cube, coarse)
    print(f"  self-calibrated s on the null cube = {s_null:.4f} quad px/frame "
          f"(FWHM measured {fw_m:.1f} frames, modelled {fw_mod:.1f})")
    arms = L.run_all_arms(cube, g, rn_e, s_null)
    dch = L.noise_channel(cube, g, rn_e, s_null, REPS, SEED, crop)
    mid = rb.band_mask(*L.MIDBAND)
    print(f"\n  {'arm':12s} {'P_sig/P_noise midband':>22s}  {'max SNR in band':>16s}   verdict")
    c1 = {}
    for a in L.ARMS:
        Po, Pn, Ps, snr = spec_stats(rb, crop(arms[a]), dch[a])
        v = float(np.mean(snr[mid]))
        mx = float(np.max(snr[mid]))
        c1[a] = dict(mean_snr_mid=v, max_snr_mid=mx,
                     Ps=Ps.tolist(), Pn=Pn.tolist(), Po=Po.tolist())
        print(f"  {a:12s} {v:22.4f}  {mx:16.4f}   "
              f"{'ok' if mx < 0.25 else 'READS SIGNAL WHERE THERE IS NONE'}")
    okc1 = bool(all(c1[a]["max_snr_mid"] < 0.25 for a in L.ARMS))
    print(f"\n  C1: {'PASS' if okc1 else 'FAIL'}  (bar: max mid-band SNR < 0.25 on a scene-free capture)")
    log["C1"] = dict(arms=c1, passed=okc1, bar=0.25,
                     centres=rb.centres.tolist(), s=s_null)

    json.dump(log, open(os.path.join(L.OUT, "s02_controls_a.json"), "w"), indent=2)
    print(f"\nelapsed {time.time()-t0:.1f}s -> s02_controls_a.json")
    print(f"\nSUMMARY  C5 {'PASS' if ok5 else 'FAIL'}   C1 {'PASS' if okc1 else 'FAIL'}")


if __name__ == "__main__":
    main()
