"""The sqrt(N) acceptance battery, runnable by someone who is not its author.

    python src/10-acceptance.py                       # binary: working tree release build
    python src/10-acceptance.py --exe path/to/strehl.exe --src path/to/repo
    python src/10-acceptance.py --spec my-spec.json --tag m64

Nothing about the binary, the subcommand, the gate or the flags is written in
this file. Arms live in `acceptance-spec.json` as `argv` templates with
`{burst}`, `{out}` and `{roi}` placeholders, so a merge with a different command
line is tested by editing data, never by editing code. The scoring statistic,
the ROI, the denominator and the tolerances are the same ones M62 pre-registered
at 906688c.

An arm whose invocation the binary refuses is reported **UNSUPPORTED**, with the
exit code and stderr in its log. That is a result: it says the control M62 relied
on no longer exists, which the report must then say out loud.

Arms carry a `role`:

  instrument  binary-independent arithmetic. A failure here means the HARNESS
              moved and no verdict about any merge can be issued.
  decision    the claim under test. Must PASS.
  power       an invocation expected to score at or below `selector_ceiling`.
              Per discipline 419 at least one must run and score low, else the
              battery has no failing arm and certifies nothing. A power arm that
              scores HIGH is NO-POWER, not FAIL -- that entry point may have been
              deliberately converted, and auto-rejecting on it would pre-commit
              the battery against the change it exists to judge.
  reference   recorded for continuity; never gates the verdict.

Verdicts per arm: PASS / FAIL / UNSUPPORTED / NO-POWER / POWER-OK / NOT-REQUIRED.
Overall: CERTIFY / REJECT / CANNOT-CERTIFY.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import sys
import time

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import harness as H  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent


def parse_gate_row(txt):
    m = re.search(
        r"^\s*([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)%\s+([0-9.]+)%\s+([0-9.]+)x\s*$",
        txt, re.M)
    if not m:
        return {}
    return dict(gate=float(m.group(1)), mean_n_eff=float(m.group(3)),
                n_eff_1_pct=float(m.group(4)), pred_sigma_gain=float(m.group(6)))


def parse_hp_row(txt):
    m = re.search(r"^\s*([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)x\s+\[", txt, re.M)
    return {} if not m else dict(hp_sd_dn=float(m.group(2)), hp_ratio=float(m.group(3)))


def run_seed(seed, spec, k, latent, tag):
    n = spec["n"]
    burst = H.DATA / f"acc-{tag}-s{seed}"
    H.make_burst(latent, n, seed=seed, outdir=burst, k=k)
    paths = sorted(burst.glob("*.arw"))
    assert len(paths) == n, f"{burst}: {len(paths)} frames, expected {n}"

    tr = H.roi(H.green(latent))
    fr = np.stack([H.green(H.read_cfa(p, latent.shape)) for p in paths])
    fr = fr[:, H.INSET:-H.INSET, H.INSET:-H.INSET]
    single_ms = ((fr - tr[None]) ** 2).mean(axis=0)  # pooled over ALL frames (fact 441)
    roi_arg = f"{H.INSET},{H.INSET},{fr.shape[2]},{fr.shape[1]}"

    def score(a):
        return H.ratio_and_se(a, tr, single_ms)

    res = {}
    for arm in spec["arms"]:
        name, kind = arm["name"], arm["kind"]

        if kind == "python-mean-ladder":
            for kk in arm["k"]:
                r, se = score(fr[:kk].mean(axis=0))
                res[f"{name}:{kk}"] = dict(arm=name, k=kk, expected=float(np.sqrt(kk)),
                                           ratio=r, se=se, criterion=arm["criterion"],
                                           role=arm["role"], required=arm["required"])
            continue

        if kind == "python-const-selector":
            r, se = score(fr[0])
        elif kind == "python-random-selector":
            rng = np.random.default_rng([seed, 424242])
            pick = rng.integers(0, n, size=fr.shape[1:])
            r, se = score(np.take_along_axis(fr, pick[None], axis=0)[0])
        elif kind == "cli":
            tif = H.DATA / f"acc-{tag}-s{seed}-{name}.tif"
            argv = [str(x).format(burst=burst, out=tif, roi=roi_arg) for x in arm["argv"]]
            txt = H.run_cli(argv, H.EVID / f"10-{tag}-s{seed}-{name}.log", check=False)
            if txt is None or not tif.exists():
                res[name] = dict(arm=name, verdict="UNSUPPORTED",
                                 log=f"out/10-{tag}-s{seed}-{name}.log",
                                 role=arm["role"], required=arm["required"],
                                 criterion=arm["criterion"], note=arm.get("note", ""))
                continue
            r, se = score(H.roi(H.read_tiff_green(tif, k)))
            extra = dict(parse_gate_row(txt), **parse_hp_row(txt))
            sha = hashlib.sha256(tif.read_bytes()).hexdigest()
            tif.unlink()
            rec = dict(arm=name, ratio=r, se=se, criterion=arm["criterion"],
                       expect=arm["expect"], role=arm["role"],
                       required=arm["required"], cli=extra, out_sha256=sha,
                       note=arm.get("note", ""))
            if extra.get("mean_n_eff"):
                # R / sqrt(n_eff): does the merge waste the samples it admitted?
                rec["efficiency"] = r / float(np.sqrt(extra["mean_n_eff"]))
            res[name] = rec
            continue
        else:
            raise AssertionError(f"unknown arm kind {kind!r}")

        res[name] = dict(arm=name, ratio=r, se=se, criterion=arm["criterion"],
                         expect=arm["expect"], role=arm["role"],
                         required=arm["required"], note=arm.get("note", ""))

    for p in paths:
        p.unlink()
    burst.rmdir()
    return res


def judge(name, rec, spec, n):
    """Apply the spec's tolerance. Verdicts are data-driven, not hand-assigned."""
    tol = spec["tolerances"]
    if rec.get("verdict") == "UNSUPPORTED":
        return rec["verdict"]
    r = rec["ratio_mean"]
    c = rec["criterion"]
    if rec.get("role") == "power":
        # NOT a pass/fail on the merge. This arm's job is to supply a failing
        # arm; if it stops scoring low the control is gone, not the merge wrong.
        return "POWER-OK" if r < tol["selector_ceiling"] else "NO-POWER"
    if c == "ladder_rel":
        return "PASS" if abs(r / rec["expected"] - 1.0) <= tol["ladder_rel"] else "FAIL"
    if c == "selector_abs":
        return "PASS" if abs(r - 1.0) <= tol["selector_abs"] else "FAIL"
    if c == "selector_ceiling":
        return "PASS" if r < tol["selector_ceiling"] else "FAIL"
    if c == "estimator_rel":
        return "PASS" if abs(r / np.sqrt(n) - 1.0) <= tol["estimator_rel"] else "FAIL"
    raise AssertionError(f"unknown criterion {c!r}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", help="strehl executable under test (else $STREHL_BIN, else target/release)")
    ap.add_argument("--src", help="crate tree the constants are parsed from; must match --exe")
    ap.add_argument("--spec", default=str(HERE / "acceptance-spec.json"))
    ap.add_argument("--tag", default="run", help="label for output files")
    ap.add_argument("--seeds", type=int, nargs="*", default=None)
    ap.add_argument("--n", type=int, default=None)
    ap.add_argument("--no-determinism", action="store_true",
                    help="skip the repeat run that checks byte-identical output")
    a = ap.parse_args()

    if a.exe:
        os.environ["STREHL_BIN"] = a.exe
    if a.src:
        os.environ["STREHL_SRC"] = a.src

    spec = json.loads(pathlib.Path(a.spec).read_text(encoding="utf-8"))
    if a.seeds:
        spec["seeds"] = a.seeds
    if a.n:
        spec["n"] = a.n
    n, seeds = spec["n"], spec["seeds"]

    prov = H.provenance()
    k = H.constants(iso=float(spec.get("iso", H.ISO)))
    latent_path = H.DATA / "latent.npy"
    assert latent_path.exists(), "run src/01-pick-latent.py first (it reads the read-only corpus)"
    latent = np.load(latent_path)

    t0 = time.time()
    per_seed = []
    for s in seeds:
        per_seed.append(run_seed(s, spec, k, latent, a.tag))
        print(f"seed {s} done")

    # Determinism: re-run seed[0] and compare output bytes for arms that ask.
    det_arms = [x["name"] for x in spec["arms"] if x.get("determinism")]
    determinism = {}
    if det_arms and not a.no_determinism:
        repeat = run_seed(seeds[0], spec, k, latent, a.tag + "-det")
        for nm in det_arms:
            first, again = per_seed[0].get(nm, {}), repeat.get(nm, {})
            if first.get("verdict") == "UNSUPPORTED" or again.get("verdict") == "UNSUPPORTED":
                determinism[nm] = dict(status="UNSUPPORTED")
                continue
            same = first.get("out_sha256") == again.get("out_sha256")
            determinism[nm] = dict(status="PASS" if same else "FAIL",
                                   sha_a=first.get("out_sha256"),
                                   sha_b=again.get("out_sha256"),
                                   ratio_a=first.get("ratio"), ratio_b=again.get("ratio"))
        print(f"determinism done: {determinism}")

    summary, verdicts = {}, {}
    for key in per_seed[0]:
        rows = [p[key] for p in per_seed]
        if rows[0].get("verdict") == "UNSUPPORTED":
            summary[key] = rows[0]
        else:
            v = np.array([r["ratio"] for r in rows])
            base = {x: y for x, y in rows[0].items() if x not in ("ratio", "se")}
            summary[key] = dict(base, ratio_mean=float(v.mean()),
                                ratio_sd_between_seeds=float(v.std(ddof=1)) if len(v) > 1 else 0.0,
                                ratio_per_seed=[float(x) for x in v],
                                bootstrap_se_seed0=rows[0]["se"])
        verdicts[key] = judge(key, summary[key], spec, n)
        summary[key]["verdict"] = verdicts[key]

    instrument_bad = [x for x, v in verdicts.items()
                      if summary[x].get("role") == "instrument" and v != "PASS"]
    required_fail = [x for x, v in verdicts.items()
                     if summary[x].get("required") and v != "PASS"]
    power_ok = [x for x, v in verdicts.items() if v == "POWER-OK"]
    power_lost = [x for x, v in verdicts.items()
                  if summary[x].get("role") == "power" and v != "POWER-OK"]
    det_fail = [x for x, d in determinism.items() if d["status"] == "FAIL"]

    # Efficiency band, reported on every cli arm that printed n_eff; gates only
    # the decision arm, whose PASS already implies it averaged something.
    lo, hi = spec["tolerances"]["efficiency_band"]
    eff_bad = [x for x, s in summary.items()
               if s.get("role") == "decision" and s.get("efficiency") is not None
               and not (lo <= s["efficiency"] <= hi)]

    if instrument_bad:
        overall, blocking = "CANNOT-CERTIFY", instrument_bad
        reason = "an instrument arm moved; the harness itself is not reproducing"
    elif required_fail or det_fail or eff_bad:
        overall, blocking = "REJECT", required_fail + det_fail + eff_bad
        reason = "a required arm failed"
    elif not power_ok:
        overall, blocking = "CANNOT-CERTIFY", power_lost
        reason = ("no power arm scored below the selector ceiling: the battery has no "
                  "failing arm and therefore certifies nothing (discipline 419)")
    else:
        overall, blocking = "CERTIFY", []
        reason = f"power supplied by {', '.join(power_ok)}"

    out = dict(overall=overall, reason=reason, blocking=blocking,
               power_ok=power_ok, power_lost=power_lost,
               determinism=determinism, focus_guard="run src/11-focus-guard.py separately",
               spec=a.spec, tag=a.tag, n=n, seeds=seeds, elapsed_s=time.time() - t0,
               provenance=prov, constants=k, tolerances=spec["tolerances"],
               summary=summary)
    H.dump(f"10-acceptance-{a.tag}.json", out)

    print(f"\n=== {overall} ===   binary {prov['binary']}")
    print(f"    {reason}")
    print(f"    repo HEAD {prov['repo_head'][:8]}  crates dirty: {prov['crates_dirty']}")
    for key, v in verdicts.items():
        s = summary[key]
        r = s.get("ratio_mean")
        eff = s.get("efficiency")
        tail = "" if eff is None else f"   eff {eff:.4f}  n_eff {s['cli'].get('mean_n_eff')}"
        print(f"    {v:<12} {key:<24} {'' if r is None else f'{r:.4f}'}{tail}")
    if blocking:
        print(f"    BLOCKING: {', '.join(blocking)}")
    print("    NOTE: this battery measures noise efficiency on a static burst. It does "
          "NOT test sensor calibration (rule 34) and does NOT test focus correctness.")


if __name__ == "__main__":
    main()
