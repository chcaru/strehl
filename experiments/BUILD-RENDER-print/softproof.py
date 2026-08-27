"""Soft-proof pictures: what the press does to a master, at 1:1, side by side.

Scores are not a print verdict.  A subject can read 50% out of gamut and look
untouched, because the clipped colours sit in a region nobody looks at, and a
subject can read 3% and lose the one hue the picture is about.  So this emits
pictures at 1:1 and the numbers are only used to decide WHERE to look.

The crop is chosen by the instrument, not by hand: the 800 x 800 window whose
out-of-gamut density is highest.  That makes the choice reproducible and it
puts the crop where the damage is, which is the honest place to look rather
than the flattering one.  Coordinates are printed so a later run can be
compared against this one.

Panels, left to right:
  MASTER     the shipped file
  PRINTABLE  the same pixels after a round trip through the print profile
  LOST       where, and how much, chroma the press cannot reach

Written as PNG.  A 1:1 artifact crop is never JPEGed here; the compression
artifacts would be indistinguishable from the thing being judged.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageCms, ImageDraw

from printqa import (
    SATURATED_CHROMA,
    SRGB_ICM,
    SWOP_ICM,
    printable_rgb8,
    read_master,
    rgb_to_lab,
)

CROP = 800


def densest_window(mask: np.ndarray, size: int) -> tuple[int, int, float]:
    """Top-left of the size x size window with the most flagged pixels."""
    step = max(size // 4, 1)
    h, w = mask.shape
    best, by, bx = -1.0, 0, 0
    integral = mask.cumsum(0).cumsum(1)
    integral = np.pad(integral, ((1, 0), (1, 0)))
    for y in range(0, max(h - size, 0) + 1, step):
        for x in range(0, max(w - size, 0) + 1, step):
            y2, x2 = y + size, x + size
            s = (
                integral[y2, x2]
                - integral[y, x2]
                - integral[y2, x]
                + integral[y, x]
            )
            if s > best:
                best, by, bx = float(s), y, x
    return by, bx, 100.0 * best / (size * size)


def label(img: Image.Image, text: str) -> Image.Image:
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, img.width, 22], fill=(0, 0, 0))
    d.text((6, 5), text, fill=(255, 255, 255))
    return img


def proof_one(path: Path, out_dir: Path, profiles: list, srgb) -> dict | None:
    """Soft-proof one master against one or more profiles, in one sheet.

    `profiles` is a list of (label, profile). The FIRST is the reference: it
    selects the crop window, so adding a second profile cannot silently move
    the crop and make two runs incomparable. With a single profile this
    produces exactly the three-panel sheet it always did.
    """
    rgb16 = read_master(path)
    rgb8 = (rgb16 >> 8).astype(np.uint8)
    lab_o = rgb_to_lab(rgb16 / 65535.0)
    c_o = np.hypot(lab_o[..., 1], lab_o[..., 2])

    arms = []
    for pname, prof in profiles:
        printable = printable_rgb8(rgb8, prof, srgb)
        lab_p = rgb_to_lab(printable / 255.0)
        lost = c_o - np.hypot(lab_p[..., 1], lab_p[..., 2])
        arms.append((pname, printable, lost))

    ref_lost = arms[0][2]
    # Condition on there being saturation to lose. Selecting on `lost` alone
    # sent the flowers-cpl crop to featureless background bokeh -- a 90.5%
    # window in which MASTER and PRINTABLE are indistinguishable by eye,
    # because the loss was taken off a near-neutral. A crop that shows no
    # visible difference cannot support a print verdict either way, so the
    # window must land where real colour is being flattened.
    mask = ((ref_lost > 2.0) & (c_o >= SATURATED_CHROMA)).astype(np.float32)
    if mask.sum() < CROP * CROP * 0.02:
        # Nothing saturated is being lost anywhere. Say so rather than falling
        # back to the old mask and presenting a near-neutral crop as evidence.
        print(f"  {path.stem}: no saturated loss to show (mask {100 * mask.mean():.3f}% of frame)")
        return None

    y, x, density = densest_window(mask, CROP)
    sl = (slice(y, y + CROP), slice(x, x + CROP))

    name = path.name.replace("--SHIP-V2-ICC.tiff", "")
    sat_crop = c_o[sl] >= SATURATED_CHROMA

    panels = [(Image.fromarray(rgb8[sl], "RGB"), f"MASTER  {name}  @ {x},{y}")]
    per_arm = {}
    for pname, printable, lost in arms:
        sev = 100.0 * float((sat_crop & (lost[sl] > 5.0)).mean())
        per_arm[pname] = sev
        panels.append(
            (Image.fromarray(printable[sl], "RGB"), f"PRINTABLE  {pname}  rel.col.+BPC")
        )
        heat = np.clip(lost[sl] / 10.0, 0, 1)
        c = np.zeros((CROP, CROP, 3), np.uint8)
        c[..., 0] = (heat * 255).astype(np.uint8)
        c[..., 1] = ((1 - heat) * 60).astype(np.uint8)
        c[..., 2] = ((1 - heat) * 60).astype(np.uint8)
        panels.append(
            (Image.fromarray(c, "RGB"), f"LOST CHROMA  {pname}  red = up to 10 Lab units")
        )

    gap = 8
    hdr = 26 if len(arms) == 1 else 44
    sheet = Image.new(
        "RGB", (CROP * len(panels) + gap * len(panels), CROP + hdr), (24, 24, 24)
    )
    for i, (img, text) in enumerate(panels):
        sheet.paste(label(img, text), (i * (CROP + gap), hdr))

    head = (
        f"{name}   crop {CROP}x{CROP} at ({x},{y})   "
        f"window out-of-gamut {density:.1f}%   1:1, no resampling"
    )
    if len(arms) > 1:
        # The decomposition ORCH asked for: how much of the verdict was the
        # profile. Stated on the sheet so a reader comparing two papers is not
        # left inferring it from two separately-run images.
        parts = "   ".join(f"{k} {v:.1f}%" for k, v in per_arm.items())
        ref = arms[0][0]
        deltas = "   ".join(
            f"{k} vs {ref}: {per_arm[k] - per_arm[ref]:+.1f} pts"
            for k, _, _ in arms[1:]
        )
        head += f"\nsaturated severe loss in crop:  {parts}      {deltas}"

    d = ImageDraw.Draw(sheet)
    d.text((6, 8), head, fill=(230, 230, 230))
    out = out_dir / f"{name}--softproof.png"
    sheet.save(out)
    return {
        "subject": name,
        "x": x,
        "y": y,
        "density": density,
        "path": out,
        "per_arm": per_arm,
    }


def commission_comparison(profiles: list, srgb) -> bool:
    """Two arms that must disagree, or a comparison sheet proves nothing.

    A comparison that silently used ONE profile for both columns would look
    exactly like two papers that happen to match -- a zero delta reading as
    agreement when it is really a wiring fault. So:

    * IDENTITY arm  -- the same profile passed twice must produce byte-identical
      printable panels. If it does not, the transform is not deterministic and
      no delta can be attributed to the paper.
    * DIFFERENCE arm -- two genuinely different profiles must produce different
      panels. If they do not, only one profile is reaching the transform and
      every comparison the tool draws is a fiction.
    """
    print("=" * 78)
    print("COMMISSIONING profile comparison")
    print("=" * 78)
    probe = np.zeros((64, 256, 3), np.uint8)
    probe[..., 0] = np.linspace(10, 245, 256).astype(np.uint8)[None, :]
    probe[..., 1] = 200
    probe[..., 2] = np.linspace(245, 10, 256).astype(np.uint8)[None, :]

    ref_name, ref_prof = profiles[0]
    a = printable_rgb8(probe, ref_prof, srgb)
    a2 = printable_rgb8(probe, ref_prof, srgb)
    ok = True
    if not np.array_equal(a, a2):
        print(f"  FAIL  identity: {ref_name} against itself differs by "
              f"{int(np.abs(a.astype(int) - a2.astype(int)).max())} DN")
        ok = False
    else:
        print(f"  PASS  identity: {ref_name} against itself is byte-identical, so a")
        print("        zero delta means the papers agree, not that the wiring failed.")

    if len(profiles) < 2:
        print("  SKIPPED difference arm: only one profile given, so no comparison")
        print("        is being drawn and there is nothing for it to check.")
    else:
        worst = 0
        for pname, prof in profiles[1:]:
            b = printable_rgb8(probe, prof, srgb)
            dn = int(np.abs(a.astype(int) - b.astype(int)).max())
            worst = max(worst, dn)
            print(f"  {'':6}{ref_name} vs {pname}: max |dDN| = {dn}")
        if worst < 4:
            print(f"  FAIL  difference: the profiles differ by only {worst} DN. Either")
            print("        they are the same profile or only one reaches the transform.")
            ok = False
        else:
            print(f"  PASS  difference: profiles move the probe by {worst} DN, so both")
            print("        are genuinely reaching the transform.")
    print("=" * 78)
    print("COMMISSIONED" if ok else "NOT COMMISSIONED -- sheets below are void")
    print("=" * 78)
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("subjects", nargs="+")
    ap.add_argument("--root", type=Path, default=Path(r"C:\dev\strehl-out\SHIP-V2-ICC"))
    ap.add_argument(
        "--out", type=Path, default=Path(r"C:\dev\strehl-out\BUILD-RENDER-print")
    )
    ap.add_argument(
        "--profile",
        type=Path,
        nargs="+",
        default=[SWOP_ICM],
        help="one or more output profiles; the FIRST is the reference and "
        "selects the crop window. Defaults to RSWOP so existing sheets are "
        "reproduced unchanged.",
    )
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    srgb = ImageCms.getOpenProfile(str(SRGB_ICM))
    profiles = []
    for p in args.profile:
        if not p.exists():
            print(f"  PROFILE NOT FOUND: {p}")
            return 1
        profiles.append((p.stem, ImageCms.getOpenProfile(str(p))))

    if not commission_comparison(profiles, srgb):
        return 1

    made, missing, skipped = 0, [], []
    for s in args.subjects:
        hits = sorted(args.root.glob(f"{s}*.tiff"))
        if not hits:
            missing.append(s)
            continue
        r = proof_one(hits[0], args.out, profiles, srgb)
        if r is None:
            skipped.append(s)
            continue
        made += 1
        print(
            f"  {r['subject']:<38} crop at ({r['x']:>4},{r['y']:>4})  "
            f"window OOG {r['density']:5.1f}%  -> {r['path'].name}"
        )
    # Partition, so a subject that produced no sheet cannot be read as one that
    # passed: written + skipped + not-found must account for every request.
    print(
        f"requested {len(args.subjects)}  written {made}  "
        f"no-saturated-loss {len(skipped)}  not found {len(missing)}"
    )
    if missing:
        print(f"  NOT FOUND: {missing}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
