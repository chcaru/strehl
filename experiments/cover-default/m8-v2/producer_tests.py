"""Commission the M8-v2 producer and injector without a real capture.

This script extracts the current committed tree with ``git archive``, injects
the live hook into that private snapshot, compiles there with private target
directories, and runs the synthetic fixture against the archived production
sampler. It validates producer bytes and refusal semantics only; it does not
compute source hulls, tolerances, contributors, or checker verdicts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import struct
import subprocess
import sys
import tarfile
from dataclasses import dataclass
from pathlib import Path


HEADER = struct.Struct("<8s9I6d2fI")
MAGIC = b"M8SITE01"
WIRE_VERSION = 2
FILENAME = re.compile(
    r"^m8-v2-block-v1-p2-([0-9a-f]{64})-s([01])([01])-([0-9a-f]{64})\.m8site$"
)
EXPECTED_FRAMES = {
    "fixtures/hard-step.arw",
    "fixtures/exact-copy.arw",
    "fixtures/fractional-bilinear.arw",
    "fixtures/transform-scale.arw",
    "fixtures/transform-rotation.arw",
    "fixtures/transform-translation.arw",
    "fixtures/transform-both-axes.arw",
    "fixtures/cfa-r.arw",
    "fixtures/cfa-g1.arw",
    "fixtures/cfa-g2.arw",
    "fixtures/cfa-b.arw",
    "fixtures/boundary.arw",
    "fixtures/source-nan-payload.arw",
    "fixtures/left/repeated.arw",
    "fixtures/right/repeated.arw",
    "plants/wrong-kernel.arw",
    "plants/wrong-transform-bit.arw",
    "plants/wrong-source-plane.arw",
    "plants/wrong-cfa-channel.arw",
    "plants/finite-as-nan.arw",
    "plants/invalid-as-finite.arw",
}


@dataclass(frozen=True)
class Completed:
    command: tuple[str, ...]
    returncode: int
    stdout: str


@dataclass(frozen=True)
class Block:
    path: Path
    version: int
    kernel: int
    source_width: int
    source_height: int
    destination_width: int
    destination_height: int
    site_x: int
    site_y: int
    channel: int
    a_re: float
    a_im: float
    b_re: float
    b_im: float
    cx: float
    cy: float
    black_white_range: float
    site_gain: float
    frame_path: str
    source_bits: tuple[int, ...]
    destination_bits: tuple[int, ...]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def capped_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(
        {
            "CARGO_BUILD_JOBS": "8",
            "RAYON_NUM_THREADS": "8",
            "OMP_NUM_THREADS": "8",
            "OPENBLAS_NUM_THREADS": "8",
            "MKL_NUM_THREADS": "8",
            "NUMEXPR_NUM_THREADS": "8",
            "BLIS_NUM_THREADS": "8",
            "VECLIB_MAXIMUM_THREADS": "8",
            "STREHL_PYRAMID_WORKERS": "1",
            "PYTHONIOENCODING": "utf-8",
        }
    )
    return environment


def run(
    command: list[str],
    *,
    cwd: Path | None = None,
    environment: dict[str, str] | None = None,
    expected: int | None = 0,
) -> Completed:
    process = subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    completed = Completed(tuple(command), process.returncode, process.stdout)
    if expected is not None and process.returncode != expected:
        rendered = subprocess.list2cmdline(command)
        raise RuntimeError(
            f"command exited {process.returncode}, expected {expected}: "
            f"{rendered}\n{process.stdout}"
        )
    return completed


def extract_committed_archive(repo: Path, snapshot: Path) -> str:
    head = run(["git", "-C", str(repo), "rev-parse", "HEAD"]).stdout.strip()
    snapshot.mkdir(parents=True)
    process = subprocess.Popen(
        ["git", "-C", str(repo), "archive", "--format=tar", "HEAD"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert process.stdout is not None
    with tarfile.open(fileobj=process.stdout, mode="r|") as archive:
        for member in archive:
            member_path = Path(member.name)
            require(
                not member_path.is_absolute() and ".." not in member_path.parts,
                f"unsafe git-archive member {member.name!r}",
            )
            archive.extract(member, snapshot, filter="data")
    _, stderr = process.communicate()
    if process.returncode != 0:
        raise RuntimeError(
            f"git archive exited {process.returncode}: "
            f"{stderr.decode('utf-8', errors='replace')}"
        )
    return head


def parse_block(path: Path) -> Block:
    payload = path.read_bytes()
    require(len(payload) >= HEADER.size, f"{path}: truncated header")
    fields = HEADER.unpack_from(payload)
    (
        magic,
        version,
        kernel,
        source_width,
        source_height,
        destination_width,
        destination_height,
        site_x,
        site_y,
        channel,
        a_re,
        a_im,
        b_re,
        b_im,
        cx,
        cy,
        black_white_range,
        site_gain,
        frame_length,
    ) = fields
    require(magic == MAGIC, f"{path}: wrong magic {magic!r}")
    require(version == WIRE_VERSION, f"{path}: wrong wire version {version}")
    frame_start = HEADER.size
    frame_end = frame_start + frame_length
    source_end = frame_end + 4 * source_width * source_height
    destination_end = source_end + 4 * destination_width * destination_height
    require(
        destination_end == len(payload),
        f"{path}: block-v1 length is {len(payload)}, expected {destination_end}",
    )
    frame_path = payload[frame_start:frame_end].decode("utf-8")
    source_bits = struct.unpack_from(
        f"<{source_width * source_height}I", payload, frame_end
    )
    destination_bits = struct.unpack_from(
        f"<{destination_width * destination_height}I", payload, source_end
    )
    return Block(
        path,
        version,
        kernel,
        source_width,
        source_height,
        destination_width,
        destination_height,
        site_x,
        site_y,
        channel,
        a_re,
        a_im,
        b_re,
        b_im,
        cx,
        cy,
        black_white_range,
        site_gain,
        frame_path,
        source_bits,
        destination_bits,
    )


def f32_bits(value: float) -> int:
    return struct.unpack("<I", struct.pack("<f", value))[0]


def f64_bits(value: float) -> int:
    return struct.unpack("<Q", struct.pack("<d", value))[0]


def is_nan_bits(bits: int) -> bool:
    return (bits & 0x7F80_0000) == 0x7F80_0000 and (bits & 0x007F_FFFF) != 0


def assert_empty_state(trace_root: Path) -> None:
    for name in ("claims", "staging"):
        entries = list((trace_root / name).iterdir())
        require(not entries, f"{trace_root / name}: leftover ambiguous state {entries}")


def inventory(blocks: Path) -> dict[str, str]:
    return {
        path.name: sha256_file(path)
        for path in sorted(blocks.glob("*.m8site"))
    }


def validate_blocks(trace_root: Path) -> dict[str, Block]:
    paths = sorted((trace_root / "blocks").glob("*.m8site"))
    require(
        len(paths) == len(EXPECTED_FRAMES),
        f"fixture emitted {len(paths)} blocks, expected {len(EXPECTED_FRAMES)}",
    )
    parsed = [parse_block(path) for path in paths]
    by_frame = {block.frame_path: block for block in parsed}
    require(
        set(by_frame) == EXPECTED_FRAMES,
        f"fixture frame set mismatch: {sorted(set(by_frame) ^ EXPECTED_FRAMES)}",
    )

    for block in parsed:
        require(
            (block.source_width, block.source_height) == (24, 20),
            f"{block.frame_path}: wrong source dimensions",
        )
        require(
            (block.destination_width, block.destination_height) == (12, 10),
            f"{block.frame_path}: wrong destination dimensions",
        )
        require(
            f32_bits(block.black_white_range) == f32_bits(14_848.0),
            f"{block.frame_path}: black/white range bits changed",
        )
        match = FILENAME.fullmatch(block.path.name)
        require(match is not None, f"{block.path}: filename is not M8-v2 block-v1")
        assert match is not None
        frame_hash, file_site_x, file_site_y, content_hash = match.groups()
        require(
            frame_hash == sha256_bytes(block.frame_path.encode("utf-8")),
            f"{block.path}: frame-path hash mismatch",
        )
        require(
            (int(file_site_x), int(file_site_y)) == (block.site_x, block.site_y),
            f"{block.path}: filename/header site mismatch",
        )
        require(
            content_hash == sha256_file(block.path),
            f"{block.path}: content hash mismatch",
        )

    hard = by_frame["fixtures/hard-step.arw"]
    require(
        f32_bits(-0.0625) in hard.destination_bits,
        "hard-step trace omitted exact -0.0625 Catmull value",
    )
    require(
        f32_bits(1.0625) in hard.destination_bits,
        "hard-step trace omitted exact +1.0625 Catmull value",
    )

    copy = by_frame["fixtures/exact-copy.arw"]
    require(
        copy.destination_bits[3 * 12 + 3] == copy.source_bits[6 * 24 + 6],
        "identity fixture did not preserve its exact-copy anchor",
    )
    bilinear = by_frame["fixtures/fractional-bilinear.arw"]
    require(
        bilinear.kernel == 1
        and any(not is_nan_bits(bits) for bits in bilinear.destination_bits),
        "fractional bilinear fixture was not emitted",
    )

    boundary = by_frame["fixtures/boundary.arw"]
    require(
        any(is_nan_bits(bits) for bits in boundary.destination_bits)
        and any(not is_nan_bits(bits) for bits in boundary.destination_bits),
        "boundary fixture lacks finite/invalid diversity",
    )
    source_nan = by_frame["fixtures/source-nan-payload.arw"]
    require(
        0x7FC1_2345 in source_nan.source_bits,
        "source NaN payload bits were not retained",
    )

    expected_sites = {
        "fixtures/cfa-r.arw": (0, 0, 0),
        "fixtures/cfa-g1.arw": (1, 0, 1),
        "fixtures/cfa-g2.arw": (0, 1, 1),
        "fixtures/cfa-b.arw": (1, 1, 2),
    }
    for frame, expected in expected_sites.items():
        block = by_frame[frame]
        require(
            (block.site_x, block.site_y, block.channel) == expected,
            f"{frame}: CFA metadata mismatch",
        )

    left = by_frame["fixtures/left/repeated.arw"]
    right = by_frame["fixtures/right/repeated.arw"]
    require(left.path.name != right.path.name, "repeated basenames collided")

    require(
        by_frame["plants/wrong-kernel.arw"].kernel == 1,
        "wrong-kernel metadata plant was not emitted",
    )
    require(
        f64_bits(by_frame["plants/wrong-transform-bit.arw"].a_re)
        == f64_bits(1.0) ^ 1,
        "wrong-transform-bit plant did not retain the flipped f64 bit",
    )
    wrong_source = by_frame["plants/wrong-source-plane.arw"]
    require(
        wrong_source.source_bits != copy.source_bits
        and wrong_source.destination_bits == copy.destination_bits,
        "wrong-source-plane plant did not separate source and gathered values",
    )
    wrong_cfa = by_frame["plants/wrong-cfa-channel.arw"]
    require(
        (wrong_cfa.site_x, wrong_cfa.site_y, wrong_cfa.channel) == (0, 0, 2),
        "wrong-CFA metadata plant was not emitted",
    )
    require(
        is_nan_bits(
            by_frame["plants/finite-as-nan.arw"].destination_bits[3 * 12 + 3]
        ),
        "finite-as-NaN plant was not emitted",
    )
    require(
        by_frame["plants/invalid-as-finite.arw"].destination_bits[0]
        == f32_bits(123.25),
        "invalid-as-finite plant was not emitted",
    )
    return by_frame


def test_injector_and_fixture(repo: Path, work: Path) -> None:
    here = Path(__file__).resolve().parent
    injector = here / "inject_trace_v2.py"
    hook = here / "trace_v2.rs"
    fixture = here / "fixture_v2.rs"
    for path in (injector, hook, fixture):
        require(path.is_file(), f"missing producer source {path}")

    hook_source = hook.read_text(encoding="utf-8")
    for forbidden in (
        "Command::new(",
        "STREHL_M8_CHECKER",
        'arg("consume")',
    ):
        require(forbidden not in hook_source, f"hook contains forbidden {forbidden!r}")
    trace_region = hook_source[hook_source.index("pub fn trace_site(") :]
    early = trace_region.index('var_os("STREHL_M8_V2_TRACE_DIR")')
    write_call = trace_region.index("write_value_block(")
    require(early < write_call, "disabled trace guard is not before producer work")

    private_refusal = run(
        [
            sys.executable,
            str(injector),
            str(repo),
            "--hook",
            str(hook),
        ],
        expected=None,
    )
    require(
        private_refusal.returncode != 0
        and "refusing to patch" in private_refusal.stdout,
        "injector did not refuse the live Git worktree",
    )

    snapshot = work / "snapshot"
    head = extract_committed_archive(repo, snapshot)
    record = work / "injection.json"
    injected = run(
        [
            sys.executable,
            str(injector),
            str(snapshot),
            "--hook",
            str(hook),
            "--record",
            str(record),
        ]
    )
    require("sample_checked-complete" in injected.stdout, "missing seam record")
    recorded = json.loads(record.read_text(encoding="utf-8"))
    require(
        recorded["protocol"] == "m8-v2-injector-v1",
        "wrong injector record protocol",
    )
    require(
        (snapshot / "crates/strehl-cli/src/m8_trace_v2.rs").read_bytes()
        == hook.read_bytes(),
        "snapshot hook copy differs from source",
    )
    align_text = (
        snapshot / "crates/strehl-cli/src/align_cmd.rs"
    ).read_text(encoding="utf-8")
    require(
        align_text.count("crate::m8_trace_v2::trace_site(") == 1,
        "snapshot hook call is not unique",
    )
    require(
        align_text.index("resampler.sample_checked(")
        < align_text.index("crate::m8_trace_v2::trace_site(")
        < align_text.index("let inv = 1.0 / gain[ci];"),
        "snapshot seam order is not sample -> trace -> inverse WB",
    )

    reinjected = run(
        [
            sys.executable,
            str(injector),
            str(snapshot),
            "--hook",
            str(hook),
        ],
        expected=None,
    )
    require(
        reinjected.returncode != 0
        and ("refusing" in reinjected.stdout or "already" in reinjected.stdout),
        "injector did not refuse idempotence",
    )

    environment = capped_environment()
    checked = run(
        [
            "cargo",
            "check",
            "--manifest-path",
            str(snapshot / "Cargo.toml"),
            "-p",
            "strehl-cli",
            "--target-dir",
            str(work / "target-cli"),
        ],
        environment=environment,
    )
    require(
        "Checking strehl-cli" in checked.stdout
        or "Compiling strehl-cli" in checked.stdout,
        "cargo check did not show that strehl-cli was checked",
    )

    examples = snapshot / "crates/strehl-cli/examples"
    examples.mkdir(parents=True, exist_ok=True)
    fixture_dst = examples / "m8_fixture_v2.rs"
    shutil.copyfile(fixture, fixture_dst)
    trace_root = work / "fixture-traces"
    fixture_command = [
        "cargo",
        "run",
        "--manifest-path",
        str(snapshot / "Cargo.toml"),
        "-p",
        "strehl-cli",
        "--example",
        "m8_fixture_v2",
        "--target-dir",
        str(work / "target-fixture"),
        "--",
        "commission",
        str(trace_root),
    ]
    commissioned = run(fixture_command, environment=environment)
    require(
        "Compiling strehl-cli" in commissioned.stdout,
        "fixture cargo run did not show a fresh strehl-cli compile",
    )
    validate_blocks(trace_root)
    assert_empty_state(trace_root)

    fixture_binary = work / "target-fixture/debug/examples/m8_fixture_v2"
    gate_root = work / "gate-off-sentinel"
    gate_environment = environment.copy()
    gate_environment.pop("STREHL_M8_V2_TRACE_DIR", None)
    run(
        [str(fixture_binary), "gate-off", str(gate_root)],
        environment=gate_environment,
    )
    require(
        not gate_root.exists(),
        "disabled trace_site touched its sentinel filesystem path",
    )

    wrapper_root = work / "trace-site-wrapper"
    wrapper_environment = environment.copy()
    wrapper_environment["STREHL_M8_V2_TRACE_DIR"] = str(wrapper_root)
    run(
        [str(fixture_binary), "trace-site", str(wrapper_root)],
        environment=wrapper_environment,
    )
    wrapper_paths = list((wrapper_root / "blocks").glob("*.m8site"))
    require(len(wrapper_paths) == 1, "enabled trace_site did not emit one block")
    wrapper = parse_block(wrapper_paths[0])
    require(
        wrapper.frame_path == "fixtures/trace-site-wrapper.arw"
        and (wrapper.source_width, wrapper.source_height) == (24, 20)
        and (wrapper.destination_width, wrapper.destination_height) == (12, 10)
        and (wrapper.site_x, wrapper.site_y, wrapper.channel) == (0, 0, 0),
        "trace_site wrapper did not derive expected frame/dimensions/CFA metadata",
    )
    wrapper_match = FILENAME.fullmatch(wrapper.path.name)
    require(wrapper_match is not None, "trace_site wrapper filename is malformed")
    assert wrapper_match is not None
    require(
        wrapper_match.group(1)
        == sha256_bytes(wrapper.frame_path.encode("utf-8"))
        and wrapper_match.group(4) == sha256_file(wrapper.path),
        "trace_site wrapper hashes do not match its path/payload",
    )
    assert_empty_state(wrapper_root)

    wrong_channel_root = work / "wrong-channel"
    wrong_channel_environment = environment.copy()
    wrong_channel_environment["STREHL_M8_V2_TRACE_DIR"] = str(
        wrong_channel_root
    )
    wrong_channel = run(
        [
            str(fixture_binary),
            "trace-site-wrong-channel",
            str(wrong_channel_root),
        ],
        environment=wrong_channel_environment,
        expected=None,
    )
    require(
        wrong_channel.returncode != 0
        and "requires channel 0, got 2" in wrong_channel.stdout
        and not wrong_channel_root.exists(),
        "trace_site did not preflight-refuse mismatched CFA metadata",
    )

    invalid_root = work / "invalid-payload"
    invalid_payload = run(
        [str(fixture_binary), "invalid-payload", str(invalid_root)],
        environment=environment,
        expected=None,
    )
    require(
        invalid_payload.returncode != 0
        and "supports Catmull-Rom and bilinear" in invalid_payload.stdout
        and not invalid_root.exists(),
        "invalid payload was not refused before creating trace state",
    )

    before_duplicate = inventory(trace_root / "blocks")
    duplicate = run(fixture_command, environment=environment, expected=None)
    require(
        duplicate.returncode != 0
        and "duplicate M8-v2 frame/site" in duplicate.stdout,
        "completed frame/site was not refused loudly",
    )
    require(
        inventory(trace_root / "blocks") == before_duplicate,
        "duplicate attempt mutated retained completed blocks",
    )
    assert_empty_state(trace_root)

    race_root = work / "race-traces"
    race_command = [
        str(fixture_binary),
        "race",
        str(race_root),
    ]
    racers = [
        subprocess.Popen(
            race_command,
            env=environment,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        for _ in range(2)
    ]
    race_results = [racer.communicate() for racer in racers]
    race_codes = [racer.returncode for racer in racers]
    require(
        sum(code == 0 for code in race_codes) == 1
        and sum(code != 0 for code in race_codes) == 1,
        f"concurrent writers were not one-winner/one-refusal: {race_codes}",
    )
    require(
        len(list((race_root / "blocks").glob("*.m8site"))) == 1,
        "concurrent write did not leave exactly one completed block",
    )
    assert_empty_state(race_root)
    loser_output = "".join(output for output, _ in race_results)
    require(
        "duplicate M8-v2" in loser_output,
        "concurrent loser did not report a duplicate",
    )

    existing = next((race_root / "blocks").glob("*.m8site"))
    match = FILENAME.fullmatch(existing.name)
    require(match is not None, "race block filename is malformed")
    assert match is not None
    frame_hash, site_x, site_y, _ = match.groups()
    ambiguous = existing.with_name(
        f"m8-v2-block-v1-p2-{frame_hash}-s{site_x}{site_y}-"
        f"{'0' * 64}.m8site"
    )
    shutil.copyfile(existing, ambiguous)
    ambiguous_run = run(race_command, environment=environment, expected=None)
    require(
        ambiguous_run.returncode != 0
        and "ambiguous duplicate M8-v2" in ambiguous_run.stdout,
        "ambiguous completed trace state was not refused",
    )

    print(f"producer tests passed against git archive {head}")
    print(f"private snapshot: {snapshot}")
    print(f"retained synthetic blocks: {len(before_duplicate)}")
    print("duplicate and concurrent-state refusals: passed")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path(__file__).resolve().parents[3],
        help="Strehl Git worktree whose committed HEAD is archived read-only",
    )
    parser.add_argument(
        "--work",
        type=Path,
        required=True,
        help="new private directory outside the Git worktree for snapshot/targets/traces",
    )
    args = parser.parse_args()
    repo = args.repo.resolve()
    work = args.work.resolve()
    require((repo / ".git").exists(), f"{repo}: not the Strehl Git worktree")
    try:
        work.relative_to(repo)
    except ValueError:
        pass
    else:
        raise RuntimeError("--work must be outside the Git worktree")
    require(not work.exists(), f"{work}: private work path must not already exist")
    work.mkdir(parents=True)
    test_injector_and_fixture(repo, work)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
