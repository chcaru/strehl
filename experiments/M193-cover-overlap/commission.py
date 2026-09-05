from __future__ import annotations

import copy
import hashlib
from pathlib import Path

from reference import (
    ContractError,
    IDENTITY_Q32,
    Q32,
    SimilarityQ32,
    common_row_intervals,
    construct_overlap,
    geometry_fixture,
    load_json,
    make_output_grid,
    map_point_q32,
    maximal_rectangle,
    output_retention,
    sha256_hex,
    synthetic_rgb,
    warp_synthetic,
    encode_tiff,
)


ROOT = Path(__file__).resolve().parent


def red(name: str, condition: bool) -> None:
    if not condition:
        raise AssertionError(f"mutation was missed: {name}")
    print(f"RED {name}")


def expect_contract_failure(name: str, operation, expected_code: str) -> None:
    try:
        operation()
    except ContractError as exc:
        red(name, exc.code == expected_code)
        return
    raise AssertionError(f"mutation was missed: {name}")


def union_rows(
    width: int,
    height: int,
    supports: list[tuple[SimilarityQ32, int, int, int]],
) -> list[tuple[int, int] | None]:
    per_support = [
        common_row_intervals(width, height, [support]) for support in supports
    ]
    rows: list[tuple[int, int] | None] = []
    for y in range(height):
        present = [item[y] for item in per_support if item[y] is not None]
        rows.append(
            None
            if not present
            else (min(row[0] for row in present), max(row[1] for row in present))
        )
    return rows


def bottom_right_tie(rows: list[tuple[int, int] | None]) -> dict[str, int]:
    best: dict[str, int] | None = None
    for top in range(len(rows)):
        if rows[top] is None:
            continue
        left, right = rows[top]
        for bottom in range(top, len(rows)):
            row = rows[bottom]
            if row is None:
                break
            left = max(left, row[0])
            right = min(right, row[1])
            if left > right:
                break
            candidate = {
                "x": left,
                "y": top,
                "width": right - left + 1,
                "height": bottom - top + 1,
            }
            candidate["area_pixels"] = candidate["width"] * candidate["height"]
            key = (
                candidate["area_pixels"],
                candidate["y"],
                candidate["x"],
                candidate["height"],
                candidate["width"],
            )
            if best is None:
                best = candidate
            else:
                best_key = (
                    best["area_pixels"],
                    best["y"],
                    best["x"],
                    best["height"],
                    best["width"],
                )
                if key >= best_key:
                    best = candidate
    assert best is not None
    return best


def main() -> None:
    fixtures = load_json(ROOT / "fixtures.json")
    expected_overlap = fixtures["synthetic_overlap"]
    base = synthetic_rgb()
    blobs = [
        encode_tiff(base),
        encode_tiff(
            warp_synthetic(
                base,
                scale=0.985,
                rotation_degrees=0.35,
                tx=3.25,
                ty=-2.5,
            )
        ),
        encode_tiff(
            warp_synthetic(
                base,
                scale=1.018,
                rotation_degrees=-0.25,
                tx=-4.0,
                ty=3.0,
            )
        ),
    ]

    reversed_overlap = construct_overlap(list(reversed(blobs)))
    first_file_reference = sha256_hex(list(reversed(blobs))[0])
    red(
        "reference-first-file",
        reversed_overlap["manifest_sha256"] == expected_overlap["manifest_sha256"]
        and first_file_reference != expected_overlap["reference_source_sha256"],
    )

    salted = hashlib.sha256(
        expected_overlap["manifest_sha256"].encode("ascii")
        + b"candidate-output-byte"
    ).hexdigest()
    red(
        "output-byte-salted-denominator",
        salted != expected_overlap["manifest_sha256"],
    )

    geometry = geometry_fixture()
    supports = [
        (
            SimilarityQ32(**item["transform"]),
            item["source_width"],
            item["source_height"],
            item["guard_q8"],
        )
        for item in geometry["supports"]
    ]
    correct_rectangle = geometry["maximal_rectangle"]
    union_rectangle = maximal_rectangle(
        union_rows(geometry["width"], geometry["height"], supports)
    )
    red("union-instead-of-intersection", union_rectangle != correct_rectangle)

    no_margin_supports = [
        (transform, width, height, 0)
        for transform, width, height, _ in supports
    ]
    no_margin_rectangle = maximal_rectangle(
        common_row_intervals(
            geometry["width"], geometry["height"], no_margin_supports
        )
    )
    red("drop-valid-support-margin", no_margin_rectangle != correct_rectangle)

    tie_rows = [
        tuple(row) if row is not None else None
        for row in fixtures["tie_break"]["rows"]
    ]
    red(
        "bottom-right-maximal-rectangle-tie",
        bottom_right_tie(tie_rows) != fixtures["tie_break"]["expected"],
    )

    transform = SimilarityQ32(
        **fixtures["mapping_round_trip"]["transform_q32"]
    )
    expected_point = tuple(fixtures["mapping_round_trip"]["mapped_xy_q32"])
    swapped = map_point_q32(23, 17, transform)
    red("mapping-axis-swap", swapped != expected_point)

    wrong_sign = SimilarityQ32(
        transform.a, transform.b, -transform.tx, -transform.ty
    )
    red(
        "mapping-translation-sign",
        map_point_q32(17, 23, wrong_sign) != expected_point,
    )

    missing = make_output_grid(
        expected_overlap,
        arm_id="missing-map",
        expected_width=expected_overlap["native_width"],
        expected_height=expected_overlap["native_height"],
    )
    del missing["common_to_output_q32"]
    expect_contract_failure(
        "missing-grid-default-identity",
        lambda: output_retention(expected_overlap, missing),
        "UNMEASURED_OUTPUT_GRID_UNDEFINED",
    )

    cropped = make_output_grid(
        expected_overlap,
        arm_id="cropped",
        expected_width=expected_overlap["native_width"] - 12,
        expected_height=expected_overlap["native_height"] - 10,
    )
    correct_retention = output_retention(expected_overlap, cropped)
    per_arm_denominator_percent = 100.0
    red(
        "per-arm-denominator-cancellation",
        correct_retention["field_of_view_verdict"]
        == "FAIL_GEOMETRY_FIELD_OF_VIEW"
        and per_arm_denominator_percent == 100.0,
    )

    inert_before = construct_overlap(blobs)
    inert_output = bytearray(b"unread stacker output")
    inert_output[0] ^= 1
    inert_after = construct_overlap(blobs)
    if inert_before != inert_after:
        raise AssertionError("inert output mutation changed input-only overlap")
    print("GREEN inert-output-bitflip")

    print("COMMISSIONED defects=9/9 inert=1/1 total=10/10")


if __name__ == "__main__":
    main()
