from __future__ import annotations

import hashlib
import json
import struct
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable


POPULATION_PREFIX = b"M10-POP-V1|"
SEED_COMMITMENT_PREFIX = b"M10-SYNTH-SEED-COMMIT-V1\x00"
SYNTH_PRF_PREFIX = b"M10-SYNTH-PRF-V1\x00"

SYNTH_WIDTH = 1280
SYNTH_HEIGHT = 1024
SYNTH_TILE = 256
SYNTH_INSTANCE_COUNT = 20
SYNTH_COLUMNS = 5
SYNTH_ROWS = 4
SYNTH_FOCUS_STEP_UM = 8
SYNTH_FRAME_STEPS = tuple(range(42))
SYNTH_TARGETS_PER_CLASS = 500
SYNTH_TARGETS_PER_INSTANCE = 2000
SYNTH_WITNESS_TRIPLES = 101

TARGET_CLASSES = (
    "near_interior",
    "far_interior",
    "near_boundary",
    "far_boundary",
)
CLASS_CODE = {name: i for i, name in enumerate(TARGET_CLASSES)}


class DuplicateKeyError(ValueError):
    pass


def sha256_bytes(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def sha256_lower(data: bytes) -> str:
    return sha256_bytes(data).hex()


def binary64_hex(value: float) -> str:
    return struct.pack(">d", value).hex()


def binary32_hex(value: float) -> str:
    return struct.pack(">f", value).hex()


def from_binary64_hex(value: str) -> float:
    return struct.unpack(">d", bytes.fromhex(value))[0]


def artifact_digest(data: bytes) -> dict[str, Any]:
    return {
        "input_hex": data.hex(),
        "byte_length": len(data),
        "sha256_lowerhex": sha256_lower(data),
    }


def make_cell_id(
    arm: str,
    capture_id: str,
    site_id: str,
    x: int,
    y: int,
) -> str:
    if not (0 <= x <= 0xFFFFFFFF and 0 <= y <= 0xFFFFFFFF):
        raise ValueError("x and y must fit unsigned 32-bit")
    for name, value in (
        ("arm", arm),
        ("capture_id", capture_id),
        ("site_id", site_id),
    ):
        if "|" in value or "\x00" in value:
            raise ValueError(f"{name} contains a forbidden delimiter")
        value.encode("utf-8", errors="strict")
    return f"{arm}|{capture_id}|{site_id}|{x:08x}|{y:08x}"


def quota_hash(cell_id: str) -> bytes:
    return sha256_bytes(POPULATION_PREFIX + cell_id.encode("utf-8"))


def quota_sort_key(cell_id: str, x: int, y: int) -> tuple[bytes, int, int, bytes]:
    cell_bytes = cell_id.encode("utf-8")
    return quota_hash(cell_id), y, x, cell_bytes


def quota_fixture(cell_id: str, x: int, y: int) -> dict[str, Any]:
    preimage = POPULATION_PREFIX + cell_id.encode("utf-8")
    digest = sha256_bytes(preimage)
    return {
        "cell_id": cell_id,
        "x": x,
        "y": y,
        "preimage_utf8_hex": preimage.hex(),
        "digest_sha256_lowerhex": digest.hex(),
        "unsigned_256_big_endian_decimal": str(int.from_bytes(digest, "big")),
        "ordering_key": {
            "digest_bytes_hex": digest.hex(),
            "then_y": y,
            "then_x": x,
            "then_cell_id_utf8_hex": cell_id.encode("utf-8").hex(),
        },
    }


def seed_commitment(seed: bytes) -> str:
    if len(seed) != 32:
        raise ValueError("synthetic seed must be exactly 32 bytes")
    return sha256_lower(SEED_COMMITMENT_PREFIX + seed)


def synth_prf(seed: bytes, label: bytes, payload: bytes) -> bytes:
    if len(seed) != 32:
        raise ValueError("synthetic seed must be exactly 32 bytes")
    if not (1 <= len(label) <= 255):
        raise ValueError("PRF label must contain 1..255 bytes")
    try:
        label.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError("PRF label must be ASCII") from exc
    preimage = SYNTH_PRF_PREFIX + seed + bytes([len(label)]) + label + payload
    return sha256_bytes(preimage)


def synth_prf_fixture(seed: bytes, label: bytes, payload: bytes) -> dict[str, Any]:
    preimage = SYNTH_PRF_PREFIX + seed + bytes([len(label)]) + label + payload
    digest = synth_prf(seed, label, payload)
    return {
        "seed_hex": seed.hex(),
        "label_ascii": label.decode("ascii"),
        "payload_hex": payload.hex(),
        "preimage_hex": preimage.hex(),
        "digest_sha256_lowerhex": digest.hex(),
    }


@dataclass(frozen=True)
class InstanceParams:
    boundary_column: int
    phase_x: int
    phase_y: int
    far_phase_y: int
    base_steps: int
    separation_steps: int


def instance_params(seed: bytes, instance: int) -> InstanceParams:
    if not 0 <= instance < SYNTH_INSTANCE_COUNT:
        raise ValueError("instance index out of range")
    digest = synth_prf(seed, b"PARAM", struct.pack(">I", instance))
    return InstanceParams(
        boundary_column=124 + digest[0] % 8,
        phase_x=digest[1] % 8,
        phase_y=digest[2] % 8,
        far_phase_y=digest[3] % 8,
        base_steps=12 + digest[4] % 4,
        separation_steps=12 + digest[5] % 4,
    )


def tent8(value: int) -> int:
    residue = value % 8
    return 4 - abs(residue - 4)


def near_depth_steps(params: InstanceParams, x: int, y: int) -> int:
    return (
        params.base_steps
        + 3 * (tent8(x + params.phase_x) - 2)
        + (tent8(y + params.phase_y) - 2)
    )


def far_depth_steps(params: InstanceParams, x: int, y: int) -> int:
    return (
        near_depth_steps(params, x, y)
        + params.separation_steps
        + (tent8(y + params.far_phase_y) - 2)
    )


def tile_origin(instance: int) -> tuple[int, int]:
    return (
        (instance % SYNTH_COLUMNS) * SYNTH_TILE,
        (instance // SYNTH_COLUMNS) * SYNTH_TILE,
    )


def distance_twice(params: InstanceParams, x: int) -> int:
    return 2 * (x - params.boundary_column) - 1


def true_layer(params: InstanceParams, x: int) -> str:
    return "near" if distance_twice(params, x) < 0 else "far"


def texture_value(
    seed: bytes,
    instance: int,
    layer: int,
    channel: int,
    x: int,
    y: int,
) -> int:
    if layer not in (0, 1):
        raise ValueError("layer must be 0 (near) or 1 (far)")
    if channel not in (0, 1, 2):
        raise ValueError("channel must be R=0, G=1, or B=2")
    if not (0 <= x < SYNTH_TILE and 0 <= y < SYNTH_TILE):
        raise ValueError("local texture coordinate out of range")
    payload = (
        struct.pack(">I", instance)
        + bytes([layer, channel])
        + struct.pack(">HH", x, y)
    )
    raw = int.from_bytes(synth_prf(seed, b"TEX", payload)[:2], "big")
    return 8192 + raw % 49152


def target_rank(
    seed: bytes,
    instance: int,
    target_class: str,
    x: int,
    y: int,
) -> tuple[bytes, int, int]:
    payload = (
        struct.pack(">I", instance)
        + bytes([CLASS_CODE[target_class]])
        + struct.pack(">HH", x, y)
    )
    return synth_prf(seed, b"TARGET", payload), y, x


def witness_centre_x(params: InstanceParams) -> int:
    for x in range(40, 48):
        if (x + params.phase_x) % 8 == 4:
            return x
    raise AssertionError("one residue must occur in every eight consecutive integers")


def witness_coordinates(params: InstanceParams) -> list[tuple[int, int, int, int]]:
    centre_x = witness_centre_x(params)
    triples = []
    for index in range(SYNTH_WITNESS_TRIPLES):
        y = 24 + 2 * index
        triples.append((centre_x - 1, centre_x, centre_x + 1, y))
    return [(x0, x1, x2, y) for x0, x1, x2, y in triples]


def geometrically_eligible(
    params: InstanceParams,
    target_class: str,
) -> Iterable[tuple[int, int]]:
    for y in range(SYNTH_TILE):
        for x in range(SYNTH_TILE):
            d2 = distance_twice(params, x)
            if target_class == "near_interior" and d2 < -64:
                yield x, y
            elif target_class == "far_interior" and d2 > 64:
                yield x, y
            elif target_class == "near_boundary" and -64 <= d2 < 0:
                yield x, y
            elif target_class == "far_boundary" and 0 < d2 <= 64:
                yield x, y


def selected_coordinates(
    seed: bytes,
    instance: int,
) -> dict[str, list[tuple[int, int]]]:
    params = instance_params(seed, instance)
    witness = witness_coordinates(params)
    witness_points = {
        (x, y)
        for x0, x1, x2, y in witness
        for x in (x0, x1, x2)
    }
    if len(witness_points) != 3 * SYNTH_WITNESS_TRIPLES:
        raise AssertionError("witness triples must be disjoint")

    result: dict[str, list[tuple[int, int]]] = {}
    near_pool = [
        point
        for point in geometrically_eligible(params, "near_interior")
        if point not in witness_points
    ]
    near_pool.sort(
        key=lambda point: target_rank(
            seed, instance, "near_interior", point[0], point[1]
        )
    )
    result["near_interior"] = sorted(witness_points) + near_pool[:197]

    for target_class in TARGET_CLASSES[1:]:
        pool = list(geometrically_eligible(params, target_class))
        pool.sort(
            key=lambda point, name=target_class: target_rank(
                seed, instance, name, point[0], point[1]
            )
        )
        result[target_class] = pool[:SYNTH_TARGETS_PER_CLASS]

    for target_class, points in result.items():
        if len(points) != SYNTH_TARGETS_PER_CLASS:
            raise AssertionError(f"{target_class} target count is not 500")
        if len(set(points)) != len(points):
            raise AssertionError(f"{target_class} target coordinates are not unique")
    all_points = [point for points in result.values() for point in points]
    if len(set(all_points)) != SYNTH_TARGETS_PER_INSTANCE:
        raise AssertionError("target classes overlap")
    return result


def target_rows(seed: bytes, instance: int) -> list[dict[str, Any]]:
    params = instance_params(seed, instance)
    origin_x, origin_y = tile_origin(instance)
    rows = []
    for target_class, points in selected_coordinates(seed, instance).items():
        layer = "near" if target_class.startswith("near_") else "far"
        for x, y in points:
            global_x = origin_x + x
            global_y = origin_y + y
            near_steps = near_depth_steps(params, x, y)
            far_steps = far_depth_steps(params, x, y)
            selected_steps = near_steps if layer == "near" else far_steps
            rows.append(
                {
                    "cell_id": make_cell_id(
                        "synthetic",
                        "m10-synth-score-v1",
                        f"syn-{instance:02d}",
                        global_x,
                        global_y,
                    ),
                    "site_id": f"syn-{instance:02d}",
                    "target_class": target_class,
                    "true_layer": layer,
                    "x": global_x,
                    "y": global_y,
                    "local_x": x,
                    "local_y": y,
                    "distance_twice_px": distance_twice(params, x),
                    "near_depth_steps": near_steps,
                    "far_depth_steps": far_steps,
                    "truth_depth_steps": selected_steps,
                    "truth_depth_um": selected_steps * SYNTH_FOCUS_STEP_UM,
                    "truth_sigma_um": 0,
                }
            )
    return sorted(rows, key=lambda row: row["cell_id"].encode("utf-8"))


def affine_certificate(seed: bytes, instance: int) -> dict[str, Any]:
    params = instance_params(seed, instance)
    origin_x, origin_y = tile_origin(instance)
    triples = []
    for x0, x1, x2, y in witness_coordinates(params):
        triples.append(
            {
                "p0": [origin_x + x0, origin_y + y],
                "p1": [origin_x + x1, origin_y + y],
                "p2": [origin_x + x2, origin_y + y],
            }
        )
    return {
        "instance": instance,
        "population_size": SYNTH_TARGETS_PER_INSTANCE,
        "required_disjoint_triples": SYNTH_TARGETS_PER_INSTANCE // 20 + 1,
        "threshold_steps": 1,
        "triples": triples,
    }


def verify_affine_certificate(
    rows: list[dict[str, Any]],
    certificate: dict[str, Any],
) -> dict[str, Any]:
    if len(rows) != certificate["population_size"]:
        raise ValueError("certificate population size mismatch")
    by_coordinate = {(row["x"], row["y"]): row for row in rows}
    used: set[tuple[int, int]] = set()
    second_differences = []
    for triple in certificate["triples"]:
        p0 = tuple(triple["p0"])
        p1 = tuple(triple["p1"])
        p2 = tuple(triple["p2"])
        if not (
            p0[0] + p2[0] == 2 * p1[0]
            and p0[1] + p2[1] == 2 * p1[1]
        ):
            raise ValueError("certificate triple is not equally spaced and collinear")
        for point in (p0, p1, p2):
            if point in used:
                raise ValueError("certificate triples are not disjoint")
            if point not in by_coordinate:
                raise ValueError("certificate point is outside the scored population")
            used.add(point)
        z0 = by_coordinate[p0]["truth_depth_steps"]
        z1 = by_coordinate[p1]["truth_depth_steps"]
        z2 = by_coordinate[p2]["truth_depth_steps"]
        second_difference = z0 - 2 * z1 + z2
        if abs(second_difference) <= 4 * certificate["threshold_steps"]:
            raise ValueError("certificate second difference is not strictly large enough")
        second_differences.append(second_difference)
    required = certificate["required_disjoint_triples"]
    if len(second_differences) < required:
        raise ValueError("too few disjoint triples for a strict nearest-rank p95 proof")
    return {
        "population_size": len(rows),
        "triple_count": len(second_differences),
        "required_triple_count": required,
        "minimum_abs_second_difference_steps": min(
            abs(value) for value in second_differences
        ),
        "strict_q95_lower_bound_steps": certificate["threshold_steps"],
        "proof": (
            "Each affine residual triple has the same second difference as truth. "
            "|r0-2r1+r2|<=4t if all three |r|<=t; therefore every certified "
            "triple forces one distinct residual >t. With floor(N/20)+1 "
            "disjoint triples, nearest-rank q0.95 is strictly >t."
        ),
    }


def round_ratio_ties_even(numerator: int, denominator: int) -> int:
    if numerator < 0 or denominator <= 0:
        raise ValueError("renderer ratio must be non-negative with positive denominator")
    quotient, remainder = divmod(numerator, denominator)
    doubled = 2 * remainder
    if doubled > denominator or (doubled == denominator and quotient % 2 == 1):
        return quotient + 1
    return quotient


def _window_bounds(coordinate: int, radius: int) -> tuple[int, int]:
    return max(0, coordinate - radius), min(SYNTH_TILE - 1, coordinate + radius)


def render_channel(
    seed: bytes,
    instance: int,
    frame_step: int,
    x: int,
    y: int,
    channel: int,
) -> int:
    params = instance_params(seed, instance)
    near_radius = min(12, abs(near_depth_steps(params, x, y) - frame_step))
    far_radius = min(12, abs(far_depth_steps(params, x, y) - frame_step))

    nx0, nx1 = _window_bounds(x, near_radius)
    ny0, ny1 = _window_bounds(y, near_radius)
    fx0, fx1 = _window_bounds(x, far_radius)
    fy0, fy1 = _window_bounds(y, far_radius)

    near_sum = 0
    near_count = 0
    for sy in range(ny0, ny1 + 1):
        for sx in range(nx0, nx1 + 1):
            if sx <= params.boundary_column:
                near_sum += texture_value(seed, instance, 0, channel, sx, sy)
                near_count += 1

    far_sum = 0
    for sy in range(fy0, fy1 + 1):
        for sx in range(fx0, fx1 + 1):
            far_sum += texture_value(seed, instance, 1, channel, sx, sy)

    near_area = (nx1 - nx0 + 1) * (ny1 - ny0 + 1)
    far_area = (fx1 - fx0 + 1) * (fy1 - fy0 + 1)
    numerator = near_sum * far_area + (near_area - near_count) * far_sum
    denominator = near_area * far_area
    value = round_ratio_ties_even(numerator, denominator)
    if not 0 <= value <= 65535:
        raise AssertionError("renderer left the unsigned 16-bit range")
    return value


def render_probe_bytes(seed: bytes, probes: list[dict[str, int]]) -> bytes:
    output = bytearray()
    for probe in probes:
        for channel in range(3):
            value = render_channel(
                seed,
                probe["instance"],
                probe["frame_step"],
                probe["local_x"],
                probe["local_y"],
                channel,
            )
            output.extend(struct.pack("<H", value))
    return bytes(output)


def exact_binary64_sum(values: Iterable[float]) -> float:
    exact = sum((Fraction.from_float(value) for value in values), Fraction(0, 1))
    return float(exact)


def fit_origin(raw_steps: list[float], valid: list[bool]) -> dict[str, Any]:
    if len(raw_steps) != len(valid):
        raise ValueError("raw_steps and valid must have the same length")
    included = [value for value, include in zip(raw_steps, valid) if include]
    n = len(included)
    if n == 0:
        return {
            "N": 0,
            "sum_binary64_hex": None,
            "origin_binary64_hex": None,
            "residual_binary64_hex": [],
            "candidate_worst": True,
        }
    summed = exact_binary64_sum(included)
    origin = summed / n
    residuals = [
        value - origin
        for value, include in zip(raw_steps, valid)
        if include
    ]
    return {
        "N": n,
        "sum_binary64_hex": binary64_hex(summed),
        "origin_binary64_hex": binary64_hex(origin),
        "residual_binary64_hex": [binary64_hex(value) for value in residuals],
        "candidate_worst": False,
    }


def _no_duplicate_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json_strict(path: Path) -> Any:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError("UTF-8 BOM is forbidden")
    text = raw.decode("utf-8", errors="strict")
    return json.loads(
        text,
        object_pairs_hook=_no_duplicate_object,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"non-JSON numeric token: {token}")
        ),
    )


