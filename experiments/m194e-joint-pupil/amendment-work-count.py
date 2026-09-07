"""Prospective geometry-only work count; no radiance/integral evaluation."""
from dataclasses import asdict
from pathlib import Path
import sys
import time

import numpy as np

from model import primary_scene, primary_frames, sha256, write_json
from render import cell_triangles, native_mask, triangle_rule, integrator_for

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=False)
started = time.monotonic()
scene = primary_scene()
records = []
for arm in ("primary", "angle-refined", "cell-refined"):
    integrator = integrator_for(arm)
    for frame in primary_frames():
        n, offset = native_mask(scene, frame)
        radius = abs(frame.defocus(scene)[0]) * np.linalg.norm(n)
        points = old_intervals = ladder_intervals = max_intervals = triangles = 0
        for y in range(48):
            for x in range(64):
                ts = cell_triangles(scene, frame, (x, y))
                triangles += len(ts)
                for triangle in ts:
                    for order in (integrator.cell_low, integrator.cell_high):
                        xy, _ = triangle_rule(triangle, order)
                        q0 = frame.forward_similarity.inverse(xy)
                        h = np.abs(q0[:, 0] * scene.mask_normal[0] + q0[:, 1] * scene.mask_normal[1] - scene.mask_offset)
                        partial = h < radius if radius else np.zeros(len(h), dtype=bool)
                        base = np.where(partial & (h > 0), 4, np.where(partial, 2, 1))
                        ladder = base.copy()
                        if radius:
                            eta = h / radius
                            for j in range(1, 33):
                                ladder += 2 * ((eta > 0) & (eta < 2. ** -j))
                        points += len(h)
                        old_intervals += int(base.sum())
                        ladder_intervals += int(ladder.sum())
                        max_intervals = max(max_intervals, int(ladder.max()))
        nodes = (integrator.angle_low + integrator.angle_high) * ladder_intervals
        item = dict(arm=arm, frame=frame.index, nominal_triangles=triangles, nominal_point_calls=points,
                    original_nominal_intervals=old_intervals, proposed_nominal_intervals=ladder_intervals,
                    proposed_max_intervals_per_point=max_intervals, proposed_nominal_angular_nodes=nodes,
                    remaining_node_ceiling=600_000_000 - nodes)
        records.append(item)
        print(item, flush=True)
result = dict(schema="m194e-prospective-geometric-work-v1", status="DERIVED_FROM_GEOMETRY_NOT_TIMING", argv=sys.argv,
              source_hashes={p: sha256(Path(__file__).parent / p) for p in ("model.py", "render.py", "amendment-work-count.py")},
              records=records, calculation_wall_seconds=time.monotonic() - started)
write_json(out / "result.json", result)
