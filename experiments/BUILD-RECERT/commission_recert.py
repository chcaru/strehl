"""BUILD-RECERT: commission the HARNESS, not just the metric.

`commission_bands.py` commissions the measurement. This file commissions the
thing that forms the verdict: it builds fake candidate arms out of the shipping
masters, runs the real pairing stage over them, and requires the real verdict
function to reach the right conclusion.

The two are not the same test. A metric can be perfectly sound and the harness
above it still certify a blurred arm, because the verdict aggregates -- and
aggregation is exactly where a trade goes missing. ORCH's requirement is that a
candidate which improves mid-band while losing fine-grain resolution be VISIBLE
AS SUCH in the output rather than hidden in an average, and only an end-to-end
arm can show that.

  NULL       arm is a byte-copy of the baseline
             -> every band HELD, verdict PROMOTABLE.
  DEGRADED   arm is the baseline blurred
             -> verdict NOT PROMOTABLE, and the reason must name structure.
             The blur makes the arm QUIETER in every band, so a harness that
             looked only at noise would promote it. That is the whole point.
  IMPROVED   arm is the baseline with band-confined noise REMOVED (so the
             baseline is the noisy one and the candidate is the clean one)
             -> scored as an improvement: CLEANER cells outnumber blur-trade,
             and structure does not fall.
  INCOMPLETE arm is missing masters
             -> INCONCLUSIVE, never PROMOTABLE. A partial arm must not be
             scored as a full one.

Run: python commission_recert.py     Exit 0 only if all four arms pass.
"""
import shutil
import sys
from pathlib import Path

import numpy as np
import tifffile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commission_bands import blur_rgb, plant_band_noise  # noqa: E402
from recert import BASELINE_DIR, CROPS, diff_gate, stage_pair, verdict  # noqa: E402

WORK = Path(r"D:\strehl-out\BUILD-OUTPUT\BUILD-RECERT\commission")
SUBJECTS = ["119MSDCF", "coffee-bean", "tweezers-cpl"]
STAGES = ["render", "gate", "pair"]


def make_arm(arm, fn):
    """Build a fake candidate arm from the shipping masters, transformed by `fn`."""
    d = WORK / arm
    d.mkdir(parents=True, exist_ok=True)
    for s in SUBJECTS:
        dst = d / f"{s}--{arm}.tiff"
        if dst.exists():
            continue
        src = BASELINE_DIR / f"{s}--SHIP-V4.tiff"
        a = tifffile.imread(str(src))
        tifffile.imwrite(str(dst), fn(a) if fn else a)
        del a
    return d


def blur_master(a):
    """Blur in 16-bit space, the way a softer merge would actually deliver it."""
    o = a.astype(np.float64)
    for c in range(o.shape[2]):
        o[..., c] = blur_rgb(o[..., c][..., None], 1, 2)[..., 0]
    return np.clip(o, 0, 65535).astype(np.uint16)


def noisy_master(a):
    """Add band-confined noise so the BASELINE is the noisy arm; the shipping
    master then plays the part of an improved candidate."""
    o = a.astype(np.float64)
    d8 = o / 65535.0 * 255.0
    noisy, _, landed = plant_band_noise(d8.astype(np.float32), "struct", factor=3.0)
    if not landed:
        raise SystemExit("REFUSED: improvement plant did not land; the arm would be untested")
    return np.clip(np.asarray(noisy, dtype=np.float64) / 255.0 * 65535.0, 0, 65535).astype(np.uint16)


def score(label, base_dir, arm_dir, arm, expect_promotable, want_reason=None):
    print(f"\n--- {label} ---")
    import recert
    old, recert.BASELINE_DIR = recert.BASELINE_DIR, base_dir
    try:
        pair = stage_pair(str(arm_dir), arm)
    finally:
        recert.BASELINE_DIR = old
    res = {"render": {"complete": True, "n_masters": len(SUBJECTS)},
           "gate": {"regressions": [], "expiries": []}, "pair": pair}
    ok, line = verdict(res, STAGES)
    print(f"  verdict: {line}")
    good = (ok == expect_promotable)
    if want_reason and want_reason not in line:
        good = False
    print(f"  {'PASS' if good else 'FAIL'}  [expected {'PROMOTABLE' if expect_promotable else 'NOT PROMOTABLE'}"
          + (f", naming '{want_reason}'" if want_reason else "") + "]")
    return good, pair