def _exact_keys(value: dict[str, Any], expected: set[str], context: str) -> None:
    actual = set(value)
    if actual != expected:
        raise ValueError(
            f"{context} keys differ: missing={sorted(expected-actual)}, "
            f"extra={sorted(actual-expected)}"
        )


def _validate_artifact_ref(value: dict[str, Any], context: str) -> None:
    _exact_keys(value, {"sha256", "byte_length"}, context)
    digest = value["sha256"]
    if not (
        isinstance(digest, str)
        and len(digest) == 64
        and all(char in "0123456789abcdef" for char in digest)
    ):
        raise ValueError(f"{context}.sha256 is not lowercase SHA-256 hex")
    if not isinstance(value["byte_length"], int) or isinstance(
        value["byte_length"], bool
    ):
        raise ValueError(f"{context}.byte_length is not an integer")
    if value["byte_length"] < 0:
        raise ValueError(f"{context}.byte_length is negative")


def _validate_file_ref(
    value: dict[str, Any],
    context: str,
    expected_name: str,
) -> None:
    _exact_keys(value, {"name", "sha256", "byte_length"}, context)
    if value["name"] != expected_name:
        raise ValueError(f"{context}.name is not {expected_name!r}")
    _validate_artifact_ref(
        {"sha256": value["sha256"], "byte_length": value["byte_length"]},
        context,
    )


