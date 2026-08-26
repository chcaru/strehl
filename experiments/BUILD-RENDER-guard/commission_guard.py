"""Commission the guard: it must ignore tone and catch blur.

A guard is only worth having if it can be shown to do both halves. Firing on
everything is easy and useless; the previous form did that. So this plants known
changes of each kind and checks the verdict, including the two that matter:

  null control     a pure tone change MUST NOT fire. This is the case that broke
                   the guard -- BUILD-RENDER's own tone fix tripped it, and a
                   guard that fires on its author's intended change gets ignored.
  positive control a blur MUST fire. Without this, "it stopped firing" is
                   indistinguishable from "it stopped working", and the quiet
                   version of a broken guard is the dangerous one.

usage: python commission_guard.py <a-real-render.jpg> <workdir>
"""
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

GUARD = Path(__file__).resolve().parents[2] / "scripts" / "guard.py"


def contrast(a: np.ndarray, t: float) -> np.ndarray:
    """A monotonic S-curve, blended by t. Maps [0,1] onto [0,1] by construction.

    A linear contrast scale is the wrong null here: on a real photograph it
    clips at one end or both, and clipping destroys detail, so the null would
    fail for a real reason at the wrong moment. The tone rendering this guard
    has to tolerate is a monotonic display-space curve, so that is what gets
    planted. Being non-linear it is also the HARDER test -- exact invariance
    only holds for a linear rescale, so this measures the real tolerance rather
    than a flattering one.
    """
    x = a.astype(np.float32) / 255.0
    s = x * x * (3.0 - 2.0 * x)
    y = (1.0 - t) * x + t * s
    assert y.min() >= -1e-6 and y.max() <= 1.0 + 1e-6, "S-curve left the unit interval"
    return np.clip(y * 255.0, 0, 255).astype(np.uint8)


def gamma(a: np.ndarray, g: float) -> np.ndarray:
    x = np.clip(a.astype(np.float32) / 255.0, 0, 1)
    return np.clip((x ** g) * 255.0, 0, 255).astype(np.uint8)


def main() -> int:
    src = Path(sys.argv[1])
    work = Path(sys.argv[2])
    work.mkdir(parents=True, exist_ok=True)
    base = np.asarray(Image.open(src).convert("RGB"), dtype=np.uint8)
    ref = work / "ref.png"
    Image.fromarray(base).save(ref)

    arms = []
    arms.append(("identity", base.copy(), "held"))
    arms.append(("S-curve t=0.35", contrast(base, 0.35), "held"))
    arms.append(("S-curve t=0.60", contrast(base, 0.60), "held"))
    arms.append(("gamma 0.85", gamma(base, 0.85), "held"))
    arms.append(("gamma 1.18", gamma(base, 1.18), "held"))
    for s in (0.5, 0.8, 1.5):
        b = np.asarray(Image.fromarray(base).filter(ImageFilter.GaussianBlur(s)), dtype=np.uint8)
        arms.append((f"blur sigma {s}", b, "MOVED"))
    sharp = np.asarray(
        Image.fromarray(base).filter(ImageFilter.UnsharpMask(radius=2, percent=90, threshold=0)),
        dtype=np.uint8,
    )
    arms.append(("unsharp +90pct", sharp, "MOVED"))

    print(f"{'arm':18} {'want':6} {'got':6}  verdict")
    print("-" * 96)
    ok = True
    for name, img, want in arms:
        p = work / (name.replace(" ", "_") + ".png")
        Image.fromarray(img).save(p)
        r = subprocess.run(
            [sys.executable, str(GUARD), str(p), str(ref), str(work / "_out")],
            capture_output=True, text=True,
        )
        line = (r.stdout.strip().splitlines() or [""])[0]
        got = "MOVED" if r.returncode == 1 else "held"
        mark = "" if got == want else "   <-- WRONG"
        if got != want:
            ok = False
        print(f"{name:18} {want:6} {got:6}  {line.split(':', 1)[-1].strip()[:58]}{mark}")

    print()
    if ok:
        print("COMMISSIONED: ignores tone, catches blur and over-sharpening.")
    else:
        print("FAILED: the guard does not discriminate. Do not trust it.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
