"""Fail-closed provenance helpers for the preregistered M8-v2 runner.

This module never decodes a RAW while inventorying inputs.  Its operational
subcommands either print JSON or create one explicitly named, previously absent
file with an atomic same-directory replace.  The PowerShell runner owns process
ordering; this module owns byte identities, strict sidecar/input validation,
trace Cartesian-product validation, and final receipt verification.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import ntpath
import os
import platform
import re
import shutil
import stat
import struct
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


SCHEMA_INPUT = "strehl-m8-v2-input-manifest"
SCHEMA_PLAN = "strehl-m8-v2-run-plan"
SCHEMA_PREPARE = "strehl-m8-v2-prepare"
SCHEMA_INVENTORY = "strehl-m8-v2-checker-inventory"
SCHEMA_TRACE = "strehl-m8-v2-trace-audit"
SCHEMA_RECEIPT = "strehl-m8-v2-arm-receipt"
SCHEMA_WRITER = "strehl-m8-v2-writer-record"
VERSION = 1

CAPTURE_ROOT = Path(
    r"D:\personal\macro\requests\misc-diagnostic"
    r"\high-res-calibration-slide-cpl\flat-sw4-cpl"
)
MACRO_ROOT = Path(r"D:\personal\macro")
SIDECAR_ROOT = Path(r"D:\strehl-out\cover-default-slide-v2\warpmaps")
REFERENCE_ROOT = Path(r"D:\strehl-out\cover-default-slide-v2\refs")
PLANE = (3516, 2344)
IDENTITY_CROP = (5, 4, 3506, 2337)
IDENTITY_REFERENCE_HASH = (
    "3A5FC6993D0EC24468FD24684AABE7783FE06D3D85EEC040584330AF0153A03B"
)

FNV1A64_OFFSET = 0xCBF29CE484222325
FNV1A64_PRIME = 0x00000100000001B3
U64_MASK = (1 << 64) - 1
SHA_RE = re.compile(r"^[0-9A-F]{64}$")
BLOCK_HEADER = struct.Struct("<8s9I6d2fI")
BLOCK_NAME = re.compile(
    r"^m8-v2-block-v1-p2-([0-9a-f]{64})-s([01])([01])-"
    r"([0-9a-f]{64})\.m8site$"
)
SITE_INDEX = {(0, 0, 0): 0, (1, 0, 1): 1, (0, 1, 1): 2, (1, 1, 2): 3}


@dataclass(frozen=True)
class Case:
    name: str
    source_dir: str
    frames: int
    reference: int
    sidecar_name: str
    sidecar_sha256: str
    fnv: str
    identity_sha256: str
    crop: tuple[int, int, int, int]
    reference_name: str
    reference_sha256: str


CASES = (
    Case(
        "flat-1s",
        "flat-et1s-sw4-cpl",
        60,
        30,
        "flat-1s.warpmap.txt",
        "862C6FD8E1956FDD53F527A12809B3079226334265EDADFF8AA1F0EA3B9B828C",
        "00feb5f7eb369463",
        "6BBAE09C4CF0CDACE84C50FCBE2D8C9D135C1B4DE9AEB1865B42B85B71DAEAEC",
        (25, 17, 3466, 2310),
        "DSC00046.ARW",
        IDENTITY_REFERENCE_HASH,
    ),
    Case(
        "flat-2p5s",
        "flat-et2.5s-sw4-cpl",
        61,
        30,
        "flat-2p5s.warpmap.txt",
        "0C2CF172F7577189D2EE6F19F281D1A5BA821E7EC4A2F4D13F0BB12B87D4C638",
        "670ef0480ca81076",
        "D39CC3AE911C7706AEB054CB470A05C16030965A225482C526115C8379DA4D71",
        (23, 16, 3470, 2312),
        "DSC00050.ARW",
        "9FB1CC9C323D13D72467411F9FFE607F20C6D088EAEA374F4F0AB9C56098535D",
    ),
    Case(
        "flat-6s",
        "flat-et6s-sw4-cpl",
        65,
        32,
        "flat-6s.warpmap.txt",
        "60A33EA0513E6408313EAA5698106FEC9B23FD6E8E325C246141C1905F2427F3",
        "7cc19bab0cba440f",
        "1DCC9A4FABCC29F5811AF075381CAFC8EF05F9A75A101DCE6C1CF024FABCCF5C",
        (25, 17, 3466, 2310),
        "DSC00047.ARW",
        "A5225AEF221DAD3D6EB850940BE527E48A99548EF3CF23990AE4D09EA5B5A146",
    ),
)
CASE_BY_NAME = {case.name: case for case in CASES}


class Refusal(RuntimeError):
    """A frozen audit precondition was not met."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Refusal(message)


