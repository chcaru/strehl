"""Emit the dust arm of the canonical map as a Rust string constant.

Default-ON means the correction must apply with no environment variable set, so
the map has to travel inside the binary rather than beside it. Only the DUST arm
is embedded: the hot arm is 14,626 sites and M101 measured it to be an
immaterial null on this body, so compiling it in would spend 300 KB of binary to
move nothing.

The emitted text is a complete, parseable sidecar in the v2 format -- magic,
geometry, the `coords` key, `hot 0`, the dust records, `end` -- so the embedded
path and the `STREHL_DEFECT_MAP` path go through exactly the same parser and
cannot drift.
"""
import os

SRC = os.path.join(os.path.dirname(__file__), "..", "out",
                   "defect-map-ILCE-7CM2-photo.txt")

hdr = {}
dust = []
with open(SRC) as f:
    for line in f:
        p = line.split()
        if not p:
            continue
        if p[0] in ("camera", "sensor", "covered", "aperture"):
            hdr[p[0]] = " ".join(p[1:])
        elif p[0] == "d":
            dust.append((int(p[1]), int(p[2]), float(p[3])))

print("header:", hdr)
print("dust records:", len(dust))
gains = [g for _, _, g in dust]
print("gain range: %.6f .. %.6f" % (min(gains), max(gains)))

body = ["strehl-defect-map 2",
        "camera %s" % hdr["camera"],
        "sensor %s" % hdr["sensor"],
        "covered %s" % hdr["covered"],
        "coords active",
        "aperture %s" % hdr["aperture"],
        "# Embedded canonical dust map for the A7C II this project was built on.",
        "# Built by experiments/BUILD-DEFECT from 160 flat fields; the two motes it",
        "# nominates were confirmed on subject frames at p = 0.0025 (BUILD-DEFECT.md",
        "# S2, S11). The hot arm is omitted: M101 measured it immaterial on this body.",
        "# Coordinates index the ACTIVE area (rawpy raw_image_visible), not the full",
        "# decoder buffer -- see the `coords` key, which the reader requires.",
        "hot 0"]
body.append("dust %d" % len(dust))
for x, y, g in dust:
    body.append("d %d %d %s" % (x, y, repr(round(g, 6))))
body.append("end")
text = "\n".join(body) + "\n"

out = os.path.join(os.path.dirname(__file__), "..", "out", "embedded-dust-map.rs.txt")
with open(out, "w", newline="\n") as f:
    f.write(text)
print("wrote %s: %d bytes, %d lines" % (out, len(text), len(body)))
