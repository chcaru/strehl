import sys, io
P = r"C:\dev\strehl-out\V-HULLCOST\t8\crates\strehl-core\src\pyramid.rs"
s = io.open(P, encoding="utf-8", newline="").read()
NL = "\r\n" if "\r\n" in s else "\n"
print("line ending detected:", repr(NL))
ANCHOR = "            hull: Hull::InputRange," + NL
REPL = NL.join([
    "            hull: match std::env::var(\"STREHL_VHULLCOST_HULL\") {",
    "                Ok(ref s) if s == \"unclamped\" => Hull::Unclamped,",
    "                Ok(ref s) if s == \"clamped\" => Hull::InputRange,",
    "                Ok(ref s) => panic!(\"V-HULLCOST: bad STREHL_VHULLCOST_HULL={s}\"),",
    "                Err(_) => Hull::InputRange,",
    "            },",
    "",
])
n = s.count(ANCHOR)
if n != 1:
    sys.exit("FATAL: anchor found %d times, expected exactly 1" % n)
s2 = s.replace(ANCHOR, REPL)
if s2 == s or REPL not in s2:
    sys.exit("FATAL: replacement did not land")
io.open(P, "w", encoding="utf-8", newline="").write(s2)
chk = io.open(P, encoding="utf-8", newline="").read()
assert REPL in chk, "FATAL: not present after write"
assert chk.count("STREHL_VHULLCOST_HULL") == 4, "FATAL: wrong env-var count %d" % chk.count("STREHL_VHULLCOST_HULL")
print("PLANT OK: anchor matched 1x, replacement verified on re-read")
