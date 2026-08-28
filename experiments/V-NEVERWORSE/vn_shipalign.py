import io, os, re, glob, json
SHIP = r"C:\dev\strehl-out\acceptance\SHIP-V4"
AL = re.compile(r"alignment\s*:\s*(.+?)$", re.M)
PL = re.compile(r"(\d+)\s+placed\s*/\s*(\d+)\s+refused")
FR = re.compile(r"frames\s*:\s*(\d+) from")
COV = re.compile(r"scaled to ([0-9.]+)")
rows, off, noparse = [], [], []
for p in sorted(glob.glob(os.path.join(SHIP, "*.log"))):
    subj = os.path.basename(p).replace("--SHIP-V4.log", "")
    t = io.open(p, encoding="utf-8", errors="replace").read()
    a = AL.search(t); f = FR.search(t); c = COV.search(t)
    n = int(f.group(1)) if f else None
    if not a:
        noparse.append(subj); continue
    line = a.group(1)
    if line.strip().startswith("OFF") or line.strip().startswith("REFUSED"):
        off.append((subj, n)); continue
    m = PL.search(line)
    if not m:
        noparse.append(subj); continue
    placed, refused = int(m.group(1)), int(m.group(2))
    rows.append(dict(subject=subj, frames=n, placed=placed, refused=refused,
                     cover=float(c.group(1)) if c else None))
print("%-26s %6s %7s %8s %7s" % ("subject", "frames", "placed", "refused", "cover"))
for r in sorted(rows, key=lambda r: -r["refused"]):
    print("%-26s %6d %7d %8d %7s" % (r["subject"], r["frames"], r["placed"], r["refused"], r["cover"]))
print()
print("aligned subjects        : %d" % len(rows))
print("alignment OFF           : %d %s" % (len(off), [s for s, _ in off]))
print("UNPARSED (not examined) : %d %s" % (len(noparse), noparse))
print("TOTAL logs found        : %d" % (len(rows) + len(off) + len(noparse)))
print("subjects with refusals  : %d" % sum(1 for r in rows if r["refused"] > 0))
print("total frames placed     : %d" % sum(r["placed"] for r in rows))
print("total frames refused    : %d" % sum(r["refused"] for r in rows))
json.dump(rows, io.open(r"C:\dev\strehl-out\V-NEVERWORSE\dilute\shipalign.json", "w", encoding="utf-8"), indent=1)

