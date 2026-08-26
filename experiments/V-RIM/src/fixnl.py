from pathlib import Path
P = Path(r"C:\dev\blog\death-of-software\projects\strehl\docs\research\V-RIM-verification.md")
t = P.read_text(encoding="utf-8")
P.write_text(t.rstrip("\n") + "\n", encoding="utf-8", newline="\n")
print("fixed")
