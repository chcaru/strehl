"""M77 arms B1 and B2 -- the dense ladder, and the null that can void the headline.

PREREGISTRATION-B.md B.3-B.4. Same shipped CLI, same private binary, nothing
under crates/ touched.

  B1  --detail-roi = the detail ROI   (the real measurement)
  B2  --detail-roi = the FLAT ROI     (the null)

B2's mechanism, registered in B.3: invariant 2's headline is
`corrected_rms = sqrt(max(0, raw_rms^2 - noise_rms^2))` where `noise_rms` is the
calibrated model's prediction and the merged sigma "already carries the
1/sqrt(n) from averaging" (merge_cmd.rs:302). Noise the model does not predict is
not subtracted, and what is not subtracted is averaged away as the gate opens. On
a structureless patch there is no detail to lose, so a fall in RETENTION there is
instrument, not subject.

The parser and the runner are imported from 02-sweep.py rather than rewritten, so
the two ladders cannot diverge in how they read the CLI.
"""

import importlib.util
import json
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import m77  # noqa: E402

_spec = importlib.util.spec_from_file_location("g12", HERE / "02-sweep.py")
g12 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(g12)

BIN = g12.BIN
STACKS = ["wrapped-text-1", "wrapped-text-2"]
LADDER = [0.0, 2.0, 4.0, 8.0, 16.0, 24.0, 32.0, 40.0, 48.0, 64.0, 96.0, 128.0]

# M70 section 21.3, out/s07_unclipped.log:60-61 -- gate-free spectral n_eff.
M70_SPECTRAL_NEFF = {"wrapped-text-1": 4.148, "wrapped-text-2": 4.050}


def run(stack, flat, detail, tag):
    args = [
        str(BIN), "stack", str(pathlib.Path(m77.CORPUS) / stack),
        "--gate", *[f"{g:g}" for g in LADDER],
        "--flat-roi", f"{flat['x']},{flat['y']},{flat['w']},{flat['h']}",
        "--detail-roi", f"{detail['x']},{detail['y']},{detail['w']},{detail['h']}",
    ]
    print("      " + " ".join(args[1:]))
    t0 = time.time()
    import subprocess
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    dt = time.time() - t0
    (m77.OUT / f"07-{tag}-{stack}.log").write_text(p.stderr + p.stdout,
                                                   encoding="utf-8")
    if p.returncode != 0:
        print(p.stderr[-3000:])
        raise SystemExit(f"{stack}/{tag}: exit {p.returncode}")
    print(f"      {dt:.1f}s  -> out/07-{tag}-{stack}.log")
    return p.stderr


def load_rois():
    a = json.loads((m77.OUT / "01-rois.json").read_text(encoding="utf-8"))
    b = json.loads((m77.OUT / "06-roi-wt2.json").read_text(encoding="utf-8"))
    return {**a, **b}


def main():
    m77.banner("M77 arms B1/B2 -- dense ladder + the null (PREREGISTRATION-B)")
    if not BIN.exists():
        raise SystemExit(f"binary not built: {BIN}")
    st = BIN.stat()
    print(f"  binary  {BIN}")
    print(f"          {st.st_size} bytes, mtime "
          f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(st.st_mtime))}")
    m77.dump_constants()
    print(f"  ladder  {' '.join(f'{g:g}' for g in LADDER)}   ({len(LADDER)} rungs)")
    print("  B1 detail-roi = DETAIL   B2 detail-roi = FLAT (null)")

    rois = load_rois()
    out = {}
    for stack in STACKS:
        r = rois[stack]
        blind = stack == "wrapped-text-2"
        print(f"\n  --- {stack}   [{'BLIND' if blind else 'NOT blind, declared B.2'}]")
        print(f"      flat {r['flat_roi']}")
        print(f"      detail {r['detail_roi']}")

        t1 = run(stack, r["flat_roi"], r["detail_roi"], "B1")
        t2 = run(stack, r["flat_roi"], r["flat_roi"], "B2")
        ne1, hp1, rt1 = g12.parse(t1)
        ne2, hp2, rt2 = g12.parse(t2)
        missing = [g for g in LADDER
                   if g not in ne1 or g not in hp1 or g not in rt1 or g not in rt2]
        if missing:
            raise SystemExit(f"{stack}: rows missing for gates {missing}")

        # Sanity: B1 and B2 differ only in --detail-roi, so n_eff and HP must match.
        dn = max(abs(ne1[g]["n_eff"] - ne2[g]["n_eff"]) for g in LADDER)
        dh = max(abs(hp1[g]["hp_ratio"] - hp2[g]["hp_ratio"]) for g in LADDER)
        print(f"      B1/B2 agreement on the shared columns: "
              f"max |dn_eff| = {dn:.2e}   max |dHP| = {dh:.2e}")

        n_total = hp1[0.0]["n_frames"]
        ref_hp = hp1[4.0]["hp_ratio"]
        ref_d1 = rt1[4.0]["retention"]
        ref_d2 = rt2[4.0]["retention"]
        rows = {}
        print(f"      {'gate':>6} {'n_eff':>9} {'HP RATIO':>9} {'dN_ben':>8} "
              f"{'RET':>9} {'dD':>8} {'RETnull':>9} {'dDnull':>8}")
        for g in LADDER:
            dnb = ref_hp / hp1[g]["hp_ratio"] if hp1[g]["hp_ratio"] > 0 else float("inf")
            dd = rt1[g]["retention"] / ref_d1 if ref_d1 > 0 else float("nan")
            ddn = rt2[g]["retention"] / ref_d2 if ref_d2 > 0 else float("nan")
            rows[f"{g:g}"] = {
                **ne1[g], **hp1[g],
                "retention": rt1[g]["retention"], "corrected": rt1[g]["corrected"],
                "raw_rms": rt1[g]["raw_rms"], "model_noise": rt1[g]["model_noise"],
                "verdict": rt1[g]["verdict"], "iso": rt1[g]["iso"],
                "retention_null": rt2[g]["retention"],
                "corrected_null": rt2[g]["corrected"],
                "raw_rms_null": rt2[g]["raw_rms"],
                "model_noise_null": rt2[g]["model_noise"],
                "n_eff_over_N": ne1[g]["n_eff"] / n_total,
                "dN_ben": dnb, "dD": dd, "dD_null": ddn,
            }
            print(f"      {g:6g} {ne1[g]['n_eff']:9.3f} {hp1[g]['hp_ratio']:9.4f} "
                  f"{dnb:8.4f} {rt1[g]['retention']:9.4f} {dd:8.4f} "
                  f"{rt2[g]['retention']:9.4f} {ddn:8.4f}")

        out[stack] = {
            "N": n_total, "iso": r["iso"], "blind": blind,
            "flat_roi": r["flat_roi"], "detail_roi": r["detail_roi"],
            "k1_met": r["k1_met"], "k2_met": r["k2_met"],
            "m70_spectral_n_eff": M70_SPECTRAL_NEFF[stack],
            "ref": {"hp_ratio_at_4": ref_hp, "ret_at_4": ref_d1,
                    "ret_null_at_4": ref_d2},
            "b1_b2_max_dn_eff": dn, "b1_b2_max_dhp": dh,
            "ladder": LADDER, "rows": rows,
        }
    (m77.OUT / "07-sweepB.json").write_text(json.dumps(out, indent=2),
                                            encoding="utf-8")
    print("\n  wrote out/07-sweepB.json")


if __name__ == "__main__":
    main()
