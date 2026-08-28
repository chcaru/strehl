"""Bank every published V-ORACLE number as text, before the .npz scratch is deleted.

ORCH wind-down STEP 1: "A number that lives only inside a [binary] you are about
to delete is a number you are destroying."  My scratch is .npz, so every figure in
docs/research/V-ORACLE.md currently lives only in binary.  This writes them out as
CSV/JSON/TXT so the published result stays reproducible after STEP 2 deletes them.

This performs NO new measurement.  It re-runs the shipped entry points to capture
their stdout verbatim, and serialises arrays that already exist on disk.

Usage:  python bank.py
"""
import csv
import hashlib
import io
import json
import os
import subprocess
import sys

import numpy as np

import ora

HERE = os.path.dirname(os.path.abspath(__file__))
BANK = os.path.join(HERE, "data")
os.makedirs(BANK, exist_ok=True)

# The six sites of the commission, as (row, col) on the 18x27 tile grid.
SITES = [(12, 1), (5, 2), (6, 5), (9, 2), (6, 8), (16, 10)]
SITE_EYE = ["SHARP", "BLURRED", "SHARP", "BLURRED", "SHARP", "BLURRED"]
SUBJ = "flowers-cpl"


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def capture(argv: list[str], name: str) -> str:
    """Run a shipped entry point and bank its stdout verbatim as UTF-8."""
    out = subprocess.run([sys.executable] + argv, capture_output=True,
                         text=True, encoding="utf-8", errors="replace", cwd=HERE)
    body = (f"$ python {' '.join(argv)}\n"
            f"# exit={out.returncode}\n\n{out.stdout}")
    if out.returncode != 0:
        body += f"\n# STDERR\n{out.stderr}"
    p = os.path.join(BANK, name)
    io.open(p, "w", encoding="utf-8", newline="\n").write(body)
    print(f"  banked stdout -> data/{name}  ({len(body)} chars, exit {out.returncode})")
    return body


