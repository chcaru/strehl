"""Run ORCH's two surviving audit checks (D1 magenta, D8 partial clip) over a
list of renders and print one table.

D3, D5 and D6 are deliberately not run: ORCH's control killed them
(`defect_audit.py`'s docstring), D6 is arithmetically broken, and quoting a
check a control has refuted would be worse than not measuring at all.

The check functions are IMPORTED from ORCH's `defect_audit.py`, never copied.

Usage:  python d1d8.py <label>=<render.tif> [...]
"""

import sys
from pathlib import Path

import numpy as np
import tifffile

_ORCH = Path(__file__).resolve().parents[2] / "ORCH-drift-check"
if not (_ORCH / "defect_audit.py").is_file():
    raise SystemExit(f"cannot find ORCH's defect_audit.py at {_ORCH}")
sys.path.insert(0, str(_ORCH))
from defect_audit import T_D1_FRAC, T_D8_FRAC, d1_magenta, d8_partial_clip  # noqa: E402


def frac_only(fn, img):
    """Re-derive the bare fraction; the imported fns return prose."""
    fired, msg = fn(img)
    return fired, float(msg.split("%")[0])


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 1
    print(f"D1 bar {T_D1_FRAC*100:.3f}%   D8 bar {T_D8_FRAC*100:.2f}%\n")
    print(f"{'label':<28} {'D1 magenta %':>13} {'':>6} {'D8 partial %':>13} {'':>6}")
    print("-" * 72)
    rows = []
    for a in args:
        label, _, path = a.rpartition("=")
        p = Path(path)
        if not p.is_file():
            print(f"{label:<28} {'MISSING':>13}")
            continue
        img = tifffile.imread(str(p)).astype(np.float32) / 65535.0
        img = img[..., :3]
        f1, v1 = frac_only(d1_magenta, img)
        f8, v8 = frac_only(d8_partial_clip, img)
        print(
            f"{label:<28} {v1:>13.4f} {'FIRED' if f1 else 'clear':>6}"
            f" {v8:>13.4f} {'FIRED' if f8 else 'clear':>6}"
        )
        rows.append((label, v1, v8))
    return 0


if __name__ == "__main__":
    sys.exit(main())
