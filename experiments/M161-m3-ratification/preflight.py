"""Fail-closed M3 measurement preflight.

This command performs metadata/path checks only. It never opens image pixels.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from m3_checker_v2 import load_checker_definition, sha256_file


HERE = Path(__file__).resolve().parent
CONTRACT = HERE / "measurement-contract.json"
OUT = HERE / "out" / "measurement-preflight.json"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def resolve(relative: str) -> Path:
    return (HERE / relative).resolve()


def main() -> int:
    contract = read_json(CONTRACT)
    definition, definition_sha = load_checker_definition()
    blockers: list[dict[str, str]] = []

    release = resolve(contract["host_release_record"])
    if not release.is_file():
        blockers.append(
            {
                "code": "HOST_RESERVED",
                "path": str(release),
                "reason": "M153 release record is absent",
            }
        )

    common_manifest = resolve(contract["common_input"]["input_manifest"])
    if not common_manifest.is_file():
        blockers.append(
            {
                "code": "COMMON_INPUT_MANIFEST_ABSENT",
                "path": str(common_manifest),
                "reason": "the registered common linear input has not been supplied",
            }
        )

    census = resolve(contract["common_input"]["site_manifest"])
    if not census.is_file():
        blockers.append(
            {
                "code": "FROZEN_SITE_MANIFEST_ABSENT",
                "path": str(census),
                "reason": "the M152 site manifest is missing",
            }
        )
    elif sha256_file(census) != definition["site_population"]["manifest_sha256"]:
        blockers.append(
            {
                "code": "FROZEN_SITE_MANIFEST_HASH_MISMATCH",
                "path": str(census),
                "reason": "the M152 site manifest no longer matches the checker",
            }
        )

    product_state = []
    for product in contract["required_products"]:
        path = resolve(product["manifest"])
        exists = path.is_file()
        product_state.append(
            {
                "product_id": product["product_id"],
                "role": product["role"],
                "manifest": str(path),
                "exists": exists,
            }
        )
        if not exists:
            blockers.append(
                {
                    "code": "REQUIRED_PRODUCT_PACKAGE_ABSENT",
                    "path": str(path),
                    "reason": product["product_id"],
                }
            )

    optional_state = []
    for product in contract["optional_products"]:
        path = resolve(product["manifest"])
        optional_state.append(
            {
                "product_id": product["product_id"],
                "role": product["role"],
                "manifest": str(path),
                "exists": path.is_file(),
            }
        )

    result = {
        "schema": "m161-m3-measurement-preflight-v1",
        "contract_sha256": sha256_file(CONTRACT),
        "checker_definition_sha256": definition_sha,
        "host_release_record": str(release),
        "required_products": product_state,
        "optional_products": optional_state,
        "pixel_files_opened": 0,
        "blockers": blockers,
        "verdict": "READY" if not blockers else "BLOCKED",
    }
    write_json(OUT, result)
    print(result["verdict"])
    for blocker in blockers:
        print(f"{blocker['code']}: {blocker['reason']} ({blocker['path']})")
    return 0 if not blockers else 4


if __name__ == "__main__":
    raise SystemExit(main())
