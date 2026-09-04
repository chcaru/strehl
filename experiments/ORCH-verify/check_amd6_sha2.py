"""Decide whether the Amendment 6 SHA mismatch is real or a line-ending artifact.

check_amd6_sha.py hashed the git blob at 19f6f54a and got D19F6267..., while
the working tree hashes to the claimed 418D2D85....

This repository converts LF to CRLF on checkout (git says so on every STATUS
commit). If that is the whole story, the blob and the working tree are the
same document and the plan's figure is correct -- and my mismatch was an
artifact of my own instrument, not a defect in anyone's work.

Normalising both sides settles it.
"""
import hashlib
import subprocess
from pathlib import Path

REV = "19f6f54a"
PATH = "experiments/M164-m2-repair/commission.json"
CLAIMED = "418D2D852DC15B072CB65DD6BAAECAA9B4CBF82843BA825F00B0440ACC733C43"

blob = subprocess.run(["git", "cat-file", "blob", f"{REV}:{PATH}"],
                      capture_output=True, check=True).stdout
disk = Path(PATH.replace("/", "\\")).read_bytes()


def h(b):
    return hashlib.sha256(b).hexdigest().upper()


print(f"claimed in plan   : {CLAIMED}\n")
print(f"blob   raw        : {h(blob)}  ({len(blob)} bytes)")
print(f"disk   raw        : {h(disk)}  ({len(disk)} bytes)")
print(f"byte delta        : {len(disk) - len(blob)}")

blob_n = blob.replace(b"\r\n", b"\n")
disk_n = disk.replace(b"\r\n", b"\n")
print(f"\nblob   LF-normal  : {h(blob_n)}  ({len(blob_n)} bytes)")
print(f"disk   LF-normal  : {h(disk_n)}  ({len(disk_n)} bytes)")

print(f"\ncrlf count on disk: {disk.count(b'crlf'.replace(b'crlf', b'\r\n'))}")
print(f"same document     : {blob_n == disk_n}")

if blob_n == disk_n and h(disk) == CLAIMED:
    print("\nVERDICT: the plan's figure is CORRECT. The mismatch was a line-ending")
    print("         artifact of hashing the object store instead of the checkout.")
elif h(disk) == CLAIMED:
    print("\nVERDICT: figure matches the checkout but the documents genuinely differ.")
else:
    print("\nVERDICT: figure is wrong on both representations. Real defect.")
