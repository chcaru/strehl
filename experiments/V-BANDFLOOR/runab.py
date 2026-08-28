import os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = r"C:\dev\strehl-out\V-BANDFLOOR"
tool = sys.argv[1]
subs = sys.argv[2:]
for s in subs:
    a = os.path.join(OUT, s + "__A-unset.tiff")
    b = os.path.join(OUT, s + "__B-coarse8.tiff")
    if not (os.path.exists(a) and os.path.exists(b)):
        print("MISSING %s" % s, flush=True); continue
    j = os.path.join(OUT, "%s__%s.json" % (s, tool))
    print("\n" + "=" * 78, flush=True)
    print("%s   %s   A=unset  B=1,8,8,8,8,8,8" % (tool.upper(), s), flush=True)
    print("=" * 78, flush=True)
    r = subprocess.run([sys.executable, os.path.join(HERE, tool + ".py"),
                        "--a", a, "--b", b, "--tag", s, "--json", j],
                       capture_output=True, text=True)
    print(r.stdout, flush=True)
    if r.returncode:
        print(r.stderr[-3000:], flush=True)
