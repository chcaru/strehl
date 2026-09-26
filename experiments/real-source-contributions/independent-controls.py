"""Independent frozen-site and signed-profile commissioning. No RAW or build."""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
from pathlib import Path


def validate_plan(plan: dict) -> list[dict]:
    width, height = plan["native_size"]
    x0, y0, plane_width, plane_height = plan["cfa_plane_crop"]
    assert [width, height] == [2 * plane_width, 2 * plane_height]
    assert plan["native_origin"] == [2 * x0, 2 * y0]
    assert plan["offsets_native"] == [-8, -4, 0, 4, 8]
    covered = []
    for lo, hi in plan["source_bins_inclusive"]:
        assert 0 <= lo <= hi < plan["source_count"]
        covered.extend(range(lo, hi + 1))
    assert covered == list(range(plan["source_count"]))
    assert len(plan["profiles"]) == 5
    assert len({p["name"] for p in plan["profiles"]}) == 5
    result = []
    for profile in plan["profiles"]:
        assert profile["axis"] in ("x", "y")
        cx, cy = profile["centre_native"]
        rx, ry, rw, rh = profile["parent_roi"]
        assert 0 <= rx < rx + rw <= width and 0 <= ry < ry + rh <= height
        for offset in plan["offsets_native"]:
            x = cx + (offset if profile["axis"] == "x" else 0)
            y = cy + (offset if profile["axis"] == "y" else 0)
            assert rx <= x < rx + rw and ry <= y < ry + rh
            assert x % 2 == y % 2 == 0
            result.append({"profile": profile["name"], "offset": offset,
                           "native_xy": [x, y], "output_quad_xy": [x // 2, y // 2],
                           "reference_quad_xy": [x // 2 + x0, y // 2 + y0]})
    assert len(result) == 25
    assert len({tuple(p["native_xy"]) for p in result}) == 25
    return result


def signed_contrast(values: list[float]) -> float:
    assert len(values) == 5
    return values[2] - 0.5 * (values[0] + values[4])


def commission(plan: dict) -> dict:
    sites = validate_plan(plan)
    rejected = []
    for name, mutate in [
        ("duplicate-temporal-membership", lambda p: p["source_bins_inclusive"][1].__setitem__(0, 79)),
        ("missing-temporal-member", lambda p: p["source_bins_inclusive"][1].__setitem__(0, 81)),
        ("wrong-native-gauge", lambda p: p["native_origin"].__setitem__(0, 383)),
        ("outside-registered-witness", lambda p: p["profiles"][0]["centre_native"].__setitem__(0, 3200)),
        ("wrong-quad-phase", lambda p: p["profiles"][0]["centre_native"].__setitem__(0, 3511)),
    ]:
        bad = copy.deepcopy(plan)
        mutate(bad)
        try:
            validate_plan(bad)
        except AssertionError:
            rejected.append(name)
        else:
            raise AssertionError(f"Plan checker did not reject {name}")

    # Deterministic signals validate this statistic, not image quality or noise.
    profile = [100.0, 112.0, 140.0, 112.0, 100.0]
    flat = [100.0] * 5
    translated = [140.0, 112.0, 100.0, 100.0, 100.0]
    assert signed_contrast(profile) == 40.0
    assert signed_contrast([x + 10000 for x in profile]) == signed_contrast(profile)
    assert signed_contrast([300 - x for x in profile]) == -signed_contrast(profile)
    assert signed_contrast(flat) == 0.0
    assert signed_contrast(translated) == -20.0
    assert signed_contrast(profile) != signed_contrast(translated)
    return {"scope": "Independent plan arithmetic and signed-profile commissioning only; no RAW, quality, noise or trace-result claim",
            "sites": sites, "rejected_mutants": rejected,
            "profile_contrast": signed_contrast(profile),
            "uniform_offset_contrast": signed_contrast([x + 10000 for x in profile]),
            "reversed_contrast": signed_contrast([300 - x for x in profile]),
            "translated_contrast": signed_contrast(translated),
            "flat_contrast": signed_contrast(flat), "passed": True}


def commission_analysis(plan: dict, directory: Path) -> dict:
    """Exercise the author's real analysis path with independently known data."""
    import numpy as np

    specification = importlib.util.spec_from_file_location("commissioned_analysis", Path(__file__).with_name("analyze.py"))
    analysis = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(analysis)
    directory.mkdir(exist_ok=False)
    source = directory / "fixture"
    source.mkdir()
    sites = [p["output_quad_xy"] for p in validate_plan(plan)]
    sizes = [[3134, 2088]]
    for _ in range(7):
        sizes.append([(n + 1) // 2 for n in sizes[-1]])
    nodes = [sorted({y * sizes[0][0] + x for x, y in sites})]
    # Deliberately derive dependency membership by the footprint inequality,
    # not by calling the author's taps or closure helper.
    for k in range(1, 8):
        selected = set()
        for address in nodes[-1]:
            x, y = address % sizes[k - 1][0], address // sizes[k - 1][0]
            xs = [i for i in range(max(0, x // 2 - 1), min(sizes[k][0], x // 2 + 2)) if abs(2 * i - x) <= 2]
            ys = [i for i in range(max(0, y // 2 - 1), min(sizes[k][1], y // 2 + 2)) if abs(2 * i - y) <= 2]
            selected.update(yy * sizes[k][0] + xx for yy in ys for xx in xs)
        nodes.append(sorted(selected))
    matrices = analysis.expansion_matrices(sizes, nodes, sites)
    for matrix in matrices:
        assert np.array_equal(matrix @ np.ones(matrix.shape[1]), np.ones(25))
    # A known diagonal noncentral coarse tap contributes exactly 1/64.
    m = analysis.expansion_matrices([[128, 96], [64, 48]],
        [[4 * 128 + 4], [y * 64 + x for y in (1, 2, 3) for x in (1, 2, 3)]], [[4, 4]])[1]
    assert m[0, 0] == 1 / 64 and m[0, 4] == 9 / 16
    assert (m @ np.array([64.0] + [0.0] * 8))[0] == 1.0

    scalar = np.tile([100.0, 112.0, 140.0, 112.0, 100.0], 5)
    cfa = np.repeat(scalar[:, None], 4, axis=1)
    for value in (scalar, cfa, np.stack([cfa, cfa])):
        assert np.all(analysis.contrast(value) == 40.0)
        assert np.array_equal(analysis.contrast(value + 10000), analysis.contrast(value))
        assert np.array_equal(analysis.contrast(300 - value), -analysis.contrast(value))
    assert np.all(analysis.contrast(np.tile([140.0, 112.0, 100.0, 100.0, 100.0], 5)) == -20.0)

    record = 100 + sum(map(len, nodes)) * 7
    raw = np.zeros((488, record), dtype="<f4")
    states = np.zeros((sum(map(len, nodes)), 13), dtype="<f4")
    # Equal and opposite AC exactly straddle a temporal boundary; their final
    # sum is zero, so a totals-only check cannot detect wrong bin attribution.
    amplitudes = np.zeros(488, dtype=np.float32)
    amplitudes[79], amplitudes[80] = 16.0, -16.0
    base = (96 + np.arange(488) % 4).astype(np.float32)
    raw[:, :100] = np.repeat((base + amplitudes)[:, None], 100, axis=1)
    cursor, pos = 100, 0
    for k, nn in enumerate(nodes):
        count = len(nn)
        values = amplitudes if k == 0 else base if k == 7 else np.zeros(488, dtype=np.float32)
        segment = raw[:, cursor:cursor + 7 * count].reshape(488, count, 7)
        segment[:, :, 3:] = values[:, None, None]
        total = np.float32(0.0)
        for value in values:
            total = np.float32(total + value)
        states[pos:pos + count, 5:9] = total
        states[pos:pos + count, 9:13] = np.float32(total * np.float32(1 / 488))
        cursor += 7 * count
        pos += count
    expected = float(np.float32(base.sum(dtype=np.float32) * np.float32(1 / 488)))
    bits = int(np.array(expected, dtype=np.float32).view(np.uint32))
    layout = {"schema": 1, "count": 488, "per_chunk": 122, "numerator_scale": 65536,
        "sizes": sizes, "nodes": nodes, "quad_sites": sites, "native_offsets": plan["offsets_native"],
        "source_record_floats": record, "temporal_groups_inclusive": plan["source_bins_inclusive"],
        "native_lines": [{"name": p["name"], "centre": p["centre_native"], "axis": 0 if p["axis"] == "x" else 1} for p in plan["profiles"]]}
    receipt = {"schema": 1, "sources": 488, "all_sampled_chunk_accumulators_bit_exact": True,
        "all_final_accumulators_bit_exact": True, "all_sampled_final_cfa_bit_exact": True,
        "sites": [{"quad": p, "pre_hull": [expected] * 4, "post_hull": [expected] * 4,
            "pre_hull_bits": [bits] * 4, "post_hull_bits": [bits] * 4, "bounds": [[0.0, 200.0]] * 4} for p in sites]}
    for name, value in [("layout.json", layout), ("receipt.json", receipt)]:
        (source / name).write_text(json.dumps(value), encoding="utf-8")
    raw.tofile(source / "sources.f32")
    states.tofile(source / "final-states.f32")
    analysis.analyze(source, directory / "result")
    result = json.loads((directory / "result" / "attribution.json").read_text(encoding="utf-8"))
    rows = result["temporal"]
    first_ac = next(row for row in rows if row["group_inclusive"] == [0, 79] and row["band"] == 0)
    second_ac = next(row for row in rows if row["group_inclusive"] == [80, 168] and row["band"] == 0)
    assert np.allclose(first_ac["signed_site_radiance_dn"], 16 / 488, rtol=0, atol=1e-15)
    assert np.allclose(second_ac["signed_site_radiance_dn"], -16 / 488, rtol=0, atol=1e-15)
    # Independent expected attribution rejects reversal despite identical
    # summed reconstruction. This commissions the loaded per-source path.
    raw[[79, 80]] = raw[[80, 79]]
    raw.tofile(source / "sources.f32")
    analysis.analyze(source, directory / "wrong-source-order")
    wrong = json.loads((directory / "wrong-source-order" / "attribution.json").read_text(encoding="utf-8"))
    wrong_ac = next(row for row in wrong["temporal"] if row["group_inclusive"] == [0, 79] and row["band"] == 0)
    assert not np.allclose(wrong_ac["signed_site_radiance_dn"], 16 / 488, rtol=0, atol=1e-15)
    raw[[79, 80]] = raw[[80, 79]]
    raw.tofile(source / "sources.f32")
    # The actual parser must refuse changed temporal membership, rather than
    # silently treating bins as a plotting annotation.
    bad = copy.deepcopy(layout)
    bad["temporal_groups_inclusive"][1][0] = 79
    (source / "layout.json").write_text(json.dumps(bad), encoding="utf-8")
    try:
        analysis.analyze(source, directory / "invalid-bin")
    except AssertionError:
        pass
    else:
        raise AssertionError("analysis accepted duplicate temporal membership")
    (source / "layout.json").write_text(json.dumps(layout), encoding="utf-8")
    return {"actual_analysis_path_passed": True, "fixture": str(source.resolve()),
            "known_noncentral_tap_gain": 1 / 64, "known_first_bin_ac_dn": 16 / 488,
            "wrong_source_order_rejected_by_independent_attribution": True,
            "invalid_temporal_membership_refused": True,
            "scope": "Synthetic accounting commission; claimed actual-consumer receipt flags are fixture values, never real RAW evidence"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, default=Path(__file__).with_name("independent-plan.json"))
    parser.add_argument("--out", type=Path)
    parser.add_argument("--analysis-dir", type=Path)
    args = parser.parse_args()
    result = commission(json.loads(args.plan.read_text(encoding="utf-8")))
    if args.analysis_dir:
        result["analysis"] = commission_analysis(json.loads(args.plan.read_text(encoding="utf-8")), args.analysis_dir)
    text = json.dumps(result, indent=2) + "\n"
    if args.out:
        with args.out.open("x", encoding="utf-8", newline="\n") as output:
            output.write(text)
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
