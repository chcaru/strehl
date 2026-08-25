import re,os,sys,glob
sys.stdout.reconfigure(encoding="utf-8",errors="replace")
files=[p for p in glob.glob("crates/**/*.rs",recursive=True)]
prod=[p for p in files]
env=set()
for p in prod:
    t=open(p,encoding="utf-8",errors="replace").read()
    for m in re.finditer(r'"(STREHL_[A-Z0-9_]+)"', t):
        env.add(m.group(1))
    for m in re.finditer(r'(?:const|static)\s+\w+\s*:\s*&?str\s*=\s*"(STREHL_[A-Z0-9_]+)"', t):
        env.add(m.group(1))
print("STREHL_* env names found in crates/**.rs:")
for e in sorted(env): print("  ",e)
print()
print("=== occurrences with 5 lines of context for default direction")
for e in sorted(env):
    for p in prod:
        lines=open(p,encoding="utf-8",errors="replace").read().split("\n")
        for i,l in enumerate(lines):
            if '"'+e+'"' in l:
                seg="\n".join("      %d: %s"%(i+1+k-2,lines[i-2+k].strip()) for k in range(0,7) if 0<=i-2+k<len(lines))
                print(f"-- {e}  {p}:{i+1}")
                print(seg)
