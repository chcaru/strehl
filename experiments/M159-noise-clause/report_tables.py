"""Print compact Markdown tables from the frozen M159 result."""

from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    path = Path(__file__).with_name("results.json")
    result = json.loads(path.read_text(encoding="utf-8"))
    controls = result["commissioning"]
    print("| control | median | min | max | directional count |")
    print("| --- | ---: | ---: | ---: | ---: |")
    for key, direction in [
        ("movable_null", "below/above"),
        ("planted_degradation", "above"),
        ("planted_improvement", "below"),
    ]:
        row = controls[key]
        if direction == "below/above":
            count = f"{row['trials_below_1']}/{row['trials_above_1']}"
        elif direction == "above":
            count = f"{row['trials_above_1']}/128 above 1"
        else:
            count = f"{row['trials_below_1']}/128 below 1"
        print(
            f"| {key.replace('_', ' ')} | {row['median']:.6f} | "
            f"{row['min']:.6f} | {row['max']:.6f} | {count} |"
        )
    print()

    for subject in result["subjects"]:
        print(f"### {subject['subject']}")
        print()
        comparator_keys = sorted(subject["sites"][0]["strehl_over_comparator"])
        headers = [
            "rank",
            "reference y,x",
            "strehl RMS",
            *[f"{key} RMS" for key in comparator_keys],
            *[f"S/{key}" for key in comparator_keys],
        ]
        print("| " + " | ".join(headers) + " |")
        print("| " + " | ".join(["---:"] * len(headers)) + " |")
        for site in subject["sites"]:
            cells = [
                str(site["rank"]),
                f"{site['reference_y']},{site['reference_x']}",
                f"{site['fractional_rms']['strehl']:.6f}",
            ]
            cells.extend(
                f"{site['fractional_rms'][key]:.6f}" for key in comparator_keys
            )
            cells.extend(
                f"{site['strehl_over_comparator'][key]:.6f}"
                for key in comparator_keys
            )
            print("| " + " | ".join(cells) + " |")
        raw = subject["raw_best_comparator_distribution"]
        corrected = subject["grade_corrected_max_elasticity_distribution"]
        print()
        print(
            f"raw: min {raw['min']:.6f}; p25 {raw['p25']:.6f}; "
            f"median {raw['median']:.6f}; p75 {raw['p75']:.6f}; "
            f"max {raw['max']:.6f}; bootstrap interval "
            f"[{raw['bootstrap_95pct_interval_for_site_median'][0]:.6f}, "
            f"{raw['bootstrap_95pct_interval_for_site_median'][1]:.6f}]"
        )
        print(
            f"grade-max: median {corrected['median']:.6f}; "
            f"range [{corrected['min']:.6f}, {corrected['max']:.6f}]"
        )
        print()

    historical = result["historical_coffee_site_current_render"]
    print(
        "historical site on current render: "
        f"fork {historical['comparator_fractional_rms']:.9f}, "
        f"strehl {historical['strehl_fractional_rms']:.9f}, "
        f"ratio {historical['strehl_over_comparator']:.6f}"
    )


if __name__ == "__main__":
    main()
