"""M66 control K4 - prove the loader before anything else is printed.

Copied in substance from M52's verified harness
(experiments/m52-gate-cluster/src/03-fact324-n-eff-independent.py): reproduce
M4 section 8.1's dark temporal sigma at two ISOs. If that misses by more than
1%, nothing downstream runs.

RULE 32: `raw_image_visible` is a VIEW. Every read copies inside the `with`.
"""

import json
import pathlib
import sys

import numpy as np
import rawpy

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from m66 import DARK_TRUTH, DARKS, OUT, banner, dump_constants  # noqa: E402


def read_planes(path):
    with rawpy.imread(path) as rr:
        v = rr.raw_image_visible
        h = (v.shape[0] // 2) * 2
        w = (v.shape[1] // 2) * 2
        r = np.array(v[0:h:2, 0:w:2], dtype=np.float64)
        g1 = np.array(v[0:h:2, 1:w:2], dtype=np.float64)
        g2 = np.array(v[1:h:2, 0:w:2], dtype=np.float64)
        b = np.array(v[1:h:2, 1:w:2], dtype=np.float64)
    return r, g1, g2, b


banner("M66 control K4 - loader check against M4 section 8.1")
dump_constants()
print()

worst = 0.0
loader = {}
for folder, (iso, truth) in DARK_TRUTH.items():
    d = pathlib.Path(DARKS) / folder
    files = sorted(p for p in d.iterdir() if p.suffix.upper() == ".ARW")[2:]
    assert len(files) == 20, f"{folder}: expected 20 usable darks, got {len(files)}"
    acc = {k: [] for k in ("R", "G1", "G2", "B")}
    for p in files:
        r, g1, g2, b = read_planes(str(p))
        for k, v in zip(("R", "G1", "G2", "B"), (r, g1, g2, b)):
            acc[k].append(v)
    row = {}
    for k in ("R", "G1", "G2", "B"):
        cube = np.stack(acc[k])
        var = cube.var(axis=0, ddof=1)
        row[k] = float(np.sqrt(var.mean()))
        worst = max(worst, abs(row[k] / truth[k] - 1.0))
    loader[folder] = {"iso": iso, "mine": row, "m4": truth}
    print(
        f"  {folder} ISO {iso:.0f}: "
        + "  ".join(
            f"{k} {row[k]:.4f} (M4 {truth[k]:.4f}, {row[k] / truth[k] - 1:+.2%})"
            for k in ("R", "G1", "G2", "B")
        )
    )

print(f"\n  worst deviation from M4 section 8.1: {worst:.2%}")
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "01-loader.json").write_text(
    json.dumps({"worst": worst, "loader": loader}, indent=2), encoding="utf-8"
)
if worst > 0.01:
    print("  K4 FAILED - refusing to report anything else.")
    sys.exit(1)
print("  K4 PASS.")
