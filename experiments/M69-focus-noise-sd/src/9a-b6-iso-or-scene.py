"""M69 arm B6 -- is P2's failure at ISO 1000 about the ISO or about the scene?

POST HOC, and it exists to remove a confound in B5 rather than to test a
hypothesis of its own.

B5 found P2 tracks the measured chain to +-3.6% on 10 of 12 stacks and
under-predicts by 34% (foam) and 59% (coffee-bubbles). Those two are exactly
the corpus's only two ISO-1000 stacks -- a perfect association at n = 2. They
are also both fine, self-similar, bubble/foam texture. **ISO is confounded with
scene and B5 cannot separate them.**

This arm holds the SCENE FIXED and sweeps the DECLARED ISO, using the model
consistently for injection, normalisation and P2 at every step.

READING RULE, fixed before the run:

  * If a low-ISO scene's meas/P2 CLIMBS toward B5's 1.3-1.6 as the declared ISO
    rises, the driver is the noise level and P2 has an ISO domain limit.
  * If it stays within B5's good band (0.96-1.03) across the whole sweep, the
    driver is the scene and P2 has a texture domain limit instead.
  * If it moves but by less than half the gap, both contribute and this arm
    says so rather than picking one.

ASYMMETRY, declared in advance: RAISING the declared ISO on a low-ISO latent is
clean -- it adds noise the model knows about. LOWERING it on a high-ISO latent
is NOT -- the latent already contains ISO-1000 noise that cannot be removed.
The lowering arm is run and reported but is labelled confounded, and no
conclusion rests on it.
"""

import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m69  # noqa: E402

a2 = __import__("importlib").import_module("20-a2-m66-replication")
p2m = __import__("importlib").import_module("40-p2-predictor")
bmod = __import__("importlib").import_module("97-b-fine-field")
b5 = __import__("importlib").import_module("99-b5-p2-vs-measured")

ISOS = [50, 100, 200, 400, 1000, 3200]
SCENES = [
    ("bee-1", 100, "clean: raising ISO adds noise the model knows about"),
    ("coffee-bean", 50, "clean: raising ISO adds noise the model knows about"),
    ("coffee-bubbles", 1000, "CONFOUNDED below its native ISO -- see docstring"),
]


def main():
    m69.banner("M69 arm B6 -- ISO or scene?  (POST HOC, confound removal)")
    m69.dump_constants()
    b = json.loads((m69.OUT / "97-b-fine-field.json").read_text(encoding="utf-8"))
    c = b["b1"]["coarse+reg"]["sd"]
    prior = json.loads((m69.OUT / "99-b5.json").read_text(encoding="utf-8"))["rows"]

    out = {}
    for stack, native, note in SCENES:
        files = m69.stack_files(stack)
        mid = files[len(files) // 2]
        raw = b5.crop_of(mid)
        print(f"\n  --- {stack}  (native ISO {native};  B5 meas/P2 = "
              f"{prior[stack]['meas_over_p2']:.3f})")
        print(f"      {note}")
        print(f"      {'ISO':>6} {'P2':>9} {'MEASURED':>10} {'meas/P2':>9} {'native?':>8}")
        rows = {}
        for iso in ISOS:
            p2v = b5.p2_rho_obs(raw, iso)
            mv = b5.measured_rho_obs(raw, iso, m69.WINDOW_RADIUS,
                                     m69.REGULARISER_RADIUS, c)
            flag = "<-- native" if iso == native else ""
            print(f"      {iso:>6} {p2v:>9.4f} {mv:>10.4f} {mv / p2v:>9.3f} {flag:>8}")
            rows[iso] = {"p2": p2v, "measured": mv, "ratio": mv / p2v}
        out[stack] = {"native_iso": native, "b5_ratio": prior[stack]["meas_over_p2"],
                      "sweep": rows}

    m69.banner("B6 -- the reading rule applied")
    for stack, native, _ in SCENES:
        r = out[stack]["sweep"]
        lo, hi = r[ISOS[0]]["ratio"], r[ISOS[-1]]["ratio"]
        print(f"  {stack:<16} ISO {ISOS[0]:>4} -> {ISOS[-1]:<5} "
              f"meas/P2 {lo:.3f} -> {hi:.3f}   swing {hi / lo:.3f}x")
    clean = [s for s, n, _ in SCENES if s != "coffee-bubbles"]
    print("\n  Clean (raising) arms only:")
    for s in clean:
        r = out[s]["sweep"]
        at1000 = r[1000]["ratio"]
        print(f"    {s:<16} at declared ISO 1000: meas/P2 = {at1000:.3f}"
              f"   (B5's ISO-1000 stacks: 1.335 foam, 1.591 coffee-bubbles;"
              f" B5's good band 0.96-1.03)")
    (m69.OUT / "9a-b6.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("\n  wrote out/9a-b6.json")


if __name__ == "__main__":
    main()
