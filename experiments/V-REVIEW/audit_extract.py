import subprocess, os, pathlib, hashlib
REPO = r"C:\dev\blog\death-of-software\projects\strehl"
PIN  = "9b05d0b7"
DEST = pathlib.Path(r"C:\dev\strehl-out\V-REVIEW\pin")

def run(args):
    p = subprocess.run(["git"]+args, cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        raise SystemExit("git failed: %s\n%s" % (args, p.stderr.decode("utf8","replace")))
    return p.stdout

names = run(["ls-tree","-r","--name-only",PIN]).decode("utf8").split("\n")
names = [n.strip() for n in names if n.strip().endswith((".rs",".md",".toml"))]
DEST.mkdir(parents=True, exist_ok=True)
n=0; tot=0
for nm in names:
    raw = run(["show","%s:%s" % (PIN, nm)])          # BYTES, never a shell redirect
    out = DEST / nm
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(raw)                              # byte-exact
    n+=1; tot+=len(raw)
print("extracted %d files, %d bytes -> %s" % (n, tot, DEST))

# integrity: the extracted bytes must hash to git's own blob id
import re
bad=0
for nm in names[:400]:
    raw = (DEST/nm).read_bytes()
    h = hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest()
    want = run(["rev-parse","%s:%s" % (PIN,nm)]).decode().strip()
    if h != want:
        print("  BLOB MISMATCH", nm, h, want); bad+=1
print("blob-id verification: %d checked, %d mismatched" % (min(len(names),400), bad))
