"""M60 — the hand-drawn cell set.

Coordinates are green-sublattice (G1: rows 0::2, cols 1::2 of the RGGB CFA),
frame size 2344 x 3514. They were read off the coordinate-gridded renders in
`fig/05-grid-*.png` BY EYE, from the raw frames. Nothing here touches the focus
volume (AGENTS rule 17).

class:
  occ      a visible silhouette where a nearer element crosses in front of a
           farther TEXTURED one -- the reviewer's configuration
  occ_flat a silhouette whose background is the white card, i.e. UNTEXTURED.
           Kept as its own class because fact 73 says the operator has exactly
           zero focus discrimination there, so it is a prediction, not a nuisance
  ctl      a continuous surface with no depth discontinuity, textured
"""

CELLS = [
    # ---- bee-3 (299 frames, ISO 100) : occlusion over textured background ----
    ("bee-3", "occ3-wing-thorax", "occ", 120, 520, 620, 1220),
    ("bee-3", "occ3-leg-hair-1", "occ", 1150, 1550, 400, 900),
    ("bee-3", "occ3-leg-hair-2", "occ", 1400, 1800, 700, 1200),
    ("bee-3", "occ3-limb-abdomen", "occ", 950, 1350, 2900, 3400),
    ("bee-3", "occ3-antenna-head", "occ", 1400, 1800, 2700, 3200),
    ("bee-3", "occ3-antenna-eye", "occ", 1620, 1950, 2250, 2700),
    # ---- bee-3 : occlusion over the untextured white card --------------------
    ("bee-3", "occ3-leg-card-1", "occ_flat", 1450, 1900, 130, 560),
    ("bee-3", "occ3-claw-card", "occ_flat", 1800, 2100, 300, 750),
    ("bee-3", "occ3-leg-card-2", "occ_flat", 1750, 2150, 850, 1350),
    # ---- bee-3 : continuous surface ------------------------------------------
    ("bee-3", "ctl3-eye", "ctl", 1500, 1880, 1950, 2250),

    # ---- bee-1 (299 frames, ISO 100, different pose) --------------------------
    ("bee-1", "occ1-leg-body-1", "occ", 950, 1300, 700, 1200),
    ("bee-1", "occ1-leg-body-2", "occ", 1550, 1900, 1200, 1750),
    # occ1-leg-body-3 (1350-1700, 400-900) was drawn here and DROPPED after the
    # contact sheet showed it is blank card at every sampled frame -- there is no
    # limb and no background texture in it. Recorded, not silently deleted.
    ("bee-1", "occ1-limb-body-r", "occ", 300, 800, 2500, 3100),
    ("bee-1", "occ1-claw-card", "occ_flat", 1850, 2100, 300, 700),
    ("bee-1", "occ1-leg-card", "occ_flat", 1300, 1750, 60, 400),

    # ---- wrapped-text-1 (130 frames, ISO 100) : the no-discontinuity control --
    ("wrapped-text-1", "ctlw1-a", "ctl", 100, 500, 600, 1200),
    ("wrapped-text-1", "ctlw1-b", "ctl", 500, 900, 1200, 1800),
    ("wrapped-text-1", "ctlw1-c", "ctl", 800, 1150, 300, 900),
    ("wrapped-text-1", "ctlw1-d", "ctl", 800, 1150, 2000, 2600),
    ("wrapped-text-1", "ctlw1-e", "ctl", 1600, 2000, 700, 1300),
    ("wrapped-text-1", "ctlw1-f", "ctl", 1950, 2300, 1400, 2000),

    # ---- wrapped-text-2 (120 frames, ISO 400) : second framing, second ISO ----
    ("wrapped-text-2", "ctlw2-a", "ctl", 150, 550, 500, 1100),
    ("wrapped-text-2", "ctlw2-b", "ctl", 600, 1000, 1400, 2000),
    ("wrapped-text-2", "ctlw2-c", "ctl", 1500, 1900, 900, 1500),
    ("wrapped-text-2", "ctlw2-d", "ctl", 1950, 2300, 1800, 2400),
]

STACK_ISO = {
    "bee-1": 100.0, "bee-2": 400.0, "bee-3": 100.0,
    "wrapped-text-1": 100.0, "wrapped-text-2": 400.0,
    "109MSDCF": 160.0, "coffee-bean": 50.0,
}
