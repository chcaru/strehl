"""Inspect the first full-run cell refusal on its frozen numerical source."""
from pathlib import Path
import sys
import traceback

import numpy as np

from model import primary_scene, primary_frames, sha256, write_json
from render import render_cell, native_mask

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=False)
here = Path(__file__).resolve().parent
assert sha256(here / "render.py") == "ef52c45d28ec2dda5aa897cfd57dacc4b4a3e300d3a581c35f305c76e2dd03f8"
scene, frame = primary_scene(), primary_frames()[3]
order = [(x, y) for by in range(0, 48, 8) for bx in range(0, 64, 8) for y in range(by, min(48, by + 8)) for x in range(bx, min(64, bx + 8))]
xy = order[230]
n, offset = native_mask(scene, frame)
record = dict(argv=sys.argv, index_in_traversal=230, xy=xy, frame=3, inverse_focus=.875,
              sources={p: sha256(here / p) for p in ("model.py", "render.py", "diagnose-cell.py")})
try:
    record["result"] = render_cell(scene, frame, xy)
except Exception as exc:
    record["error"] = repr(exc)
    record["traceback"] = traceback.format_exc()
    record["triangles"] = []
    tb = exc.__traceback__
    while tb:
        scope = tb.tb_frame.f_locals
        if tb.tb_frame.f_code.co_name == "integrate_triangle":
            entry = {k: float(scope[k]) for k in ("area", "low", "high", "pl", "ph", "indicator")}
            entry.update(depth=scope["depth"], triangle=scope["triangle"].tolist(),
                         allocated_budget=scope["integrator"].cell_tolerance * scope["area"],
                         cell_delta_e=abs(scope["high"] - scope["low"]),
                         h_vertices=(scope["triangle"] @ n - offset).tolist(),
                         max_low_point_error=float(scope["low_e"].max()), max_high_point_error=float(scope["high_e"].max()),
                         max_low_point_error_xy=scope["low_xy"][np.argmax(scope["low_e"])].tolist(),
                         max_high_point_error_xy=scope["high_xy"][np.argmax(scope["high_e"])].tolist())
            record["triangles"].append(entry)
        tb = tb.tb_next
write_json(out / "result.json", record)
print(record)
