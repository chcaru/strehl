"""M77 arms G1 and G2 -- the gate sweep, through the SHIPPED CLI, unmodified.

Nothing under crates/ is touched. The CLI already sweeps (`--gate` takes
num_args = 1.., main.rs:120) and already prints both sides of the tradeoff:

  merge_cmd.rs:966   mean n_eff ladder
  merge_cmd.rs:1007  ACCEPTANCE INVARIANT 1 of 2 -- flat-ROI high-pass sd + HP RATIO
  merge_cmd.rs:1189  ACCEPTANCE INVARIANT 2 of 2 -- corrected detail gradient + RETENTION

Every gate is folded in the same pass two, so one invocation per stack.

The binary is the private build at experiments/M77-gate-sweep/target-m77, built
by this milestone into its own CARGO_TARGET_DIR because the workspace target/ is
shared with other live agents and a `Finished` with no `Compiling` proves
freshness, not authorship.
"""

import json
import pathlib
import re
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m77  # noqa: E402

BIN = m77.EXP / "target-m77" / "release" / "strehl.exe"

NEFF_ROW = re.compile(
    r"^\s*([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)%\s+([0-9.]+)%\s+([0-9.]+)x\s*$"
)
HP_ROW = re.compile(
    r"^\s*([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)x\s+\[\s*([0-9.]+)x\s*\.\.\s*([0-9.]+)x\]"
    r"\s+(\d+)\s+([0-9.]+)x\s*$"
)
RET_ROW = re.compile(
    r"^\s*([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)x\s+(\S+)\s+([0-9.]+)\s+([0-9.]+)"
    r"\s+([0-9.]+)\s+([0-9.]+)\s*$"
)


def run(stack, flat, detail, log_dir, tag=""):
    args = [
        str(BIN), "stack", str(pathlib.Path(m77.CORPUS) / stack),
        "--gate", *[f"{g:g}" for g in m77.GATES],
        "--flat-roi", f"{flat['x']},{flat['y']},{flat['w']},{flat['h']}",
        "--detail-roi", f"{detail['x']},{detail['y']},{detail['w']},{detail['h']}",
    ]
    print("    " + " ".join(args[1:]))
    t0 = time.time()
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    dt = time.time() - t0
    (log_dir / f"02{tag}-{stack}.log").write_text(p.stderr + p.stdout, encoding="utf-8")
    if p.returncode != 0:
        print(p.stderr[-3000:])
        raise SystemExit(f"{stack}: exit {p.returncode}")
    print(f"    {dt:.1f}s  -> out/02{tag}-{stack}.log")
    return p.stderr


def parse(text):
    neff, hp, ret = {}, {}, {}
    for line in text.splitlines():
        m = NEFF_ROW.match(line)
        if m:
            neff[float(m.group(1))] = {
                "tol": float(m.group(2)), "n_eff": float(m.group(3)),
                "n_eff_1_pct": float(m.group(4)), "boundary_pct": float(m.group(5)),
                "pred_sigma_gain": float(m.group(6)),
            }
            continue
        m = HP_ROW.match(line)
        if m:
            hp[float(m.group(1))] = {
                "hp_sd": float(m.group(2)), "hp_ratio": float(m.group(3)),
                "lo": float(m.group(4)), "hi": float(m.group(5)),
                "n_frames": int(m.group(6)), "vs_single": float(m.group(7)),
            }
            continue
        m = RET_ROW.match(line)
        if m:
            ret[float(m.group(1))] = {
                "corrected": float(m.group(2)), "retention": float(m.group(3)),
                "verdict": m.group(4), "raw_rms": float(m.group(5)),
                "model_noise": float(m.group(6)), "m2": float(m.group(7)),
                "iso": float(m.group(8)),
            }
    return neff, hp, ret


def main():
    m77.banner("M77 arms G1/G2 -- gate sweep through the shipped CLI")
    if not BIN.exists():
        raise SystemExit(f"binary not built: {BIN}")
    st = BIN.stat()
    print(f"  binary  {BIN}")
    print(f"          {st.st_size} bytes, mtime "
          f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(st.st_mtime))}")
    m77.dump_constants()

    tag = sys.argv[1] if len(sys.argv) > 1 else ""
    src = f"01{tag}-rois.json"
    dst = f"02{tag}-sweep.json"
    print(f"  ROIs from {src}  ->  {dst}"
          + ("   [arm G0' -- DECLARED DEVIATION, post hoc]" if tag else "   [arm G0]"))
    rois = json.loads((m77.OUT / src).read_text(encoding="utf-8"))
    out = {}
    for stack in m77.STACKS:
        r = rois[stack]
        print(f"\n  --- {stack}")
        text = run(stack, r["flat_roi"], r["detail_roi"], m77.OUT, tag)
        neff, hp, ret = parse(text)
        missing = [g for g in m77.GATES if g not in neff or g not in hp or g not in ret]
        if missing:
            raise SystemExit(f"{stack}: rows missing for gates {missing}")

        # K3 -- selector anchor at gate 0.
        k3_neff = abs(neff[0.0]["n_eff"] - 1.0) < 5e-4
        k3_hp = 0.90 <= hp[0.0]["hp_ratio"] <= 1.10
        # K4 -- monotone n_eff along the ladder.
        seq = [neff[g]["n_eff"] for g in m77.GATES]
        k4 = all(b >= a - 1e-9 for a, b in zip(seq, seq[1:]))

        print(f"      K3 gate-0 n_eff = {neff[0.0]['n_eff']:.3f} "
              f"[{'MET' if k3_neff else 'NOT MET'}]   "
              f"HP RATIO = {hp[0.0]['hp_ratio']:.4f}x "
              f"[bar 0.90-1.10 -> {'MET' if k3_hp else 'NOT MET'}]")
        print(f"      K4 n_eff monotone [{'MET' if k4 else 'NOT MET'}]  "
              f"{seq[0]:.3f} -> {seq[-1]:.3f}")

        print(f"      {'gate':>6} {'n_eff':>9} {'n_eff/N':>9} {'HP RATIO':>9} "
              f"{'RETENT':>8} {'eff':>8}")
        n_total = hp[0.0]["n_frames"]
        rows = {}
        for g in m77.GATES:
            ne = neff[g]["n_eff"]
            eff = hp[g]["hp_ratio"] * (ne ** 0.5)  # G2: noise x sqrt(n), 1.0 = ideal
            rows[g] = {**neff[g], **hp[g], **ret[g],
                       "n_eff_over_N": ne / n_total, "eff": eff}
            print(f"      {g:6g} {ne:9.3f} {ne / n_total:9.4f} "
                  f"{hp[g]['hp_ratio']:9.4f} {ret[g]['retention']:8.3f} {eff:8.4f}")
        out[stack] = {
            "N": n_total, "iso": r["iso"],
            "flat_roi": r["flat_roi"], "detail_roi": r["detail_roi"],
            "contam_max": r["flat_roi"]["contam_max"],
            "k1_met": r["k1_met"], "k2_met": r["k2_met"],
            "k5_flat_met": r["k5_flat_met"], "k5_detail_met": r["k5_detail_met"],
            "k3_neff_met": bool(k3_neff), "k3_hp_met": bool(k3_hp), "k4_met": bool(k4),
            "rows": {f"{g:g}": rows[g] for g in m77.GATES},
        }
    (m77.OUT / dst).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\n  wrote out/{dst}")


if __name__ == "__main__":
    main()
