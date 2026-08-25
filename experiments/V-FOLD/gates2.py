import re,glob,sys
sys.stdout.reconfigure(encoding="utf-8",errors="replace")
for name in ["STREHL_SOFT_GATE","STREHL_SMOOTH","STREHL_SMOOTH_HUBER","STREHL_ROBUST_ELECTION","STREHL_PHOTOMETRIC","STREHL_ALIGN"]:
    for p in glob.glob("crates/**/*.rs",recursive=True):
        if "tests" in p: continue
        lines=open(p,encoding="utf-8",errors="replace").read().split("\n")
        for i,l in enumerate(lines):
            if '"'+name+'"' in l:
                print(f"### {name}  {p}:{i+1}")
                for k in range(max(0,i-8), min(len(lines), i+14)):
                    print("   %4d %s"%(k+1, lines[k]))
                print()
