from __future__ import annotations

import hashlib
import json
import ntpath
import os
import stat
from pathlib import Path
from typing import Any, NoReturn


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXPERIMENT_DIR.parents[1]
APPROVED_INPUT = r"D:\personal\macro\coffee-bubbles"
PRIVATE_SCRATCH = Path(
    r"C:\Users\chris\.copilot\session-state"
    r"\841ddf83-8ef0-40bd-a341-d2c66d487731\files\M176-worker-invariance"
)
FORBIDDEN_CAPTURE = r"D:\personal\macro\requests\7-aperture-pairs"
PROTECTED_ROOTS = (r"D:\personal\macro", r"D:\edited\macro")
EXPECTED_ARW_COUNT = 19
MAX_RESIDENT_BYTES = 4 * 1024**3
MIN_FREE_SCRATCH_BYTES = 10 * 1024**3
PIXEL_HASH_DOMAIN = b"M176-PIXELS-V1\0"
BOUND_SOURCE_NAMES = (
    ".gitattributes",
    ".gitignore",
    "analyze.py",
    "common.py",
    "mutation_commission.py",
    "preregistration.json",
    "run.py",
    "test_verify.py",
    "verify.py",
)
CHECKOUT_BOUND_RELATIVE_PATHS = (
    ".gitattributes",
    ".gitignore",
    "analyze.py",
    "common.py",
    "mutation_commission.py",
    "out/analysis.json",
    "out/builds.json",
    "out/claim-audit.json",
    "out/commission.json",
    "out/input-after.json",
    "out/input-before.json",
    "out/lineage.json",
    "out/provenance.json",
    "out/resource-estimate.json",
    "out/runs.json",
    "out/source-evidence.json",
    "out/verification.json",
    "preregistration.json",
    "run.py",
    "test_verify.py",
    "verify.py",
)


