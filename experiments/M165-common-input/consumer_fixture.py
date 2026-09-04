#!/usr/bin/env python3
"""Commissioning-only consumer that attests to the exact TIFF bytes it parsed."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import consumer_gate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--consumer-id", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--attestation", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    attestation_path = Path(args.attestation)
    try:
        consumer_gate.check_id(args.consumer_id, "consumer_id")
        input_path = Path(args.input).resolve()
        data = input_path.read_bytes()
        snapshot = consumer_gate.inspect_tiff_bytes(data)
        output_path = Path(args.output).resolve()
        output = {
            "schema": "m165-synthetic-consumer-output-v1",
            "consumer_id": args.consumer_id,
            "input_file_sha256": snapshot["file_sha256"],
            "input_pixel_payload_sha256": snapshot["pixel_payload_sha256"],
        }
        consumer_gate.write_json(output_path, output)
        output_bytes = output_path.read_bytes()
        attestation = {
            "schema": consumer_gate.STANDARD_ATTESTATION_SCHEMA,
            "status": "PASS",
            "commissioning_only": True,
            "consumer_id": args.consumer_id,
            "input_path": str(input_path),
            "input_file_sha256": snapshot["file_sha256"],
            "input_pixel_payload_sha256": snapshot["pixel_payload_sha256"],
            "whole_file_hash": snapshot["whole_file_hash"],
            "pixel_payload_hash": snapshot["pixel_payload_hash"],
            "read_contract": {
                "artifact_read_count": 1,
                "hash_and_parse_same_memory": True,
            },
            "complete_invocation": [sys.executable, str(Path(__file__).resolve())]
            + sys.argv[1:],
            "exit_code": 0,
            "outputs": [
                {
                    "path": str(output_path),
                    "bytes": len(output_bytes),
                    "sha256": consumer_gate.hash_bytes(output_bytes),
                }
            ],
        }
        consumer_gate.write_json(attestation_path, attestation)
        print(json.dumps(attestation, sort_keys=True))
        return 0
    except BaseException as exc:
        failure = consumer_gate.failure_record(
            exc, consumer_gate.STANDARD_ATTESTATION_SCHEMA
        )
        try:
            consumer_gate.write_json(attestation_path, failure)
        except BaseException:
            pass
        print(json.dumps(failure, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
