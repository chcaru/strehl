from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("m76c_analysis", HERE / "analyse.py")
analysis = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(analysis)

y, x = np.mgrid[:256, :256]
pattern = np.cos(2 * np.pi * 20 * x / 128)
pattern = (pattern - pattern.mean()) / pattern.std()
bands = analysis.cross_bands(pattern, pattern)
mid_mean = float(np.mean(list(bands.values())))

assert np.isclose(pattern.var(), 1.0)
assert bands["b3_mid"] > 1.0
assert mid_mean > 1.0

print(f"spatial variance: {pattern.var():.7f}")
for name, value in bands.items():
    print(f"{name}: {value:.7f}")
print(f"equal-three-band mean: {mid_mean:.7f}")
print("PASS: a unit-variance pattern produces band-density power above 1")
