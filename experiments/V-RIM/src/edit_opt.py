from pathlib import Path
P = Path(r"C:\dev\blog\death-of-software\projects\strehl\docs\research\V-RIM-verification.md")
t = P.read_text(encoding="utf-8")
OLD = """An optical veiling term belongs to the scene and the lens. It would appear in
every frame, most clearly in the sharp one. It is absent from the sharp one on
`coffee-bean` and from all ten on `flower-bud-alone-cpl`, including the frame of
true silhouette focus. **Therefore it is not optical.**"""
NEW = """An optical veiling term belongs to the scene and the lens. It would appear in
every frame, and most clearly in the sharp ones. It is absent from all six
usable frames of `coffee-bean` and all ten of `flower-bud-alone-cpl`, including
on each subject the frame of true silhouette focus. **Therefore it is not
optical.**"""
assert OLD in t, "ANCHOR NOT FOUND"
P.write_text(t.replace(OLD, NEW).rstrip("\n") + "\n", encoding="utf-8", newline="\n")
print("ok")
