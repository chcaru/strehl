"""Run ORCH's noise_vs_detail.py VERBATIM on BUILD-BLEND's own paired renders.

ORCH's attribution -- that the high-frequency energy this arm adds is
correlated structure (recovered detail) rather than white noise -- was measured
on two pinned binaries. flatnoise_on_mine.py established that those pins are
not the arms that ship: ORCH's own instrument reads +32.1% on couch-fibers-cpl
for their renders and +3.6% for these, so the instruments agree and the RENDERS
differ.

That leaves the attribution untested on the shipping arm, which is the only arm
that matters. This runs ORCH's rho_add estimator, unmodified, on these renders.
The only change is flatnoise.TIFF_DIR, which noise_vs_detail reads for its
inputs.

The discriminator is ORCH's own: white noise has rho_lag1 ~ 0, so a measured
rho_add far above the counterfactual "would read if NOISE" column means the
added energy is band-limited structure. This does not bound every component --
a real noise increase can ride underneath a larger detail increase -- and that
caveat is ORCH's, kept here deliberately.
"""
import importlib.util
import sys
from pathlib import Path

ORCH_DIR = Path(r"C:\dev\strehl-out\ORCH-100")
STAGE = Path(r"C:\dev\strehl-out\BUILD-BLEND\flatnoise-mine")

if not any(STAGE.glob("*-before.tiff")):
    sys.exit(f"no staged pairs in {STAGE} -- run flatnoise_on_mine.py first")

# noise_vs_detail does `import flatnoise`, so ORCH's directory must be
# importable and flatnoise must be bound before it is imported.
sys.path.insert(0, str(ORCH_DIR))
import flatnoise  # noqa: E402

flatnoise.TIFF_DIR = STAGE  # the ONLY modification

spec = importlib.util.spec_from_file_location(
    "orch_noise_vs_detail", ORCH_DIR / "noise_vs_detail.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

print(f"ORCH's constants, unmodified: HP_RADIUS={flatnoise.HP_RADIUS} "
      f"TILE={flatnoise.TILE} N_TILES={flatnoise.N_TILES}")
print(f"inputs: {STAGE}\n")
sys.exit(mod.main())