class EvidenceError(RuntimeError):
    """Fail-closed error carrying a stable machine-readable code."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def fail(code: str, detail: str) -> NoReturn:
    raise EvidenceError(code, detail)


def _win_norm(value: str | os.PathLike[str]) -> str:
    return ntpath.normcase(ntpath.normpath(os.fspath(value)))


def guard_capture_path(value: str | os.PathLike[str]) -> str:
    """Reject protected paths lexically, before any filesystem call."""

    raw = os.fspath(value)
    norm = _win_norm(raw)
    approved = _win_norm(APPROVED_INPUT)
    forbidden = _win_norm(FORBIDDEN_CAPTURE)
    if norm == forbidden or norm.startswith(forbidden + "\\"):
        fail(
            "M176-E-FORBIDDEN-PATH",
            "forbidden capture subtree refused before filesystem access",
        )
    for root_raw in PROTECTED_ROOTS:
        root = _win_norm(root_raw)
        if (norm == root or norm.startswith(root + "\\")) and norm != approved:
            fail("M176-E-PROTECTED-PATH", "unapproved protected macro path refused")
    if raw != APPROVED_INPUT:
        fail(
            "M176-E-INPUT", f"input must be the literal approved directory, got {raw!r}"
        )
    return raw


def ensure_private_path(value: str | os.PathLike[str]) -> Path:
    path = Path(value).resolve()
    root = PRIVATE_SCRATCH.resolve()
    try:
        path.relative_to(root)
    except ValueError:
        fail("M176-E-PRIVATE-PATH", f"path is outside private scratch: {path}")
    return path


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(chunk_size):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def json_digest(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def write_json_new(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
    except FileExistsError:
        fail("M176-E-STALE", f"refusing to replace pre-existing evidence: {path}")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _entry_attributes(st: os.stat_result) -> int:
    return int(getattr(st, "st_file_attributes", 0))


def capture_manifest(value: str | os.PathLike[str]) -> dict[str, Any]:
    """Hash every regular file below the one approved input directory."""

    root_text = guard_capture_path(value)
    root = Path(root_text)
    entries: list[dict[str, Any]] = []
    top_level_arw: list[str] = []
    reparse_flag = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))

    def visit(directory: Path, relative: Path) -> None:
        with os.scandir(directory) as scan:
            children = sorted(scan, key=lambda item: item.name.casefold())
        for child in children:
            child_rel = relative / child.name
            st = child.stat(follow_symlinks=False)
            attrs = _entry_attributes(st)
            if child.is_symlink() or attrs & reparse_flag:
                fail(
                    "M176-E-INPUT-REPARSE",
                    f"reparse point refused: {child_rel.as_posix()}",
                )
            common = {
                "relative_path": child_rel.as_posix(),
                "mode": int(st.st_mode),
                "mtime_ns": int(st.st_mtime_ns),
                "ctime_ns": int(st.st_ctime_ns),
                "file_attributes": attrs,
            }
            if child.is_dir(follow_symlinks=False):
                entries.append({**common, "kind": "directory"})
                visit(Path(child.path), child_rel)
            elif child.is_file(follow_symlinks=False):
                item = {
                    **common,
                    "kind": "file",
                    "size": int(st.st_size),
                    "sha256": sha256_file(Path(child.path)),
                }
                entries.append(item)
                if relative == Path() and child.name.lower().endswith(".arw"):
                    top_level_arw.append(child.name)
            else:
                fail(
                    "M176-E-INPUT-TYPE",
                    f"unsupported input entry: {child_rel.as_posix()}",
                )

    visit(root, Path())
    if len(top_level_arw) != EXPECTED_ARW_COUNT:
        fail(
            "M176-E-INPUT-COUNT",
            f"expected {EXPECTED_ARW_COUNT} top-level ARWs, found {len(top_level_arw)}",
        )
    body = {
        "schema": "strehl-m176-capture-manifest-v1",
        "root": root_text,
        "top_level_arw_count": len(top_level_arw),
        "top_level_arw_names": sorted(top_level_arw, key=str.casefold),
        "entries": entries,
    }
    body["manifest_sha256"] = json_digest(body)
    return body


def source_tree_manifest(root: Path) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix().casefold()):
        if path.is_symlink():
            fail("M176-E-SOURCE-REPARSE", f"archived source contains a symlink: {path}")
        if path.is_file():
            files.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "size": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    body = {"file_count": len(files), "files": files}
    return {
        "file_count": len(files),
        "total_bytes": sum(item["size"] for item in files),
        "manifest_sha256": json_digest(body),
    }


def canonical_pixel_hash(array: Any) -> str:
    import numpy as np

    pixels = np.asarray(array)
    if pixels.dtype != np.dtype("uint16"):
        fail("M176-E-PIXEL-DTYPE", f"expected uint16 pixels, got {pixels.dtype}")
    if pixels.ndim != 3 or pixels.shape[2] != 3:
        fail("M176-E-PIXEL-SHAPE", f"expected HxWx3 pixels, got {pixels.shape}")
    little = np.ascontiguousarray(pixels.astype("<u2", copy=False))
    descriptor = canonical_json_bytes({"dtype": "<u2", "shape": list(little.shape)})
    digest = hashlib.sha256()
    digest.update(PIXEL_HASH_DOMAIN)
    digest.update(descriptor)
    digest.update(b"\0")
    digest.update(memoryview(little).cast("B"))
    return digest.hexdigest()


def file_record(path: Path) -> dict[str, Any]:
    st = path.stat()
    return {
        "path": str(path),
        "size": st.st_size,
        "sha256": sha256_file(path),
        "mtime_ns": st.st_mtime_ns,
    }


def script_hashes() -> dict[str, str]:
    return {name: sha256_file(EXPERIMENT_DIR / name) for name in BOUND_SOURCE_NAMES}


def chunk_sizes(frames: int, groups: int) -> list[int]:
    if frames < 1 or groups < 1:
        fail("M176-E-CHUNKS", "frames and groups must be positive")
    per_chunk = (frames + groups - 1) // groups
    return [min(per_chunk, frames - start) for start in range(0, frames, per_chunk)]
