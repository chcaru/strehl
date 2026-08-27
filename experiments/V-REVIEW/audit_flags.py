"""Enumerate every CLI flag at the pin and count where its field is actually USED.
Commissioned on --exposure, which is independently known to be a no-op."""
import re, pathlib, collections
PIN = pathlib.Path(r"C:\dev\strehl-out\V-REVIEW\pin")
SRC = sorted(PIN.glob("crates/**/*.rs"))
TEXT = {p: p.read_text("utf8", errors="replace") for p in SRC}
main = TEXT[PIN/"crates/strehl-cli/src/main.rs"]

# --- carve the Stack { ... } variant out of the Command enum
i = main.index("\n    Stack {")
j, depth = main.index("{", i), 0
for k in range(j, len(main)):
    if main[k] == "{": depth += 1
    elif main[k] == "}":
        depth -= 1
        if depth == 0: end = k; break
block = main[j:end]

# --- fields: #[arg(...)] then  name: Type,
fields = []
for m in re.finditer(r"#\[arg\(([^\]]*)\)\]\s*\n\s*(?:pub\s+)?(\w+)\s*:\s*([^,]+),", block):
    attr, name, ty = m.group(1), m.group(2), m.group(3).strip()
    fm = re.search(r'long\s*=\s*"([^"]+)"', attr)
    flag = fm.group(1) if fm else name.replace("_", "-")
    if "long" not in attr and "short" not in attr: flag = "(positional)"
    fields.append((name, flag, ty))
print("flags parsed from the shipping Stack command: %d\n" % len(fields))

DEF_FILE = PIN/"crates/strehl-cli/src/main.rs"
def sites(name):
    out = []
    for p, t in TEXT.items():
        for n, line in enumerate(t.split("\n"), 1):
            if re.search(r"\b%s\b" % re.escape(name), line):
                s = line.strip()
                if s.startswith("///") or s.startswith("//"): continue    # doc/comment, not code
                out.append((p.relative_to(PIN).as_posix(), n, s))
    return out

print("%-22s %-22s %6s  %s" % ("field", "flag", "code", "verdict"))
print("-"*110)
rows = []
for name, flag, ty in fields:
    st = sites(name)
    # a site is "structural" if it is the declaration, a destructure, or a pass-through arg list
    real = [s for s in st if not (s[0].endswith("main.rs") and s[1] < 1200)]
    rows.append((name, flag, ty, st, real))
    v = "NO-OP SUSPECT" if len(real) == 0 else ("thin: %d" % len(real) if len(real) <= 2 else "")
    print("%-22s %-22s %6d  %s" % (name, "--"+flag if flag!="(positional)" else flag, len(st), v))

print("\n" + "="*110)
print("COMMISSIONING: --exposure is independently known to be a no-op. Does the detector see it?")
print("="*110)
for name, flag, ty, st, real in rows:
    if name in ("exposure", "auto_exposure", "srgb"):
        print("\n  %s  (--%s)  -- every non-comment code site in the shipping tree:" % (name, flag))
        for f, n, s in st: print("     %-42s:%-5d %s" % (f, n, s[:96]))
