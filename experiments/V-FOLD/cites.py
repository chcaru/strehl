import re, json, os, glob
f = json.load(open("experiments/V-FOLD/facts.json",encoding="utf-8"))
nums = set(int(k) for k in f)
def collapse(s): return re.sub(r"\s+"," ",s)
cites = {}
def scan(path):
    try: t = open(path,encoding="utf-8",errors="replace").read()
    except: return
    t = collapse(t)
    for m in re.finditer(r"\bfacts?\s+([0-9,\s\u2013\-and]+)", t, re.I):
        seg = m.group(1)
        for mm in re.finditer(r"\d{3,4}", seg):
            n = int(mm.group(0))
            if n in nums: cites.setdefault(n,set()).add(path)
scan("docs/captures-needed.md")
capt = {n:v for n,v in cites.items()}
print("captures-needed.md cites facts in range:", sorted(capt))
cites2 = {}
def scan2(path):
    try: t = open(path,encoding="utf-8",errors="replace").read()
    except: return
    t = collapse(t)
    for m in re.finditer(r"\bfacts?\s+([0-9,\s\u2013\-and]+)", t, re.I):
        for mm in re.finditer(r"\d{3,4}", m.group(1)):
            n = int(mm.group(0))
            if n in nums: cites2.setdefault(n,set()).add(path)
for p in glob.glob("crates/**/*.rs", recursive=True):
    scan2(p)
print("crates cites facts in range:", {k:sorted(v) for k,v in sorted(cites2.items())})
