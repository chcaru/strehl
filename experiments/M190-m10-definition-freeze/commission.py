from __future__ import annotations

import copy
import struct

from reference import (
    affine_certificate,
    artifact_digest,
    fit_origin,
    make_fixtures,
    make_sample_manifest,
    quota_hash,
    render_probe_bytes,
    target_rows,
    validate_manifest_dict,
    verify_affine_certificate,
)


def expect_failure(name: str, operation) -> None:
    try:
        operation()
    except (AssertionError, ValueError):
        print(f"CAUGHT {name}")
        return
    raise AssertionError(f"negative control did not fail: {name}")


def main() -> None:
    fixtures = make_fixtures()
    seed = bytes(range(32))
    caught = 0

    digest = quota_hash(fixtures["quota_hash"]["cell_id"])
    big = int.from_bytes(digest, "big")
    little = int.from_bytes(digest, "little")
    if big == little:
        raise AssertionError("byte-order control is degenerate")
    if str(little) == fixtures["quota_hash"]["unsigned_256_big_endian_decimal"]:
        raise AssertionError("little-endian mutation unexpectedly matched")
    print("CAUGHT quota-little-endian")
    caught += 1

    wrong_origin = (1.0 + 2.0 + 4.0) / 4.0
    wrong_origin_hex = struct.pack(">d", wrong_origin).hex()
    if wrong_origin_hex == fixtures["origin_fit"]["expected"]["origin_binary64_hex"]:
        raise AssertionError("origin-divisor control is degenerate")
    print("CAUGHT origin-total-target-divisor")
    caught += 1

    bad_manifest = make_sample_manifest()
    bad_manifest["bindings"]["settings"]["sha256"] = bad_manifest["bindings"][
        "settings"
    ]["sha256"].upper()
    expect_failure(
        "manifest-uppercase-digest",
        lambda: validate_manifest_dict(bad_manifest),
    )
    caught += 1

    extra_manifest = make_sample_manifest()
    extra_manifest["default_pass"] = True
    expect_failure(
        "manifest-extra-default-pass",
        lambda: validate_manifest_dict(extra_manifest),
    )
    caught += 1

    rows = target_rows(seed, 0)
    short_certificate = affine_certificate(seed, 0)
    short_certificate["triples"] = short_certificate["triples"][:-1]
    expect_failure(
        "affine-only-100-triples",
        lambda: verify_affine_certificate(rows, short_certificate),
    )
    caught += 1

    weak_rows = copy.deepcopy(rows)
    certificate = affine_certificate(seed, 0)
    centre = tuple(certificate["triples"][0]["p1"])
    by_coordinate = {(row["x"], row["y"]): row for row in weak_rows}
    by_coordinate[centre]["truth_depth_steps"] -= 1
    expect_failure(
        "affine-second-difference-weakened",
        lambda: verify_affine_certificate(weak_rows, certificate),
    )
    caught += 1

    probes = fixtures["renderer_probe"]["probes"]
    rendered = bytearray(render_probe_bytes(seed, probes))
    rendered[0] ^= 1
    mutated = artifact_digest(bytes(rendered))["sha256_lowerhex"]
    if mutated == fixtures["renderer_probe"]["expected_sha256_lowerhex"]:
        raise AssertionError("renderer mutation did not move the digest")
    print("CAUGHT renderer-one-bit-mutation")
    caught += 1

    wrong_fit = fit_origin([1.0, 2.0, 99.0, 4.0], [True, True, True, True])
    if wrong_fit["N"] != 4:
        raise AssertionError("origin validity mutation did not exercise N=4")
    if (
        wrong_fit["origin_binary64_hex"]
        == fixtures["origin_fit"]["expected"]["origin_binary64_hex"]
    ):
        raise AssertionError("origin validity mutation did not move the result")
    print("CAUGHT origin-invalid-row-included")
    caught += 1

    if caught != 8:
        raise AssertionError(f"expected 8 caught controls, got {caught}")
    print("COMMISSIONED 8/8")


if __name__ == "__main__":
    main()
