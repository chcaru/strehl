import re, pathlib
R = pathlib.Path(r"C:\dev\strehl-out\DELIVER-V5\full-resolution\README.md")
T = R.read_text("utf8","replace"); L = T.split("\n")
print("README: %s  (%d lines)" % (R, len(L)))
COMP = re.compile(r"enfuse|focus-stack|Helicon|Zerene|Photoshop|comparator", re.I)
SUBJ = re.compile(r"\b(113|112|119|109)MSDCF\b|coffee-bubbles|foam|bee-3|flower|leaf|lead-|couch|ruler|tweezers|subject", re.I)
FRAM = re.compile(r"\b\d+[- ]frame|\bframes\b|\bN\s*=\s*\d+", re.I)
RATIO= re.compile(r"(?<![\w.])(\d+\.\d+)\s*(x|×)(?!\w)")
DIRN = re.compile(r"cleaner|noisier|sharper|softer|better|worse|less|more|lower|higher|faster|slower|than", re.I)

def ctx(i, n=2):
    return " ".join(x.strip() for x in L[max(0,i-n):min(len(L),i+n+1)])

print("\n" + "="*100)
print("A. RATIOS WHOSE DIRECTION IS NOT STATED IN THEIR OWN NEIGHBOURHOOD")
print("="*100)
bad=0
for i,line in enumerate(L):
    if line.strip().startswith(("#","```")): continue
    for m in RATIO.finditer(line):
        c = ctx(i)
        if not DIRN.search(c):
            bad+=1; print("  L%-4d %s" % (i+1, line.strip()[:104]))
print("  ratios with no direction word nearby: %d" % bad)

print("\n" + "="*100)
print("B. RATIO LINES THAT NAME NO COMPARATOR / NO SUBJECT / NO FRAME COUNT (within +/-2 lines)")
print("="*100)
miss=[]
for i,line in enumerate(L):
    if line.strip().startswith(("#","```")): continue
    if not RATIO.search(line): continue
    c=ctx(i)
    lack=[n for n,rx in (("comparator",COMP),("subject",SUBJ),("frames",FRAM)) if not rx.search(c)]
    if lack: miss.append((i+1,line.strip()[:88],lack))
for n,s,lack in miss[:22]: print("  L%-4d %-88s  missing: %s" % (n,s,",".join(lack)))
print("  total ratio lines missing at least one attribution: %d" % len(miss))

print("\n" + "="*100)
print("C. DOES THE README PRESENT ANY FEATURE THE BINARY DOES NOT DELIVER?")
print("="*100)
for pat,label in [(r"--exposure","--exposure (VERIFIED no-op on pixels)"),
                  (r"--auto-exposure","--auto-exposure (moves 0.075% of px only)"),
                  (r"STREHL_SOFT_GATE|soft.gate","soft gate (never ran on 26/26; panics on bad value)"),
                  (r"\bestimator\b.{0,40}default|default.{0,40}\bestimator\b","'estimator is the default' (FALSE)")]:
    hits=[(i+1,l.strip()[:96]) for i,l in enumerate(L) if re.search(pat,l,re.I)]
    print("  %-52s %d mention(s)" % (label,len(hits)))
    for n,s in hits[:4]: print("      L%-4d %s" % (n,s))

print("\n" + "="*100)
print("D. BAND NUMBERS WITHOUT A NAMED BAND")
print("="*100)
bn=[(i+1,l.strip()[:96]) for i,l in enumerate(L)
    if re.search(r"\bband\b",l,re.I) and re.search(r"\d",l) and not re.search(r"band\s*(\d|B\d|[0-6]|coarse|fine|base)",l,re.I)]
print("  suspect lines: %d" % len(bn))
for n,s in bn[:10]: print("      L%-4d %s" % (n,s))
