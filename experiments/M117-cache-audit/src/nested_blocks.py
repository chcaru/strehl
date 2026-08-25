import pathlib, re
root = pathlib.Path(r"C:\dev\blog\death-of-software\projects\strehl\docs\research")
NESTED = ["STREHL_FIX_CA", "STREHL_SMOOTH_HUBER", "STREHL_SMOOTH"]
OFF = re.compile(r"STREHL_ALIGN\s*[=:]\s*[\"']?(0|off|false|no)\b", re.I)
ON  = re.compile(r"STREHL_ALIGN\s*[=:]\s*[\"']?(1|on|true|yes)\b", re.I)
def is_set(block, g):
    # a gate counts as SET only on a real assignment to a non-empty value
    return bool(re.search(re.escape(g) + r"\s*=\s*[\"']?[^\s\"'=]+", block))
def scan_block(b):
    out = []
    if OFF.search(b) and not ON.search(b):
        for g in NESTED:
            if is_set(b, g):
                out.append(g)
    return out
risk = []
for f in sorted(root.glob("*.md")):
    lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
    inb, start, buf = False, 0, []
    for i, ln in enumerate(lines, 1):
        if ln.lstrip().startswith("```"):
            if inb:
                for g in scan_block("\n".join(buf)):
                    risk.append((f.name, start, g))
                inb, buf = False, []
            else:
                inb, start = True, i
        elif inb:
            buf.append(ln)

# controls, both directions
pos = "STREHL_ALIGN=0\nSTREHL_FIX_CA=a7c2-fe100gm-2xtc-x4cpl\nstrehl stack x"
neg = "STREHL_ALIGN unset (ON)\nSTREHL_SMOOTH unset  STREHL_SMOOTH_HUBER unset\nthe PLANT arm differs only by STREHL_ALIGN=0"
assert scan_block(pos) == ["STREHL_FIX_CA"], "POSITIVE CONTROL FAILED: %r" % scan_block(pos)
assert scan_block(neg) == [], "NEGATIVE CONTROL FAILED: %r" % scan_block(neg)
print("controls: positive fires (%s), negative silent []" % scan_block(pos)[0])
print("\n=== corpus measurements with a nested gate SET while alignment OFF ===")
print("  " + (str(risk) if risk else "NONE - 0 reports"))
