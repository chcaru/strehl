"""Correct my own first attempt.

I restricted the FAR FIELD to the dominant component's Voronoi cell as well as
the near bands. That was wrong on two counts, both measured:

  * It starved the reference. `lead-1-cpl` reaches 1766 px yet got 0 far-field
    px inside the cell, and `leaf-2-cpl` got 1101 against a need of 1250 -- so
    the subjects the Voronoi restriction was built to rescue became
    unmeasurable for a NEW reason instead.
  * It moved every already-passing subject, because changing the reference
    level shifts all seven bands together: bee-2-cpl -4273.0 -> -2477.0.

The far field is a GLOBAL REFERENCE LEVEL -- background far from the whole
subject. Only the outward WALK has to stay inside one part's territory, which
is what the gap-crossing concern is actually about. So: near bands restricted,
far field not.
"""
import io

PATH = r"C:\dev\blog\death-of-software\projects\strehl\experiments\ORCH-drift-check\halo_profile.py"
src = io.open(PATH, encoding="utf-8").read()

EDITS = [
    ("    far = own & (d >= FAR[0]) & (d < FAR[1])\n"
     "    nfar = int(far.sum())\n"
     "    if nfar < MIN_FARPX // (sub * sub):\n"
     "        return (\"UNMEASURABLE\", None, None, None, None, None,\n"
     "                \"far field only %d px within the dominant part's cell, need %d \"\n"
     "                \"(subject reaches %.0f px)\"\n"
     "                % (nfar, MIN_FARPX // (sub * sub), float(d.max())))",
     "    # THE FAR FIELD IS NOT RESTRICTED TO THE CELL. It is a global reference\n"
     "    # level -- background far from the whole subject -- and starving it by\n"
     "    # intersecting with one part's cell both broke the fibrous subjects this\n"
     "    # restriction exists to rescue and shifted every already-passing subject,\n"
     "    # because moving the reference moves all seven bands together. Only the\n"
     "    # outward WALK has to stay inside one part's territory.\n"
     "    far = (d >= FAR[0]) & (d < FAR[1])\n"
     "    nfar = int(far.sum())\n"
     "    if nfar < MIN_FARPX // (sub * sub):\n"
     "        return (\"UNMEASURABLE\", None, None, None, None, None,\n"
     "                \"far field only %d px, need %d (subject reaches %.0f px)\"\n"
     "                % (nfar, MIN_FARPX // (sub * sub), float(d.max())))"),
]
for a, b in EDITS:
    if a not in src:
        raise SystemExit("ANCHOR NOT FOUND:\n%s" % a[:200])
    src = src.replace(a, b, 1)

with io.open(PATH, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(src)
print("patched far-field scope")
