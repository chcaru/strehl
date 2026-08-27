import re, pathlib, subprocess
PIN = pathlib.Path(r"C:\dev\strehl-out\V-REVIEW\pin")
RS  = sorted(PIN.glob("crates/**/*.rs"))
SHIP = [p for p in RS if "/examples/" not in p.as_posix() and "/tests/" not in p.as_posix()]
TXT = {p: p.read_text("utf8","replace") for p in RS}
helptxt = pathlib.Path(r"C:\dev\strehl-out\V-REVIEW\help\stack.txt").read_text("utf8","replace")

def code_lines(t):
    return [L for L in t.split("\n") if not L.strip().startswith(("///","//!","//"))]

READ, MENTION = {}, {}
for p,t in TXT.items():
    ship = p in SHIP
    for L in t.split("\n"):
        for v in re.findall(r"STREHL_[A-Z0-9_]+", L):
            s=L.strip()
            if s.startswith(("///","//!","//")): MENTION.setdefault(v,set()).add(p.name)
            elif re.search(r'(env::var|var_os|env!)\s*\(\s*"?%s' % v, L) or ('"%s"'%v) in L:
                READ.setdefault(v,set()).add((p.name, ship))
            else: MENTION.setdefault(v,set()).add(p.name)

allv = sorted(set(READ)|set(MENTION))
print("="*104); print("ENVIRONMENT VARIABLES: read by the SHIPPING binary vs merely mentioned"); print("="*104)
print("  %-30s %-10s %-10s %s" % ("variable","in ship","in help","files that read it"))
print("  "+"-"*100)
for v in allv:
    r = READ.get(v,set())
    ship = any(s for _,s in r)
    inhelp = v in helptxt
    files = ",".join(sorted({n for n,_ in r})) or "-"
    flag = ""
    if inhelp and not ship: flag = "  <== DOCUMENTED IN --help BUT NEVER READ BY SHIPPING CODE"
    print("  %-30s %-10s %-10s %s%s" % (v, "yes" if ship else "NO", "yes" if inhelp else "no", files, flag))

print("\n"+"="*104); print("STREHL_SOFT_GATE: is softgate.rs reachable in the shipping binary?"); print("="*104)
sg = PIN/"crates/strehl-core/src/softgate.rs"
print("  softgate.rs at the pin: %d lines" % len(sg.read_text('utf8','replace').split("\n")))
for p,t in TXT.items():
    for i,L in enumerate(t.split("\n"),1):
        if "softgate" in L and not L.strip().startswith(("///","//")):
            print("    %-28s:%-5d %s" % (p.name,i,L.strip()[:88]))

print("\n"+"="*104); print("STATED DEFAULTS vs the actual constants"); print("="*104)
consts={}
for p,t in TXT.items():
    for m in re.finditer(r"pub const (DEFAULT_[A-Z0-9_]+|[A-Z0-9_]*GATE[A-Z0-9_]*)\s*:\s*([^=]+)=\s*([^;]+);", t):
        consts[m.group(1)]=(p.name, m.group(3).strip().replace("\n"," ")[:60])
for k,(f,v) in sorted(consts.items()):
    print("  %-34s = %-42s (%s)" % (k,v,f))
