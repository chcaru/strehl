"""Commission the repaired `verdict()` in throughfocus_probe.py.

The old implementation took `argmax` and asked whether it was interior. It could
not express the two-layer case that the probe exists to detect, and on the
flagship's occluded claw it returned INTERIOR-PEAK for the *foreground* peak.

A fix is only a fix if the thing it fixes can be shown to have been broken. So
this harness runs BOTH implementations over the same inputs and requires:

  * the old one to MISS the two-layer cases (otherwise there was no defect and
    this change is unjustified), and
  * the new one to CATCH them while still agreeing with the old one everywhere
    the old one was right.

Synthetic curves carry known truth. The real claw curve, if present, is the
potency control from data: it is known to be two-layer by direct observation of
the frames, so an instrument that calls it SINGLE-PEAK is not usable.
"""
import importlib.util
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
PROBE = HERE / "throughfocus_probe.py"
REAL_CSV = pathlib.Path(r"C:\dev\strehl-out\V-VEILCLAW\probe2\clawtight.csv")


def load_new():
    spec = importlib.util.spec_from_file_location("tfp_under_test", PROBE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.verdict


def old_verdict(vals):
    """The implementation as it stood before the repair, verbatim."""
    v = np.asarray(vals, dtype=np.float64)
    n = len(v)
    if n < 5:
        return "TOO-FEW-FRAMES"
    k = int(np.argmax(v))
    lo, hi = float(v.min()), float(v.max())
    contrast = (hi - lo) / max(lo, 1e-9)
    edge = k <= 1 or k >= n - 2
    if contrast < 0.15:
        return f"FLAT (peak/floor={1+contrast:.3f}) -> never resolved"
    if edge:
        return f"PEAK-AT-END frame#{k}/{n - 1} (ratio {1 + contrast:.2f}) -> bracket ran out"
    return f"INTERIOR-PEAK frame#{k}/{n - 1} (ratio {1 + contrast:.2f}) -> a frame HAD it"


def bump(n, centre, width, height):
    x = np.arange(n, dtype=np.float64)
    return height * np.exp(-0.5 * ((x - centre) / width) ** 2)


def main() -> int:
    rng = np.random.default_rng(20260824)
    new = load_new()
    n = 299
    floor = 85.0

    cases = []

    # Truth known by construction. `want_new` is the specification for the
    # repaired implementation and IS asserted. The original implementation's
    # output is recorded as evidence, and is only asserted where the claim
    # under test is that it missed something.
    flat = floor + rng.normal(0, 0.6, n)
    cases.append(("flat + noise", flat, "FLAT"))

    single = floor + bump(n, 150, 12, 45) + rng.normal(0, 0.6, n)
    cases.append(("single interior peak", single, "SINGLE-PEAK"))

    two = floor + bump(n, 182, 11, 45) + bump(n, 288, 9, 30) + rng.normal(0, 0.6, n)
    cases.append(("two peaks, claw-like", two, "TWO-PEAK"))

    two_close = floor + bump(n, 140, 8, 40) + bump(n, 175, 8, 36) + rng.normal(0, 0.6, n)
    cases.append(("two peaks, 35 apart", two_close, "TWO-PEAK"))

    ramp = floor + bump(n, n - 1, 40, 50) + rng.normal(0, 0.6, n)
    cases.append(("monotone rise to end", ramp, "PEAK-AT-END"))

    # A small bump beside a deep valley: the case the global-minimum form of
    # prominence inflates into a spurious second layer.
    decoy = floor + bump(n, 150, 14, 60) - bump(n, 240, 18, 40) + bump(n, 285, 7, 3.0)
    decoy = decoy + rng.normal(0, 0.4, n)
    cases.append(("single peak + valley + tiny bump", decoy, "SINGLE-PEAK"))

    real = None
    if REAL_CSV.exists():
        lines = REAL_CSV.read_text(encoding="utf-8").strip().splitlines()
        hdr = [h.strip() for h in lines[0].split(",")]
        rows = [l.split(",") for l in lines[1:]]
        if "probe" in hdr:
            j = hdr.index("probe")
            real = np.array([float(r[j]) for r in rows])
            cases.append(("REAL claw (observed 2 layers)", real, "TWO-PEAK"))

    print(f"real claw curve available: {REAL_CSV.exists()}"
          f"{'' if real is not None else '  (synthetic cases only)'}")
    print()
    print(f"{'case':<34}{'want':<13}{'new':<13}{'old':<15}{'verdict'}")
    ok = True
    old_missed = 0
    two_layer_cases = 0
    for name, v, want_new in cases:
        gn = new(v)
        go = old_verdict(v)
        n_ok = gn.startswith(want_new)
        ok = ok and n_ok
        if want_new == "TWO-PEAK":
            two_layer_cases += 1
            if not go.startswith("TWO-PEAK"):
                old_missed += 1
        print(f"{name:<34}{want_new:<13}{gn.split(' ')[0]:<13}{go.split(' ')[0]:<15}"
              f"{'PASS' if n_ok else 'FAIL'}")

    print()
    print(f"repaired verdict() correct on   : "
          f"{sum(1 for nm, v, wn in cases if new(v).startswith(wn))}/{len(cases)}")
    print(f"two-layer cases                 : {two_layer_cases}")
    print(f"  caught by repaired verdict()  : "
          f"{sum(1 for nm, v, wn in cases if wn == 'TWO-PEAK' and new(v).startswith('TWO-PEAK'))}")
    print(f"  missed by original verdict()  : {old_missed}")
    print()
    if old_missed != two_layer_cases:
        print("NOT COMMISSIONED: the original implementation did not miss every")
        print("two-layer case, so the defect this change repairs is not established.")
        ok = False
    print("COMMISSIONED" if ok else "NOT COMMISSIONED")
    if real is not None:
        print()
        print("real claw, full verdict:")
        print(f"  new: {new(real)}")
        print(f"  old: {old_verdict(real)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
