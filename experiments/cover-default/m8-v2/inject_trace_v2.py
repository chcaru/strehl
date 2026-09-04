"""Inject the M8-v2 value-only hook into a private, non-worktree snapshot.

The injector refuses idempotence: it succeeds exactly once on the registered
source shape. It preserves the snapshot's newline convention and verifies that
the sole hook call is the first statement after the full-resolution
``sample_checked`` gather and immediately precedes inverse white balance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path


INJECTOR_PROTOCOL = "m8-v2-injector-v1"
MODULE_ANCHOR = "mod merge_cmd;\n"
MODULE_REPLACEMENT = "mod merge_cmd;\nmod m8_trace_v2;\n"
GATHER_ANCHOR = """                            }
                        }
                    });
            }

            let inv = 1.0 / gain[ci];
"""
HOOK_CALL = """            crate::m8_trace_v2::trace_site(
                frame,
                dx,
                dy,
                geom,
                t_site,
                cx,
                cy,
                ci,
                gain[ci],
                resampler,
                plane,
                &scratch.dst,
            )?;
"""
GATHER_REPLACEMENT = GATHER_ANCHOR.replace(
    "            let inv = 1.0 / gain[ci];\n",
    HOOK_CALL + "            let inv = 1.0 / gain[ci];\n",
)
FULLRES_START = "pub fn warp_frame_in_place_fullres("
FULLRES_END = "\n/// Gate W8"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def read_normalized(path: Path) -> tuple[str, str]:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise RuntimeError(f"{path}: source is not UTF-8") from error
    if "\r\n" in text and text.replace("\r\n", "").find("\r") == -1:
        newline = "\r\n"
    elif "\r" not in text:
        newline = "\n"
    else:
        raise RuntimeError(f"{path}: mixed or bare-CR newlines are not supported")
    return text.replace("\r\n", "\n"), newline


def replace_unique(text: str, anchor: str, replacement: str, label: str) -> str:
    count = text.count(anchor)
    if count != 1:
        raise RuntimeError(
            f"{label}: full-line anchor occurred {count} times, required exactly once"
        )
    return text.replace(anchor, replacement)


def encoded(text: str, newline: str) -> bytes:
    if newline == "\r\n":
        text = text.replace("\n", "\r\n")
    return text.encode("utf-8")


def atomic_write(path: Path, payload: bytes) -> None:
    temporary = path.with_name(f".{path.name}.m8-v2-{os.getpid()}.new")
    try:
        with temporary.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def require_private_snapshot(snapshot: Path) -> None:
    if not snapshot.is_dir():
        raise FileNotFoundError(f"{snapshot}: snapshot directory does not exist")
    if (snapshot / ".git").exists():
        raise RuntimeError(f"{snapshot}: refusing to patch a Git worktree")
    probe = subprocess.run(
        ["git", "-C", str(snapshot), "rev-parse", "--show-toplevel"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if probe.returncode == 0:
        raise RuntimeError(
            f"{snapshot}: refusing to patch a directory inside a Git worktree"
        )
    for required in ("Cargo.toml", "Cargo.lock"):
        if not (snapshot / required).is_file():
            raise FileNotFoundError(f"{snapshot}: missing archive member {required}")


def fullres_region(align_text: str) -> str:
    if align_text.count(FULLRES_START) != 1:
        raise RuntimeError("align_cmd.rs: full-resolution gather function is not unique")
    start = align_text.index(FULLRES_START)
    end = align_text.find(FULLRES_END, start)
    if end == -1:
        raise RuntimeError("align_cmd.rs: full-resolution gather end anchor is absent")
    return align_text[start:end]


def verify_postconditions(main_text: str, align_text: str, hook_text: str) -> None:
    if main_text.count("mod m8_trace_v2;\n") != 1:
        raise RuntimeError("main.rs: injected module declaration is not unique")
    if main_text.count(MODULE_ANCHOR) != 1:
        raise RuntimeError("main.rs: merge_cmd module anchor was not preserved")
    if align_text.count(HOOK_CALL) != 1:
        raise RuntimeError("align_cmd.rs: injected hook call is not unique")
    if align_text.count(GATHER_REPLACEMENT) != 1:
        raise RuntimeError(
            "align_cmd.rs: hook is not exactly between gather completion and inverse WB"
        )
    region = fullres_region(align_text)
    if region.count("resampler.sample_checked(") != 1:
        raise RuntimeError(
            "align_cmd.rs: full-resolution sample_checked call is not unique"
        )
    if region.count(HOOK_CALL) != 1:
        raise RuntimeError(
            "align_cmd.rs: hook did not land inside the full-resolution gather"
        )
    sample_at = region.index("resampler.sample_checked(")
    hook_at = region.index(HOOK_CALL)
    inverse_at = region.index("            let inv = 1.0 / gain[ci];\n")
    if not sample_at < hook_at < inverse_at:
        raise RuntimeError(
            "align_cmd.rs: required sample_checked -> hook -> inverse-WB order was not met"
        )
    required_hook_fragments = (
        'var_os("STREHL_M8_V2_TRACE_DIR")',
        "pub fn trace_site(",
        "pub fn write_value_block(",
        'const PRODUCER_TAG: &str = "m8-v2-block-v1-p2";',
    )
    for fragment in required_hook_fragments:
        if fragment not in hook_text:
            raise RuntimeError(f"hook source is missing required fragment {fragment!r}")


def inject(snapshot: Path, hook: Path, record: Path | None) -> dict[str, object]:
    snapshot = snapshot.resolve()
    hook = hook.resolve()
    require_private_snapshot(snapshot)
    if not hook.is_file():
        raise FileNotFoundError(f"{hook}: hook source does not exist")

    cli = snapshot / "crates" / "strehl-cli" / "src"
    main_rs = cli / "main.rs"
    align_rs = cli / "align_cmd.rs"
    hook_dst = cli / "m8_trace_v2.rs"
    if not (main_rs.is_file() and align_rs.is_file()):
        raise FileNotFoundError(f"{snapshot}: not a Strehl source archive")
    if hook_dst.exists():
        raise RuntimeError(f"{hook_dst}: refusing to overwrite an existing hook")

    main_text, main_newline = read_normalized(main_rs)
    align_text, align_newline = read_normalized(align_rs)
    hook_text, hook_newline = read_normalized(hook)
    if "mod m8_trace_v2;" in main_text or "crate::m8_trace_v2::" in align_text:
        raise RuntimeError("snapshot is already M8-v2-instrumented; refusing idempotence")

    # Preflight every strict anchor before writing any snapshot member.
    new_main = replace_unique(
        main_text, MODULE_ANCHOR, MODULE_REPLACEMENT, str(main_rs)
    )
    new_align = replace_unique(
        align_text, GATHER_ANCHOR, GATHER_REPLACEMENT, str(align_rs)
    )
    verify_postconditions(new_main, new_align, hook_text)

    before = {
        "main.rs": sha256(main_rs),
        "align_cmd.rs": sha256(align_rs),
        "hook_source": sha256(hook),
    }
    atomic_write(hook_dst, encoded(hook_text, hook_newline))
    atomic_write(main_rs, encoded(new_main, main_newline))
    atomic_write(align_rs, encoded(new_align, align_newline))

    written_main, _ = read_normalized(main_rs)
    written_align, _ = read_normalized(align_rs)
    written_hook, _ = read_normalized(hook_dst)
    verify_postconditions(written_main, written_align, written_hook)
    if hook_dst.read_bytes() != hook.read_bytes():
        raise RuntimeError("copied hook differs byte-for-byte from its source")

    payload: dict[str, object] = {
        "protocol": INJECTOR_PROTOCOL,
        "snapshot": str(snapshot),
        "seam": "sample_checked-complete -> trace_site -> inverse-white-balance",
        "before": before,
        "after": {
            "main.rs": sha256(main_rs),
            "align_cmd.rs": sha256(align_rs),
            "m8_trace_v2.rs": sha256(hook_dst),
        },
    }
    if record is not None:
        record = record.resolve()
        record.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(
            record,
            (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Patch one private Strehl source archive with the M8-v2 value-only "
            "producer. Re-running on an instrumented snapshot is an error."
        )
    )
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--hook", type=Path, required=True)
    parser.add_argument("--record", type=Path)
    args = parser.parse_args()
    print(json.dumps(inject(args.snapshot, args.hook, args.record), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
