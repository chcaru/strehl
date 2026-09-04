"""Fixed external commissioning predicates for checker_v2.py.

All expected values below are literal properties of the fixtures.  The tests
never copy an aggregate, support interval, witness or verdict from checker
output into an expectation.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import struct
import tempfile
import unittest
from pathlib import Path

import numpy as np
import tifffile

import checker_v2 as m8


EXTERNAL_HEADER = struct.Struct("<8s9I6d2fI")
EXTERNAL_MAGIC = b"M8SITE01"
EXTERNAL_PROTOCOL = 2
HASH_A = "A" * 64
SITE_COORDS = ((0, 0), (1, 0), (0, 1), (1, 1))
SITE_CHANNELS = (0, 1, 1, 2)


def external_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rewrite_content_addressed_index(
    output: Path, result: dict, index: dict
) -> Path:
    payload = (
        json.dumps(index, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest().upper()
    path = output / f"evidence-index-{digest.lower()}.json"
    path.write_bytes(payload)
    result["evidence_index"] = {
        "path": path.name,
        "bytes": len(payload),
        "sha256": digest,
    }
    (output / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return path


def external_weights(t: float) -> np.ndarray:
    """Literal Catmull-Rom a=-1/2 weights, independent of the checker."""

    t = np.float32(t)
    t2 = np.float32(t * t)
    t3 = np.float32(t2 * t)
    return np.asarray(
        [
            np.float32(-0.5) * t3 + t2 - np.float32(0.5) * t,
            np.float32(1.5) * t3 - np.float32(2.5) * t2 + np.float32(1.0),
            np.float32(-1.5) * t3 + np.float32(2.0) * t2 + np.float32(0.5) * t,
            np.float32(0.5) * t3 - np.float32(0.5) * t2,
        ],
        dtype=np.float32,
    )


def external_catmull(source: np.ndarray, x: float, y: float) -> np.float32:
    x = min(max(x, 1.0), source.shape[1] - 3.0)
    y = min(max(y, 1.0), source.shape[0] - 3.0)
    x0, y0 = math.floor(x), math.floor(y)
    wx = external_weights(x - x0)
    wy = external_weights(y - y0)
    total = np.float32(0.0)
    for dy in range(4):
        row = np.float32(0.0)
        for dx in range(4):
            row = np.float32(
                row
                + np.float32(source[y0 + dy - 1, x0 + dx - 1] * wx[dx])
            )
        total = np.float32(total + np.float32(row * wy[dy]))
    return total


def external_bilinear(source: np.ndarray, x: float, y: float) -> np.float32:
    x = min(max(x, 0.0), source.shape[1] - 2.0)
    y = min(max(y, 0.0), source.shape[0] - 2.0)
    x0, y0 = math.floor(x), math.floor(y)
    fx, fy = np.float32(x - x0), np.float32(y - y0)
    a = np.float32(
        source[y0, x0] * (np.float32(1.0) - fx)
        + source[y0, x0 + 1] * fx
    )
    b = np.float32(
        source[y0 + 1, x0] * (np.float32(1.0) - fx)
        + source[y0 + 1, x0 + 1] * fx
    )
    return np.float32(a * (np.float32(1.0) - fy) + b * fy)


def external_trace(
    source: np.ndarray,
    dst_width: int,
    dst_height: int,
    site: tuple[int, int],
    transform: tuple[float, float, float, float],
    *,
    kernel: str = "catmull-rom",
) -> np.ndarray:
    """Independent scalar trace used only to plant synthetic payload values."""

    a_re, a_im, b_re, b_im = transform
    cx, cy = 0.5 * dst_width, 0.5 * dst_height
    ox, oy = 0.5 * site[0], 0.5 * site[1]
    support = 2.0 if kernel == "catmull-rom" else 1.0
    out = np.full((dst_height, dst_width), np.float32(np.nan), dtype=np.float32)
    for py in range(dst_height):
        for px in range(dst_width):
            xr, yr = px + ox - cx, py + oy - cy
            sx = 2.0 * (a_re * xr - a_im * yr + b_re + cx)
            sy = 2.0 * (a_re * yr + a_im * xr + b_im + cy)
            valid = (
                sx >= support - 0.5
                and sy >= support - 0.5
                and sx <= source.shape[1] - 0.5 - support
                and sy <= source.shape[0] - 0.5 - support
            )
            if valid:
                out[py, px] = (
                    external_catmull(source, sx, sy)
                    if kernel == "catmull-rom"
                    else external_bilinear(source, sx, sy)
                )
    return out


def write_external_block(
    path: Path,
    frame_path: Path,
    source: np.ndarray,
    gathered: np.ndarray,
    *,
    site_index: int,
    transform: tuple[float, float, float, float] = (1.0, 0.0, 0.0, 0.0),
    kernel: int = 0,
    value_range: float = 1.0,
    site_gain: float = 1.0,
    protocol: int = EXTERNAL_PROTOCOL,
) -> None:
    source = np.asarray(source, dtype="<f4")
    gathered = np.asarray(gathered, dtype="<f4")
    dst_height, dst_width = gathered.shape
    src_height, src_width = source.shape
    site_x, site_y = SITE_COORDS[site_index]
    frame = str(frame_path).encode("utf-8")
    header = EXTERNAL_HEADER.pack(
        EXTERNAL_MAGIC,
        protocol,
        kernel,
        src_width,
        src_height,
        dst_width,
        dst_height,
        site_x,
        site_y,
        SITE_CHANNELS[site_index],
        *transform,
        0.5 * dst_width,
        0.5 * dst_height,
        value_range,
        site_gain,
        len(frame),
    )
    path.write_bytes(header + frame + source.tobytes() + gathered.tobytes())


def dummy_block(
    *,
    site_index: int = 0,
    transform: tuple[float, float, float, float] = (1.0, 0.0, 0.0, 0.0),
    dst_width: int = 8,
    dst_height: int = 6,
) -> m8.Block:
    site_x, site_y = SITE_COORDS[site_index]
    return m8.Block(
        path=Path("synthetic.m8site"),
        payload_sha256=HASH_A,
        protocol=2,
        kernel=0,
        src_width=2 * dst_width,
        src_height=2 * dst_height,
        dst_width=dst_width,
        dst_height=dst_height,
        site_x=site_x,
        site_y=site_y,
        channel=SITE_CHANNELS[site_index],
        a_re=transform[0],
        a_im=transform[1],
        b_re=transform[2],
        b_im=transform[3],
        cx=0.5 * dst_width,
        cy=0.5 * dst_height,
        value_range=np.float32(1.0),
        site_gain=np.float32(1.0),
        frame_path="synthetic.ARW",
        source_offset=0,
        gathered_offset=0,
    )


def checker_census(
    source: np.ndarray,
    gathered: np.ndarray,
    block: m8.Block,
    *,
    kernel: str = "catmull-rom",
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    sx, sy = m8.coordinates(block, 0, block.dst_height)
    valid, lo, hi = m8.support_bounds(source, block, sx, sy, kernel=kernel)
    tau = m8.tau_r(lo, hi)
    lower, upper = m8._f32_threshold_masks(
        np.asarray(gathered, dtype=np.float32), lo, hi, tau, valid
    )
    return valid, lo, hi, lower, upper


class SyntheticArm:
    def __init__(self, root: Path, frame_values: list[list[float]], value_range: float):
        self.root = root
        self.sources = root / "sources"
        self.traces = root / "traces"
        self.sources.mkdir()
        self.traces.mkdir()
        self.frame_values = frame_values
        self.value_range = value_range
        self.source_paths: list[Path] = []
        inventory_rows = []
        block_rows = []
        for frame_index, values in enumerate(frame_values):
            source_path = self.sources / f"frame-{frame_index:03d}.ARW"
            source_path.write_bytes(f"synthetic-source-{frame_index}".encode("ascii"))
            self.source_paths.append(source_path)
            inventory_rows.append(
                {
                    "path": str(source_path),
                    "name": source_path.name,
                    "size": source_path.stat().st_size,
                    "sha256": external_sha256(source_path),
                }
            )
            for site_index, value in enumerate(values):
                source = np.full((8, 8), np.float32(value), dtype=np.float32)
                gathered = external_trace(
                    source, 4, 4, SITE_COORDS[site_index], (1.0, 0.0, 0.0, 0.0)
                )
                block_path = (
                    self.traces
                    / f"frame-{frame_index:03d}-{site_index}.m8site"
                )
                write_external_block(
                    block_path,
                    source_path,
                    source,
                    gathered,
                    site_index=site_index,
                    value_range=value_range,
                )
                block_rows.append(
                    {
                        "path": block_path.name,
                        "sha256": external_sha256(block_path),
                        # Deliberately false producer answers.  Acceptance proves
                        # the wrapper's hull/support fields are ignored.
                        "support": [999],
                        "lo": -999,
                        "hi": 999,
                        "tau": 999,
                    }
                )
        self.inventory = root / "inventory.json"
        self.inventory.write_text(
            json.dumps({"entries": inventory_rows}, indent=2) + "\n",
            encoding="utf-8",
        )
        (self.traces / "trace-metadata.json").write_text(
            json.dumps(
                {
                    "schema": "strehl-m8-trace-metadata",
                    "version": 1,
                    "payload_layout": "block-v1",
                    "blocks": block_rows,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    def write_tiff(self, values: np.ndarray, name: str = "out.tiff") -> Path:
        path = self.root / name
        tifffile.imwrite(path, np.asarray(values, dtype=np.uint16), photometric="rgb")
        return path

    def adjudicate(
        self,
        tiff: Path,
        output_name: str,
        *,
        crop: m8.CropRect = m8.CropRect(1, 1, 2, 2),
    ) -> tuple[dict, Path]:
        output = self.root / output_name
        result = m8.adjudicate_arm(
            capture="synthetic",
            trace_dir=self.traces,
            tiff_path=tiff,
            source_inventory_path=self.inventory,
            sidecar_sha256=HASH_A,
            mode="crop",
            crop=crop,
            output_dir=output,
        )
        return result, output


class KernelAndToleranceTests(unittest.TestCase):
    def test_catmull_hard_step_copy_and_bilinear_fixed_predicates(self) -> None:
        source = np.zeros((12, 12), dtype=np.float32)
        source[:, 6:] = np.float32(1.0)
        transform = (1.0, 0.0, 0.25, 0.25)
        catmull = external_trace(source, 6, 6, (0, 0), transform)
        block = dummy_block(transform=transform, dst_width=6, dst_height=6)
        valid, _, _, lower, upper = checker_census(source, catmull, block)
        self.assertEqual(int(np.count_nonzero(valid)), 16)
        self.assertEqual(int(np.count_nonzero(lower)), 4)
        self.assertEqual(int(np.count_nonzero(upper)), 4)
        self.assertEqual(float(np.nanmin(catmull)), -0.0625)
        self.assertEqual(float(np.nanmax(catmull)), 1.0625)

        texture = (
            np.arange(144, dtype=np.float32).reshape(12, 12) / np.float32(256)
        )
        copy = external_trace(texture, 6, 6, (0, 0), (1.0, 0.0, 0.0, 0.0))
        copy_block = dummy_block(dst_width=6, dst_height=6)
        _, _, _, lower, upper = checker_census(texture, copy, copy_block)
        self.assertEqual(int(np.count_nonzero(lower | upper)), 0)

        bilinear = external_trace(
            texture, 6, 6, (0, 0), transform, kernel="bilinear"
        )
        _, _, _, lower, upper = checker_census(
            texture, bilinear, block, kernel="bilinear"
        )
        self.assertEqual(int(np.count_nonzero(lower | upper)), 0)

    def test_explicit_32tau_16tau_restoration_and_exact_boundaries(self) -> None:
        source = np.ones((12, 12), dtype=np.float32)
        block = dummy_block(dst_width=6, dst_height=6)
        baseline = external_trace(source, 6, 6, (0, 0), (1.0, 0.0, 0.0, 0.0))
        tau = np.float32(2.0**-20)
        self.assertEqual(float(m8.tau_r(np.float32(1), np.float32(1))), float(tau))

        plant32 = baseline.copy()
        plant32[2, 2] = np.float32(1.0 - np.float32(32.0) * tau)
        plant32[2, 3] = np.float32(1.0 + np.float32(32.0) * tau)
        _, lo, hi, lower32, upper32 = checker_census(source, plant32, block)
        self.assertEqual(int(np.count_nonzero(lower32)), 1)
        self.assertEqual(int(np.count_nonzero(upper32)), 1)
        excess32 = max(
            float(np.max(lo[lower32] - plant32[lower32] - tau)),
            float(np.max(plant32[upper32] - hi[upper32] - tau)),
        )
        self.assertEqual(excess32, float(np.float32(31.0) * tau))

        plant16 = baseline.copy()
        plant16[2, 2] = np.float32(1.0 - np.float32(16.0) * tau)
        plant16[2, 3] = np.float32(1.0 + np.float32(16.0) * tau)
        _, lo, hi, lower16, upper16 = checker_census(source, plant16, block)
        excess16 = max(
            float(np.max(lo[lower16] - plant16[lower16] - tau)),
            float(np.max(plant16[upper16] - hi[upper16] - tau)),
        )
        self.assertEqual(int(np.count_nonzero(lower16 | upper16)), 2)
        self.assertEqual(excess16, float(np.float32(15.0) * tau))
        self.assertLess(excess16, excess32)

        boundary = baseline.copy()
        boundary[2, 2] = np.float32(1.0 - tau)
        boundary[2, 3] = np.float32(1.0 + tau)
        _, _, _, lower, upper = checker_census(source, boundary, block)
        self.assertEqual(int(np.count_nonzero(lower | upper)), 0)

        _, _, _, lower, upper = checker_census(source, baseline, block)
        self.assertEqual(int(np.count_nonzero(lower | upper)), 0)

    def test_binary32_tau_at_power_boundaries(self) -> None:
        expected = {
            0.5: 2.0**-20,
            1.0: 2.0**-20,
            2.0: 2.0**-19,
            4.0: 2.0**-18,
        }
        for value, tau in expected.items():
            got = float(m8.tau_r(np.float32(-value), np.float32(value)))
            self.assertEqual(got, tau)


class GeometryAndRefusalTests(unittest.TestCase):
    def test_transform_scale_rotation_translation_both_axes_and_cfa(self) -> None:
        translation = dummy_block(transform=(1.0, 0.0, 0.25, -0.5))
        sx, sy = m8.coordinates(translation, 1, 2)
        self.assertEqual((float(sx[0, 2]), float(sy[0, 0])), (4.5, 1.0))

        scale = dummy_block(transform=(1.1, 0.0, 0.0, 0.0))
        sx, sy = m8.coordinates(scale, 1, 2)
        self.assertAlmostEqual(float(sx[0, 2]), 3.6, places=14)
        self.assertAlmostEqual(float(sy[0, 0]), 1.6, places=14)

        rotation = dummy_block(transform=(1.0, 0.2, 0.0, 0.0))
        sx, sy = m8.coordinates(rotation, 1, 2)
        self.assertAlmostEqual(float(sx[0, 2]), 4.8, places=14)
        self.assertAlmostEqual(float(sy[0, 2]), 1.2, places=14)

        both = dummy_block(site_index=2, transform=(1.1, 0.2, 0.3, -0.4))
        sx, sy = m8.coordinates(both, 1, 2)
        self.assertAlmostEqual(float(sx[0, 2]), 4.8, places=14)
        self.assertAlmostEqual(float(sy[0, 2]), 1.1, places=14)

        red = dummy_block(site_index=0)
        blue = dummy_block(site_index=3)
        rsx, rsy = m8.coordinates(red, 1, 2)
        bsx, bsy = m8.coordinates(blue, 1, 2)
        self.assertEqual((float(rsx[0, 2]), float(rsy[0, 0])), (4.0, 2.0))
        self.assertEqual((float(bsx[0, 2]), float(bsy[0, 0])), (5.0, 3.0))

    def test_boundary_clamp_floor_and_exact_4x4_support(self) -> None:
        block = dummy_block(dst_width=6, dst_height=6)
        source = np.arange(144, dtype=np.float32).reshape(12, 12)
        sx = np.asarray([[1.5, 1.499, 9.5, 9.501]], dtype=np.float64)
        sy = np.full_like(sx, 2.0)
        valid, lo, hi = m8.support_bounds(source, block, sx, sy)
        self.assertEqual(valid.tolist(), [[True, False, True, False]])
        self.assertEqual(float(lo[0, 0]), float(source[1, 0]))
        self.assertEqual(float(hi[0, 0]), float(source[4, 3]))
        self.assertEqual(float(lo[0, 2]), float(source[1, 8]))
        self.assertEqual(float(hi[0, 2]), float(source[4, 11]))

    def test_wrong_source_wrong_transform_and_wrong_kernel_fail(self) -> None:
        block = dummy_block(dst_width=6, dst_height=6)
        source = np.zeros((12, 12), dtype=np.float32)
        gathered = external_trace(source, 6, 6, (0, 0), (1.0, 0.0, 0.0, 0.0))
        gathered[2, 2] = np.float32(1.0)
        _, _, _, lower, upper = checker_census(source, gathered, block)
        self.assertEqual(int(np.count_nonzero(lower | upper)), 1)

        boundary_transform = (0.75, 0.0, 0.0, 0.0)
        boundary_trace = external_trace(
            source, 6, 6, (0, 0), boundary_transform
        )
        shifted = dummy_block(
            transform=(
                float(np.nextafter(np.float64(0.75), np.float64(1.0))),
                0.0,
                0.0,
                0.0,
            ),
            dst_width=6,
            dst_height=6,
        )
        sx, sy = m8.coordinates(shifted, 0, 6)
        valid, _, _ = m8.support_bounds(source, shifted, sx, sy)
        self.assertGreater(
            int(np.count_nonzero(np.isfinite(boundary_trace) ^ valid)),
            0,
            "one changed f64 transform bit must alter validity in this plant",
        )

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source_path = root / "frame.ARW"
            source_path.write_bytes(b"x")
            bilinear_path = root / "bad.m8site"
            bilinear = external_trace(
                source,
                6,
                6,
                (0, 0),
                (1.0, 0.0, 0.0, 0.0),
                kernel="bilinear",
            )
            write_external_block(
                bilinear_path,
                source_path,
                source,
                bilinear,
                site_index=0,
                kernel=1,
            )
            parsed = m8.read_block(bilinear_path)
            self.assertEqual(parsed.kernel, 1)

            invalid_cfa = bytearray(bilinear_path.read_bytes())
            # Header field 8 of 9I is channel; R may not declare green.
            invalid_cfa[40:44] = struct.pack("<I", 1)
            cfa_path = root / "bad-cfa.m8site"
            cfa_path.write_bytes(invalid_cfa)
            with self.assertRaises(m8.Refusal):
                m8.read_block(cfa_path)

    def test_finite_pattern_source_missing_duplicate_and_concurrency_refusals(self) -> None:
        block = dummy_block(dst_width=6, dst_height=6)
        source = np.zeros((12, 12), dtype=np.float32)
        gathered = external_trace(source, 6, 6, (0, 0), (1.0, 0.0, 0.0, 0.0))
        sx, sy = m8.coordinates(block, 0, 6)
        valid, _, _ = m8.support_bounds(source, block, sx, sy)
        bad_valid = gathered.copy()
        bad_valid[2, 2] = np.float32(np.nan)
        self.assertTrue(np.any(np.isfinite(bad_valid) ^ valid))
        bad_invalid = gathered.copy()
        bad_invalid[0, 0] = np.float32(0.0)
        self.assertTrue(np.any(np.isfinite(bad_invalid) ^ valid))
        source[0, 0] = np.float32(np.nan)
        self.assertFalse(np.all(np.isfinite(source)))

        with self.assertRaises(m8.Refusal):
            m8.refuse_unsafe_producer_state(
                expected_blocks=4,
                observed_blocks=3,
                duplicate_blocks=0,
                concurrent_writers=1,
                transparency_hashes=(HASH_A, HASH_A, HASH_A),
            )
        with self.assertRaises(m8.Refusal):
            m8.refuse_unsafe_producer_state(
                expected_blocks=4,
                observed_blocks=4,
                duplicate_blocks=1,
                concurrent_writers=1,
                transparency_hashes=(HASH_A, HASH_A, HASH_A),
            )
        with self.assertRaises(m8.Refusal):
            m8.refuse_unsafe_producer_state(
                expected_blocks=4,
                observed_blocks=4,
                duplicate_blocks=0,
                concurrent_writers=2,
                transparency_hashes=(HASH_A, HASH_A, HASH_A),
            )
        with self.assertRaises(m8.Refusal):
            m8.refuse_unsafe_producer_state(
                expected_blocks=4,
                observed_blocks=4,
                duplicate_blocks=0,
                concurrent_writers=1,
                transparency_hashes=(HASH_A, HASH_A, "B" * 64),
            )
        m8.refuse_unsafe_producer_state(
            expected_blocks=4,
            observed_blocks=4,
            duplicate_blocks=0,
            concurrent_writers=1,
            transparency_hashes=(HASH_A, HASH_A, HASH_A),
        )

    def test_trace_path_must_match_inventory_not_only_basename(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            arm = SyntheticArm(root, [[0.5, 0.5, 0.5, 0.5]], value_range=1.0)
            wrong_dir = root / "wrong-source"
            wrong_dir.mkdir()
            wrong_source = wrong_dir / arm.source_paths[0].name
            wrong_source.write_bytes(arm.source_paths[0].read_bytes())

            block_path = arm.traces / "frame-000-0.m8site"
            source = np.full((12, 12), np.float32(0.5), dtype=np.float32)
            gathered = external_trace(
                source, 6, 6, (0, 0), (1.0, 0.0, 0.0, 0.0)
            )
            write_external_block(
                block_path,
                wrong_source,
                source,
                gathered,
                site_index=0,
                value_range=1.0,
                site_gain=1.0,
            )
            wrapper_path = arm.traces / "trace-metadata.json"
            wrapper = json.loads(wrapper_path.read_text("utf-8"))
            wrapper["blocks"][0]["sha256"] = external_sha256(block_path)
            wrapper_path.write_text(
                json.dumps(wrapper, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            inventory = m8.read_source_inventory(arm.inventory)
            blocks, _ = m8.discover_blocks(arm.traces)
            with self.assertRaisesRegex(
                m8.Refusal, "absent from the source inventory"
            ):
                m8._validate_trace_set(blocks, inventory)


class OutputAndEvidenceTests(unittest.TestCase):
    def test_scale_full_and_delivered_domains_coincide(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            arm = SyntheticArm(root, [[0.5, 0.5, 0.5, 0.5]], value_range=1.0)
            wrapper = json.loads(
                (arm.traces / "trace-metadata.json").read_text("utf-8")
            )
            for site_index in range(4):
                path = arm.traces / f"frame-000-{site_index}.m8site"
                source = np.full((8, 8), np.float32(0.5), dtype=np.float32)
                gathered = external_trace(
                    source,
                    4,
                    4,
                    SITE_COORDS[site_index],
                    (0.5, 0.0, 0.0, 0.0),
                )
                write_external_block(
                    path,
                    arm.source_paths[0],
                    source,
                    gathered,
                    site_index=site_index,
                    transform=(0.5, 0.0, 0.0, 0.0),
                    value_range=1.0,
                )
                wrapper["blocks"][site_index]["sha256"] = external_sha256(path)
            (arm.traces / "trace-metadata.json").write_text(
                json.dumps(wrapper, indent=2) + "\n", encoding="utf-8"
            )
            tiff = arm.write_tiff(
                np.full((4, 4, 3), 32768, dtype=np.uint16)
            )
            output = root / "scale"
            result = m8.adjudicate_arm(
                capture="synthetic-scale",
                trace_dir=arm.traces,
                tiff_path=tiff,
                source_inventory_path=arm.inventory,
                sidecar_sha256=HASH_A,
                mode="scale",
                crop=None,
                output_dir=output,
            )
            full = result["m8_r"]["primary_full"]
            delivered = result["m8_r"]["delivered_subset"]
            self.assertEqual(full["denominator"], delivered["denominator"])
            self.assertEqual(full["violations"], delivered["violations"])
            self.assertEqual(full["denominator"], 64)

    def test_multiframe_endpoint_tau_green_witnesses_and_both_directions(self) -> None:
        values = [
            [1.0, 1.6, 0.8, 1.0],
            [0.5, 0.4, 1.2, 0.25],
            [3.0, 2.4, 4.1, 2.0],
        ]
        image = np.full((2, 2, 3), 10000, dtype=np.uint16)
        image[0, 0, :] = 0
        image[0, 1, :] = 65535
        with tempfile.TemporaryDirectory() as raw:
            arm = SyntheticArm(Path(raw), values, value_range=8.0)
            tiff = arm.write_tiff(image)
            result, output = arm.adjudicate(tiff, "adjudicated")
            self.assertEqual(result["m8_r"]["primary_full"]["violations"], 0)
            self.assertEqual(result["m8_o"]["violations"], 6)
            self.assertEqual(result["m8_o"]["lower_violations"], 3)
            self.assertEqual(result["m8_o"]["upper_violations"], 3)

            index = json.loads(
                (output / result["evidence_index"]["path"]).read_text("utf-8")
            )
            endpoint = np.load(output / index["m8_o"]["endpoint_values"]["path"])
            witness = np.load(
                output / index["m8_o"]["endpoint_witness_frames"]["path"]
            )
            self.assertEqual(float(endpoint[0, 1, 1, 0]), 0.0625)
            self.assertEqual(float(endpoint[0, 1, 1, 1]), 0.375)
            self.assertEqual(int(witness[0, 1, 1, 0]), 1)
            self.assertEqual(int(witness[0, 1, 1, 1]), 2)
            self.assertEqual(int(witness[0, 1, 1, 2]), 2)
            self.assertEqual(int(witness[1, 1, 1, 0]), 1)
            self.assertEqual(int(witness[2, 1, 1, 0]), 0)
            self.assertEqual(int(witness[1, 1, 1, 1]), 2)
            self.assertEqual(int(witness[2, 1, 1, 1]), 2)
            self.assertEqual(int(witness[2, 1, 1, 2]), 2)

            rows = np.load(
                output / index["m8_o"]["violations_file"]["path"],
                allow_pickle=False,
            )
            green_lower = rows[(rows["channel"] == 1) & (rows["direction"] == -1)][0]
            self.assertAlmostEqual(float(green_lower["lo"]), 0.075, places=7)
            self.assertAlmostEqual(float(green_lower["hi"]), 0.40625, places=7)
            self.assertEqual(
                (
                    int(green_lower["lo_frame_a"]),
                    int(green_lower["lo_site_a"]),
                    int(green_lower["lo_frame_b"]),
                    int(green_lower["lo_site_b"]),
                ),
                (1, 1, 0, 2),
            )
            self.assertEqual(
                (
                    int(green_lower["hi_frame_a"]),
                    int(green_lower["hi_site_a"]),
                    int(green_lower["hi_frame_b"]),
                    int(green_lower["hi_site_b"]),
                ),
                (2, 1, 2, 2),
            )
            self.assertEqual(
                (int(green_lower["tau_frame"]), int(green_lower["tau_site"])),
                (2, 2),
            )

    def test_exact_ties_choose_lowest_frame_and_zero_rows_keep_witness_maps(self) -> None:
        image = np.full((2, 2, 3), 32768, dtype=np.uint16)
        with tempfile.TemporaryDirectory() as raw:
            arm = SyntheticArm(
                Path(raw),
                [[0.5, 0.5, 0.5, 0.5], [0.5, 0.5, 0.5, 0.5]],
                value_range=1.0,
            )
            tiff = arm.write_tiff(image)
            result, output = arm.adjudicate(tiff, "ties")
            self.assertEqual(result["m8_r"]["primary_full"]["violations"], 0)
            self.assertEqual(result["m8_o"]["violations"], 0)
            index = json.loads(
                (output / result["evidence_index"]["path"]).read_text("utf-8")
            )
            witness = np.load(
                output / index["m8_o"]["endpoint_witness_frames"]["path"]
            )
            self.assertTrue(np.all(witness[:, 1:3, 1:3, :] == 0))
            self.assertEqual(
                index["m8_o"]["violations_file"]["rows"],
                0,
            )
            self.assertTrue(all(row["rows"] == 0 for row in index["m8_r"]["files"]))

    def test_quantization_boundaries_and_clamp_cases(self) -> None:
        encoded = np.asarray([[100, 201]], dtype=np.uint16)
        lo = np.asarray([[100.5 / 65535.0, 0.0]], dtype=np.float64)
        hi = np.asarray([[1.0, 200.5 / 65535.0]], dtype=np.float64)
        tau = np.zeros_like(lo)
        lower, upper, _, tolerance = m8._output_threshold_masks(
            encoded, lo, hi, tau
        )
        self.assertEqual(lower.tolist(), [[False, False]])
        self.assertEqual(upper.tolist(), [[False, False]])
        self.assertEqual(float(tolerance[0, 0]), 0.5 / 65535.0)

        encoded = np.asarray([[99, 202]], dtype=np.uint16)
        lower, upper, _, _ = m8._output_threshold_masks(encoded, lo, hi, tau)
        self.assertEqual(lower.tolist(), [[True, False]])
        self.assertEqual(upper.tolist(), [[False, True]])

        encoded = np.asarray([[0, 65535]], dtype=np.uint16)
        lo = np.asarray([[-0.1, -0.1]])
        hi = np.asarray([[1.1, 1.1]])
        lower, upper, _, _ = m8._output_threshold_masks(encoded, lo, hi, tau)
        self.assertFalse(np.any(lower | upper))

    def test_final_32tau_16tau_improvement_and_restoration_order(self) -> None:
        centre = 32768
        bound = np.full((1, 2), centre / 65535.0, dtype=np.float64)
        tau = np.full((1, 2), 2.0 / 65535.0, dtype=np.float64)
        plant32 = np.asarray([[centre - 64, centre + 64]], dtype=np.uint16)
        lower32, upper32, normalized32, tolerance32 = (
            m8._output_threshold_masks(plant32, bound, bound, tau)
        )
        self.assertEqual(
            (int(np.count_nonzero(lower32)), int(np.count_nonzero(upper32))),
            (1, 1),
        )
        excess32 = float(
            np.max(
                np.where(
                    lower32,
                    bound - normalized32 - tolerance32,
                    normalized32 - bound - tolerance32,
                )
            )
        )
        self.assertAlmostEqual(excess32 * 65535.0, 61.5, places=10)

        plant16 = np.asarray([[centre - 32, centre + 32]], dtype=np.uint16)
        lower16, upper16, normalized16, tolerance16 = (
            m8._output_threshold_masks(plant16, bound, bound, tau)
        )
        self.assertEqual(
            (int(np.count_nonzero(lower16)), int(np.count_nonzero(upper16))),
            (1, 1),
        )
        excess16 = float(
            np.max(
                np.where(
                    lower16,
                    bound - normalized16 - tolerance16,
                    normalized16 - bound - tolerance16,
                )
            )
        )
        self.assertAlmostEqual(excess16 * 65535.0, 29.5, places=10)
        self.assertLess(excess16, excess32)

        restored = np.asarray([[centre, centre]], dtype=np.uint16)
        lower0, upper0, _, _ = m8._output_threshold_masks(
            restored, bound, bound, tau
        )
        self.assertEqual(int(np.count_nonzero(lower0 | upper0)), 0)

    def test_wrong_kernel_and_finite_pattern_are_end_to_end_refusals(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            arm = SyntheticArm(root, [[0.5, 0.5, 0.5, 0.5]], value_range=1.0)
            path = arm.traces / "frame-000-0.m8site"
            source = np.full((8, 8), np.float32(0.5), dtype=np.float32)
            gathered = external_trace(
                source,
                4,
                4,
                SITE_COORDS[0],
                (1.0, 0.0, 0.0, 0.0),
                kernel="bilinear",
            )
            write_external_block(
                path,
                arm.source_paths[0],
                source,
                gathered,
                site_index=0,
                kernel=1,
            )
            wrapper = json.loads(
                (arm.traces / "trace-metadata.json").read_text("utf-8")
            )
            wrapper["blocks"][0]["sha256"] = external_sha256(path)
            (arm.traces / "trace-metadata.json").write_text(
                json.dumps(wrapper, indent=2) + "\n", encoding="utf-8"
            )
            tiff = arm.write_tiff(np.full((2, 2, 3), 32768, dtype=np.uint16))
            with self.assertRaises(m8.Refusal):
                arm.adjudicate(tiff, "wrong-kernel")
            self.assertFalse((root / "wrong-kernel").exists())

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            arm = SyntheticArm(root, [[0.5, 0.5, 0.5, 0.5]], value_range=1.0)
            path = arm.traces / "frame-000-0.m8site"
            parsed = m8.read_block(path)
            payload = bytearray(path.read_bytes())
            # Full (0,0) is independently invalid under identity Catmull, but
            # the retained gather is planted finite there.
            struct.pack_into("<f", payload, parsed.gathered_offset, 0.5)
            path.write_bytes(payload)
            wrapper = json.loads(
                (arm.traces / "trace-metadata.json").read_text("utf-8")
            )
            wrapper["blocks"][0]["sha256"] = external_sha256(path)
            (arm.traces / "trace-metadata.json").write_text(
                json.dumps(wrapper, indent=2) + "\n", encoding="utf-8"
            )
            tiff = arm.write_tiff(np.full((2, 2, 3), 32768, dtype=np.uint16))
            with self.assertRaises(m8.Refusal):
                arm.adjudicate(tiff, "wrong-finite")
            self.assertFalse((root / "wrong-finite").exists())

    def test_wrong_crop_origin_dimensions_and_correct_restoration(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            arm = SyntheticArm(root, [[1.0, 1.0, 1.0, 1.0]], value_range=16.0)
            # Replace the constant payloads with an x ramp.  The exact identity
            # samples at full x=1 are R=2, G=(3+2)/2, B=3.
            for site_index, site in enumerate(("R", "G1", "G2", "B")):
                block_path = arm.traces / f"frame-000-{site_index}.m8site"
                source = np.broadcast_to(
                    np.arange(12, dtype=np.float32)[None, :], (12, 12)
                ).copy()
                gathered = external_trace(
                    source, 6, 6, SITE_COORDS[site_index], (1.0, 0.0, 0.0, 0.0)
                )
                write_external_block(
                    block_path,
                    arm.source_paths[0],
                    source,
                    gathered,
                    site_index=site_index,
                    value_range=16.0,
                )
            wrapper = json.loads(
                (arm.traces / "trace-metadata.json").read_text("utf-8")
            )
            for row in wrapper["blocks"]:
                row["sha256"] = external_sha256(arm.traces / row["path"])
            (arm.traces / "trace-metadata.json").write_text(
                json.dumps(wrapper, indent=2) + "\n", encoding="utf-8"
            )
            normalized = np.asarray([2.0, 2.5, 3.0]) / 16.0
            image = np.rint(normalized * 65535.0).astype(np.uint16).reshape(1, 1, 3)
            tiff = arm.write_tiff(image)

            correct, correct_output = arm.adjudicate(
                tiff, "crop-correct", crop=m8.CropRect(1, 1, 1, 1)
            )
            self.assertEqual(correct["m8_o"]["violations"], 0)
            mismatched_result = json.loads(
                (correct_output / "result.json").read_text("utf-8")
            )
            mismatched_result["crop"]["x"] = 2
            (correct_output / "result.json").write_text(
                json.dumps(mismatched_result, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(m8.Refusal, "crop disagrees"):
                m8.verify_result(correct_output / "result.json")
            wrong, _ = arm.adjudicate(
                tiff, "crop-wrong-origin", crop=m8.CropRect(3, 1, 1, 1)
            )
            self.assertEqual(wrong["m8_o"]["lower_violations"], 3)
            with self.assertRaises(m8.Refusal):
                arm.adjudicate(
                    tiff,
                    "crop-wrong-size",
                    crop=m8.CropRect(1, 1, 2, 1),
                )
            self.assertFalse((root / "crop-wrong-size").exists())

    def test_final_clamp_m8r_red_m8o_green_and_complete_crop_markers(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            arm = SyntheticArm(root, [[0.0, 0.0, 0.0, 0.0]], value_range=1.0)
            block_path = arm.traces / "frame-000-0.m8site"
            source = np.zeros((8, 8), dtype=np.float32)
            gathered = external_trace(
                source, 4, 4, SITE_COORDS[0], (1.0, 0.0, 0.0, 0.0)
            )
            gathered[1, 1] = np.float32(-0.0625)
            gathered[2, 2] = np.float32(0.0625)
            write_external_block(
                block_path,
                arm.source_paths[0],
                source,
                gathered,
                site_index=0,
                value_range=1.0,
            )
            wrapper = json.loads(
                (arm.traces / "trace-metadata.json").read_text("utf-8")
            )
            wrapper["blocks"][0]["sha256"] = external_sha256(block_path)
            (arm.traces / "trace-metadata.json").write_text(
                json.dumps(wrapper, indent=2) + "\n", encoding="utf-8"
            )
            tiff = arm.write_tiff(np.zeros((1, 1, 3), dtype=np.uint16))
            result, output = arm.adjudicate(
                tiff, "final-clamp", crop=m8.CropRect(1, 1, 1, 1)
            )
            self.assertEqual(result["m8_r"]["primary_full"]["violations"], 2)
            self.assertEqual(result["m8_r"]["delivered_subset"]["violations"], 1)
            self.assertEqual(result["m8_o"]["violations"], 0)
            index = json.loads(
                (output / result["evidence_index"]["path"]).read_text("utf-8")
            )
            red_file = next(
                row
                for row in index["m8_r"]["files"]
                if row["frame_index"] == 0 and row["site"] == "R"
            )
            rows = np.load(output / red_file["path"], allow_pickle=False)
            self.assertEqual(len(rows), 2)
            inside = rows[(rows["full_x"] == 1) & (rows["full_y"] == 1)][0]
            outside = rows[(rows["full_x"] == 2) & (rows["full_y"] == 2)][0]
            self.assertEqual(
                (int(inside["crop_local_x"]), int(inside["crop_local_y"])),
                (0, 0),
            )
            self.assertEqual(
                (int(outside["crop_local_x"]), int(outside["crop_local_y"])),
                (-1, -1),
            )

    def test_hash_and_complete_coordinate_tampering_are_refused(self) -> None:
        image = np.full((2, 2, 3), 32768, dtype=np.uint16)
        with tempfile.TemporaryDirectory() as raw:
            arm = SyntheticArm(
                Path(raw), [[0.5, 0.5, 0.5, 0.5]], value_range=1.0
            )
            tiff = arm.write_tiff(image)
            result, output = arm.adjudicate(tiff, "hash-ok")
            verified = m8.verify_result(output / "result.json")
            self.assertTrue(verified["verified"])

            index = json.loads(
                (output / result["evidence_index"]["path"]).read_text("utf-8")
            )
            evidence = output / index["m8_r"]["files"][0]["path"]
            with evidence.open("r+b") as stream:
                stream.seek(-1, os.SEEK_END)
                value = stream.read(1)
                stream.seek(-1, os.SEEK_END)
                stream.write(bytes((value[0] ^ 1,)))
            with self.assertRaises(m8.Refusal):
                m8.verify_result(output / "result.json")

        # Re-addressing both JSON files cannot turn an incomplete semantic
        # frame/site index into complete evidence.
        with tempfile.TemporaryDirectory() as raw:
            arm = SyntheticArm(
                Path(raw), [[0.5, 0.5, 0.5, 0.5]], value_range=1.0
            )
            tiff = arm.write_tiff(image)
            result, output = arm.adjudicate(tiff, "semantic-r")
            index = json.loads(
                (output / result["evidence_index"]["path"]).read_text("utf-8")
            )
            index["m8_r"]["files"][1]["frame_index"] = 0
            index["m8_r"]["files"][1]["site_index"] = 0
            rewrite_content_addressed_index(output, result, index)
            with self.assertRaises(m8.Refusal):
                m8.verify_result(output / "result.json")

        # Completeness is anchored to the separately hashed retained inventory,
        # not merely to the mutable source list inside the re-addressed index.
        with tempfile.TemporaryDirectory() as raw:
            arm = SyntheticArm(
                Path(raw),
                [[0.5, 0.5, 0.5, 0.5], [0.5, 0.5, 0.5, 0.5]],
                value_range=1.0,
            )
            tiff = arm.write_tiff(image)
            result, output = arm.adjudicate(tiff, "semantic-whole-frame")
            index = json.loads(
                (output / result["evidence_index"]["path"]).read_text("utf-8")
            )
            index["source_inventory"]["entries"] = index["source_inventory"][
                "entries"
            ][:1]
            removed = {
                row["path"]
                for row in index["m8_r"]["files"]
                if row["frame_index"] == 1
            }
            index["m8_r"]["files"] = [
                row
                for row in index["m8_r"]["files"]
                if row["frame_index"] == 0
            ]
            index["artifacts"] = [
                row for row in index["artifacts"] if row["path"] not in removed
            ]
            for summary in index["m8_r"]["summary"].values():
                summary["denominator"] //= 2
            result["m8_r"] = index["m8_r"]["summary"]
            rewrite_content_addressed_index(output, result, index)
            with self.assertRaises(m8.Refusal):
                m8.verify_result(output / "result.json")

        # The same applies to named zero-violation output/witness artifacts:
        # zero rows do not license omitting their complete maps.
        with tempfile.TemporaryDirectory() as raw:
            arm = SyntheticArm(
                Path(raw), [[0.5, 0.5, 0.5, 0.5]], value_range=1.0
            )
            tiff = arm.write_tiff(image)
            result, output = arm.adjudicate(tiff, "semantic-o")
            index = json.loads(
                (output / result["evidence_index"]["path"]).read_text("utf-8")
            )
            removed = index["m8_o"].pop("endpoint_values")
            index["artifacts"] = [
                row for row in index["artifacts"] if row["path"] != removed["path"]
            ]
            rewrite_content_addressed_index(output, result, index)
            with self.assertRaises(m8.Refusal):
                m8.verify_result(output / "result.json")

        with tempfile.TemporaryDirectory() as raw:
            arm = SyntheticArm(
                Path(raw), [[0.5, 0.5, 0.5, 0.5]], value_range=1.0
            )
            tiff = arm.write_tiff(image)
            result, output = arm.adjudicate(tiff, "index-ok")
            index_path = output / result["evidence_index"]["path"]
            index_path.write_bytes(index_path.read_bytes() + b" ")
            with self.assertRaises(m8.Refusal):
                m8.verify_result(output / "result.json")

    def test_independence_and_thread_caps(self) -> None:
        report = m8.independence_report()
        self.assertTrue(report["independent"])
        self.assertEqual(report["forbidden_imports"], [])
        for name in m8.THREAD_ENV:
            self.assertLessEqual(int(os.environ[name]), 8)


if __name__ == "__main__":
    unittest.main()
