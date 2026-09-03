"""Fit monotone-invariant geometry for the two frozen render pairs."""

from __future__ import annotations

import argparse
import json
import sys

import numpy as np

from ordinal import PAIRS, fit_geometry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pairs", nargs="*", choices=tuple(PAIRS), default=None)
    args = parser.parse_args(argv)
    output = {}
    for key in args.pairs or list(PAIRS):
        pair = PAIRS[key]
        print(f"=== {key}: strehl vs {pair.label} ===")
        result = fit_geometry(pair.strehl, pair.comparator)
        output[key] = result
        print(
            f"scale={result['scale']:.4f} score={result['score']:.6f} "
            f"coarse_interior={result['coarse_interior']} "
            f"fine_interior={result['fine_interior']}"
        )
        print(
            "global correction (strehl px)="
            f"({result['global_correction'][0]:+.1f},"
            f"{result['global_correction'][1]:+.1f}); "
            f"tile residual={result['residual_rms']:.2f}px rms"
        )
        if not result["coarse_interior"] or not result["fine_interior"]:
            print("REFUSAL: scale fit lacks an interior maximum")
            return 2
    print("GEOMETRY_JSON=" + json.dumps(output, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
