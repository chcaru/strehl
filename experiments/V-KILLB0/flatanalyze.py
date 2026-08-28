"""V-KILLB0 flat-site qualification analyzer. Decision rule imported, not rewritten."""
import os, sys
import numpy as np
_E = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(_E, "V-LINEAR2")); sys.path.insert(0, os.path.join(_E, "V-HEADTOHEAD2"))
import bandsignal as BS
ALLB = BS.FINE


def pfpd(power, selp, far, order=None):
    n, nt, nb = power.shape
    pf, pd, selr, keep = [], [], [], []
    for i in range(nt):
        s = selp[:, i] if order is None else selp[order[:, i], i]
        p = power[:, i, :] if order is None else power[order[:, i], i, :]
        b = int(np.nanargmax(s))
        if b < far // 4 + 1 or b > n - far // 4 - 2:
            continue
        ref = [r for r in (b - far, b + far) if 0 <= r < n]
        if not ref:
            continue
        keep.append(i); pf.append(p[b]); pd.append(p[ref].mean(0))
        selr.append(s[b] / s[ref].mean())
    return np.array(pf), np.array(pd), np.array(selr), np.array(keep)


def table(pf, pd, mask, title, note=""):
    if mask.sum() < 4:
        print(f"  {title}: only {mask.sum()} tiles, not scored"); return {}
    print(f"  {title}   (n={mask.sum()} tiles) {note}")
    print(f"    {'band':<12} {'R':>8} {'CI low':>8} {'CI high':>9}  verdict")
    out = {}
    for j, (a, b) in enumerate(ALLB):
        r, cl, ch = BS.ratio_ci(pf[mask, j], pd[mask, j])
        v = BS.verdict(r, cl)
        out[(a, b)] = (r, cl, v)
        star = "  <<< band 0 territory" if a >= 0.25 else ""
        print(f"    {a:.2f}-{b:.2f}    {r:8.3f} {cl:8.3f} {ch:9.3f}  {v}{star}")
    return out


def main():
    key = sys.argv[1]
    o = r"C:\dev\strehl-out\V-KILLB0"
    power = np.load(os.path.join(o, f"{key}-power.npy"))
    selp = np.load(os.path.join(o, f"{key}-selp.npy"))
    far = int(np.load(os.path.join(o, f"{key}-meta.npy"))[0])
    n = power.shape[0]
    print(f"=== FLAT-SITE QUALIFICATION  {key}   far={far}  reads={n}")
    print("    rule imported from V-LINEAR2/bandsignal.py: PASS = R>=2.0 and CI low>=1.5\n")

    pf, pd, selr, keep = pfpd(power, selp, far)
    infocus = selp[[int(np.nanargmax(selp[:, i])) for i in keep], keep]
    q1, q3 = np.percentile(infocus, 25), np.percentile(infocus, 75)
    flat, struct = infocus <= q1, infocus >= q3
    conf = selr >= 2.0

    table(pf, pd, np.ones(len(pf), bool), "ALL TILES (frame-wide, ALL population)")
    print()
    table(pf, pd, conf, "CONFIRMED tiles (V-LINEAR's headline population)",
          "<- reproduces the published boundary")
    print()
    table(pf, pd, struct, "STRUCTURED sites (top quartile of in-focus structure)")
    print()
    r_flat = table(pf, pd, flat, "FLAT SITES  <<<< THE MEASUREMENT ORCH'S RESULT RESTS ON")

    print("\n  --- NULLS: what a flat-site R reads when there is NO focus response ---")
    rng = np.random.default_rng(20260827)
    order = np.stack([rng.permutation(n) for _ in range(power.shape[1])], axis=1)
    pf2, pd2, _, keep2 = pfpd(power, selp, far, order=order)
    m2 = np.zeros(len(pf2), bool)
    kk = {k: i for i, k in enumerate(keep2)}
    for i, k in enumerate(keep):
        if flat[i] and k in kk:
            m2[kk[k]] = True
    r_perm = table(pf2, pd2, m2, "PERMUTED null at the SAME flat tiles",
                   "<- frame order shuffled: focus response destroyed, noise kept")

    print("\n  --- READING ---")
    for (a, b) in [(0.25, 0.30), (0.30, 0.40), (0.40, 0.48)]:
        if (a, b) in r_flat and (a, b) in r_perm:
            rf, _, vf = r_flat[(a, b)]
            rp, _, _ = r_perm[(a, b)]
            print(f"    {a:.2f}-{b:.2f}  flat R={rf:.3f} ({vf})   selection-bias floor={rp:.3f}"
                  f"   excess={rf - rp:+.3f}")


if __name__ == "__main__":
    main()
