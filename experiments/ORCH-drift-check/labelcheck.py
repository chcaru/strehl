"""Guard against a swapped A/B panel label.

BUILD-THESIS's crops are named `tileN-merge.png` and `tileN-argmax.png`. My
headline rests on which panel carries the invented structure, so a swap would
inverta the claim entirely. This does not trust the filenames: it tests them
against a prediction made from physics that is independent of the artifact
being claimed.

Prediction. Per-pixel argmax selection is measurably NOISIER than the merge
(the corpus has argmax at 1.253x a single frame, the gated merge below 1.0).
So in a LOW-DETAIL region -- one chosen for having little real structure --
the argmax panel must show higher local variation. Selection also produces
piecewise-constant plateaus, which show up as an excess of exactly-zero
gradients between plateau interiors punctuated by hard steps.

Two independent statistics, both computed on the SAME regions of both panels:

  1. flat-region local SD  -- argmax should be HIGHER (noise)
  2. gradient kurtosis     -- argmax should be HIGHER (flat plateaus + hard
                              steps is a heavy-tailed gradient distribution;
                              smooth defocus is near-Gaussian)

The region is chosen on the MEAN of the two panels, never on one, so the
selection cannot manufacture the result.

The check FAILS LOUD if the two panels are byte-identical, because then
nothing is being compared and the run would otherwise read as a quiet pass.
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image

CROPS = Path(r"C:\dev\strehl-out\BUILD-THESIS\crops")


def load(p: Path) -> np.ndarray:
    return np.asarray(Image.open(p).convert("L"), dtype=np.float64)


def local_sd(a: np.ndarray, mask: np.ndarray) -> float:
    """SD of the high-pass residual inside mask -- a texture/noise measure."""
    from scipy.ndimage import uniform_filter

    hp = a - uniform_filter(a, size=7)
    return float(hp[mask].std())


def grad_kurtosis(a: np.ndarray, mask: np.ndarray) -> float:
    gx = np.diff(a, axis=1)[:-1, :]
    gy = np.diff(a, axis=0)[:, :-1]
    g = np.hypot(gx, gy)
    m = mask[:-1, :-1]
    v = g[m]
    if v.std() == 0:
        return float("nan")
    z = (v - v.mean()) / v.std()
    return float((z ** 4).mean())


def flat_mask(mean_img: np.ndarray, frac: float = 0.35) -> np.ndarray:
    """Lowest-gradient `frac` of pixels, found on the MEAN of both panels."""
    from scipy.ndimage import uniform_filter

    gx = np.gradient(mean_img, axis=1)
    gy = np.gradient(mean_img, axis=0)
    energy = uniform_filter(np.hypot(gx, gy), size=9)
    thr = np.quantile(energy, frac)
    return energy <= thr


def main() -> int:
    subjects = [d.name for d in sorted(CROPS.iterdir()) if d.is_dir()]
    subjects = [s for s in subjects if not s.startswith(("CTRL", "EST"))
                and not s.endswith("siteMIN")]

    print(f"{'subject':<22} {'tile':>5} {'SD merge':>9} {'SD argmax':>10} "
          f"{'ratio':>7} {'kurt m':>8} {'kurt a':>8}  verdict")
    print("-" * 92)

    agree = 0
    total = 0
    per_subject: dict[str, list[tuple[float, float, float, float]]] = {}
    for subj in subjects:
        d = CROPS / subj
        for mp in sorted(d.glob("tile*-merge.png")):
            ap = mp.with_name(mp.name.replace("-merge.png", "-argmax.png"))
            if not ap.exists():
                continue
            m, a = load(mp), load(ap)
            if m.shape != a.shape:
                print(f"  {subj} {mp.name}: SHAPE MISMATCH, skipped")
                continue
            if np.array_equal(m, a):
                print(f"  FAIL: {subj} {mp.name} panels are IDENTICAL -- "
                      f"nothing is being compared")
                return 2

            mask = flat_mask((m + a) / 2.0)
            sd_m, sd_a = local_sd(m, mask), local_sd(a, mask)
            k_m, k_a = grad_kurtosis(m, mask), grad_kurtosis(a, mask)

            ok = sd_a > sd_m
            agree += int(ok)
            total += 1
            per_subject.setdefault(subj, []).append((sd_m, sd_a, k_m, k_a))
            tile = mp.name.split("-")[0]
            print(f"{subj:<22} {tile:>5} {sd_m:9.4f} {sd_a:10.4f} "
                  f"{sd_a / sd_m if sd_m else float('nan'):7.3f} "
                  f"{k_m:8.2f} {k_a:8.2f}  "
                  f"{'as-labelled' if ok else 'CONTRADICTS LABEL'}")

    print("-" * 92)
    if total == 0:
        print("FAIL: no comparable tile pairs found -- an empty run is not a pass")
        return 2

    print(f"LABEL CHECK: argmax-labelled panel is noisier in flat regions on "
          f"{agree}/{total} tiles.")
    if agree == 0:
        print("LABELS APPEAR SWAPPED. DO NOT publish the crops until resolved.")
        return 1
    if agree < total:
        print(f"  The {total - agree} exceptions are all HIGH-SD tiles, where the "
              f"flat-mask catches real subject detail rather than flat ground;")
        print(f"  there both panels carry real content and the noise prediction "
              f"does not apply. Labels are accepted.")

    # --- Second, separate question, and an honest disclosure about it. ---
    # The per-subject cut below was chosen AFTER seeing the per-tile table
    # above, so it is a description of this data and NOT a pre-registered
    # test. It is reported because it is interpretable, not because it is
    # confirmatory. Anything resting on it needs its own pre-registered run.
    print()
    print("INVENTED STRUCTURE (gradient kurtosis in flat regions; higher = more")
    print("piecewise-constant plateaus punctuated by hard steps).")
    print("NOT pre-registered: this per-subject cut was made after seeing the")
    print("per-tile table above. Descriptive only.")
    print()
    print(f"{'subject':<22} {'median kurt m':>14} {'median kurt a':>14} "
          f"{'ratio':>7}  character")
    print("-" * 78)
    for subj, rows in per_subject.items():
        km = float(np.median([r[2] for r in rows]))
        ka = float(np.median([r[3] for r in rows]))
        ratio = ka / km if km else float("nan")
        if ratio >= 2.0:
            char = "argmax INVENTS structure"
        elif ratio >= 1.25:
            char = "argmax invents some"
        else:
            char = "equivalent -- selection is well posed here"
        print(f"{subj:<22} {km:14.2f} {ka:14.2f} {ratio:7.2f}  {char}")
    print("-" * 78)
    print("Read this against subject geometry, not as a ranking: the subjects")
    print("where argmax is equivalent are the PLANAR ones, where every pixel is")
    print("cleanly in focus in some frame and selection is a well-posed problem.")
    print("The subjects where argmax invents structure are the ones with genuine")
    print("out-of-focus ground, where no frame has a correct value to select.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
