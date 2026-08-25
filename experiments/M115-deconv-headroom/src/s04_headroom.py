"""M115 s04 -- the headline.  Contrast and SNR against spatial frequency, per
arm, on real detail regions of real stacks, measured with the split-stack
channel validated in s03.

Reported per radial bin, all relative to the reference the brief names -- what a
perfect SELECTOR delivers:

    G_sig(f)   = sqrt(P_sig_arm  / P_sig_ref)     contrast gain
    G_noise(f) = sqrt(P_noise_arm/ P_noise_ref)   the price
    R_SNR(f)   = sqrt(SNR_arm    / SNR_ref)       the only quantity a
                                                  post-sharpening pass cannot
                                                  manufacture (control C3)

Two references are carried, because they answer two different questions:
  BEST1   the single globally sharpest frame -- the brief's literal wording,
          'contrast that NO single frame in the stack contains'
  FRAME*  per-tile election on the regularised field -- a PERFECT selector,
          which is strictly stronger than BEST1 and is the honest bar for
          'is a reconstruction merge worth building over what we ship'

Uncertainty: the ROI is divided into 4 non-overlapping quadrant crops per
stack, giving 8 spatial blocks across the two stacks.  Statistics are the mean
over blocks with the standard error of that mean -- not the spread of the
blocks, which is roughly sqrt(8) wider and is not a confidence interval on a
mean.
"""
import os, sys, json, time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m115lib as L
from s03_instrument import load_detail, banner

DF = 0.01
SUB = 256
STACKS = ["109MSDCF", "119MSDCF"]


def quadrants(img, sub=SUB):
    h, w = img.shape
    return [img[y:y + sub, x:x + sub]
            for y in (0, h - sub) for x in (0, w - sub)]


def run_stack(stack, log):
    banner(f"headroom -- {stack} detail ROI")
    cube, g, rn_e, B = load_detail(stack)
    crop = L.crop_fn(L.PAD, B)
    fine, coarse, reg = L.focus_fields(cube, g, rn_e)
    s0, fw_m, fw_mod = L.calibrate_s(cube, coarse)
    print(f"  {cube.shape[0]} frames, ROI {B}x{B}, level {cube.mean():.0f} DN, "
          f"self-calibrated s = {s0:.4f} quad px/frame")
    sp = L.split_channel(cube, g, rn_e, s0, crop)
    rb = L.RadialBins(SUB, DF)
    mid = rb.band_mask(*L.MIDBAND)

    # per-block statistics, so the mean has a standard error
    blocks = {}
    for a in L.ARMS:
        A, Bo = sp[a]
        qa, qb = quadrants(A), quadrants(Bo)
        st = [L.split_stats(rb, x, y) for x, y in zip(qa, qb)]
        blocks[a] = dict(Ps=np.array([s[0] for s in st]),
                         Pn=np.array([s[1] for s in st]))
    log.setdefault("blocks", {})[stack] = {
        a: dict(Ps=blocks[a]["Ps"].tolist(), Pn=blocks[a]["Pn"].tolist())
        for a in L.ARMS}
    log.setdefault("meta", {})[stack] = dict(
        n=int(cube.shape[0]), B=B, level=float(cube.mean()), s=s0,
        fwhm_meas=fw_m, fwhm_modelled=fw_mod, centres=rb.centres.tolist(),
        mid=[bool(x) for x in mid])
    return blocks, rb, mid


def main():
    t0 = time.time()
    log = {}
    allb = {}
    for st in STACKS:
        b, rb, mid = run_stack(st, log)
        allb[st] = b

    # pool the 8 blocks
    pool = {a: dict(Ps=np.concatenate([allb[s][a]["Ps"] for s in STACKS]),
                    Pn=np.concatenate([allb[s][a]["Pn"] for s in STACKS]))
            for a in L.ARMS}
    nb = pool["FRAME*"]["Ps"].shape[0]

    for ref in ["BEST1", "FRAME*"]:
        banner(f"R_SNR and its price, referenced to {ref}   ({nb} spatial blocks)")
        Rp = pool[ref]
        # per-block ratios, then mean +/- SE of the mean over blocks
        print(f"  {'f cyc/px':>9s} {'arm':11s} {'G_sig':>16s} {'G_noise':>16s} "
              f"{'R_SNR':>18s}")
        rows = {}
        fs = rb.centres[mid]
        for a in L.ARMS:
            if a == ref:
                continue
            gs = np.sqrt(np.maximum(pool[a]["Ps"], 0) / np.maximum(Rp["Ps"], 1e-30))
            gn = np.sqrt(np.maximum(pool[a]["Pn"], 0) / np.maximum(Rp["Pn"], 1e-30))
            rs = gs / np.maximum(gn, 1e-30)
            rows[a] = dict(
                f=fs.tolist(),
                gs=gs[:, mid].mean(0).tolist(), gs_se=(gs[:, mid].std(0, ddof=1) / np.sqrt(nb)).tolist(),
                gn=gn[:, mid].mean(0).tolist(), gn_se=(gn[:, mid].std(0, ddof=1) / np.sqrt(nb)).tolist(),
                rs=rs[:, mid].mean(0).tolist(), rs_se=(rs[:, mid].std(0, ddof=1) / np.sqrt(nb)).tolist())
        for i, f in enumerate(fs):
            for a in L.ARMS:
                if a == ref:
                    continue
                r = rows[a]
                print(f"  {f:9.3f} {a:11s} {r['gs'][i]:9.4f}+-{r['gs_se'][i]:5.4f} "
                      f"{r['gn'][i]:9.4f}+-{r['gn_se'][i]:5.4f} "
                      f"{r['rs'][i]:11.4f}+-{r['rs_se'][i]:5.4f}")
            print()
        log.setdefault("headline", {})[ref] = rows

    # decision rule, scored exactly as registered
    banner("registered decision rule")
    ref = "FRAME*"
    verdicts = {}
    for a in ["GATE", "MEAN", "MF", "WIENER", "WIENER_UNG"]:
        r = log["headline"][ref][a]
        v = np.array(r["rs"]); se = np.array(r["rs_se"])
        i = int(np.argmax(v))
        verdicts[a] = dict(max_rsnr=float(v[i]), se=float(se[i]),
                           at_f=float(r["f"][i]),
                           band_mean=float(np.mean(v)),
                           band_mean_se=float(np.mean(se) / np.sqrt(len(v))))
        tag = ("MEANINGFUL" if v[i] - 2 * se[i] >= 1.25 else
               "SMALL" if v[i] + 2 * se[i] < 1.15 else "AMBIGUOUS")
        print(f"  {a:11s} max mid-band R_SNR vs {ref} = {v[i]:.4f} +- {se[i]:.4f} "
              f"at f={r['f'][i]:.3f}   -> {tag}")
        verdicts[a]["verdict"] = tag
    pm70 = verdicts["MF"]["max_rsnr"] / max(verdicts["GATE"]["max_rsnr"], 1e-9)
    print(f"\n  prediction P-M70: max R_SNR(MF) / max R_SNR(GATE) = {pm70:.4f}   "
          f"registered interval [1.00, 1.25] -> "
          f"{'CONSISTENT' if 1.00 <= pm70 <= 1.25 else 'INCONSISTENT'}")
    log["decision"] = dict(verdicts=verdicts, p_m70=float(pm70))

    json.dump(log, open(os.path.join(L.OUT, "s04_headroom.json"), "w"), indent=2)
    print(f"\nelapsed {time.time()-t0:.1f}s -> s04_headroom.json")


if __name__ == "__main__":
    main()
