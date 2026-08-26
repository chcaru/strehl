import sys, io
P = r"C:\dev\strehl-out\V-HULLCOST\t8\crates\strehl-cli\src\merge_cmd.rs"
s = io.open(P, encoding="utf-8", newline="").read()
NL = "\r\n" if "\r\n" in s else "\n"
ANCHOR = NL.join([
 "                    if veil_on {",
 "                        e.enable_veil(",
 "                            veil_excess.as_deref().expect(\"refused above if absent\"),",
 "                            veil_cut,",
 "                            veil_margin,",
 "                            veil_floor,",
 "                        );",
 "                    }",
]) + NL
REPL = NL.join([
 "                    if veil_on {",
 "                        let _ = (&veil_excess, veil_cut, veil_margin, veil_floor);",
 "                        panic!(\"V-HULLCOST: veil path stubbed to fix a pre-existing \\",
 "                                compile break; no render in this audit may reach it\");",
 "                    }",
]) + NL
n = s.count(ANCHOR)
if n != 1:
    sys.exit("FATAL: veil anchor found %d times, expected exactly 1" % n)
s2 = s.replace(ANCHOR, REPL)
if s2 == s or REPL not in s2:
    sys.exit("FATAL: veil replacement did not land")
io.open(P, "w", encoding="utf-8", newline="").write(s2)
chk = io.open(P, encoding="utf-8", newline="").read()
if REPL not in chk or "e.enable_veil(" in chk:
    sys.exit("FATAL: post-write verification failed")
print("PLANT2 OK: veil call stubbed with panic!, anchor matched exactly 1x, verified on re-read")