def canonical_json(payload: Any) -> bytes:
    return (
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for part in iter(lambda: stream.read(1 << 20), b""):
                digest.update(part)
    except OSError as error:
        raise Refusal(f"cannot hash {path}: {error}") from error
    return digest.hexdigest().upper()


def hash_record(path: Path) -> dict[str, Any]:
    path = Path(os.path.abspath(path))
    try:
        info = path.lstat()
    except OSError as error:
        raise Refusal(f"cannot stat {path}: {error}") from error
    require(stat.S_ISREG(info.st_mode), f"{path}: expected a regular file")
    require(not path.is_symlink(), f"{path}: symbolic links are forbidden")
    return {
        "path": str(path),
        "bytes": info.st_size,
        "sha256": sha256_file(path),
    }


def _windows_key(path: Path | str) -> str:
    return ntpath.normcase(ntpath.normpath(ntpath.abspath(os.fspath(path))))


def _under_windows(path: Path | str, root: Path | str) -> bool:
    candidate = _windows_key(path)
    anchor = _windows_key(root)
    try:
        return ntpath.commonpath((candidate, anchor)) == anchor
    except ValueError:
        return False


def refuse_write_under_macro(path: Path) -> None:
    lexical = Path(os.path.abspath(path))
    resolved = lexical.resolve(strict=False)
    if _under_windows(lexical, MACRO_ROOT) or _under_windows(resolved, MACRO_ROOT):
        raise Refusal(f"refusing any output beneath {MACRO_ROOT}: {path}")


def atomic_write(path: Path, payload: bytes) -> None:
    path = Path(os.path.abspath(path))
    refuse_write_under_macro(path)
    require(not path.exists(), f"{path}: output already exists")
    require(path.parent.is_dir(), f"{path.parent}: output parent must already exist")
    temporary = path.with_name(f".{path.name}.m8-v2-{os.getpid()}.new")
    require(not temporary.exists(), f"{temporary}: atomic staging path already exists")
    try:
        with temporary.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def emit(payload: Any, output: Path | None) -> None:
    data = canonical_json(payload)
    if output is None:
        sys.stdout.buffer.write(data)
    else:
        atomic_write(output, data)
        print(
            json.dumps(
                {
                    "path": str(Path(os.path.abspath(output))),
                    "bytes": len(data),
                    "sha256": sha256_bytes(data),
                },
                sort_keys=True,
            )
        )


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise Refusal(f"cannot read JSON {path}: {error}") from error


def run(
    command: Sequence[str],
    *,
    cwd: Path | None = None,
    expected: int = 0,
) -> subprocess.CompletedProcess[str]:
    process = subprocess.run(
        list(command),
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if process.returncode != expected:
        raise Refusal(
            f"command exited {process.returncode}, expected {expected}: "
            f"{subprocess.list2cmdline(list(command))}\n{process.stdout}"
        )
    return process


def git(repo: Path, *arguments: str, text: bool = True) -> str | bytes:
    command = ["git", "-C", str(repo), *arguments]
    process = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=text,
        encoding="utf-8" if text else None,
        errors="replace" if text else None,
        check=False,
    )
    if process.returncode != 0:
        stderr = process.stderr if text else process.stderr.decode("utf-8", "replace")
        raise Refusal(
            f"git failed ({subprocess.list2cmdline(command)}): {stderr.strip()}"
        )
    return process.stdout


def exact_commit(repo: Path, value: str) -> str:
    require(
        re.fullmatch(r"[0-9A-Fa-f]{40}", value) is not None,
        "commit must be an explicit full 40-hex Git SHA",
    )
    resolved = str(git(repo, "rev-parse", f"{value}^{{commit}}")).strip().lower()
    require(resolved == value.lower(), f"{value}: did not resolve to that exact commit")
    return resolved


def committed_file(repo: Path, commit: str, path: Path) -> dict[str, Any]:
    repo = repo.resolve()
    path = path.resolve()
    try:
        relative = path.relative_to(repo).as_posix()
    except ValueError as error:
        raise Refusal(f"{path}: committed evidence must be below {repo}") from error
    blob = str(git(repo, "rev-parse", f"{commit}:{relative}")).strip()
    kind = str(git(repo, "cat-file", "-t", blob)).strip()
    require(kind == "blob", f"{relative}@{commit}: expected a Git blob, got {kind}")
    checkout_blob = str(
        git(repo, "hash-object", "--path", relative, str(path))
    ).strip()
    require(
        checkout_blob == blob,
        f"{path}: checkout bytes do not match {relative}@{commit}",
    )
    return {**hash_record(path), "relative_path": relative, "git_blob": blob}


def tool_audit(repo: Path, commit_raw: str, extras: Sequence[str]) -> dict[str, Any]:
    repo = repo.resolve()
    commit = exact_commit(repo, commit_raw)
    prefix = "experiments/cover-default/m8-v2"
    listed = str(git(repo, "ls-tree", "-r", "--name-only", commit, "--", prefix))
    committed = tuple(line for line in listed.splitlines() if line)
    require(committed, f"{prefix}@{commit}: no committed M8-v2 files")

    directory = repo / Path(prefix)
    actual: list[str] = []
    for root, directories, files in os.walk(directory, followlinks=False):
        directories.sort()
        files.sort()
        for name in files:
            path = Path(root) / name
            require(not path.is_symlink(), f"{path}: tool symlinks are forbidden")
            actual.append(path.relative_to(repo).as_posix())
    require(
        tuple(actual) == committed,
        "M8-v2 checkout file set differs from the committed tool set: "
        f"checkout_only={sorted(set(actual) - set(committed))}, "
        f"commit_only={sorted(set(committed) - set(actual))}",
    )

    paths = list(committed)
    for extra in extras:
        clean = Path(extra).as_posix().lstrip("/")
        require(clean not in paths, f"duplicate audited tool path {clean}")
        paths.append(clean)

    records = []
    for relative in paths:
        path = (repo / Path(relative)).resolve()
        record = committed_file(repo, commit, path)
        records.append(record)
    return {
        "schema": "strehl-m8-v2-tool-audit",
        "version": VERSION,
        "repo": str(repo),
        "commit": commit,
        "files": records,
    }


def git_tree_audit(repo: Path, commit_raw: str) -> dict[str, Any]:
    repo = repo.resolve()
    commit = exact_commit(repo, commit_raw)
    tree = str(git(repo, "rev-parse", f"{commit}^{{tree}}")).strip()
    raw = bytes(git(repo, "ls-tree", "-r", "-l", "-z", commit, text=False))
    records: list[dict[str, Any]] = []
    for row in raw.split(b"\0"):
        if not row:
            continue
        try:
            header, raw_path = row.split(b"\t", 1)
            mode, kind, oid, size = header.decode("ascii").split()
            path = raw_path.decode("utf-8")
        except (ValueError, UnicodeError) as error:
            raise Refusal("cannot parse UTF-8 git ls-tree output") from error
        records.append(
            {
                "mode": mode,
                "type": kind,
                "object": oid,
                "bytes": None if size == "-" else int(size),
                "path": path,
            }
        )
    payload = canonical_json(records)
    return {
        "schema": "strehl-m8-v2-git-tree",
        "version": VERSION,
        "repo": str(repo),
        "commit": commit,
        "tree": tree,
        "entry_count": len(records),
        "entries_sha256": sha256_bytes(payload),
        "entries": records,
    }


def tree_audit(root: Path) -> dict[str, Any]:
    root = root.resolve()
    require(root.is_dir(), f"{root}: tree root does not exist")
    records: list[dict[str, Any]] = []

    def walk(directory: Path) -> None:
        try:
            entries = sorted(os.scandir(directory), key=lambda item: item.name)
        except OSError as error:
            raise Refusal(f"cannot list {directory}: {error}") from error
        for entry in entries:
            path = Path(entry.path)
            relative = path.relative_to(root).as_posix()
            info = entry.stat(follow_symlinks=False)
            if stat.S_ISDIR(info.st_mode):
                records.append({"path": relative, "type": "directory"})
                walk(path)
            elif stat.S_ISREG(info.st_mode):
                records.append(
                    {
                        "path": relative,
                        "type": "file",
                        "bytes": info.st_size,
                        "sha256": sha256_file(path),
                    }
                )
            elif stat.S_ISLNK(info.st_mode):
                records.append(
                    {
                        "path": relative,
                        "type": "symlink",
                        "target": os.readlink(path),
                    }
                )
            else:
                raise Refusal(f"{path}: unsupported filesystem entry in source tree")

    walk(root)
    payload = canonical_json(records)
    return {
        "schema": "strehl-m8-v2-tree-audit",
        "version": VERSION,
        "root": str(root),
        "entry_count": len(records),
        "regular_bytes": sum(
            row.get("bytes", 0) for row in records if row["type"] == "file"
        ),
        "inventory_sha256": sha256_bytes(payload),
    }


def _stack_identity_bytes(entries: Sequence[tuple[str, int]]) -> bytes:
    payload = bytearray()
    for name, size in entries:
        require(0 <= size <= U64_MASK, f"{name}: size is outside u64")
        try:
            payload.extend(name.encode("utf-8"))
        except UnicodeEncodeError as error:
            raise Refusal(f"{name!r}: filename is not UTF-8 encodable") from error
        payload.append(0)
        payload.extend(size.to_bytes(8, "little"))
        payload.append(0)
    return bytes(payload)


def stack_digest(entries: Sequence[tuple[str, int]]) -> tuple[str, str]:
    payload = _stack_identity_bytes(entries)
    digest = FNV1A64_OFFSET
    for byte in payload:
        digest = ((digest ^ byte) * FNV1A64_PRIME) & U64_MASK
    return f"{digest:016x}", sha256_bytes(payload)


def utc_ns(value: int) -> str:
    seconds, nanoseconds = divmod(value, 1_000_000_000)
    stamp = dt.datetime.fromtimestamp(seconds, tz=dt.timezone.utc)
    return stamp.strftime("%Y-%m-%dT%H:%M:%S") + f".{nanoseconds:09d}Z"


def resolve_exiftool(raw: str) -> Path:
    candidate = shutil.which(raw)
    if candidate is None:
        path = Path(raw)
        if path.is_file():
            candidate = str(path)
    require(candidate is not None, f"ExifTool is unavailable: {raw!r}")
    path = Path(candidate).resolve()
    version = run([str(path), "-ver"]).stdout.strip()
    require(
        re.fullmatch(r"\d+(?:\.\d+)+", version) is not None,
        f"{path}: did not identify itself as ExifTool: {version!r}",
    )
    return path


def _unique_object(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in pairs:
        if key in output:
            raise Refusal(f"ExifTool JSON contains duplicate key {key!r}")
        output[key] = value
    return output


def exif_dump(tool: Path, source: Path) -> tuple[dict[str, Any], str]:
    command = [
        str(tool),
        "-j",
        "-G0:1:2:3:4",
        "-a",
        "-s",
        "-u",
        "-n",
        "-sort",
        "-charset",
        "filename=UTF8",
        "-EXIF:all",
        "-MakerNotes:all",
        "--",
        str(source),
    ]
    process = run(command)
    try:
        parsed = json.loads(process.stdout, object_pairs_hook=_unique_object)
    except json.JSONDecodeError as error:
        raise Refusal(f"ExifTool returned invalid JSON for {source}: {error}") from error
    require(
        isinstance(parsed, list) and len(parsed) == 1 and isinstance(parsed[0], dict),
        f"ExifTool returned an unexpected document for {source}",
    )
    dump = dict(parsed[0])
    dump.pop("SourceFile", None)
    encoded = canonical_json(dump)
    return dump, sha256_bytes(encoded)


def parse_sidecar(path: Path, case: Case) -> dict[str, Any]:
    record = hash_record(path)
    require(
        record["sha256"] == case.sidecar_sha256,
        f"{path}: sidecar SHA-256 {record['sha256']} != frozen {case.sidecar_sha256}",
    )
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise Refusal(f"cannot read sidecar {path}: {error}") from error
    headers: dict[str, str] = {}
    placements: dict[int, str] = {}
    magic = False
    ended = False
    end_count: int | None = None
    for number, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split(maxsplit=1)
        head = fields[0]
        tail = fields[1].strip() if len(fields) == 2 else ""
        if not magic:
            require(
                head == "strehl-warpmap" and tail == "1",
                f"{path}:{number}: wrong sidecar magic",
            )
            magic = True
            continue
        require(not ended, f"{path}:{number}: data follows end marker")
        if head == "end":
            require(tail.isdigit(), f"{path}:{number}: invalid end count")
            end_count = int(tail)
            ended = True
        elif head.isdigit():
            index = int(head)
            require(index not in placements, f"{path}:{number}: duplicate frame {index}")
            state_fields = tail.split()
            require(
                len(state_fields) >= 1 and state_fields[0] == "placed",
                f"{path}:{number}: every frame must be placed",
            )
            bits = tail.split("#", 1)[0].split()[1:]
            require(
                len(bits) == 4
                and all(re.fullmatch(r"[0-9A-Fa-f]{16}", item) for item in bits),
                f"{path}:{number}: malformed placement bits",
            )
            placements[index] = " ".join(item.lower() for item in bits)
        else:
            require(head not in headers, f"{path}:{number}: duplicate header {head}")
            headers[head] = tail
    required = {
        "stack-name",
        "stack-digest",
        "frames",
        "plane",
        "reference",
        "strategy",
        "resampler",
    }
    require(magic and ended, f"{path}: incomplete sidecar")
    require(required <= headers.keys(), f"{path}: missing required sidecar headers")
    require(headers["stack-name"] == case.source_dir, f"{path}: wrong stack-name")
    require(headers["stack-digest"].lower() == case.fnv, f"{path}: wrong stack-digest")
    require(headers["frames"] == str(case.frames), f"{path}: wrong frame count")
    require(headers["reference"] == str(case.reference), f"{path}: wrong reference")
    require(headers["plane"] == f"{PLANE[0]}x{PLANE[1]}", f"{path}: wrong plane")
    require(headers["resampler"] == "catmull-rom", f"{path}: wrong resampler")
    require(end_count == case.frames, f"{path}: wrong end count")
    require(
        set(placements) == set(range(case.frames)),
        f"{path}: placement indices are not exactly 0..{case.frames - 1}",
    )
    return {
        **record,
        "stack_name": headers["stack-name"],
        "stack_digest": headers["stack-digest"].lower(),
        "frames": case.frames,
        "reference": case.reference,
        "plane": list(PLANE),
        "resampler": headers["resampler"],
        "placed": len(placements),
        "refused": 0,
    }


def exact_registered_root(supplied: Path, expected: Path, label: str) -> Path:
    supplied = Path(os.path.abspath(supplied))
    require(
        _windows_key(supplied) == _windows_key(expected),
        f"{label} must be the released path {expected}, got {supplied}",
    )
    require(supplied.is_dir(), f"{supplied}: {label} does not exist")
    return supplied


def list_arws(directory: Path) -> list[tuple[Path, os.stat_result]]:
    try:
        entries = tuple(os.scandir(directory))
    except OSError as error:
        raise Refusal(f"cannot list {directory}: {error}") from error
    selected: list[tuple[Path, os.stat_result]] = []
    for entry in entries:
        suffix = Path(entry.name).suffix
        if suffix.lower() != ".arw":
            continue
        info = entry.stat(follow_symlinks=False)
        require(not stat.S_ISLNK(info.st_mode), f"{entry.path}: ARW symlink is forbidden")
        require(
            stat.S_ISREG(info.st_mode),
            f"{entry.path}: every ARW directory entry must be a regular file",
        )
        selected.append((Path(entry.path), info))
    selected.sort(key=lambda row: row[0].name)
    require(selected, f"{directory}: no ARW files")
    names = [path.name for path, _ in selected]
    require(names == sorted(names), f"{directory}: case-sensitive lexical ordering failed")
    require(len(names) == len(set(names)), f"{directory}: duplicate ARW names")
    return selected


def read_only_tree_state(directory: Path) -> dict[str, Any]:
    """Hash every entry below one admitted source directory without following links."""

    directory = directory.resolve()
    records: list[dict[str, Any]] = []

    def walk(parent: Path) -> None:
        try:
            children = sorted(os.scandir(parent), key=lambda item: item.name)
        except OSError as error:
            raise Refusal(f"cannot list source tree {parent}: {error}") from error
        for child in children:
            path = Path(child.path)
            relative = path.relative_to(directory).as_posix()
            info = child.stat(follow_symlinks=False)
            require(
                not child.is_symlink() and not stat.S_ISLNK(info.st_mode),
                f"{path}: source-tree symlinks are forbidden",
            )
            if stat.S_ISDIR(info.st_mode):
                records.append(
                    {
                        "path": relative,
                        "type": "directory",
                        "mtime_ns": info.st_mtime_ns,
                    }
                )
                walk(path)
            elif stat.S_ISREG(info.st_mode):
                records.append(
                    {
                        "path": relative,
                        "type": "file",
                        "bytes": info.st_size,
                        "mtime_ns": info.st_mtime_ns,
                        "sha256": sha256_file(path),
                    }
                )
            else:
                raise Refusal(f"{path}: unsupported source-tree entry type")

    walk(directory)
    return {
        "entry_count": len(records),
        "inventory_sha256": sha256_bytes(canonical_json(records)),
        "entries": records,
    }


def build_input_manifest(
    capture_root_raw: Path,
    sidecar_root_raw: Path,
    exif_tool_raw: str,
) -> dict[str, Any]:
    capture_root = exact_registered_root(capture_root_raw, CAPTURE_ROOT, "capture root")
    sidecar_root = exact_registered_root(sidecar_root_raw, SIDECAR_ROOT, "sidecar root")
    exif_tool = resolve_exiftool(exif_tool_raw)
    exif_version = run([str(exif_tool), "-ver"]).stdout.strip()
    captures = []
    for case in CASES:
        directory = capture_root / case.source_dir
        require(directory.is_dir(), f"{directory}: released source directory is missing")
        tree_before = read_only_tree_state(directory)
        listed = list_arws(directory)
        require(
            len(listed) == case.frames,
            f"{case.name}: expected {case.frames} ARWs, found {len(listed)}",
        )
        tree_files = {
            row["path"]: row
            for row in tree_before["entries"]
            if row["type"] == "file"
        }
        name_sizes = [(path.name, info.st_size) for path, info in listed]
        fnv, identity_sha = stack_digest(name_sizes)
        require(fnv == case.fnv, f"{case.name}: FNV {fnv} != frozen {case.fnv}")
        require(
            identity_sha == case.identity_sha256,
            f"{case.name}: identity SHA-256 {identity_sha} != released "
            f"{case.identity_sha256}",
        )
        rows = []
        for index, (path, info) in enumerate(listed):
            dump, dump_hash = exif_dump(exif_tool, path)
            rows.append(
                {
                    "frame_index": index,
                    "name": path.name,
                    "path": str(Path(os.path.abspath(path))),
                    "size": info.st_size,
                    "mtime_utc": utc_ns(info.st_mtime_ns),
                    "mtime_ns": info.st_mtime_ns,
                    "sha256": tree_files[path.name]["sha256"],
                    "exif": {
                        "schema": "canonical-exiftool-json-v1",
                        "sha256": dump_hash,
                        "dump": dump,
                    },
                }
            )
        reference_row = rows[case.reference]
        require(
            reference_row["name"] == case.reference_name,
            f"{case.name}: reference index {case.reference} is "
            f"{reference_row['name']!r}, expected {case.reference_name!r}",
        )
        require(
            reference_row["sha256"] == case.reference_sha256,
            f"{case.name}: released reference source SHA-256 changed",
        )
        sidecar = parse_sidecar(sidecar_root / case.sidecar_name, case)
        tree_after = read_only_tree_state(directory)
        require(
            tree_after == tree_before,
            f"{case.name}: source tree changed while the read-only manifest was generated",
        )
        checker_payload = {
            "schema": SCHEMA_INVENTORY,
            "version": VERSION,
            "directory": str(Path(os.path.abspath(directory))),
            "entries": rows,
        }
        captures.append(
            {
                "name": case.name,
                "directory": str(Path(os.path.abspath(directory))),
                "expected_frames": case.frames,
                "reference": case.reference,
                "reference_source": {
                    "name": reference_row["name"],
                    "path": reference_row["path"],
                    "sha256": reference_row["sha256"],
                },
                "crop_xywh": list(case.crop),
                "rust_order": "Windows PathBuf Ord / case-sensitive lexical filename order",
                "fnv1a64": fnv,
                "identity_bytes_sha256": identity_sha,
                "sidecar": sidecar,
                "entries": rows,
                "checker_inventory_sha256": sha256_bytes(
                    canonical_json(checker_payload)
                ),
                "read_only_tree_state": tree_before,
            }
        )
    return {
        "schema": SCHEMA_INPUT,
        "version": VERSION,
        "capture_root": str(capture_root),
        "sidecar_root": str(sidecar_root),
        "read_contract": (
            "direct-directory lstat; regular ARW only; no symlinks; no RAW decode/render"
        ),
        "exif_tool": {
            **hash_record(exif_tool),
            "name": "ExifTool",
            "version": exif_version,
            "command": [
                "-j",
                "-G0:1:2:3:4",
                "-a",
                "-s",
                "-u",
                "-n",
                "-sort",
                "-charset",
                "filename=UTF8",
                "-EXIF:all",
                "-MakerNotes:all",
                "--",
                "SOURCE",
            ],
        },
        "captures": captures,
    }


def validate_input_shape(payload: Any) -> dict[str, Any]:
    require(
        isinstance(payload, dict)
        and payload.get("schema") == SCHEMA_INPUT
        and payload.get("version") == VERSION,
        "unsupported M8-v2 input manifest",
    )
    captures = payload.get("captures")
    require(isinstance(captures, list), "input manifest has no captures")
    require(
        [row.get("name") for row in captures] == [case.name for case in CASES],
        "input manifest capture order differs from the frozen order",
    )
    return payload


def verify_input_manifest(path: Path, exif_override: str | None) -> dict[str, Any]:
    path = path.resolve()
    expected = validate_input_shape(read_json(path))
    tool = exif_override or expected["exif_tool"]["path"]
    rebuilt = build_input_manifest(
        Path(expected["capture_root"]), Path(expected["sidecar_root"]), tool
    )
    require(
        canonical_json(rebuilt) == canonical_json(expected),
        f"{path}: current inputs/EXIF/sidecars do not reproduce the manifest",
    )
    return {
        "status": "VERIFIED",
        "manifest": hash_record(path),
        "captures": [
            {
                "name": row["name"],
                "frames": len(row["entries"]),
                "fnv1a64": row["fnv1a64"],
                "sidecar_sha256": row["sidecar"]["sha256"],
            }
            for row in expected["captures"]
        ],
    }


def capture_row(manifest: dict[str, Any], name: str) -> dict[str, Any]:
    for row in manifest["captures"]:
        if row["name"] == name:
            return row
    raise Refusal(f"input manifest has no capture {name!r}")


def checker_inventory(manifest_path: Path, case_name: str) -> dict[str, Any]:
    manifest = validate_input_shape(read_json(manifest_path))
    row = capture_row(manifest, case_name)
    payload = {
        "schema": SCHEMA_INVENTORY,
        "version": VERSION,
        "directory": row["directory"],
        "entries": row["entries"],
    }
    require(
        sha256_bytes(canonical_json(payload)) == row["checker_inventory_sha256"],
        f"{case_name}: embedded checker inventory identity changed",
    )
    return payload


def identity_sidecar(source: Path) -> tuple[bytes, dict[str, Any]]:
    source = source.resolve()
    info = source.lstat()
    require(stat.S_ISREG(info.st_mode), f"{source}: identity RAW must be regular")
    require(not source.is_symlink(), f"{source}: identity RAW may not be a symlink")
    refuse_write_under_macro(source.parent / "not-an-output-probe")
    fnv, identity_sha = stack_digest([(source.name, info.st_size)])
    text = "\n".join(
        (
            "strehl-warpmap 1",
            f"stack-name {source.parent.name}",
            f"stack-digest {fnv}",
            "frames 1",
            f"plane {PLANE[0]}x{PLANE[1]}",
            "reference 0",
            "strategy m8-v2-copied-reference-identity",
            "resampler catmull-rom",
            "heldout-px none",
            "cycle-floor-px none",
            "note preregistered M8-v2 copied-reference identity control",
            "0 placed 3ff0000000000000 0000000000000000 "
            "0000000000000000 0000000000000000",
            "end 1",
            "",
        )
    ).encode("utf-8")
    return text, {
        "fnv1a64": fnv,
        "identity_bytes_sha256": identity_sha,
        "source": hash_record(source),
        "crop_xywh": list(IDENTITY_CROP),
    }


def single_inventory(source: Path) -> dict[str, Any]:
    source = source.resolve()
    record = hash_record(source)
    return {
        "schema": SCHEMA_INVENTORY,
        "version": VERSION,
        "directory": str(source.parent),
        "entries": [
            {
                "frame_index": 0,
                "name": source.name,
                "path": str(source),
                "size": record["bytes"],
                "sha256": record["sha256"],
            }
        ],
    }


def runtime_info() -> dict[str, Any]:
    try:
        import numpy
        import tifffile
        import rawpy
    except Exception as error:
        raise Refusal(
            "Python, NumPy, tifffile, rawpy and LibRaw versions are mandatory"
        ) from error
    libraw = getattr(rawpy, "libraw_version", None)
    require(libraw is not None, "rawpy did not expose its LibRaw version")
    executable = Path(sys.executable).resolve()
    return {
        "schema": "strehl-m8-v2-runtime",
        "version": VERSION,
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "executable": hash_record(executable),
        },
        "numpy": numpy.__version__,
        "tifffile": tifffile.__version__,
        "rawpy": rawpy.__version__,
        "libraw": list(libraw) if isinstance(libraw, tuple) else str(libraw),
        "os": {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
        },
    }


def read_inventory(path: Path) -> tuple[Path, list[dict[str, Any]]]:
    raw = read_json(path)
    require(isinstance(raw, dict), f"{path}: inventory must be an object")
    rows = raw.get("entries", raw.get("sources"))
    require(isinstance(rows, list) and rows, f"{path}: inventory has no entries")
    directory = Path(raw.get("directory", path.parent)).resolve()
    names = []
    clean = []
    for index, row in enumerate(rows):
        require(isinstance(row, dict), f"{path}: entry {index} is not an object")
        name = row.get("name")
        raw_path = row.get("path", name)
        require(isinstance(name, str) and name, f"{path}: entry {index} has no name")
        require(isinstance(raw_path, str), f"{path}: entry {index} has no path")
        source = Path(raw_path)
        if not source.is_absolute():
            source = directory / source
        source = source.resolve()
        require(source.name == name, f"{path}: entry {index} path/name disagree")
        names.append(name)
        clean.append({**row, "path": str(source), "name": name})
    require(names == sorted(names), f"{path}: inventory order is not lexical")
    require(len(names) == len(set(names)), f"{path}: duplicate source names")
    return directory, clean


def parse_trace_block(path: Path) -> dict[str, Any]:
    record = hash_record(path)
    match = BLOCK_NAME.fullmatch(path.name)
    require(match is not None, f"{path}: invalid M8-v2 completed filename")
    frame_name_hash, sx_name, sy_name, content_name = match.groups()
    require(
        content_name.upper() == record["sha256"],
        f"{path}: filename/content SHA-256 disagree",
    )
    with path.open("rb") as stream:
        raw = stream.read(BLOCK_HEADER.size)
        require(len(raw) == BLOCK_HEADER.size, f"{path}: truncated block header")
        fields = BLOCK_HEADER.unpack(raw)
        (
            magic,
            protocol,
            kernel,
            src_width,
            src_height,
            dst_width,
            dst_height,
            site_x,
            site_y,
            channel,
            _a_re,
            _a_im,
            _b_re,
            _b_im,
            _cx,
            _cy,
            _value_range,
            _site_gain,
            frame_bytes,
        ) = fields
        require(magic == b"M8SITE01", f"{path}: wrong block magic")
        require(protocol == 2, f"{path}: expected producer protocol 2")
        require(kernel == 0, f"{path}: real arm must be Catmull-Rom")
        require(
            src_width == 2 * dst_width and src_height == 2 * dst_height,
            f"{path}: full-resolution source/destination geometry disagrees",
        )
        raw_frame = stream.read(frame_bytes)
        require(len(raw_frame) == frame_bytes, f"{path}: truncated frame path")
    try:
        frame_path = raw_frame.decode("utf-8")
    except UnicodeDecodeError as error:
        raise Refusal(f"{path}: frame path is not UTF-8") from error
    expected_size = (
        BLOCK_HEADER.size
        + frame_bytes
        + 4 * src_width * src_height
        + 4 * dst_width * dst_height
    )
    require(record["bytes"] == expected_size, f"{path}: block length is inconsistent")
    require(
        frame_name_hash == hashlib.sha256(raw_frame).hexdigest(),
        f"{path}: frame-path hash mismatch",
    )
    require(
        (str(site_x), str(site_y)) == (sx_name, sy_name),
        f"{path}: filename/header site mismatch",
    )
    site = SITE_INDEX.get((site_x, site_y, channel))
    require(site is not None, f"{path}: invalid RGGB site/channel")
    return {
        **record,
        "frame_path": frame_path,
        "frame_name": Path(frame_path).name,
        "site_index": site,
        "site": ("R", "G1", "G2", "B")[site],
        "source_width": src_width,
        "source_height": src_height,
        "destination_width": dst_width,
        "destination_height": dst_height,
    }


def _empty_directory(path: Path, label: str) -> None:
    require(path.is_dir() and not path.is_symlink(), f"{path}: missing {label} directory")
    entries = list(os.scandir(path))
    require(not entries, f"{path}: leftover {label} state: {[row.name for row in entries]}")


def trace_audit(
    trace_dir: Path,
    inventory_path: Path,
    writer_record_path: Path,
    transparency_hashes: Sequence[str],
) -> dict[str, Any]:
    trace_dir = trace_dir.resolve()
    require(trace_dir.is_dir(), f"{trace_dir}: trace root is missing")
    root_entries = sorted(entry.name for entry in os.scandir(trace_dir))
    require(
        root_entries == ["blocks", "claims", "staging"],
        f"{trace_dir}: trace root must contain only blocks/claims/staging, got "
        f"{root_entries}",
    )
    _empty_directory(trace_dir / "claims", "claim")
    _empty_directory(trace_dir / "staging", "staging")
    blocks_dir = trace_dir / "blocks"
    require(blocks_dir.is_dir(), f"{blocks_dir}: completed block directory is missing")
    block_entries = list(os.scandir(blocks_dir))
    require(
        all(entry.is_file(follow_symlinks=False) and not entry.is_symlink() for entry in block_entries),
        f"{blocks_dir}: only regular completed files are allowed",
    )
    blocks = [parse_trace_block(Path(entry.path)) for entry in block_entries]
    blocks.sort(key=lambda row: row["path"])

    _directory, sources = read_inventory(inventory_path)
    by_path = {
        _windows_key(row["path"]): index for index, row in enumerate(sources)
    }
    keys: list[tuple[int, int]] = []
    for block in blocks:
        emitted = Path(block["frame_path"])
        require(
            emitted.is_absolute(),
            f"{block['path']}: emitted frame path is not absolute",
        )
        emitted_key = _windows_key(emitted)
        require(
            emitted_key in by_path,
            f"{block['path']}: emitted frame path is absent from source inventory",
        )
        block["frame_index"] = by_path[emitted_key]
        keys.append((block["frame_index"], block["site_index"]))
    duplicates = len(keys) - len(set(keys))
    required = {
        (frame_index, site_index)
        for frame_index in range(len(sources))
        for site_index in range(4)
    }
    require(
        set(keys) == required,
        "trace Cartesian product is incomplete or has extra keys: "
        f"missing={sorted(required - set(keys))[:8]}, "
        f"extra={sorted(set(keys) - required)[:8]}",
    )

    writer = read_json(writer_record_path)
    require(
        isinstance(writer, dict)
        and writer.get("schema") == SCHEMA_WRITER
        and writer.get("version") == VERSION,
        f"{writer_record_path}: unsupported writer record",
    )
    launches = writer.get("writer_processes")
    require(isinstance(launches, list), f"{writer_record_path}: no writer process list")
    hashes = [value.upper() for value in transparency_hashes]
    require(
        len(hashes) == 3 and all(SHA_RE.fullmatch(value) for value in hashes),
        "three valid output-transparency SHA-256 values are required",
    )

    # Checker CLI/schema is authoritative for the runner-owned state gate.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from checker_v2 import refuse_unsafe_producer_state

    refuse_unsafe_producer_state(
        expected_blocks=4 * len(sources),
        observed_blocks=len(blocks),
        duplicate_blocks=duplicates,
        concurrent_writers=len(launches),
        transparency_hashes=hashes,
    )
    blocks.sort(key=lambda row: (row["frame_index"], row["site_index"]))
    return {
        "schema": SCHEMA_TRACE,
        "version": VERSION,
        "trace_dir": str(trace_dir),
        "inventory": hash_record(inventory_path.resolve()),
        "writer_record": hash_record(writer_record_path.resolve()),
        "ordered_frames": len(sources),
        "expected_blocks": 4 * len(sources),
        "observed_blocks": len(blocks),
        "duplicate_blocks": duplicates,
        "concurrent_writers": len(launches),
        "output_transparency_sha256": hashes[0],
        "cartesian_product": "COMPLETE",
        "claims": 0,
        "staging": 0,
        "blocks": blocks,
    }


def fixture_audit(trace_dir: Path, expected: int | None) -> dict[str, Any]:
    trace_dir = trace_dir.resolve()
    _empty_directory(trace_dir / "claims", "claim")
    _empty_directory(trace_dir / "staging", "staging")
    paths = sorted((trace_dir / "blocks").glob("*.m8site"))
    if expected is not None:
        require(len(paths) == expected, f"{trace_dir}: expected {expected} blocks")
    records = []
    for path in paths:
        record = hash_record(path)
        match = BLOCK_NAME.fullmatch(path.name)
        require(match is not None, f"{path}: malformed fixture block filename")
        require(
            match.group(4).upper() == record["sha256"],
            f"{path}: fixture block content hash mismatch",
        )
        records.append(record)
    return {
        "status": "VERIFIED",
        "trace_dir": str(trace_dir),
        "blocks": records,
        "claims": 0,
        "staging": 0,
    }


def commission_runner_gate() -> dict[str, Any]:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from checker_v2 import Refusal as CheckerRefusal
    from checker_v2 import refuse_unsafe_producer_state

    good_hash = "A" * 64
    refuse_unsafe_producer_state(
        expected_blocks=4,
        observed_blocks=4,
        duplicate_blocks=0,
        concurrent_writers=1,
        transparency_hashes=(good_hash, good_hash, good_hash),
    )
    plants = {
        "missing": dict(observed_blocks=3),
        "duplicate": dict(duplicate_blocks=1),
        "concurrent": dict(concurrent_writers=2),
        "transparency": dict(
            transparency_hashes=(good_hash, "B" * 64, good_hash)
        ),
    }
    refusals: dict[str, str] = {}
    base = {
        "expected_blocks": 4,
        "observed_blocks": 4,
        "duplicate_blocks": 0,
        "concurrent_writers": 1,
        "transparency_hashes": (good_hash, good_hash, good_hash),
    }
    for name, change in plants.items():
        try:
            refuse_unsafe_producer_state(**{**base, **change})
        except CheckerRefusal as error:
            refusals[name] = str(error)
        else:
            raise Refusal(f"runner gate accepted {name} plant")
    registered = Path(r"C:\registered\frame.ARW")
    wrong = Path(r"C:\other\frame.ARW")
    require(
        registered.name == wrong.name
        and _windows_key(registered) != _windows_key(wrong),
        "full-path commissioning fixture is malformed",
    )
    path_refusal = (
        "same basename at a different absolute path is not an inventory match"
    )
    return {
        "status": "COMMISSIONED",
        "authority": "checker_v2.refuse_unsafe_producer_state",
        "positive_control": "accepted",
        "refusals": refusals,
        "full_path_refusal": path_refusal,
    }


def load_external_module(path: Path) -> Any:
    path = path.resolve()
    spec = importlib.util.spec_from_file_location("m8_v2_external_q1", path)
    require(spec is not None and spec.loader is not None, f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def external_identity(
    comparator: Path,
    raw: Path,
    candidates: Sequence[Path],
    crop: tuple[int, int, int, int],
) -> dict[str, Any]:
    require(len(candidates) == 3, "identity requires exactly three candidate TIFFs")
    raw = raw.resolve()
    require(
        sha256_file(raw) == IDENTITY_REFERENCE_HASH,
        f"{raw}: copied flat-1s reference hash is not frozen",
    )
    q1 = load_external_module(comparator)
    first = q1.decode_rawpy(raw)
    second = q1.decode_rawpy(raw)
    first_hash = q1.array_sha256(first.mosaic)
    second_hash = q1.array_sha256(second.mosaic)
    require(
        first_hash == second_hash
        and q1.raw_metadata_sha256(first) == q1.raw_metadata_sha256(second)
        and q1.raw_metadata_equal(first, second),
        "two independent rawpy/LibRaw contexts disagreed",
    )
    gains, site_black = q1.validate_raw_loader(first)
    x, y, width, height = crop
    prediction = q1.external_prediction(
        first.mosaic, site_black, gains, (x, y), width, height
    )
    rows = []
    for candidate in candidates:
        array = q1.read_rgb16_tiff(candidate.resolve())
        stats = q1.compare_rgb16(prediction, array)
        require(
            q1._stats_exact(stats),
            f"{candidate}: existing external rawpy/LibRaw Q1 comparator found differences",
        )
        rows.append(
            {
                "candidate": hash_record(candidate.resolve()),
                "comparison": stats,
            }
        )
    return {
        "schema": "strehl-m8-v2-external-identity",
        "version": VERSION,
        "comparator": hash_record(comparator.resolve()),
        "raw": hash_record(raw),
        "crop_xywh": list(crop),
        "rawpy_context_1_mosaic_sha256": first_hash,
        "rawpy_context_2_mosaic_sha256": second_hash,
        "prediction_array_sha256": q1.array_sha256(prediction),
        "candidates": rows,
        "status": "EXACT",
    }


def common_environment() -> dict[str, str | None]:
    return {
        "CARGO_BUILD_JOBS": "8",
        "CARGO_INCREMENTAL": "0",
        "RAYON_NUM_THREADS": "8",
        "OMP_NUM_THREADS": "8",
        "OPENBLAS_NUM_THREADS": "8",
        "MKL_NUM_THREADS": "8",
        "NUMEXPR_NUM_THREADS": "8",
        "BLIS_NUM_THREADS": "8",
        "VECLIB_MAXIMUM_THREADS": "8",
        "STREHL_PYRAMID_WORKERS": "1",
        "STREHL_GATE_FLOOR": "white",
        "STREHL_FULLRES_GATHER": "on",
        "STREHL_DEFECT": "off",
        "STREHL_RESTORE": "off",
        "STREHL_ALIGN": "1",
        "STREHL_FIX_CA": None,
        "STREHL_M8_V2_TRACE_DIR": None,
        "STREHL_CONFIDENCE_MAP": None,
        "STREHL_CONFIDENCE_DEBUG": None,
        "STREHL_GATE_FLOOR_SCALE": None,
        "STREHL_RESTORE_SIGMA": None,
    }


def render_command(
    binary: str,
    source: str,
    sidecar: str,
    output: str,
    mode: str,
    *,
    identity: bool,
) -> dict[str, Any]:
    arguments = [
        "stack",
        source,
        "--out",
        output,
        "--merge",
        "pyramid",
        "--cover",
        mode,
        "--resampler",
        "catmull-rom",
        "--binned",
    ]
    if identity:
        arguments.extend(("--fix-ca", "off"))
    environment = common_environment()
    environment["STREHL_WARPMAP"] = sidecar
    return {"file": binary, "arguments": arguments, "environment": environment}


def seal_plan(
    prepare_path: Path,
    input_path: Path,
    input_runtime: Path,
    plan_runtime: Path,
) -> dict[str, Any]:
    prepare = read_json(prepare_path)
    require(
        isinstance(prepare, dict)
        and prepare.get("schema") == SCHEMA_PREPARE
        and prepare.get("version") == VERSION,
        f"{prepare_path}: unsupported prepare receipt",
    )
    input_manifest = validate_input_shape(read_json(input_path))
    tool_audit_path = Path(prepare["tool_audit"]["path"])
    require(
        sha256_file(tool_audit_path) == prepare["tool_audit"]["sha256"],
        "prepare tool-audit file hash changed before sealing",
    )
    committed_tools = read_json(tool_audit_path)
    require(
        isinstance(committed_tools, dict)
        and committed_tools.get("schema") == "strehl-m8-v2-tool-audit"
        and committed_tools.get("commit") == prepare["source_commit"],
        "prepare tool audit is unsupported or belongs to another commit",
    )
    git_tree_path = Path(prepare["git_tree"]["path"])
    require(
        sha256_file(git_tree_path) == prepare["git_tree"]["sha256"],
        "prepare Git tree/blob file hash changed before sealing",
    )
    source_git = read_json(git_tree_path)
    require(
        isinstance(source_git, dict)
        and source_git.get("schema") == "strehl-m8-v2-git-tree"
        and source_git.get("commit") == prepare["source_commit"],
        "prepare Git tree/blob record is unsupported or belongs to another commit",
    )
    root = Path(prepare["output_root"]).resolve()
    uninstrumented = prepare["binaries"]["uninstrumented"]["path"]
    instrumented = prepare["binaries"]["instrumented"]["path"]
    checker = str(
        Path(prepare["repo"])
        / "experiments"
        / "cover-default"
        / "m8-v2"
        / "checker_v2.py"
    )
    arms = []
    for case in CASES:
        source_row = capture_row(input_manifest, case.name)
        for mode in ("scale", "crop"):
            arm_root = root / "arms" / f"{case.name}-{mode}"
            inventory = arm_root / "source-inventory.json"
            outputs = {
                "uninstrumented": arm_root / "tiff" / "uninstrumented.tiff",
                "instrumented_off": arm_root / "tiff" / "instrumented-off.tiff",
                "instrumented_on": arm_root / "tiff" / "instrumented-on.tiff",
            }
            commands = {}
            for role, binary in (
                ("uninstrumented", uninstrumented),
                ("instrumented_off", instrumented),
                ("instrumented_on", instrumented),
            ):
                commands[role] = render_command(
                    binary,
                    source_row["directory"],
                    source_row["sidecar"]["path"],
                    str(outputs[role]),
                    mode,
                    identity=False,
                )
                commands[role]["environment"]["TEMP"] = str(root / "temp")
                commands[role]["environment"]["TMP"] = str(root / "temp")
            commands["instrumented_on"]["environment"][
                "STREHL_M8_V2_TRACE_DIR"
            ] = str(arm_root / "trace")
            commands["uninstrumented"]["environment"]["STREHL_M8_V2_TRACE_DIR"] = None
            commands["instrumented_off"]["environment"]["STREHL_M8_V2_TRACE_DIR"] = None
            checker_args = [
                "-B",
                checker,
                "adjudicate",
                "--capture",
                case.name,
                "--trace-dir",
                str(arm_root / "trace"),
                "--tiff",
                str(outputs["instrumented_on"]),
                "--source-inventory",
                str(inventory),
                "--sidecar-sha256",
                case.sidecar_sha256,
                "--mode",
                mode,
            ]
            if mode == "crop":
                checker_args.extend(("--crop", ",".join(map(str, case.crop))))
            checker_args.extend(("--output-dir", str(arm_root / "adjudication")))
            arms.append(
                {
                    "kind": "full",
                    "case": case.name,
                    "mode": mode,
                    "root": str(arm_root),
                    "source": source_row["directory"],
                    "sidecar": source_row["sidecar"],
                    "crop_xywh": list(case.crop) if mode == "crop" else None,
                    "source_inventory": str(inventory),
                    "outputs": {key: str(value) for key, value in outputs.items()},
                    "render_commands": commands,
                    "checker_command": {"file": sys.executable, "arguments": checker_args},
                }
            )

    identity_root = root / "arms" / "identity-crop"
    identity_source = identity_root / "source"
    identity_raw = identity_source / CASES[0].reference_name
    identity_sidecar_path = identity_root / "identity.warpmap.txt"
    identity_inventory_path = identity_root / "source-inventory.json"
    identity_outputs = {
        "uninstrumented": identity_root / "tiff" / "uninstrumented.tiff",
        "instrumented_off": identity_root / "tiff" / "instrumented-off.tiff",
        "instrumented_on": identity_root / "tiff" / "instrumented-on.tiff",
    }
    identity_commands = {}
    for role, binary in (
        ("uninstrumented", uninstrumented),
        ("instrumented_off", instrumented),
        ("instrumented_on", instrumented),
    ):
        identity_commands[role] = render_command(
            binary,
            str(identity_source),
            str(identity_sidecar_path),
            str(identity_outputs[role]),
            "crop",
            identity=True,
        )
        identity_commands[role]["environment"]["TEMP"] = str(root / "temp")
        identity_commands[role]["environment"]["TMP"] = str(root / "temp")
        identity_commands[role]["environment"]["STREHL_M8_V2_TRACE_DIR"] = (
            str(identity_root / "trace") if role == "instrumented_on" else None
        )
    identity_checker = [
        "-B",
        checker,
        "adjudicate",
        "--capture",
        "identity-flat-1s",
        "--trace-dir",
        str(identity_root / "trace"),
        "--tiff",
        str(identity_outputs["instrumented_on"]),
        "--source-inventory",
        str(identity_inventory_path),
        "--sidecar-sha256",
        "{IDENTITY_SIDECAR_SHA256}",
        "--mode",
        "crop",
        "--crop",
        ",".join(map(str, IDENTITY_CROP)),
        "--output-dir",
        str(identity_root / "adjudication"),
    ]
    identity = {
        "kind": "identity",
        "case": "identity-flat-1s",
        "mode": "crop",
        "root": str(identity_root),
        "released_reference": str(
            REFERENCE_ROOT / CASES[0].name / CASES[0].reference_name
        ),
        "released_reference_sha256": IDENTITY_REFERENCE_HASH,
        "source": str(identity_source),
        "raw": str(identity_raw),
        "sidecar": str(identity_sidecar_path),
        "source_inventory": str(identity_inventory_path),
        "crop_xywh": list(IDENTITY_CROP),
        "outputs": {key: str(value) for key, value in identity_outputs.items()},
        "render_commands": identity_commands,
        "checker_command": {"file": sys.executable, "arguments": identity_checker},
    }
    input_record = hash_record(input_path.resolve())
    input_runtime_resolved = str(Path(os.path.abspath(input_runtime)))
    input_record["path"] = input_runtime_resolved
    return {
        "schema": SCHEMA_PLAN,
        "version": VERSION,
        "repo": prepare["repo"],
        "source_commit": prepare["source_commit"],
        "output_root": str(root),
        "prepare_receipt": hash_record(prepare_path.resolve()),
        "preparation": {
            "git_tree": prepare["git_tree"],
            "source_git": source_git,
            "git_archive": prepare["git_archive"],
            "source_files": prepare["source_files"],
            "source_snapshots": prepare["snapshots"],
            "binaries": prepare["binaries"],
            "runtime": prepare["runtime"],
            "host_tools": prepare["host_tools"],
            "toolchain": prepare["toolchain"],
            "os": prepare["os"],
            "power_plan": prepare["power_plan"],
            "power_plan_text": prepare["power_plan_text"],
            "environment": prepare["environment"],
            "prepare_operations": prepare["operations"],
            "committed_tools": committed_tools,
        },
        "input_manifest": {
            **input_record,
            "runtime_path": input_runtime_resolved,
        },
        "runtime_path": str(Path(os.path.abspath(plan_runtime))),
        "frozen_environment": {
            **common_environment(),
            "TEMP": str(root / "temp"),
            "TMP": str(root / "temp"),
        },
        "output_contract": (
            "camera-linear, camera-native, binned RGB16 TIFF; ordinary pyramid; "
            "full-resolution Catmull-Rom gather; no defect/restoration/exposure/"
            "confidence pass; default active CA except identity control"
        ),
        "identity": identity,
        "arms": arms,
        "continuation_rule": (
            "Complete flat-1s scale and crop. Any Crop M8-R or M8-O violation "
            "stops later exposures; otherwise later exposure requires explicit "
            "operator continuation acknowledgement."
        ),
    }


def validate_plan(
    plan_path: Path,
    prepare_path: Path,
    input_path: Path,
    output_root: Path,
) -> dict[str, Any]:
    plan = read_json(plan_path)
    require(
        isinstance(plan, dict)
        and plan.get("schema") == SCHEMA_PLAN
        and plan.get("version") == VERSION,
        f"{plan_path}: unsupported run plan",
    )
    require(
        Path(plan["runtime_path"]).resolve() == plan_path.resolve(),
        f"{plan_path}: not at its preregistered runtime path",
    )
    require(
        Path(plan["input_manifest"]["runtime_path"]).resolve() == input_path.resolve(),
        f"{input_path}: not at the preregistered runtime path",
    )
    require(
        plan["input_manifest"]["sha256"] == sha256_file(input_path.resolve()),
        "input manifest hash differs from run plan",
    )
    require(
        plan["prepare_receipt"]["sha256"] == sha256_file(prepare_path.resolve()),
        "prepare receipt hash differs from run plan",
    )
    require(
        Path(plan["output_root"]).resolve() == output_root.resolve(),
        "run plan output root differs from the selected private root",
    )
    rebuilt = seal_plan(
        prepare_path,
        input_path,
        Path(plan["input_manifest"]["runtime_path"]),
        Path(plan["runtime_path"]),
    )
    require(
        canonical_json(rebuilt) == canonical_json(plan),
        "run plan does not exactly reproduce PREPARE, input, commands and identities",
    )
    return {
        "status": "VALID",
        "plan": hash_record(plan_path.resolve()),
        "prepare": hash_record(prepare_path.resolve()),
        "input": hash_record(input_path.resolve()),
        "source_commit": plan["source_commit"],
    }


def _verify_hash_record(row: Any, label: str) -> dict[str, Any]:
    require(isinstance(row, dict), f"{label}: hash record is not an object")
    require(
        isinstance(row.get("path"), str)
        and isinstance(row.get("bytes"), int)
        and isinstance(row.get("sha256"), str),
        f"{label}: incomplete hash record",
    )
    current = hash_record(Path(row["path"]))
    require(
        current["bytes"] == row["bytes"]
        and current["sha256"] == row["sha256"],
        f"{label}: identity changed",
    )
    return current


def _arm_file_paths(root: Path, receipt_path: Path) -> set[Path]:
    paths: set[Path] = set()
    for directory, names, files in os.walk(root, followlinks=False):
        names.sort()
        files.sort()
        for name in names:
            path = Path(directory) / name
            require(not path.is_symlink(), f"{path}: arm-directory symlink forbidden")
        for name in files:
            lexical_path = Path(directory) / name
            require(
                not lexical_path.is_symlink(),
                f"{lexical_path}: arm-file symlink forbidden",
            )
            path = lexical_path.resolve()
            require(path.is_file(), f"{path}: arm entry is not a regular file")
            if path != receipt_path:
                paths.add(path)
    return paths


def verify_arm(receipt_path: Path) -> dict[str, Any]:
    receipt_path = receipt_path.resolve()
    receipt = read_json(receipt_path)
    require(
        isinstance(receipt, dict)
        and receipt.get("schema") == SCHEMA_RECEIPT
        and receipt.get("version") == VERSION,
        f"{receipt_path}: unsupported arm receipt",
    )
    required_fields = {
        "arm",
        "kind",
        "case",
        "mode",
        "evidence_commit",
        "source_commit",
        "run_plan",
        "input_manifest",
        "prepare_receipt",
        "binaries",
        "outputs",
        "source_trees",
        "commands",
        "trace",
        "result",
        "evidence_index",
        "external_identity",
        "reported_crop_rectangles",
        "files",
    }
    require(
        required_fields <= receipt.keys(),
        f"{receipt_path}: missing receipt fields "
        f"{sorted(required_fields - receipt.keys())}",
    )
    require(receipt.get("kind") in ("identity", "full"), "invalid arm kind")
    require(receipt.get("mode") in ("scale", "crop"), "invalid arm mode")
    require(
        isinstance(receipt.get("arm"), str)
        and receipt_path.name == "receipt.json"
        and receipt_path.parent.name == receipt["arm"],
        "receipt path does not match its arm identity",
    )
    arm_root = receipt_path.parent
    output_root = arm_root.parent.parent

    plan_record = _verify_hash_record(receipt["run_plan"], "run plan")
    input_record = _verify_hash_record(
        receipt["input_manifest"], "input manifest"
    )
    prepare_record = _verify_hash_record(
        receipt["prepare_receipt"], "prepare receipt"
    )
    require(
        Path(prepare_record["path"]) == output_root / "prepare.json",
        "prepare receipt is not the selected private root's receipt",
    )
    validate_plan(
        Path(plan_record["path"]),
        Path(prepare_record["path"]),
        Path(input_record["path"]),
        output_root,
    )
    plan = read_json(Path(plan_record["path"]))
    prepare = read_json(Path(prepare_record["path"]))
    require(
        receipt["source_commit"] == plan["source_commit"]
        and receipt["source_commit"] == prepare["source_commit"],
        "receipt source commit disagrees with plan/PREPARE",
    )
    repo = Path(plan["repo"]).resolve()
    evidence_commit = exact_commit(repo, receipt["evidence_commit"])
    require(
        evidence_commit == receipt["evidence_commit"].lower(),
        "receipt evidence commit is not its exact 40-hex commit",
    )
    committed_file(repo, evidence_commit, Path(plan_record["path"]))
    committed_file(repo, evidence_commit, Path(input_record["path"]))

    if receipt["kind"] == "identity":
        entry = plan.get("identity")
        require(isinstance(entry, dict), "run plan has no identity arm")
    else:
        entries = [
            row
            for row in plan.get("arms", [])
            if isinstance(row, dict)
            and row.get("case") == receipt["case"]
            and row.get("mode") == receipt["mode"]
        ]
        require(len(entries) == 1, "run plan does not name exactly one receipt arm")
        entry = entries[0]
    require(
        entry.get("kind") == receipt["kind"]
        and entry.get("case") == receipt["case"]
        and entry.get("mode") == receipt["mode"]
        and Path(entry.get("root", "")).resolve() == arm_root,
        "receipt arm context disagrees with the run plan",
    )

    binaries = receipt["binaries"]
    require(
        isinstance(binaries, dict)
        and binaries == prepare.get("binaries")
        and set(binaries) == {"uninstrumented", "instrumented", "fixture"},
        "receipt binary identities disagree with PREPARE",
    )
    for name, row in binaries.items():
        _verify_hash_record(row, f"{name} binary")

    source_trees = receipt["source_trees"]
    require(
        isinstance(source_trees, dict)
        and set(source_trees) == {"uninstrumented", "instrumented"},
        "receipt has no complete prepared source-tree identities",
    )
    for name, row in source_trees.items():
        require(isinstance(row, dict) and row.get("root"), f"{name}: bad tree record")
        prepared_snapshot = prepare["snapshots"][name]
        require(
            Path(row["root"]).resolve()
            == Path(prepared_snapshot["path"]).resolve()
            and row == prepared_snapshot["post_build"],
            f"{name}: receipt tree is not the PREPARE snapshot",
        )
        current = tree_audit(Path(row["root"]))
        require(
            current == row,
            f"{name}: prepared source tree changed after rendering",
        )

    file_rows = receipt["files"]
    require(
        isinstance(file_rows, list) and file_rows,
        "receipt has no complete retained-file identities",
    )
    verified_files = [
        _verify_hash_record(row, f"receipt file {index}")
        for index, row in enumerate(file_rows)
    ]
    retained_paths = [Path(row["path"]).resolve() for row in verified_files]
    require(
        len(retained_paths) == len(set(retained_paths)),
        "receipt has duplicate retained-file identities",
    )
    expected_lock = (
        output_root / "locks" / f"{receipt['arm']}.lock.json"
    ).resolve()
    actual_arm_files = _arm_file_paths(arm_root, receipt_path)
    require(
        set(retained_paths) == actual_arm_files | {expected_lock},
        "receipt retained-file set is incomplete or has extra paths",
    )

    outputs = receipt["outputs"]
    require(
        isinstance(outputs, dict)
        and set(outputs)
        == {"uninstrumented", "instrumented_off", "instrumented_on"},
        "receipt has no complete three-way output identities",
    )
    output_hashes = []
    for role in ("uninstrumented", "instrumented_off", "instrumented_on"):
        row = _verify_hash_record(outputs[role], f"{role} output")
        require(
            Path(row["path"]).resolve()
            == Path(entry["outputs"][role]).resolve(),
            f"{role} output path disagrees with run plan",
        )
        output_hashes.append(row["sha256"])
    require(
        len(set(output_hashes)) == 1,
        "receipt output-transparency hashes are not byte-identical",
    )

    trace = receipt["trace"]
    require(isinstance(trace, dict), "receipt has no trace record")
    require(
        Path(trace.get("trace_dir", "")).resolve()
        == Path(
            entry["render_commands"]["instrumented_on"]["environment"][
                "STREHL_M8_V2_TRACE_DIR"
            ]
        ).resolve()
        and Path(trace.get("inventory", "")).resolve()
        == Path(entry["source_inventory"]).resolve(),
        "receipt trace paths disagree with run plan",
    )
    require(
        [value.upper() for value in trace.get("transparency_hashes", [])]
        == output_hashes,
        "trace transparency hashes do not bind the three receipt outputs",
    )
    require(
        Path(trace.get("writer_record", "")).resolve()
        == (arm_root / "writer-record.json").resolve(),
        "trace writer record is not the arm writer record",
    )
    audit_record = _verify_hash_record(trace.get("audit"), "trace audit")
    require(
        Path(audit_record["path"]).resolve()
        == (arm_root / "trace-audit.json").resolve()
        and audit_record["sha256"] == trace.get("audit_payload_sha256"),
        "trace audit record is not the arm's recomputed audit payload",
    )
    current_trace = trace_audit(
        Path(trace["trace_dir"]),
        Path(trace["inventory"]),
        Path(trace["writer_record"]),
        trace["transparency_hashes"],
    )
    require(
        sha256_bytes(canonical_json(current_trace))
        == trace["audit_payload_sha256"],
        "current trace audit differs from the arm receipt",
    )

    result_record = _verify_hash_record(receipt["result"], "checker result")
    expected_result_path = arm_root / "adjudication" / "result.json"
    require(
        Path(result_record["path"]).resolve() == expected_result_path.resolve(),
        "checker result path disagrees with the arm root",
    )
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from checker_v2 import verify_result as verify_checker_result

    checker_verification = verify_checker_result(expected_result_path)
    result = read_json(expected_result_path)
    require(
        result.get("capture") == receipt["case"]
        and result.get("mode") == receipt["mode"],
        "checker result context disagrees with receipt",
    )
    evidence_record = _verify_hash_record(
        receipt["evidence_index"], "evidence index"
    )
    require(
        Path(evidence_record["path"]).resolve()
        == Path(checker_verification["evidence_index"]).resolve()
        and evidence_record["sha256"]
        == checker_verification["evidence_index_sha256"],
        "receipt evidence index disagrees with checker verification",
    )

    reports = receipt["reported_crop_rectangles"]
    require(
        isinstance(reports, dict)
        and set(reports)
        == {"uninstrumented", "instrumented_off", "instrumented_on"},
        "receipt has no complete rendered Crop-rectangle reports",
    )
    if receipt["mode"] == "crop":
        crop = result.get("crop")
        require(isinstance(crop, dict), "Crop result has no explicit rectangle")
        result_crop = {
            "x": int(crop["x"]),
            "y": int(crop["y"]),
            "width": int(crop["width"]),
            "height": int(crop["height"]),
        }
        planned_crop = entry.get("crop_xywh")
        require(
            isinstance(planned_crop, list)
            and len(planned_crop) == 4
            and result_crop
            == {
                "x": int(planned_crop[0]),
                "y": int(planned_crop[1]),
                "width": int(planned_crop[2]),
                "height": int(planned_crop[3]),
            },
            "adjudicated Crop rectangle differs from the run plan",
        )
        require(
            all(value == result_crop for value in reports.values()),
            "rendered Crop rectangles differ from the adjudicated rectangle",
        )
    else:
        require(
            entry.get("crop_xywh") is None
            and result.get("crop") is None
            and
            all(value is None for value in reports.values()),
            "non-Crop receipt contains a rendered Crop rectangle",
        )

    commands = receipt["commands"]
    expected_command_count = 9 if receipt["kind"] == "identity" else 7
    require(
        isinstance(commands, list) and len(commands) == expected_command_count,
        f"receipt needs exactly {expected_command_count} executed commands",
    )
    command_paths: set[Path] = set()
    log_paths: set[Path] = set()
    parsed_commands: list[dict[str, Any]] = []
    for index, command in enumerate(commands):
        require(isinstance(command, dict), f"command {index}: not an object")
        require(
            set(command)
            == {"file", "arguments", "exit_code", "command", "log"}
            and command.get("exit_code") == 0
            and isinstance(command.get("file"), str)
            and isinstance(command.get("arguments"), list),
            f"command {index}: malformed execution record",
        )
        command_record = _verify_hash_record(
            command["command"], f"command {index} record"
        )
        log_record = _verify_hash_record(command["log"], f"command {index} log")
        command_path = Path(command_record["path"]).resolve()
        log_path = Path(log_record["path"]).resolve()
        require(
            command_path == Path(str(log_path) + ".command.json")
            and log_path.is_relative_to((arm_root / "logs").resolve()),
            f"command {index}: command/log paths are not the arm log pair",
        )
        require(
            command_path not in command_paths and log_path not in log_paths,
            f"command {index}: duplicate command/log identity",
        )
        command_paths.add(command_path)
        log_paths.add(log_path)
        command_payload = read_json(command_path)
        require(
            isinstance(command_payload, dict)
            and command_payload.get("schema") == "strehl-m8-v2-command"
            and command_payload.get("version") == VERSION
            and command_payload.get("file") == command["file"]
            and command_payload.get("arguments") == command["arguments"]
            and Path(command_payload.get("working_directory", "")).resolve()
            == repo,
            f"command {index}: command JSON disagrees with its execution record",
        )
        require(
            isinstance(command_payload.get("environment"), dict),
            f"command {index}: command JSON has no environment",
        )
        parsed_commands.append(command_payload)
    for role in ("uninstrumented", "instrumented_off", "instrumented_on"):
        planned = entry["render_commands"][role]
        matches = [
            command
            for command in parsed_commands
            if command["file"] == planned["file"]
            and command["arguments"] == planned["arguments"]
            and all(
                command["environment"].get(name) == value
                for name, value in planned["environment"].items()
            )
        ]
        require(
            len(matches) == 1,
            f"receipt does not bind exactly one {role} planned render command",
        )

    external_identity = receipt["external_identity"]
    if receipt["kind"] == "identity":
        _verify_hash_record(external_identity, "external identity result")
    else:
        require(
            external_identity is None,
            "full arm unexpectedly carries an external identity result",
        )
    return {
        "status": "VERIFIED",
        "receipt": hash_record(receipt_path),
        "files": len(verified_files),
        "trace_blocks": current_trace["observed_blocks"],
        "cartesian_product": current_trace["cartesian_product"],
        "result": result_record,
        "evidence_index": evidence_record,
        "checker": checker_verification,
        "source_commit": receipt["source_commit"],
        "evidence_commit": evidence_commit,
    }


def parse_crop(raw: str) -> tuple[int, int, int, int]:
    fields = raw.split(",")
    require(len(fields) == 4, "crop must be x,y,w,h")
    try:
        values = tuple(int(value) for value in fields)
    except ValueError as error:
        raise Refusal("crop must contain integers") from error
    require(min(values) >= 0 and values[2] > 0 and values[3] > 0, "invalid crop")
    return values  # type: ignore[return-value]


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)

    atomic = commands.add_parser("atomic-json")
    atomic.add_argument("--output", type=Path, required=True)

    tools = commands.add_parser("tool-audit")
    tools.add_argument("--repo", type=Path, required=True)
    tools.add_argument("--commit", required=True)
    tools.add_argument("--extra", action="append", default=[])
    tools.add_argument("--output", type=Path)

    tree = commands.add_parser("git-tree")
    tree.add_argument("--repo", type=Path, required=True)
    tree.add_argument("--commit", required=True)
    tree.add_argument("--output", type=Path)

    snapshot = commands.add_parser("tree-audit")
    snapshot.add_argument("--root", type=Path, required=True)
    snapshot.add_argument("--output", type=Path)

    runtime = commands.add_parser("runtime-info")
    runtime.add_argument("--output", type=Path)

    inventory = commands.add_parser("input-manifest")
    inventory.add_argument("--capture-root", type=Path, required=True)
    inventory.add_argument("--sidecar-root", type=Path, required=True)
    inventory.add_argument("--exif-tool", required=True)
    inventory.add_argument("--output", type=Path, required=True)

    verify_input = commands.add_parser("verify-input")
    verify_input.add_argument("--input", type=Path, required=True)
    verify_input.add_argument("--exif-tool")
    verify_input.add_argument("--output", type=Path)

    extract = commands.add_parser("extract-inventory")
    extract.add_argument("--input", type=Path, required=True)
    extract.add_argument("--case", choices=tuple(CASE_BY_NAME), required=True)
    extract.add_argument("--output", type=Path, required=True)

    sidecar = commands.add_parser("identity-sidecar")
    sidecar.add_argument("--source", type=Path, required=True)
    sidecar.add_argument("--output", type=Path, required=True)

    single = commands.add_parser("single-inventory")
    single.add_argument("--source", type=Path, required=True)
    single.add_argument("--output", type=Path, required=True)

    trace = commands.add_parser("trace-audit")
    trace.add_argument("--trace-dir", type=Path, required=True)
    trace.add_argument("--inventory", type=Path, required=True)
    trace.add_argument("--writer-record", type=Path, required=True)
    trace.add_argument("--tiff-hash", action="append", required=True)
    trace.add_argument("--output", type=Path)

    fixture = commands.add_parser("fixture-audit")
    fixture.add_argument("--trace-dir", type=Path, required=True)
    fixture.add_argument("--expected", type=int)
    fixture.add_argument("--output", type=Path)

    runner_gate = commands.add_parser("commission-runner-gate")
    runner_gate.add_argument("--output", type=Path)

    external = commands.add_parser("external-identity")
    external.add_argument("--comparator", type=Path, required=True)
    external.add_argument("--raw", type=Path, required=True)
    external.add_argument("--candidate", type=Path, action="append", required=True)
    external.add_argument("--crop", type=parse_crop, required=True)
    external.add_argument("--output", type=Path)

    committed = commands.add_parser("committed-files")
    committed.add_argument("--repo", type=Path, required=True)
    committed.add_argument("--commit", required=True)
    committed.add_argument("--path", type=Path, action="append", required=True)
    committed.add_argument("--output", type=Path)

    seal = commands.add_parser("seal-plan")
    seal.add_argument("--prepare", type=Path, required=True)
    seal.add_argument("--input", type=Path, required=True)
    seal.add_argument("--input-runtime-path", type=Path, required=True)
    seal.add_argument("--plan-runtime-path", type=Path, required=True)
    seal.add_argument("--output", type=Path, required=True)

    validate = commands.add_parser("validate-plan")
    validate.add_argument("--plan", type=Path, required=True)
    validate.add_argument("--prepare", type=Path, required=True)
    validate.add_argument("--input", type=Path, required=True)
    validate.add_argument("--output-root", type=Path, required=True)
    validate.add_argument("--output", type=Path)

    arm = commands.add_parser("verify-arm")
    arm.add_argument("--receipt", type=Path, required=True)
    arm.add_argument("--output", type=Path)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "atomic-json":
            payload = json.load(sys.stdin)
            atomic_write(args.output, canonical_json(payload))
        elif args.command == "tool-audit":
            emit(tool_audit(args.repo, args.commit, args.extra), args.output)
        elif args.command == "git-tree":
            emit(git_tree_audit(args.repo, args.commit), args.output)
        elif args.command == "tree-audit":
            emit(tree_audit(args.root), args.output)
        elif args.command == "runtime-info":
            emit(runtime_info(), args.output)
        elif args.command == "input-manifest":
            emit(
                build_input_manifest(
                    args.capture_root, args.sidecar_root, args.exif_tool
                ),
                args.output,
            )
        elif args.command == "verify-input":
            emit(verify_input_manifest(args.input, args.exif_tool), args.output)
        elif args.command == "extract-inventory":
            emit(checker_inventory(args.input, args.case), args.output)
        elif args.command == "identity-sidecar":
            payload, _record = identity_sidecar(args.source)
            atomic_write(args.output, payload)
            print(json.dumps(hash_record(args.output.resolve()), sort_keys=True))
        elif args.command == "single-inventory":
            emit(single_inventory(args.source), args.output)
        elif args.command == "trace-audit":
            emit(
                trace_audit(
                    args.trace_dir,
                    args.inventory,
                    args.writer_record,
                    args.tiff_hash,
                ),
                args.output,
            )
        elif args.command == "fixture-audit":
            emit(fixture_audit(args.trace_dir, args.expected), args.output)
        elif args.command == "commission-runner-gate":
            emit(commission_runner_gate(), args.output)
        elif args.command == "external-identity":
            emit(
                external_identity(
                    args.comparator, args.raw, args.candidate, args.crop
                ),
                args.output,
            )
        elif args.command == "committed-files":
            commit = exact_commit(args.repo.resolve(), args.commit)
            emit(
                {
                    "schema": "strehl-m8-v2-committed-files",
                    "version": VERSION,
                    "repo": str(args.repo.resolve()),
                    "commit": commit,
                    "files": [
                        committed_file(args.repo.resolve(), commit, path)
                        for path in args.path
                    ],
                },
                args.output,
            )
        elif args.command == "seal-plan":
            emit(
                seal_plan(
                    args.prepare,
                    args.input,
                    args.input_runtime_path,
                    args.plan_runtime_path,
                ),
                args.output,
            )
        elif args.command == "validate-plan":
            emit(
                validate_plan(
                    args.plan, args.prepare, args.input, args.output_root
                ),
                args.output,
            )
        elif args.command == "verify-arm":
            emit(verify_arm(args.receipt), args.output)
        else:
            raise AssertionError(args.command)
        return 0
    except (Refusal, OSError, ValueError, KeyError, TypeError) as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