def commission_gate_diff():
    """The gate-diff rule, on synthetic states, with a plant at each end.

    This is a unit arm and not a render arm because the property under test is
    the RULE, not the renderer: which state transitions count as a regression.
    Running it against real masters would cost 370 s of gate time and would
    exercise only the transitions that corpus happens to contain -- and the one
    that mattered (PASS->SKIP) was absent from every arm until a real candidate
    produced twelve of them at once.
    """
    print("\n=== ARM: the gate-diff regression rule ===")
    base = {"states": {"a": "PASS", "b": "PASS", "c": "ACQUIT", "d": "PASS", "e": "ACQUIT"},
            "partition": "synthetic"}
    cases = [
        # (label, candidate states, subjects that MUST be named regressions)
        ("null -- nothing moved", dict(base["states"]), []),
        ("planted PASS->FAIL", {**base["states"], "a": "FAIL"}, ["a"]),
        ("planted PASS->SKIP (the gate crashed on it)",
         {**base["states"], "b": "SKIP"}, ["b"]),
        ("planted ACQUIT->FAIL", {**base["states"], "c": "FAIL"}, ["c"]),
        ("planted improvement ACQUIT->PASS", {**base["states"], "e": "PASS"}, []),
        ("all three damaging moves at once",
         {**base["states"], "a": "FAIL", "b": "SKIP", "c": "FAIL"}, ["a", "b", "c"]),
    ]
    ok = True
    for label, cand_states, want in cases:
        r = diff_gate({"states": base["states"], "partition": "synthetic"},
                      {"states": cand_states, "partition": "synthetic"})
        got = sorted(r[1])
        good = got == sorted(want)
        ok &= good
        print(f"  {label:46s} -> regressions {got}  want {sorted(want)}   "
              f"{'PASS' if good else 'FAIL'}")
    # The improvement arm is not decoration: a rule that named every move a
    # regression would pass all four damaging cases above and still be useless,
    # because it could never report that a candidate had FIXED something.
    print(f"  gate-diff rule {'PASSED' if ok else 'FAILED'}")
    return ok


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    base = WORK / "BASE"
    base.mkdir(parents=True, exist_ok=True)
    for s in SUBJECTS:
        dst = base / f"{s}--SHIP-V4.tiff"
        if not dst.exists():
            shutil.copy2(BASELINE_DIR / f"{s}--SHIP-V4.tiff", dst)
    results = []
    results.append(commission_gate_diff())

    a = make_arm("CNULL", None)
    results.append(score("NULL: arm is a byte-copy of the baseline", base, a, "CNULL", True)[0])

    a = make_arm("CBLUR", blur_master)
    ok, pair = score("DEGRADED: arm is the baseline blurred -- quieter in every band",
                     base, a, "CBLUR", False, "structure")
    results.append(ok)
    s = pair["summary"]
    print("  the trade, made visible rather than averaged away:")
    for b, v in s.items():
        print(f"    {b:7s} median d_floor {('%+.4f' % v['median_d_floor']) if v['median_d_floor'] is not None else '  -'}"
              f"  (quieter)   median d_structure "
              f"{('%+.4f' % v['median_d_structure']) if v['median_d_structure'] is not None else '  -'}  (softer)")

    # IMPROVED: baseline is the NOISY arm, candidate is the shipping master.
    nb = WORK / "NOISYBASE"
    nb.mkdir(parents=True, exist_ok=True)
    for s_ in SUBJECTS:
        dst = nb / f"{s_}--SHIP-V4.tiff"
        if not dst.exists():
            arr = tifffile.imread(str(BASELINE_DIR / f"{s_}--SHIP-V4.tiff"))
            tifffile.imwrite(str(dst), noisy_master(arr))
            del arr
    a = make_arm("CCLEAN", None)
    ok, pair = score("IMPROVED: baseline is noisy, arm is the clean shipping master",
                     nb, a, "CCLEAN", True)
    v = pair["summary"]["struct"]
    improved = v["cleaner"] > v["blur_trade"] and (v["median_d_structure"] or 0) >= -0.02
    print(f"  struct: cleaner {v['cleaner']} vs blur_trade {v['blur_trade']}, "
          f"median d_structure {v['median_d_structure']:+.4f}  "
          f"{'PASS' if improved else 'FAIL'}  [an improvement must be SCORED as one]")
    results.append(ok and improved)

    inc = {"render": {"complete": False, "n_masters": 2},
           "gate": {"regressions": [], "expiries": []}, "pair": {"summary": {}}}
    ok2, line = verdict(inc, STAGES)
    good = (not ok2) and "INCOMPLETE" in line
    print(f"\n--- INCOMPLETE: arm is missing masters ---\n  verdict: {line}\n"
          f"  {'PASS' if good else 'FAIL'}  [a partial arm must never be scored as a full one]")
    results.append(good)

    print("\n" + "=" * 92)
    if all(results):
        print(f"HARNESS COMMISSIONING PASSED -- {len(results)}/{len(results)} arms. A blurred arm is")
        print("refused despite being quieter in every band; a genuinely cleaner arm is scored as an")
        print("improvement; a partial arm is inconclusive.")
        return 0
    print(f"HARNESS COMMISSIONING FAILED -- {sum(results)}/{len(results)} arms passed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
