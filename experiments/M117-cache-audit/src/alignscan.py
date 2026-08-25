import os, re, json, subprocess
os.chdir(r"C:\dev\blog\death-of-software\projects\strehl")
cls = json.load(open(r"C:\dev\strehl-out\M117\corpus_cls.json"))
inwin = [r["file"] for r in cls if r["cls"]=="IN-WINDOW"]
# search reports AND experiment scripts for align invocations
targets = []
for r,d,fs in os.walk("docs/research"):
    for f in fs:
        if f.endswith(".md"): targets.append(os.path.join(r,f))
for r,d,fs in os.walk("experiments"):
    for f in fs:
        if f.rsplit(".",1)[-1].lower() in ("ps1","py","md","txt","bat","cmd","sh"):
            targets.append(os.path.join(r,f))
pat = re.compile(r"[^\n]*\balign\b[ \t]+[^\n|]*", re.I)
hits = []
for t in targets:
    txt = open(t,"rb").read().decode("utf-8","replace")
    for m in re.finditer(r"^.*?(strehl(?:\.exe)?\s+align|\$exe\s+align|&\s*\$\w+\s+align|argmax)?.*$", "", re.M):
        pass
    for i, line in enumerate(txt.splitlines(), 1):
        if re.search(r"(strehl(\.exe)?[\"']?\s+align\b|\bexe\b[^\n]{0,30}\s+align\b|^\s*align\b)", line, re.I):
            has_out = "--out" in line
            hits.append((t, i, has_out, line.strip()[:160]))
print(f"total align-mentioning lines: {len(hits)}")
print()
print("=== IN EXPERIMENTS (executable) ===")
for t,i,o,l in hits:
    if t.startswith("experiments"):
        print(f"{'OUT ' if o else 'NOOUT'} {t}:{i}  {l}")
