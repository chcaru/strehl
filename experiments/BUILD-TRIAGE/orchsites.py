"""ORCH's per-subject best-resolved site, transcribed from the labelled
navigation sheet at C:\\dev\\strehl-out\\ORCH-DETAIL\\detail-sheet.png
(tool: experiments/ORCH-drift-check/detailgallery.py).

WHY THIS FILE EXISTS
--------------------
BUILD-TRIAGE's own site selectors (compare.py: DETAIL / TRANSITION / FLAT /
SOURCE-BEST / DEFICIT) choose sites by *gradient percentile within the merge*.
FLAT and DEFICIT are chosen to be the EMPTIEST sites in the frame.  That is the
correct design for the headline "does the merge ever lose" question, because a
deficit at an empty site is gated out by min-arm-SNR.

It is the WRONG design for CLASSIFICATION.  A subject whose four windows all
landed on background reads as "no detail in either arm anywhere" -- which is
indistinguishable, in the output, from a genuine capture limit.  That is exactly
how `highly-angled-ruler-mm-cpl` was wrongly classified as a coverage gap:

    my windows            (6197,512) and (512,1502)  -- corners, 22-29 DN/px
                          against a 13-17 DN noise floor.  frame SNR ~1.4.
    ORCH's window         (3808,3808) -- merge 1487.2 vs frame 775.5 DN/px,
                          frame SNR 12.1, merge AHEAD by 1.92x.

ORCH independently warned about precisely this failure mode after hitting it
with throughfocus_probe.py: "It caught me placing a probe window on blank
background and reading the resulting flatness as 'capture-limited' -- the
reading was right and the window was wrong."

So these coordinates are used as an INDEPENDENT, SUBJECT-OPTIMAL window: chosen
by a different tool, by a different agent, on a different statistic (mean
|laplacian| on a coarse grid) than any selector in this directory.  Agreement
between two independent site pickers is worth more than either alone.

COORDINATE CONVENTION
---------------------
The sheet prints `y=<Y> x=<X>` for each subject.  Every value is congruent to
64 mod 200, i.e. these are coarse-grid points, and they are the ORIGIN of the
800x800 tile, not its centre.  Proof: flowers-cpl is x=64; an 800px tile
*centred* there would span x=-336..464, which is off the master.  As origins
every tile lands inside every master.  Hence centre = origin + 400, and that is
what site_xy() returns -- confirmed empirically on highly-angled-ruler-mm-cpl,
where origin+400 gave ncc=0.744 and the bare origin gave ncc=0.138.

CAVEAT ON THE DN COLUMN (recorded because ORCH asked for it explicitly, and
because it bears directly on the pale-flower question)
------------------------------------------------------
`detail_dn` is ORCH's in-tile mean |laplacian| in linear DN.  ORCH states its
limitation in its own words: it "conflates *contrast* with *sharpness* -- it
cannot separate them ... A subject can be perfectly stacked and still score low
here."  A white filament on a white petal and a blurred white filament on a
white petal both score low.  So a low detail_dn is a place to LOOK, never a
verdict.  The verdict needs the through-focus SHAPE (sitescan.py), which is
scale-free in exactly the way this amplitude is not.
"""

# subject -> (rank, detail_dn, x_origin, y_origin)
ORCH_DETAIL = {
    "flat-on-ruler-cpl":                    (1,  3044, 4464,   64),
    "tweezers-cpl":                         (2,  2881, 2064, 2464),
    "coffee-bean":                          (3,  2332, 2864,  864),
    "wrapped-text-2":                       (4,  2186, 3664, 1664),
    "112MSDCF":                             (5,  2158, 4064,  864),
    "bee-1-cpl":                            (6,  2154, 4064, 1264),
    "113MSDCF":                             (7,  1989, 4064,  864),
    "wrapped-text-1":                       (8,  1968, 4864, 1264),
    "pencil-steep-angle-cpl":               (9,  1844, 1664, 2464),
    "coffee-bubbles":                       (10, 1806, 3264, 1664),
    "lavendar-cpl":                         (11, 1622, 2064, 2864),
    "bee-2-cpl":                            (12, 1592, 3264, 1264),
    "bee-3-cpl":                            (13, 1404, 3664, 2464),
    "pencil-flatter-angle-cpl":             (14, 1372, 1664, 2064),
    "highly-angled-ruler-mm-cpl":           (15, 1364, 3664, 3664),
    "foam":                                 (16, 1350, 3664, 2464),
    "leaf-2-cpl":                           (17, 1281, 3664, 2064),
    "couch-fibers-cpl":                     (18, 1247,  464, 3264),
    "dry-erase-marker-head-cpl":            (19, 1177, 2464, 1664),
    "flower-bud-with-background-fern-cpl":  (20, 1066, 4464,  864),
    "lead-1-cpl":                           (21,  961, 3664, 1664),
    "109MSDCF":                             (22,  705, 4064, 1664),
    "119MSDCF":                             (23,  602, 3664, 2064),
    "flower-bud-alone-cpl":                 (24,  594, 2864,  864),
    "flowers-cpl":                          (25,  507,   64, 2464),
    "flower-inner-edge-cpl":                (26,  406, 2864,  864),
}

TILE = 800


def site_xy(subject):
    """Centre of ORCH's best-resolved tile, as (x, y)."""
    _, _, x, y = ORCH_DETAIL[subject]
    return x + TILE // 2, y + TILE // 2


def subjects_by_rank():
    return sorted(ORCH_DETAIL, key=lambda s: ORCH_DETAIL[s][0])


if __name__ == "__main__":
    print(f"{'#':>3} {'subject':<38} {'detailDN':>8}  {'site(x,y)':>13}")
    for s in subjects_by_rank():
        rank, dn, _, _ = ORCH_DETAIL[s]
        x, y = site_xy(s)
        print(f"{rank:>3} {s:<38} {dn:>8}  {x:>6},{y:<6}")
    print(f"\n{len(ORCH_DETAIL)} subjects")
