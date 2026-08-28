"""Read-vs-documented audit of STREHL_* environment variables at a given commit.

My committed AUDIT-user-surface.md tested only ONE direction -- "is every
DOCUMENTED variable read?" -- and answered yes for the eight in `stack --help`.
The reverse direction (is every READ variable documented?) was never measured.
This measures both.
"""
import re, subprocess, sys

REPO = r"C:\dev\blog\death-of-software\projects\strehl"
PIN  = sys.argv[1] if len(sys.argv) > 1 else "d35f9055"
NAME = re.compile(r"STREHL_[A-Z0-9_]+")

def git(*a):
    r = subprocess.run(["git", "-C", REPO, *a], capture_output=True)
    return r.stdout.decode("utf-8", "replace")

rs = [f for f in git("ls-tree", "-r", "--name-only", PIN, "--", "crates/").splitlines()
      if f.endswith(".rs")]
ship = [f for f in rs if "/tests/" not in f and "/examples/" not in f and
        not f.split("/")[-1].startswith("test")]

read, const_of, doc_src = {}, {}, {}
ENVCALL = re.compile(r"env::var(?:_os)?\s*\(\s*([^)]*?)\s*\)")
CONSTD  = re.compile(r"(?:const|static)\s+([A-Z0-9_]+)\s*:\s*&(?:'static\s+)?str\s*=\s*\"(STREHL_[A-Z0-9_]+)\"")

for f in ship:
    body = git("show", f"{PIN}:{f}")
    for m in CONSTD.finditer(body):
        const_of[m.group(1)] = (m.group(2), f)
    for m in ENVCALL.finditer(body):
        arg = m.group(1)
        for n in NAME.findall(arg):
            read.setdefault(n, f)
        for c in re.findall(r"\b([A-Z0-9_]{4,})\b", arg):
            if c in const_of:
                read.setdefault(const_of[c][0], f)
    for line in body.splitlines():
        s = line.strip()
        if s.startswith("///") or s.startswith("//!") or "help =" in s or "long_help" in s:
            for n in NAME.findall(line):
                doc_src.setdefault(n, f)

# second pass: consts defined in one file, used in another
for f in ship:
    body = git("show", f"{PIN}:{f}")
    for m in ENVCALL.finditer(body):
        for c in re.findall(r"\b([A-Z0-9_]{4,})\b", m.group(1)):
            if c in const_of:
                read.setdefault(const_of[c][0], f)

USER = [r"C:\dev\strehl-out\DELIVER-V5\full-resolution\README.md",
        REPO + r"\README.md"]
docd = {}
for u in USER:
    try:
        t = open(u, encoding="utf-8", errors="replace").read()
    except OSError:
        continue
    for n in set(NAME.findall(t)):
        docd.setdefault(n, u)

print(f"commit {PIN}   shipping .rs files scanned: {len(ship)}")
print(f"READ by non-test shipping code : {len(read)}")
print(f"  of those, named in a user-facing README : {len(set(read) & set(docd))}")
print(f"  of those, named only in a /// or help= string : "
      f"{len(set(read) & set(doc_src) - set(docd))}")
und = sorted(set(read) - set(docd) - set(doc_src))
print(f"  of those, UNDOCUMENTED everywhere checked : {len(und)}")
print(f"DOCUMENTED in a README but never read : {sorted(set(docd) - set(read))}")
print()
for n in und:
    print(f"  undocumented  {n:34s} {read[n]}")
print()
for n in sorted(set(read) & set(docd)):
    print(f"  in README     {n:34s} {docd[n]}")
