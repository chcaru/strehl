import pathlib, re, json
root = pathlib.Path(r"C:\dev\blog\death-of-software\projects\strehl\docs\research")
NESTED = ["STREHL_FIX_CA", "STREHL_SMOOTH_HUBER", "STREHL_SMOOTH", "STREHL_CACHE_DIR"]
OFF = re.compile(r"STREHL_ALIGN\s*[=:]\s*[\"']?(0|off|false|no)\b", re.I)
hits, setters = [], {}
for f in sorted(root.glob("*.md")):
    txt = f.read_text(encoding="utf-8", errors="replace")
    for g in NESTED:
        if g in txt:
            setters.setdefault(f.name, []).append(g)
    for i, ln in enumerate(txt.splitlines(), 1):
        if OFF.search(ln):
            for g in NESTED:
                if g in ln:
                    hits.append((f.name, i, g, ln.strip()[:150]))
print("=== SAME-LINE co-occurrence: nested gate set while alignment OFF ===")
if hits:
    for h in hits:
        print("  %-34s L%-6d %s\n      %s" % h)
else:
    print("  NONE on any single line")
print("\n=== reports that set a nested gate anywhere (audit candidates) ===")
for k in sorted(setters):
    print("  %-36s %s" % (k, ", ".join(sorted(set(setters[k])))))
print("\ntotal reports naming a nested gate: %d" % len(setters))
