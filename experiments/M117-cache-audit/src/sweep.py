import os, re, glob
roots = [r"C:\dev\blog\death-of-software\projects\strehl", r"C:\dev\strehl-out",
         os.path.join(os.environ["LOCALAPPDATA"], "strehl", "warpmaps")]
found = []
for root in roots:
    for dp, dn, fn in os.walk(root):
        if "\\target\\" in dp or "\\.git" in dp: continue
        for f in fn:
            if not f.endswith(".txt"): continue
            p = os.path.join(dp, f)
            try:
                head = open(p, "rb").read(1200).decode("utf-8","replace")
            except Exception: continue
            if not head.startswith("strehl-warpmap"): continue
            m_f = re.search(r"^frames (\d+)", head, re.M)
            m_r = re.search(r"^reference (\d+)", head, re.M)
            m_s = re.search(r"^resampler (\S+)", head, re.M)
            m_n = re.search(r"^note (.*)$", head, re.M)
            if not (m_f and m_r): continue
            n, ref = int(m_f.group(1)), int(m_r.group(1))
            found.append((p, n, ref, m_s.group(1) if m_s else "?", (m_n.group(1) if m_n else "")[:60]))
print(f"warp sidecars found: {len(found)}")
bad = [x for x in found if x[2] != x[1]//2]
print(f"reference != n/2 (poisoning-shaped): {len(bad)}")
for p,n,ref,rs,note in sorted(bad, key=lambda x:x[0]):
    print(f"  n={n:4d} ref={ref:4d} (merge would use {n//2:4d})  resampler={rs:12s}  {p}")
odd = [x for x in found if x[3] not in ("catmull-rom","?")]
print(f"\nresampler != catmull-rom: {len(odd)}")
for p,n,ref,rs,note in odd: print(f"  {rs:12s} n={n} ref={ref}  {p}")
oddspan = [x for x in found if "spans [1, 2, 4, 8, 16, 32, 64, 96, 128]" not in x[4] and x[4]]
print(f"\nnon-default spans: {len(oddspan)}")
for p,n,ref,rs,note in oddspan: print(f"  {note}  n={n} ref={ref}  {p}")
