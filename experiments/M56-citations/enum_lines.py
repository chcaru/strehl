import os, re, json, io

root = r"C:\dev\blog\death-of-software\projects\strehl\crates"
rows = []
for dirpath, dirnames, filenames in os.walk(root):
    if "target" in dirpath.split(os.sep):
        continue
    for fn in filenames:
        if not fn.endswith(".rs"):
            continue
        p = os.path.join(dirpath, fn)
        rel = os.path.relpath(p, r"C:\dev\blog\death-of-software\projects\strehl")
        with io.open(p, encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                if re.search(r"fact", line, re.I):
                    rows.append((rel, i, line.rstrip("\n")))

print("TOTAL LINES:", len(rows))
for rel, i, line in rows:
    print(f"{rel}:{i}: {line.strip()}")