def validate_manifest_dict(manifest: dict[str, Any]) -> None:
    _exact_keys(
        manifest,
        {
            "schema",
            "capture_id",
            "mode",
            "hash_contract",
            "grid",
            "semantics",
            "bindings",
            "files",
        },
        "manifest",
    )
    if manifest["schema"] != "strehl.m10-depth-product-manifest.v1":
        raise ValueError("manifest schema identifier mismatch")
    if manifest["mode"] != "common-merge-shipping-default":
        raise ValueError("manifest mode mismatch")
    if manifest["hash_contract"] != "sha256-raw-bytes-lowerhex-v1":
        raise ValueError("manifest hash contract mismatch")
    capture_id = manifest["capture_id"]
    if not isinstance(capture_id, str) or not capture_id:
        raise ValueError("capture_id must be a non-empty string")
    if any(
        not (char.isascii() and (char.isalnum() or char in "._-"))
        for char in capture_id
    ):
        raise ValueError("capture_id contains a forbidden character")

    grid = manifest["grid"]
    _exact_keys(
        grid,
        {
            "width",
            "height",
            "pixel_center",
            "origin",
            "x_direction",
            "y_direction",
        },
        "grid",
    )
    for name in ("width", "height"):
        if not isinstance(grid[name], int) or isinstance(grid[name], bool):
            raise ValueError(f"grid.{name} is not an integer")
        if grid[name] < 1:
            raise ValueError(f"grid.{name} is not positive")
    fixed_grid = {
        "pixel_center": "integer-column-row-centres",
        "origin": "top-left",
        "x_direction": "right",
        "y_direction": "down",
    }
    for name, expected in fixed_grid.items():
        if grid[name] != expected:
            raise ValueError(f"grid.{name} mismatch")

    semantics = manifest["semantics"]
    _exact_keys(
        semantics,
        {
            "depth_units",
            "depth_axis",
            "depth_positive",
            "depth_origin",
            "uncertainty",
            "invalid_mask_value",
            "valid_mask_value",
            "invalid_float32_bits",
            "field_curvature_applied",
        },
        "semantics",
    )
    fixed_semantics = {
        "depth_units": "micrometre",
        "depth_axis": "camera-optical-axis-distance",
        "depth_positive": "away-from-sensor",
        "depth_origin": "one-arbitrary-additive-constant-per-capture",
        "uncertainty": "candidate-only-one-standard-deviation-micrometres",
        "invalid_mask_value": 0,
        "valid_mask_value": 1,
        "invalid_float32_bits": "7fc00000",
        "field_curvature_applied": True,
    }
    if semantics != fixed_semantics:
        raise ValueError("manifest semantics differ from the frozen contract")

    bindings = manifest["bindings"]
    binding_names = {
        "common_input_manifest",
        "capture_manifest",
        "focus_axis_map",
        "field_curvature_profile",
        "gear_profile",
        "candidate_executable",
        "settings",
        "output_grid_descriptor",
    }
    _exact_keys(bindings, binding_names, "bindings")
    for name in sorted(binding_names):
        _validate_artifact_ref(bindings[name], f"bindings.{name}")

    files = manifest["files"]
    _exact_keys(files, {"rgb", "depth_um", "depth_sigma_um", "depth_valid"}, "files")
    _validate_file_ref(files["rgb"], "files.rgb", "rgb.tif")
    _validate_file_ref(files["depth_um"], "files.depth_um", "depth-um.tif")
    _validate_file_ref(
        files["depth_sigma_um"],
        "files.depth_sigma_um",
        "depth-sigma-um.tif",
    )
    _validate_file_ref(files["depth_valid"], "files.depth_valid", "depth-valid.tif")


