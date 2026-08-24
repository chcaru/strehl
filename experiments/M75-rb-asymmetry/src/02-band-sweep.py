r"""M75 step 2 -- band-resolved variance and covariance sweep.

Committed before running.  Produces the raw material for O1, O3, O4, O5 and for
the adversarial gate A2, in a single pass over the 11 ISO groups.

For every group, every plane and every inter-plane pair, this accumulates the
per-cell temporal second moments into 32 row bands and 32 column bands, under
four defect-exclusion arms (none / k3 / k6 / k9).  Nothing is interpreted here;
adjudication is src/03-criteria.py, which is committed separately and also
before it is run.

Per-cell moments are computed ONCE and then summed into bands under each arm,
because the arms differ only in which cells are included.  That guarantees the
four arms are the same measurement differently masked, which is what A2 needs.

Read-only on D:\macro-dark-frames.  Nothing is written outside this experiment.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
M72SRC = HERE.parent.parent / "M72-green-correlation" / "src"
DATA = HERE.parent / "data"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


m72 = _load("m72", M72SRC / "01-green-correlation.py")
pre = _load("pre", HERE / "01-preregistration.py")

NBAND = pre.NBAND
ARMS = {"none": None, "k3": 3.0, "k6": 6.0, "k9": 9.0}
PERM_SEED = 20250917


def band_sums(x: np.ndarray, mask: np.ndarray, axis: str) -> tuple[list, list]:
    """Sum x over `mask` within NBAND bands along rows (axis='row') or columns."""
    n = x.shape[0] if axis == "row" else x.shape[1]
    sl = pre.bands(n, NBAND)
    tot, cnt = [], []
    for s in sl:
        sub = (x[s, :], mask[s, :]) if axis == "row" else (x[:, s], mask[:, s])
        tot.append(float(sub[0][sub[1]].sum()))
        cnt.append(int(sub[1].sum()))
    return tot, cnt


def analyse(name: str, iso: int, frames: np.ndarray) -> dict:
    t0 = time.time()
    T = frames.shape[0]
    dev, mean = {}, {}
    for p in m72.PLANES:
        a = m72.split_plane(frames, p).astype(np.float32)
        mu = a.mean(axis=0)
        mean[p] = mu
        dev[p] = a - mu
        del a
    h, w = mean["R"].shape

    perm = m72.derangement(T, PERM_SEED)
    ss = {p: np.einsum("tij,tij->ij", dev[p], dev[p]).astype(np.float64)
          for p in m72.PLANES}
    cov, covp = {}, {}
    for a, b, cls in m72.PAIRS:
        k = f"{a}-{b}"
        cov[k] = np.einsum("tij,tij->ij", dev[a], dev[b]).astype(np.float64)
        covp[k] = np.einsum("tij,tij->ij", dev[a], dev[b][perm]).astype(np.float64)
    del dev

    flags = {p: {kk: m72.defect_flags(mean[p], kv) for kk, kv in ARMS.items()
                 if kv is not None} for p in m72.PLANES}
    masks = {}
    for arm in ARMS:
        if ARMS[arm] is None:
            masks[arm] = {p: np.ones((h, w), bool) for p in m72.PLANES}
        else:
            masks[arm] = {p: ~flags[p][arm] for p in m72.PLANES}

    out = {"name": name, "iso": iso, "T": T, "shape": [h, w], "axes": {}}
    for axis in ("row", "column"):
        ax = {}
        for arm in ARMS:
            entry = {"planes": {}, "pairs": {}}
            for p in m72.PLANES:
                tot, cnt = band_sums(ss[p], masks[arm][p], axis)
                entry["planes"][p] = {
                    "var": [t / ((T - 1) * c) if c else float("nan")
                            for t, c in zip(tot, cnt)],
                    "n": cnt,
                    "mean_dn": band_sums(mean[p] - m72.PEDESTAL,
                                         masks[arm][p], axis)[0],
                }
            for a, b, cls in m72.PAIRS:
                k = f"{a}-{b}"
                mm = masks[arm][a] & masks[arm][b]
                ct, cn = band_sums(cov[k], mm, axis)
                pt, _ = band_sums(covp[k], mm, axis)
                at, _ = band_sums(ss[a], mm, axis)
                bt, _ = band_sums(ss[b], mm, axis)
                d = (T - 1)
                entry["pairs"][k] = {
                    "cls": cls,
                    "n": cn,
                    "cov": [t / (d * c) if c else float("nan")
                            for t, c in zip(ct, cn)],
                    "cov_perm": [t / (d * c) if c else float("nan")
                                 for t, c in zip(pt, cn)],
                    "var_a": [t / (d * c) if c else float("nan")
                              for t, c in zip(at, cn)],
                    "var_b": [t / (d * c) if c else float("nan")
                              for t, c in zip(bt, cn)],
                }
            ax[arm] = entry
        out["axes"][axis] = ax
    out["seconds"] = round(time.time() - t0, 1)
    return out


def main() -> int:
    folders = sorted(p for p in m72.DARKS.iterdir() if p.is_dir())
    print(f"{len(folders)} groups under {m72.DARKS}")
    DATA.mkdir(exist_ok=True)
    dest = DATA / "02-band-sweep.json"
    results = []
    if dest.exists():
        results = json.loads(dest.read_text(encoding="utf-8"))["groups"]
        print(f"resuming: {len(results)} groups already on disk")
    done = {r["name"] for r in results}
    for f in folders:
        if f.name in done:
            continue
        t0 = time.time()
        iso, frames = m72.load_group(f)
        dec = time.time() - t0
        r = analyse(f.name, iso, frames)
        del frames
        results.append(r)
        results.sort(key=lambda x: x["iso"])
        dest.write_text(json.dumps({"nband": NBAND, "arms": list(ARMS),
                                    "groups": results}), encoding="utf-8")
        print(f"  {f.name:12s} ISO {iso:5d}  decode {dec:5.1f}s  "
              f"analyse {r['seconds']:5.1f}s  planes {r['shape']}", flush=True)
    print(f"wrote {dest} with {len(results)} groups")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
