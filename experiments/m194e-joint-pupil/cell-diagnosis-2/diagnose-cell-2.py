"""Read the exact second full-run refusal without changing its numerical source."""
from pathlib import Path
import shutil
import sys
import traceback

import numpy as np

HERE = Path(__file__).resolve().parent
FROZEN = HERE / "float-run-2" / "source"
sys.path.insert(0, str(FROZEN))
from model import primary_scene, primary_frames, sha256, write_json
from render import render_cell, native_mask

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=False)
assert sha256(FROZEN / "render.py") == "a59e9686823d6f4ab2749dd8ca0f1a0bbf6cd847ee32ed04eef44dc78a87aba5"
scene, frame = primary_scene(), primary_frames()[3]
order = [(x, y) for by in range(0, 48, 8) for bx in range(0, 64, 8)
         for y in range(by, min(48, by + 8)) for x in range(bx, min(64, bx + 8))]
xy = order[255]
n, offset = native_mask(scene, frame)
record = dict(argv=sys.argv, orig_argv=sys.orig_argv, xoptions=sys._xoptions,
              executable=sys.executable, cwd=str(Path.cwd()), index_in_traversal=255,
              xy=xy, frame=3, inverse_focus=.875,
              sources={p: sha256(FROZEN / p) for p in ("model.py", "render.py")},
              diagnostic_source=sha256(Path(__file__)), source_directory=str(FROZEN))
for p in ("model.py", "render.py"):
    shutil.copyfile(FROZEN / p, out / p)
shutil.copyfile(Path(__file__), out / Path(__file__).name)
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
                         selected_indices=list(scope["indices"]),
                         allocated_budget=scope["integrator"].cell_tolerance * scope["area"],
                         cell_delta_e=abs(scope["high"] - scope["low"]),
                         h_vertices=(scope["triangle"] @ n - offset).tolist(),
                         max_low_point_error=float(scope["low_e"].max()),
                         max_high_point_error=float(scope["high_e"].max()),
                         max_low_point_error_xy=scope["low_xy"][np.argmax(scope["low_e"])].tolist(),
                         max_high_point_error_xy=scope["high_xy"][np.argmax(scope["high_e"])].tolist())
            record["triangles"].append(entry)
        tb = tb.tb_next
record["sources_after"] = {p: sha256(FROZEN / p) for p in record["sources"]}
assert record["sources_after"] == record["sources"]
write_json(out / "result.json", record)
print(record)