def make_sample_manifest() -> dict[str, Any]:
    def ref(label: str) -> dict[str, Any]:
        data = label.encode("ascii")
        return {"sha256": sha256_lower(data), "byte_length": len(data)}

    def file_ref(name: str, label: str) -> dict[str, Any]:
        value = ref(label)
        return {"name": name, **value}

    return {
        "schema": "strehl.m10-depth-product-manifest.v1",
        "capture_id": "fixture-capture-01",
        "mode": "common-merge-shipping-default",
        "hash_contract": "sha256-raw-bytes-lowerhex-v1",
        "grid": {
            "width": 64,
            "height": 48,
            "pixel_center": "integer-column-row-centres",
            "origin": "top-left",
            "x_direction": "right",
            "y_direction": "down",
        },
        "semantics": {
            "depth_units": "micrometre",
            "depth_axis": "camera-optical-axis-distance",
            "depth_positive": "away-from-sensor",
            "depth_origin": "one-arbitrary-additive-constant-per-capture",
            "uncertainty": "candidate-only-one-standard-deviation-micrometres",
            "invalid_mask_value": 0,
            "valid_mask_value": 1,
            "invalid_float32_bits": "7fc00000",
            "field_curvature_applied": True,
        },
        "bindings": {
            name: ref(name)
            for name in (
                "common_input_manifest",
                "capture_manifest",
                "focus_axis_map",
                "field_curvature_profile",
                "gear_profile",
                "candidate_executable",
                "settings",
                "output_grid_descriptor",
            )
        },
        "files": {
            "rgb": file_ref("rgb.tif", "rgb"),
            "depth_um": file_ref("depth-um.tif", "depth"),
            "depth_sigma_um": file_ref("depth-sigma-um.tif", "sigma"),
            "depth_valid": file_ref("depth-valid.tif", "valid"),
        },
    }


