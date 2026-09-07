"""Re-derive complete diagnostic leaf partitions; never an admission receipt."""
import hashlib
import json
import math
from pathlib import Path
import sys
import numpy as np

HERE = Path(__file__).resolve().parent
path = HERE / "cell-allocation-2/result.json"
assert hashlib.sha256(path.read_bytes()).hexdigest() == "5b4932da5b6807e3746dab7c8a4c02ad7cea8f899d08c61bbb4e4c5d01f48291"
j = json.loads(path.read_text())
nodes = j["nodes"]
assert len(nodes) == 508 and j["sources_before"] == j["sources_after"]
reference_path = HERE / "independent-reference-1/result.json"
assert hashlib.sha256(reference_path.read_bytes()).hexdigest() == "8791700cdc969847ff75f9fbd9205739ee2135ac4bbbdbe445d00b6664c7eccc"
reference = json.loads(reference_path.read_text())
ref = next(r["array"] for r in reference["frames"] if r["arm"] == "refined" and r["index"] == 3)
array_path = reference_path.parent / ref["path"]
assert hashlib.sha256(array_path.read_bytes()).hexdigest() == ref["sha256"]
truth = float(np.load(array_path, allow_pickle=False)[7, 31])


def area(t):
    a, b, c = t
    return abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])) / 2


def indicator(node):
    return abs(node["high_e"] - node["low_e"]) + node["low_pupil_e"] + node["high_pupil_e"]


for key, n in nodes.items():
    assert n["depth"] == key.count("/") and 0 <= n["depth"] <= 6
    assert n["area"] > 0 and abs(area(n["triangle"]) - n["area"]) <= 1e-13
    assert math.isfinite(indicator(n)) and n["low_pupil_e"] >= 0 and n["high_pupil_e"] >= 0
    assert abs(indicator(n) - n["indicator_e"]) <= 1e-15
    if n["depth"] < 6:
        assert n["children"] == [key + "/0", key + "/1"]
        children = [nodes[k] for k in n["children"]]
        assert abs(sum(c["area"] for c in children) - n["area"]) <= 1e-13
        parent_vertices = {tuple(v) for v in n["triangle"]}
        child_vertices = {tuple(v) for c in children for v in c["triangle"]}
        assert parent_vertices <= child_vertices and len(child_vertices - parent_vertices) == 1
        midpoint = next(iter(child_vertices - parent_vertices))
        assert any(max(abs(midpoint[q] - (a[q] + b[q]) / 2) for q in (0, 1)) <= 1e-13
                   for a in n["triangle"] for b in n["triangle"] if a != b)
    else:
        assert not n["children"]


def aggregate(keys):
    keys = sorted(keys)
    assert len(keys) == len(set(keys))
    assert not any(b.startswith(a + "/") for a in keys for b in keys)
    # Each of the four root binary trees is fully covered without overlap.
    for root in ("root-0", "root-1", "root-2", "root-3"):
        assert sum(2. ** -nodes[k]["depth"] for k in keys if k == root or k.startswith(root + "/")) == 1
    high = math.fsum(nodes[k]["high_e"] for k in keys)
    low = math.fsum(nodes[k]["low_e"] for k in keys)
    cell = math.fsum(indicator(nodes[k]) for k in keys)
    pupil = math.fsum(nodes[k]["high_pupil_e"] for k in keys)
    covered = math.fsum(nodes[k]["area"] for k in keys)
    assert abs(covered - 1) < 1e-12
    return dict(leaves=len(keys), area=covered, cell_indicator_e=cell, high_pupil_indicator_e=pupil,
                high_e=high, low_e=low, abs_truth_error_e=abs(high - truth),
                within_existing_global_budgets=cell <= .00075 and pupil <= .00025,
                local_failures=[k for k in keys if indicator(nodes[k]) > .00075 * nodes[k]["area"]], paths=keys)


def local_stop(key):
    n = nodes[key]
    if indicator(n) <= .00075 * n["area"] or n["depth"] == 6:
        return [key]
    return [leaf for child in n["children"] for leaf in local_stop(child)]


roots = ["root-" + str(i) for i in range(4)]
original = aggregate([k for root in roots for k in local_stop(root)])
assert original["paths"] == j["original_local_terminal"]["paths"]
sequence = []
frontier = roots.copy()
while True:
    row = aggregate(frontier)
    sequence.append(row)
    if row["within_existing_global_budgets"]:
        break
    eligible = [k for k in frontier if nodes[k]["depth"] < 6]
    if not eligible:
        raise AssertionError("recorded tree cannot meet unchanged global bars")
    chosen = min(eligible, key=lambda k: (-indicator(nodes[k]), k))
    frontier.remove(chosen)
    frontier.extend(nodes[chosen]["children"])
assert len(sequence) == len(j["diagnostic_global_sequence"])
for ours, reported in zip(sequence, j["diagnostic_global_sequence"]):
    assert ours["paths"] == reported["paths"]
    for field in ("area", "cell_indicator_e", "high_pupil_indicator_e", "high_e", "low_e"):
        assert abs(ours[field] - reported[field]) < 1e-9
uniform = aggregate([k for k, n in nodes.items() if n["depth"] == 6])
assert len(uniform["paths"]) == 256
result = dict(schema="m194e-independent-allocation-read-v1", status="DIAGNOSTIC_VERIFIED_NOT_ADMITTED", command=sys.argv,
              author_diagnostic_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), nodes_checked=len(nodes),
              source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), reference_e=truth,
              initial=sequence[0], original_local_terminal=original, global_terminal=sequence[-1],
              global_splits=len(sequence) - 1, uniform_depth6=uniform,
              scope="raw-table partition/accounting review; no new radiance evaluation or renderer admission")
out = HERE / "independent-allocation-read.json"
if out.exists():
    raise FileExistsError("preserve prior independent diagnostic")
out.write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf8")
print(json.dumps({k: v for k, v in result.items() if k not in ("initial", "original_local_terminal", "global_terminal", "uniform_depth6")}))
print(json.dumps({name: {k: v for k, v in result[name].items() if k != "paths"} for name in ("original_local_terminal", "global_terminal")}))
