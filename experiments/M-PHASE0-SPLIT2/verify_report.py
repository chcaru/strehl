"""Independently derive every load-bearing SPLIT2 report literal."""

from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path


LANE = Path(__file__).resolve().parent
OUT = LANE / "out"
NOTE = LANE.parents[1] / "docs" / "research" / "M-PHASE0-SPLIT2.md"


def require(text: str, literal: str) -> None:
    if literal not in text:
        raise AssertionError(f"missing report literal: {literal!r}")


def verify(*, plant_report_value: bool) -> dict[str, object]:
    note = NOTE.read_text(encoding="utf-8")
    metadata = json.loads((OUT / "capture-manifest.json").read_text(encoding="utf-8"))
    metadata_commission = json.loads(
        (OUT / "validator-commission.json").read_text(encoding="utf-8")
    )
    commission = json.loads((OUT / "commission.json").read_text(encoding="utf-8"))
    gate = json.loads((OUT / "pixel-gate.json").read_text(encoding="utf-8"))
    independent = json.loads(
        (OUT / "pixel-gate-verification.json").read_text(encoding="utf-8")
    )

    file_count = int(metadata["files"]) + (1 if plant_report_value else 0)
    require(note, f"{file_count} contiguous ARWs")
    require(
        note,
        f"`{metadata['filename_first']}`–`{metadata['filename_last']}`",
    )
    assert len(metadata["groups"]) == 18
    assert all(len(group["files"]) == 32 for group in metadata["groups"])
    assert all(count == 64 for count in metadata["iso_counts"].values())
    focus = metadata["focus_numeric_values"]["FocusDistance2"]
    assert focus == ["0.273841307296975"]
    require(note, f"`FocusDistance2 = {focus[0]} m`")
    assert metadata["image_stabilization_labels"] == ["On"]
    assert metadata["image_stabilization_tag_count"] == metadata["files"]
    require(note, "`ImageStabilization = On`")

    durations = [float(group["duration_seconds"]) for group in metadata["groups"]]
    gaps = [
        float(group["inter_frame_gap_seconds"]["maximum"])
        for group in metadata["groups"]
    ]
    brightness_ranges = [
        float(group["brightness_value_ev"]["range"])
        for group in metadata["groups"]
    ]
    shifts = [float(value) for value in metadata["light_shift_ev_pass2_minus_pass1"].values()]
    require(note, f"{min(durations):.3f}–{max(durations):.3f} s")
    require(note, f"{max(gaps):.3f} s")
    require(note, f"{abs(max(shifts)):.6f}–{abs(min(shifts)):.6f} EV darker")
    require(note, f"{max(brightness_ranges):.6f} EV")

    counts = Counter(tuple(value) for value in gate["stability"]["shifts"])
    assert counts == Counter({(0, 0): 1, (1, 0): 21, (2, 0): 10})
    for shift, count in sorted(counts.items()):
        require(note, f"| `({shift[0]},{shift[1]})` | {count} |")
    require(
        note,
        f"{float(gate['stability']['maximum_deviation']):.6f} against the 0.10 bar",
    )
    require(
        note,
        f"CV is {float(gate['photometric_strip_level']['cv']):.6f}",
    )
    assert gate["saturated_fraction"] == 0.0

    assert independent["all_methods_agree"] is True
    assert independent["maximum_absolute_displacement_quad_pixels"] == 2
    assert independent["commission"]["zero_only_plant_exit"] == 1
    nonidentity_correlations = independent["best_correlations"][1:]
    require(
        note,
        f"{min(nonidentity_correlations):.6f}–{max(nonidentity_correlations):.6f}",
    )

    clean = commission["readings"]
    require(note, f"{clean['null']['mean_abs_frc']:.6f}")
    require(note, f"{clean['null']['max_ring_abs_t']:.6f}")
    require(
        note,
        ", ".join(f"{value:+.6f}" for value in clean["null"]["bands"]),
    )
    require(
        note,
        f"{clean['positive']['low_band_frc']:.6f} / "
        f"{clean['positive']['high_band_frc']:.6f}",
    )
    require(note, "4.44e−16")
    require(note, f"{clean['common_mode']['low_band_frc']:.6f}")
    require(note, f"{clean['sharpening']['crossing_move']:.6f} cycles/quad-pixel")
    require(note, f"{clean['sharpening']['naive_acuity_gain']:.6f}x")

    assert commission["all_plants_red"] is True
    assert set(commission["plants"]) == {
        "N1",
        "P1",
        "S1",
        "C1",
        "C2",
        "C3",
        "G1",
        "G2",
        "T1",
    }
    assert all(code == 1 for code in commission["plants"].values())
    tuner = commission["plant_measurements"]["T1"]["data_dependent_tuner"]
    assert tuner["selected_leak"] == 1.0
    assert tuner["evaluation_high_band_frc"] == 1.0
    require(note, f"{tuner['external_c_output_max_change']:.6f}")

    assert metadata_commission["all_plants_red"] is True
    assert len(metadata_commission["plants"]) == 4
    assert independent["commission"]["plant_went_red"] is True
    total_plants = (
        len(metadata_commission["plants"])
        + len(commission["plants"])
        + 1
    )
    require(note, f"{total_plants}/{total_plants} planted defects go RED")

    if (OUT / "measurement.json").exists():
        raise AssertionError("real FRC measurement exists despite failed gate")
    require(note, "There is deliberately no `out/measurement.json`.")
    require(note, "are **not measured**")
    require(note, "**Nothing changes in Rust.**")

    return {
        "status": "VERIFIED",
        "claims_checked": 26,
        "capture_files": metadata["files"],
        "groups": len(metadata["groups"]),
        "shift_counts": {str(key): value for key, value in counts.items()},
        "all_gate_methods_agree": independent["all_methods_agree"],
        "total_plants_red": total_plants,
        "measurement_file_absent": True,
    }


def child(plant: bool) -> subprocess.CompletedProcess[str]:
    arguments = [sys.executable, str(Path(__file__).resolve()), "--internal"]
    if plant:
        arguments.append("--plant-report-value")
    return subprocess.run(
        arguments,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def main() -> int:
    if "--internal" in sys.argv:
        try:
            verify(plant_report_value="--plant-report-value" in sys.argv)
        except Exception as error:
            print(f"REPORT CHECK RED: {type(error).__name__}: {error}")
            return 1
        print("REPORT CHECK GREEN")
        return 0

    clean = child(False)
    planted = child(True)
    if clean.returncode != 0 or planted.returncode != 1:
        print(clean.stdout)
        print(planted.stdout)
        raise RuntimeError(
            f"report verification commissioning failed: "
            f"clean={clean.returncode}, plant={planted.returncode}"
        )
    result = verify(plant_report_value=False)
    result["commission"] = {
        "clean_exit": clean.returncode,
        "planted_report_value_exit": planted.returncode,
        "plant_went_red": planted.returncode == 1,
    }
    (OUT / "report-verification.json").write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"REPORT VERIFY FAILED: {type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1)
