import subprocess, os, re, json

REPO = r"C:\dev\blog\death-of-software\projects\strehl"
os.chdir(REPO)

def git(*a):
    r = subprocess.run(["git"] + list(a), capture_output=True)
    return r.stdout.decode("utf-8", "replace")

docs = sorted(f for f in os.listdir("docs/research") if f.endswith(".md"))
rows = []
for f in docs:
    p = "docs/research/" + f
    # first (introducing) commit date
    d_add = git("log", "--format=%h %ad", "--date=iso", "--diff-filter=A", "--", p).strip().splitlines()
    d_last = git("log", "--format=%h %ad", "--date=iso", "-1", "--", p).strip().splitlines()
    add = d_add[-1] if d_add else ""
    last = d_last[0] if d_last else ""
    b = open(p, "rb").read().decode("utf-8", "replace")
    flat = re.sub(r"\s+", " ", b)
    rows.append(dict(
        file=f, added=add, last=last,
        n_stack=len(re.findall(r"strehl stack|strehl-cli.*stack |\bstack\b\s+D:", flat)),
        align_cmd = len(re.findall(r"strehl align\b", flat)),
        ref_flag  = len(re.findall(r"--reference", flat)),
        align0    = len(re.findall(r"STREHL_ALIGN\s*=\s*0", flat)),
        align_env = len(re.findall(r"STREHL_ALIGN", flat)),
        warpmap   = len(re.findall(r"STREHL_WARPMAP", flat)),
        cachedir  = len(re.findall(r"STREHL_CACHE_DIR", flat)),
        smooth    = len(re.findall(r"STREHL_SMOOTH", flat)),
        sidecar   = len(re.findall(r"sidecar", flat, re.I)),
        resampler = len(re.findall(r"--resampler", flat)),
        spans     = len(re.findall(r"--spans", flat)),
    ))
with open(r"C:\dev\strehl-out\M117\corpus.json","w") as fh:
    json.dump(rows, fh, indent=1)
print("reports:", len(rows))