def main() -> int:
    manifest: dict = {"lane": "V-ORACLE",
                      "verdict": "(a) CAPTURE GAP at all six sites on licensed bands 2,3",
                      "detection_floor": "0.75 green px = 1.5 master px",
                      "tile_grid": "18 rows x 27 cols = 486 tiles",
                      "bands": "b0..b4 from SIGMAS=[0.0,0.8,1.6,3.2,6.4,12.8]",
                      "licensed_bands": [2, 3],
                      "band_licence_note": ("b1 withdrawn pending measurement: half-power "
                                            "top edge 0.283 cyc/green-px vs the 0.17 corpus "
                                            "floor. b2/b3 clear it under both grid readings."),
                      "deleted_scratch_sha256": {},
                      "regeneration": {}}

    # ---- 1. verbatim stdout of the shipped entry points --------------------
    print("[1/4] banking shipped entry-point stdout")
    capture(["verdict.py", SUBJ], "verdict-flowers-cpl-allbands.txt")
    capture(["verdict.py", SUBJ, "--bands", "2,3"], "verdict-flowers-cpl-licensed.txt")
    capture(["rank.py"], "rank-corpus.txt")
    capture(["commission_verdict.py"], "commission-verdict.txt")

    # ---- 2. flowers-cpl per-tile table -------------------------------------
    print("[2/4] banking flowers-cpl per-tile table")
    a = np.load(os.path.join(ora.OUT, "stageA", SUBJ + ".npz"))
    b = np.load(os.path.join(ora.OUT, "stageB", SUBJ + ".npz"))
    nb, nr, nc = a["contrast"].shape
    p = os.path.join(BANK, "flowers-cpl-tiles.csv")
    with io.open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["band", "row", "col", "src_contrast", "best_frame",
                    "src_sig", "point_sig", "box_sig",
                    "ratio_point", "ratio_box"])
        n = 0
        for bi in range(nb):
            for r in range(nr):
                for c in range(nc):
                    ps, bs = b["point_sig"][bi, r, c], b["box_sig"][bi, r, c]
                    ss = b["src_sig"][bi, r, c]
                    w.writerow([bi, r, c,
                                f"{a['contrast'][bi, r, c]:.6g}",
                                int(a["best_k"][bi, r, c]),
                                f"{ss:.6g}", f"{ps:.6g}", f"{bs:.6g}",
                                f"{ss / ps:.6g}" if ps > 0 else "",
                                f"{ss / bs:.6g}" if bs > 0 else ""])
                    n += 1
    print(f"  data/flowers-cpl-tiles.csv  {n} rows ({nb} bands x {nr*nc} tiles)")
    assert n == nb * nr * nc, "row count does not partition the grid"

    # ---- 3. through-focus curves at the six sites (THE decisive evidence) ---
    print("[3/4] banking six-site through-focus curves")
    var_k, frames = a["var_k"], a["frames"]
    p = os.path.join(BANK, "flowers-cpl-sites-through-focus.csv")
    with io.open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["site", "eye", "row", "col", "band", "k", "frame", "var"])
        n = 0
        for si, (r, c) in enumerate(SITES):
            for bi in range(nb):
                for k in range(var_k.shape[0]):
                    w.writerow([si, SITE_EYE[si], r, c, bi, k, int(frames[k]),
                                f"{var_k[k, bi, r, c]:.6g}"])
                    n += 1
    print(f"  data/flowers-cpl-sites-through-focus.csv  {n} rows "
          f"({len(SITES)} sites x {nb} bands x {var_k.shape[0]} frames)")
    assert n == len(SITES) * nb * var_k.shape[0]

    # ---- 4. corpus per-subject summary -------------------------------------
    print("[4/4] banking corpus per-subject summary")
    sa = os.path.join(ora.OUT, "stageA")
    subjects = sorted(f[:-4] for f in os.listdir(sa) if f.endswith(".npz"))
    p = os.path.join(BANK, "corpus-subject-summary.csv")
    counted = {"summarised": 0, "no_stageB": 0}
    with io.open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["subject", "status", "nframes", "band",
                    "median_ratio_point", "n_detail_tiles", "n_src_beats_merge"])
        for s in subjects:
            bp = os.path.join(ora.OUT, "stageB", s + ".npz")
            za = np.load(os.path.join(sa, s + ".npz"))
            if not os.path.exists(bp):
                w.writerow([s, "NO_STAGEB", int(za["nframes"]), "", "", "", ""])
                counted["no_stageB"] += 1
                continue
            zb = np.load(bp)
            for bi in range(nb):
                ss, ps = zb["src_sig"][bi], zb["point_sig"][bi]
                m = (ps > 0) & (ss > 0)
                ratio = np.where(m, ss / np.where(ps > 0, ps, 1), np.nan)
                det = m & (ss > np.nanmedian(ss[m]) * 0.1) if m.any() else m
                med = float(np.nanmedian(ratio[det])) if det.any() else float("nan")
                w.writerow([s, "SUMMARISED", int(za["nframes"]), bi,
                            f"{med:.6g}", int(det.sum()),
                            int((ratio[det] > 1).sum()) if det.any() else 0])
            counted["summarised"] += 1
    tot = counted["summarised"] + counted["no_stageB"]
    print(f"  data/corpus-subject-summary.csv  "
          f"summarised {counted['summarised']} + no_stageB {counted['no_stageB']} "
          f"= {tot} of {len(subjects)} subjects")
    assert tot == len(subjects), "subject partition does not sum to the total"

    # ---- provenance of everything about to be deleted ----------------------
    for stage in ("stageA", "stageB"):
        d = os.path.join(ora.OUT, stage)
        for f in sorted(os.listdir(d)):
            fp = os.path.join(d, f)
            manifest["deleted_scratch_sha256"][f"{stage}/{f}"] = {
                "sha256": sha256(fp), "bytes": os.path.getsize(fp)}
    manifest["regeneration"] = {
        "stageA": "python experiments/V-ORACLE/stageA.py <subject>   "
                  "(reads D:\\personal\\macro, read-only; ~7-11 s/frame)",
        "stageB": "python experiments/V-ORACLE/stageB.py <subject> "
                  "[--chan green]   (needs stageA first; ~30 s/subject)",
        "crops": "python experiments/ORCH-drift-check/crop1to1.py "
                 "<master.tiff> <out.jpg> --sites 6 --size 520 --mode edge",
        "note": "All scratch is regenerable from these committed scripts plus the "
                "read-only originals under D:\\personal\\macro. Nothing unique was "
                "destroyed; the numbers themselves are banked in data/.",
    }
    io.open(os.path.join(BANK, "manifest.json"), "w", encoding="utf-8",
            newline="\n").write(json.dumps(manifest, indent=2) + "\n")
    print(f"\n  data/manifest.json  "
          f"{len(manifest['deleted_scratch_sha256'])} scratch files fingerprinted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