def development_summary(seed: bytes) -> dict[str, Any]:
    instances = []
    min_separation = None
    min_depth = None
    max_depth = None
    for instance in range(SYNTH_INSTANCE_COUNT):
        rows = target_rows(seed, instance)
        certificate = affine_certificate(seed, instance)
        certificate_result = verify_affine_certificate(rows, certificate)
        separations = [
            row["far_depth_steps"] - row["near_depth_steps"] for row in rows
        ]
        depths = [row["truth_depth_steps"] for row in rows]
        current_min_separation = min(separations)
        current_min_depth = min(depths)
        current_max_depth = max(depths)
        min_separation = (
            current_min_separation
            if min_separation is None
            else min(min_separation, current_min_separation)
        )
        min_depth = (
            current_min_depth
            if min_depth is None
            else min(min_depth, current_min_depth)
        )
        max_depth = (
            current_max_depth
            if max_depth is None
            else max(max_depth, current_max_depth)
        )
        counts = {
            target_class: sum(
                row["target_class"] == target_class for row in rows
            )
            for target_class in TARGET_CLASSES
        }
        instances.append(
            {
                "instance": instance,
                "target_counts": counts,
                "certificate": certificate_result,
            }
        )
    return {
        "schema": "strehl.m10-synthetic-development-summary.v1",
        "seed_hex": seed.hex(),
        "width": SYNTH_WIDTH,
        "height": SYNTH_HEIGHT,
        "instances": instances,
        "total_target_count": SYNTH_INSTANCE_COUNT * SYNTH_TARGETS_PER_INSTANCE,
        "interior_target_count": SYNTH_INSTANCE_COUNT * 1000,
        "boundary_target_count": SYNTH_INSTANCE_COUNT * 1000,
        "minimum_layer_separation_steps": min_separation,
        "minimum_truth_depth_steps": min_depth,
        "maximum_truth_depth_steps": max_depth,
        "focus_frame_min_step": min(SYNTH_FRAME_STEPS),
        "focus_frame_max_step": max(SYNTH_FRAME_STEPS),
    }


