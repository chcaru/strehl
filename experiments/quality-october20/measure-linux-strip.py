"""Measure symbol removal on an isolated copy of the alpha.5 Linux executable.

Run under existing WSL Python. Never reads dependency implementation sources.
This is a packaging-size experiment, not a full app runtime validation.
"""
from pathlib import Path
import hashlib
import json
import shutil
import struct
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / "linux-strip"
IMAGE = ROOT / "public-release-validation/alpha5-release-assets/" \
    "Strehl-0.1.0-alpha.5-x86_64-unknown-linux-gnu.AppImage"


def run(args):
    return subprocess.run([str(a) for a in args], check=True, capture_output=True, text=True).stdout


def sha(data):
    return hashlib.sha256(data).hexdigest()


def allocated_sections(path):
    data = path.read_bytes()
    assert data[:6] == b"\x7fELF\x02\x01", "expect ELF64 little endian"
    off = struct.unpack_from("<Q", data, 40)[0]
    size, count, names = struct.unpack_from("<HHH", data, 58)
    entries = [struct.unpack_from("<IIQQQQIIQQ", data, off+i*size) for i in range(count)]
    name_entry = entries[names]
    strings = data[name_entry[4]:name_entry[4]+name_entry[5]]
    result = {}
    for name, kind, flags, addr, pos, length, _, _, _, _ in entries:
        if flags & 2:  # SHF_ALLOC; loader-visible code, constants, data.
            title = strings[name:strings.find(b"\0", name)].decode()
            result[title] = {"address": addr, "size": length, "flags": flags,
                             "sha256": None if kind == 8 else sha(data[pos:pos+length])}
    return result


def main():
    OUT.mkdir(exist_ok=True)
    extracted = OUT / "unstripped"
    if not extracted.exists():
        run(["unsquashfs", "-processors", "1", "-o", "944632", "-d", extracted,
             IMAGE, "usr/bin/Strehl"])
    original = extracted / "usr/bin/Strehl"
    stripped = OUT / "Strehl-stripped"
    shutil.copy2(original, stripped)
    run(["strip", "--strip-all", stripped])
    before, after = allocated_sections(original), allocated_sections(stripped)
    assert before == after, "stripping changed a loadable section"
    versions = [run([p, "--engine-worker", "--version"]).strip() for p in [original, stripped]]
    assert versions[0] == versions[1]
    helps = [run([p, "--engine-worker", "--help"]) for p in [original, stripped]]
    assert helps[0] == helps[1] and "stack" in helps[0]
    result = {
        "input_appimage_sha256": sha(IMAGE.read_bytes()),
        "before_bytes": original.stat().st_size, "after_bytes": stripped.stat().st_size,
        "before_sha256": sha(original.read_bytes()), "after_sha256": sha(stripped.read_bytes()),
        "allocated_sections_equal": True, "allocated_sections": before,
        "strip_version": run(["strip", "--version"]).splitlines()[0],
        "version_before_after": versions,
        "help_byte_equal": True,
        "limitation": "Exact existing Linux binary comparison, worker startup only. "
        "Not a rebuilt Cargo profile pair, GUI test, or compressed AppImage reduction."
    }
    (OUT / "receipt.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps({k:v for k,v in result.items() if k != "allocated_sections"}, indent=2))


if __name__ == "__main__":
    main()
