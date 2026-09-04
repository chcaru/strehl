"""Post-result diagnostic forced by the asymmetric frozen-base null.

This does not replace or edit the frozen synthetic audit. It re-pairs the
already generated independent same-optics readings without privileging the
historical `base` realization.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent


def run(output: Path) -> int:
    if output.exists():
        raise RuntimeError(f"refusing to overwrite {output}")
    source = json.loads(
        (HERE / "synthetic-choice-audit.json").read_text(encoding="utf-8")
    )
    values = np.asarray(
        source["independent_same_optics_null"]["independent_null_d2"],
        dtype=np.float64,
    )
    if len(values) % 2:
        raise RuntimeError("adjacent pairing requires an even reading count")
    ratios = values[1::2] / values[0::2]
    logs = np.log(ratios)
    mean_log = float(logs.mean())
    se_log = float(logs.std(ddof=1) / math.sqrt(len(logs)))
    ci_log = [mean_log - 1.96 * se_log, mean_log + 1.96 * se_log]
    record = {
        "protocol": "M131-post-result-null-rechoice-v1",
        "reason": (
            "All eight historical-base/null ratios fell below one. Adjacent "
            "independent-null pairing checks whether that was denominator "
            "selection rather than a same-optics effect."
        ),
        "source": "synthetic-choice-audit.json",
        "pairing": "stored readings (0,1), (2,3), (4,5), (6,7)",
        "ratios_second_over_first": ratios.tolist(),
        "geometric_mean_ratio": float(math.exp(mean_log)),
        "log_ratio_mean": mean_log,
        "log_ratio_standard_error": se_log,
        "ratio_ci95_from_log": [
            float(math.exp(ci_log[0])),
            float(math.exp(ci_log[1])),
        ],
        "unity_in_ci95": ci_log[0] <= 0.0 <= ci_log[1],
        "disclosure": (
            "This pairing was specified after seeing the frozen-base null "
            "shift. It is diagnostic only and changes no acceptance rule."
        ),
    }
    output.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        f"geomean={record['geometric_mean_ratio']:.6f} "
        f"log_se={se_log:.6f} ci={record['ratio_ci95_from_log']}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        type=Path,
        default=HERE / "null-rechoice.json",
    )
    args = parser.parse_args()
    return run(args.out.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
