import re,glob,os,json
f=json.load(open("experiments/V-FOLD/facts.json",encoding="utf-8"))
nums=set(int(k) for k in f)
def collapse(s): return re.sub(r"\s+"," ",s)
pats=[r"\bfacts?\s*#?\s*([0-9]{3,4})", r"\bF\s?([0-9]{3,4})\b", r"SYNTHESIS[^.\n]{0,40}?([0-9]{3,4})", r"\bfacts?\s*([0-9]{3,4})\s*[-\u2013]\s*([0-9]{3,4})"]
def scan(path):
    hits=set()
    try: t=collapse(open(path,encoding="utf-8",errors="replace").read())
    except: return hits
    for m in re.finditer(r"\bfacts?\s*#?\s*([0-9]{3,4})(?:\s*[-\u2013,]\s*([0-9]{3,4}))?", t, re.I):
        a=int(m.group(1)); b=int(m.group(2)) if m.group(2) else a
        if b>=a and b-a<40:
            for n in range(a,b+1):
                if n in nums: hits.add(n)
        else:
            if a in nums: hits.add(a)
            if b in nums: hits.add(b)
    return hits
h=scan("docs/captures-needed.md")
print("captures-needed:", sorted(h))
allc={}
for p in glob.glob("crates/**/*.rs",recursive=True):
    hh=scan(p)
    for n in hh: allc.setdefault(n,set()).add(p)
print("crates:", {k:sorted(v) for k,v in sorted(allc.items())})
