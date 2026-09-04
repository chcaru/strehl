#!/usr/bin/env python3
"""One-frame, in-memory commissioning probe; never emits a scoreable TIFF."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import converter


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--settings", required=True)
    parser.add_argument("--icc", required=True)
    parser.add_argument("--freeze", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out = Path(args.out)
    try:
        settings_path = Path(args.settings)
        icc_path = Path(args.icc)
        converter.validate_settings(settings_path)
        freeze = converter.verify_freeze(Path(args.freeze), settings_path, icc_path)
        np, rawpy = converter.import_runtime()
        source = Path(args.input)
        source_sha = converter.hash_file(source)
        camera = converter.read_camera_metadata(source)
        with rawpy.imread(str(source)) as raw:
            metadata = converter.raw_metadata(raw, camera)
            black = metadata["black_levels"]
            whites = metadata["white_levels"]
            if len(set(whites)) != 1:
                raise converter.ContractFailure(
                    "PER_CHANNEL_WHITE_UNSUPPORTED",
                    f"rawpy exposes only scalar user_sat; channel whites are {whites}",
                )
            rgb = raw.postprocess(
                **converter.postprocess_kwargs(rawpy, black, whites[0])
            )
        pixel_hash = converter.hash_bytes(memoryview(rgb).cast("B"))
        result = {
            "schema": "m165-development-raw-probe-v1",
            "status": "DEVELOPMENT_ONLY_NONCONTRACT",
            "burned_input_permitted_for_commissioning_only": True,
            "scoreable": False,
            "pattern_map_applied": False,
            "blocker": "no frozen matching dark/flat pattern map exists",
            "source": {
                "path": str(source.resolve()),
                "sha256": source_sha,
                "metadata": metadata,
            },
            "converter_executable_sha256": freeze["converter"][
                "executable_bundle_sha256"
            ],
            "settings_sha256": converter.hash_file(settings_path),
            "icc_sha256": converter.hash_file(icc_path),
            "icc_inspection": converter.inspect_linear_prophoto_icc(
                icc_path.read_bytes()
            ),
            "in_memory_output": {
                "shape": [int(v) for v in rgb.shape],
                "dtype": str(rgb.dtype),
                "c_contiguous": bool(rgb.flags.c_contiguous),
                "rgb16_byte_sha256": pixel_hash,
                "first_pixel": [int(v) for v in rgb[0, 0]],
                "last_pixel": [int(v) for v in rgb[-1, -1]],
            },
            "complete_invocation": [
                sys.executable,
                str(Path(__file__).resolve()),
            ]
            + sys.argv[1:],
            "working_directory": str(Path.cwd()),
        }
        converter.write_json(out, result)
        print(json.dumps(result, sort_keys=True))
        return 0
    except BaseException as exc:
        result = converter.failure_record(exc)
        converter.write_json(out, result)
        print(json.dumps(result, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
