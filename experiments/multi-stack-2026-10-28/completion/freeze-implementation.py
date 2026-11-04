"""Record a tested CLI snapshot under an explicit source-edit hold.

This is an implementation/evidence archive, not the source-inclusive desktop
distribution package. --product-only includes the CLI and UI, without copying
a potentially stale research example executable.
"""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile

root = Path(__file__).resolve().parents[3]
destination = root / sys.argv[1]
product_only = "--product-only" in sys.argv[2:]
destination.mkdir(parents=True, exist_ok=False)
digest = lambda path: hashlib.file_digest(path.open("rb"), "sha256").hexdigest()
files = [root / "Cargo.toml", root / "Cargo.lock"]
extensions = {".rs", ".toml", ".wgsl", ".json", ".csv", ".txt", ".md"}
files += sorted(p for p in (root / "crates").rglob("*")
                if p.is_file() and (product_only or "strehl-ui" not in p.parts) and p.suffix in extensions)
files += sorted((root / "experiments").rglob("*.rs"))
if product_only:
    files += [root / "scripts/strehl-control.py"]
receipt = {"schema": "strehl.implementation-snapshot.v1",
           "policy": "Captured after successful build during an explicit registered-source edit hold; "
                     + ("CLI and UI included, research executable excluded; " if product_only else "UI excluded; ")
                     + "included research sources are not all compiled.",
           "source_sha256": {}, "executables": {}}
with zipfile.ZipFile(destination / "implementation-source.zip", "x", zipfile.ZIP_DEFLATED) as archive:
    for path in files:
        name = path.relative_to(root).as_posix()
        before = digest(path)
        archive.write(path, name)
        assert digest(path) == before
        receipt["source_sha256"][name] = before
executables = ("strehl.exe", "strehl-ui.exe") if product_only else ("strehl.exe", "examples/session-reconstruction-roi.exe")
for executable in executables:
    source = root / "target/release" / executable
    target = destination / source.name
    shutil.copy2(source, target)
    receipt["executables"][target.name] = digest(target)
(destination / "build.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"destination": str(destination), "files": len(files), "executables": receipt["executables"]}, indent=2))