def make_fixtures() -> dict[str, Any]:
    development_seed = bytes(range(32))
    cell = make_cell_id(
        "ruler",
        "capture-01",
        "strip-07",
        0x123,
        0x456,
    )
    raw_steps = [1.0, 2.0, 99.0, 4.0]
    valid = [True, True, False, True]
    probes = [
        {"instance": 0, "frame_step": 12, "local_x": 50, "local_y": 24},
        {"instance": 0, "frame_step": 24, "local_x": 128, "local_y": 96},
        {"instance": 7, "frame_step": 20, "local_x": 130, "local_y": 111},
        {"instance": 19, "frame_step": 35, "local_x": 200, "local_y": 200},
    ]
    rendered = render_probe_bytes(development_seed, probes)
    instance_zero_rows = target_rows(development_seed, 0)
    certificate_result = verify_affine_certificate(
        instance_zero_rows,
        affine_certificate(development_seed, 0),
    )
    parameter_payload = struct.pack(">I", 0)
    texture_payload = (
        struct.pack(">I", 7)
        + bytes([1, 2])
        + struct.pack(">HH", 130, 111)
    )
    return {
        "schema": "strehl.m10-definition-fixtures.v1",
        "quota_hash": quota_fixture(cell, 0x123, 0x456),
        "raw_artifact_hash": artifact_digest(
            bytes.fromhex("00ff0a4d313930")
        ),
        "seed_commitment": {
            "seed_hex": development_seed.hex(),
            "preimage_hex": (
                SEED_COMMITMENT_PREFIX + development_seed
            ).hex(),
            "digest_sha256_lowerhex": seed_commitment(development_seed),
        },
        "synthetic_prf": {
            "parameter_block": synth_prf_fixture(
                development_seed,
                b"PARAM",
                parameter_payload,
            ),
            "texture_block": synth_prf_fixture(
                development_seed,
                b"TEX",
                texture_payload,
            ),
            "instance_zero_parameters": instance_params(
                development_seed, 0
            ).__dict__,
            "texture_value": {
                "instance": 7,
                "layer": 1,
                "channel": 2,
                "local_x": 130,
                "local_y": 111,
                "u16": texture_value(
                    development_seed, 7, 1, 2, 130, 111
                ),
            },
        },
        "origin_fit": {
            "raw_step_binary64_hex": [
                binary64_hex(value) for value in raw_steps
            ],
            "candidate_valid": valid,
            "expected": fit_origin(raw_steps, valid),
            "meaning": (
                "N is the count of candidate-valid truth targets, so the "
                "origin is their unweighted arithmetic-mean residual."
            ),
        },
        "renderer_probe": {
            "seed_hex": development_seed.hex(),
            "probes": probes,
            "expected_bytes_hex": rendered.hex(),
            "expected_sha256_lowerhex": sha256_lower(rendered),
            "layout": (
                "Probe order; within each probe R,G,B; each sample unsigned "
                "16-bit little-endian."
            ),
        },
        "affine_certificate": {
            "seed_hex": development_seed.hex(),
            "instance": 0,
            "result": certificate_result,
        },
        "manifest_shape": make_sample_manifest(),
        "failure_partition": {
            "records": [
                {"code": "OK", "outcome": "PASS"},
                {
                    "code": "PRODUCT_FILE_HASH_MISMATCH",
                    "outcome": "CANDIDATE_FAIL",
                },
                {
                    "code": "CANDIDATE_PRODUCT_NOT_AVAILABLE",
                    "outcome": "PRODUCT_UNMEASURED",
                },
                {
                    "code": "SYNTH_CERTIFICATE_INVALID",
                    "outcome": "TRUTH_UNMEASURED",
                },
                {
                    "code": "UNRECOGNIZED_FAILURE_CODE",
                    "outcome": "CHECKER_ERROR",
                },
            ],
            "expected_counts": {
                "PASS": 1,
                "CANDIDATE_FAIL": 1,
                "PRODUCT_UNMEASURED": 1,
                "TRUTH_UNMEASURED": 1,
                "CHECKER_ERROR": 1,
                "total_examined": 5,
            },
        },
    }
