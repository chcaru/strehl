# Lens ends, a stalled plane and a short calibration range (2026-11-24)

The owner reported three faults on the evening of 2026-11-24:

1. Calibrate step failed with "Not measurable: 1 of 14652 tiles come into and out of focus".
2. A stack stopped half way with "Focus did not reach and hold target 61892; no exposure".
3. The depth rail offered focus past the lens's physical end, and moving there "disconnected
   the camera and broke Strehl".

## Evidence

**The stack** (`D:/StrehlCaptures/stack-1795583186775-12502`, read only): plan 61850 to 61936, step 7,
14 planes, four-shot, highlight groups every second plane. Error correction asked for retakes of
planes 6 and 7 (ordinals 5 and 6) with "witness tiles disagree locally" by 0.73, 1.44, 0.85 and
2.04 px at p99 (limit 0.51). The second retake of plane 7 moved the lens to its approach position
61764 and then to 61892. The lens did not report 61892 within 10 s plus the settle time, and the
whole run ended `uncertain` with 8 of 14 planes. The same pair of moves had landed 13 s earlier.
The journal does not say where the lens stopped, and the Pi's system journal has nothing. MEASURED.

**The calibration**: the marked range was 86 units. The dense cluster (25 positions 8 units apart)
was kept inside the marks, so tiles near either mark could not come into and out of focus inside
the survey, and the step was not measurable. The second round then took its spacing from the
first gap between positions. In the two-shutter survey that gap is 0, because a long and a short
shot are taken at one position. 4 x 0 became a survey 1 unit apart over 24 units, which measured
1 tile. DERIVED from the code and the marks in the stack's manifest.

**The lens ends** (owner's go-ahead; rig probes through the Pi's own API, camera and light off
after): the lens was moved by jogs of 128 from 62800, then by 16 and 1 near each end, and by
large moves down to the near end.

| Move | Result |
| --- | --- |
| 63440 to 63487 by jogs | lands |
| to 63488 | lens stops at 63487; after 10.6 s the controller faults with "Focus did not reach and hold target 63488"; Recover reads 63487 |
| down to 1509 | lands (whole-travel moves take about 1 s) |
| to 1508 or 1000 | lens stops at 1509; same fault |
| after a camera power cycle | 1509 and 63487 land, 1508 and 63488 do not |

The camera stays connected and needs only Recover. So "broke Strehl" is the controller's fault
state, not a USB disconnect. The camera's focus property advertises 0 to 65535 whatever the
lens, and the rail drew that range. MEASURED on the A7CR with the owner's lens, 2026-11-24
21:24-21:28.

Which end is which: the subject outline's magnification rate is about -13 ppm a unit on the
weevil (plan section on the subject), so magnification falls as the number rises. 63487 is the
Far end and 1509 the Near end, as the rail labels them.

## Changes (commit on `studio2/cal-focus`)

- `ptp.rs`: a focus move whose readback stays unchanged for 1.5 s short of the target returns
  `stopped_short` with the readback (over twice the 0.67 s readback lag measured on 2026-11-20).
  Every timeout message now includes where the lens is.
- `backend.rs`: `LensStopped {from, target, at}`, a typed error.
- `worker.rs`:
  - A manual move that stops short records the end, keeps the controller ready and says "The
    lens's far end is 63487: it goes no further". Ends are kept in `lens-travel.json` in the
    state directory, and widened when the lens lands beyond one.
  - A capture's plane move that fails is tried once more through the approach (`focus_retry`).
  - A retake that cannot reach focus keeps the plane's last group, and the run goes on
    (`retake_abandoned`).
- `session.rs`:
  - Jog and focus from inside the travel stop at a known end; from the end itself they go to
    the lens as asked.
  - `start` and `capture_positions` with a plane or the approach past a known end are refused.
  - The state carries `lens_travel`, with `capabilities.lens_travel`.
- Desktop:
  - The calibration's cluster is centred on the marks and runs past them when the range is
    shorter, inside the known ends. Its second round uses the cluster's spacing.
  - The rail shades the travel past each known end, draws a "lens end" rule and keeps clicks
    and handle drags inside.

Each test was checked to fail with its fix reverted and to pass with it.

## Rig checks after the change

The Pi was deployed with receipt `../capture-implementation-2026-11-20/install-1795585858.json`
(controller sha 608bca40..., bridge 744324f9..., backup `/root/strehl-before-round4-1795585858`).
The checks ran on 2026-11-24 between 21:51 and 22:24 and are MEASURED:

| Action | Result |
| --- | --- |
| jog +128 from 63400 | 2.1 s, ready at 63487, "The lens's far end is 63487: it goes no further (asked for 63528)" |
| jog -128 | 0.8 s, lands at 63359; no Recover needed |
| focus 65000 | 0.5 s, kept at 63487, "Focus settled" |
| jog +16 at the end | 1.6 s, stops at 63487 again, the end is kept |
| focus 1000 from 2000 | 2.2 s, ready at 1509, "The lens's near end is 1509" |

The Pi's `lens-travel.json` now holds 1509 and 63487.

Calibrate step ran end to end through the release desktop, headless, with a scratch copy of the
owner's capture settings, at the owner's marks 61850 to 61936 (ISO 100, 0.5 s, four-shot). It
ended `done` about 4.5 minutes after it started: "Subject found (9.1 % of the frame), sharp from
focus 61797 to 61989. Detail stays sharp over about 69 focus units; a step of 9 suits it." Those
are the survey's own limits, so the subject's depth reaches at least to both ends of the survey.
The camera was at ISO 100, 0.5 s and four-shot afterwards, as before. The survey was deleted.
Light and camera were off and "manage power" on at the end.

## Not explained

Why the lens did not arrive at 61892 on the second retake is unknown. The failing move was
identical to one that landed. The new error message will say where the lens stopped next time.
The same planes were also being retaken for local disagreement of 0.7 to 2 px, so something
moved during planes 6 and 7: the subject, the rig, or a focus slip. That cause is not
established.
