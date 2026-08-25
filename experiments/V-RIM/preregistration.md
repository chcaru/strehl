# V-RIM pre-registration: silhouette morphology classes for the n=26 test

Status: PRE-REGISTERED. Written and committed BEFORE any ring number was
computed on any subject other than the two already in ORCH-veiling section 12.

Author: V-RIM (independent verifier). Written 2026-08-25.

## Why this file exists

Section 12 of `docs/research/ORCH-veiling.md` claims C2: the bright ring near a
silhouette appears **only where the silhouette carries a fine fringe**. The
evidence offered is two subjects. Two subjects is an anecdote, and the
classification of those two was made by the same person who read their ring
numbers.

To test C2 at n=26 the classification has to be fixed before the numbers exist,
otherwise the correlation can be manufactured by relabelling the exceptions.
This file is that fix. It was written from the viewing JPEGs in
`C:\dev\strehl-out\gallery-1cacb61\` alone. No linear render other than
coffee-bean and flower-bud-alone-cpl had been profiled when it was committed.

## Inclusion rule, applied before measurement

A subject is MEASURABLE if and only if all three hold on its gallery JPEG:

- **I1.** A single dominant opaque object is silhouetted against a visually
  smooth backdrop, meaning a sweep, paper or defocused field that carries no
  subject detail of its own.
- **I2.** That backdrop is a contiguous region of roughly a fifth of the frame
  or more, so a far-field reference away from the object exists at all.
- **I3.** The object-versus-backdrop boundary runs for a substantial part of
  the frame, rather than clipping one corner.

Otherwise the subject is EXCLUDED, with one of three stated reasons:

- **FILL** — the object fills the frame and there is no backdrop to profile.
- **PLANAR** — a flat surface whose markings lie in the surface, so there is no
  object-versus-backdrop silhouette at all.
- **NO-DOMINANT** — many small objects and no single dominant silhouette.

## Morphology classes, applied before measurement

Judged on the object-versus-backdrop boundary only, never on internal texture:

- **FRINGED** — fine projecting structures such as hairs, trichomes, bristles
  or filaments along roughly a third or more of the boundary.
- **SMOOTH** — a clean curve or line with no projecting fine structure.
- **INTERMEDIATE** — fringe over a minority of the boundary, or coarse
  irregularity that is not a fine fringe.

## The prediction under test

C2 predicts ring prominence is high on FRINGED and near zero on SMOOTH. The
two anchors already published are coffee-bean at 0.23 percent (SMOOTH) and
flower-bud-alone-cpl at 12.0 percent (FRINGED). C2 survives if the FRINGED
group sits well above the SMOOTH group across the whole corpus, and fails if
the groups overlap.

## The classification

| subject | verdict | class | note |
| --- | --- | --- | --- |
| 109MSDCF | MEASURABLE | SMOOTH | paint strokes, white paper backdrop |
| 112MSDCF | EXCLUDED FILL | — | dendrites, dense fill, no backdrop |
| 113MSDCF | EXCLUDED FILL | — | dendrites, dense fill, no backdrop |
| 119MSDCF | MEASURABLE | SMOOTH | same scene as 109MSDCF, tighter crop |
| bee-1-cpl | MEASURABLE | FRINGED | dense hair over the whole outline |
| bee-2-cpl | MEASURABLE | FRINGED | dense hair over the whole outline |
| bee-3-cpl | MEASURABLE | FRINGED | dense hair over the whole outline |
| coffee-bean | MEASURABLE | SMOOTH | one convex bean, published anchor |
| coffee-bubbles | EXCLUDED NO-DOMINANT | — | many small bubbles on dark |
| couch-fibers-cpl | EXCLUDED FILL | — | dense filament fill |
| dry-erase-marker-head-cpl | MEASURABLE | FRINGED | bristle ends along the outline |
| flat-on-ruler-cpl | EXCLUDED PLANAR | — | markings lie in the surface |
| flower-bud-alone-cpl | MEASURABLE | FRINGED | trichomes, published anchor |
| flower-bud-with-background-fern-cpl | MEASURABLE | FRINGED | trichomes, plus a leaf |
| flower-inner-edge-cpl | EXCLUDED FILL | — | fills the frame |
| flowers-cpl | EXCLUDED FILL | — | fills the frame |
| foam | EXCLUDED FILL | — | fills the frame |
| highly-angled-ruler-mm-cpl | MEASURABLE | SMOOTH | borderline, backdrop carries a gradient |
| lavendar-cpl | MEASURABLE | FRINGED | woolly calyx with projecting filaments |
| lead-1-cpl | EXCLUDED FILL | — | leaf fills the frame, backdrop is a corner |
| leaf-2-cpl | EXCLUDED FILL | — | leaf fills the frame, backdrop is a corner |
| pencil-flatter-angle-cpl | MEASURABLE | SMOOTH | clean pencil outline |
| pencil-steep-angle-cpl | MEASURABLE | SMOOTH | clean pencil outline |
| tweezers-cpl | MEASURABLE | SMOOTH | borderline, small burrs on the metal edge |
| wrapped-text-1 | EXCLUDED PLANAR | — | printed text on a flat label |
| wrapped-text-2 | EXCLUDED PLANAR | — | printed text on a flat label |

Totals: 14 MEASURABLE, of which 7 FRINGED and 7 SMOOTH. 12 EXCLUDED, of which
8 FILL, 3 PLANAR and 1 NO-DOMINANT. No subject was classed INTERMEDIATE.

Two subjects are recorded as borderline SMOOTH at classification time, before
their numbers were seen: highly-angled-ruler-mm-cpl for its gradient backdrop,
and tweezers-cpl for the small burrs on its metal edge. They stay SMOOTH.
