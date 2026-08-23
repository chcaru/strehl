import os, re, io, json, collections

proj = r"C:\dev\blog\death-of-software\projects\strehl"
root = os.path.join(proj, "crates")

pat_multi = re.compile(r"(?i)\bfacts?\s+((?:\d+)(?:\s*(?:[-/,]|and|to|&)\s*\d+)*)")
pat_test  = re.compile(r"(?i)fact_(\d+)")
pat_m     = re.compile(r"(?i)\bM(\d+)\s+facts?\s+(\d+)")

cites = []
for dirpath, dirnames, filenames in os.walk(root):
    if "target" in dirpath.split(os.sep): continue
    for fn in sorted(filenames):
        if not fn.endswith(".rs"): continue
        p = os.path.join(dirpath, fn)
        rel = os.path.relpath(p, proj).replace("\\","/")
        lines = io.open(p, encoding="utf-8").read().split("\n")
        for i, line in enumerate(lines, 1):
            nums = set()
            for m in pat_multi.finditer(line):
                for n in re.findall(r"\d+", m.group(1)):
                    nums.add(int(n))
                # expand ranges like 509-511
                g = m.group(1)
                for rm in re.finditer(r"(\d+)\s*-\s*(\d+)", g):
                    a,b = int(rm.group(1)), int(rm.group(2))
                    if b>a and b-a < 20:
                        for k in range(a,b+1): nums.add(k)
            for m in pat_test.finditer(line):
                nums.add(int(m.group(1)))
            for n in sorted(nums):
                cites.append({"file":rel,"line":i,"num":n,"text":line.strip()})

print("citation instances:", len(cites))
print("distinct numbers:", len(set(c["num"] for c in cites)))
print("numbers:", sorted(set(c["num"] for c in cites)))
byfile = collections.Counter(c["file"] for c in cites)
for f,c in sorted(byfile.items()): print(f"{c:4d}  {f}")
json.dump(cites, io.open(os.path.join(proj,"experiments","M56-citations","cites.json"),"w",encoding="utf-8"), indent=1)
