from pathlib import Path

P = Path(r"C:\dev\blog\death-of-software\projects\strehl\docs\research\V-RIM-verification.md")
t = P.read_text(encoding="utf-8")

ANCHOR = "## Defects found in my own instruments, disclosed"

INS = """## Sections 13 and 15 landed while this was being measured

This verification is pinned to section 12 at commit `eff23fb`. Sections 13, 14
and 15 were committed to `ORCH-veiling.md` while the sweep was running. Two of
them touch C1, and neither changes the verdict:

- **Section 13** already impeaches the −36.5% / −38.2% target, by a completely
  different route: an extremum estimator is biased upward by construction, and
  a +169 DN additive bias is invisible to an error-and-ratio measurement. That
  is an argument that the number may be *contaminated*. Mine is a measurement
  that the number is *not a property of the scene*. They are independent and
  they agree.
- **Section 15** reports a two-reference bug in `rimprofile.py`: the encoded
  table normalised to the outermost bin at d = 550 px, itself inside the
  artifact, while the linear table used the far field. Section 12's numbers come
  from the linear table, so they are not directly affected. But it is the same
  failure mode as my attack 5 — the reported quantity moving with an unexamined
  choice of zero — found twice in one instrument by two parties who were not
  talking to each other. That is worth more than either finding alone.

Nothing in 13, 14 or 15 withdraws C1 or C2, so section 12 still stands as
written and this document is still the test of it.

"""

assert ANCHOR in t, "ANCHOR NOT FOUND"
t = t.replace(ANCHOR, INS + ANCHOR)
P.write_text(t.rstrip("\n") + "\n", encoding="utf-8", newline="\n")
print("ok, lines:", t.count("\n"))
