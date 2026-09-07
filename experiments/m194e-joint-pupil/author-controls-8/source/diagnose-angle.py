"""Inspect the original registered angular refusal without changing its method."""
import json
import math
from pathlib import Path
import sys
import traceback

import numpy as np

from model import Field, Frame, Scene, Similarity, sha256, write_json
from render import Integrator, Meter, render_cell

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=False)
c = np.array((37.23, 24.61))
n = np.array((12 / 13, 5 / 13))
s, angle = 1.037, .071
matrix = np.array(((math.cos(angle), -math.sin(angle)), (math.sin(angle), math.cos(angle)))) * s
b = c - matrix @ c + (.31, -.27)
inverse = np.linalg.inv(matrix)
translation = inverse @ (c - b) - c
sim = Similarity(1 / s, -angle, tuple(c), tuple(translation))
scene = Scene(Field(12000), Field(10000 - 800 * n @ c, tuple(800 * n)), (1.25, 2.5), tuple(n), float(n @ c))
frame = Frame(0, .53, 11, sim)
record = dict(sources={p: sha256(Path(__file__).parent / p) for p in ("model.py", "render.py", "diagnose-angle.py")}, argv=sys.argv)
try:
    record["result"] = render_cell(scene, frame, c)
except Exception as exc:
    record["error"] = repr(exc)
    record["traceback"] = traceback.format_exc()
    tb = exc.__traceback__
    while tb:
        scope = tb.tb_frame.f_locals
        if tb.tb_frame.f_code.co_name == "render_points":
            bad = ~scope["good"]
            ix = scope["ix"][bad]
            record["diagnostic"] = {k: np.asarray(scope[k])[bad].tolist() for k in ("a", "b", "budget", "low", "high", "error")}
            record["diagnostic"].update(xy=scope["xy"][ix].tolist(), depth=scope["depth"], h=scope["h"][ix].tolist(),
                                        radius=scope["radius"], alpha=scope["alpha"], start=scope["start"])
        tb = tb.tb_next
write_json(out / "result.json", record)
print(json.dumps(record, indent=2))
