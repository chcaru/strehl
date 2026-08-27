"""ORCH: REFUTED INSTRUMENT. Kept as a record, disabled against re-use.

WHAT IT WAS FOR. Two lanes measured that the merge manufactures mid-scale
mottle. Before letting that set the whole fleet's priority I wanted to see it,
because a defect that cannot be seen at 1:1 is not what stands between this
project and a print-worthy result.

WHAT IT DID. Picked the flattest lit region of each master, cropped 400 px at
1:1, and boosted a 20-60 px mid-band as a diagnostic. It ranked all three
convicted subjects above both controls, by 3x to 39x:

    CONVICTED  113MSDCF        0.05236
    CONVICTED  lead-1-cpl      0.02883
    CONVICTED  coffee-bubbles  0.00420
    control    119MSDCF        0.00160
    control    109MSDCF        0.00133

WHY IT IS REFUTED. The ordering is real and means nothing. Looking at the
sheets, the flattest region of `lead-1-cpl` is a LEAF, and the diagnostic was
lighting up its VEIN NETWORK -- genuine subject structure that happens to live
at 20-60 px, exactly the band the convictions are stated in. The statistic
therefore ranks subjects by how much mid-scale CONTENT their flattest area
holds. It never compares the master against the frames that went into it, so it
cannot separate structure the merge invented from structure the subject
supplied. A confirming ordering was available for the taking and would have been
worthless.

This is the same failure the project has hit before from the other direction: a
statistic that charges for detail. The defence is not a better band or a better
site rule, it is the RATIO TO SOURCE -- and that is precisely the design both
convicting lanes used, which is why their numbers stand and this one does not.
The ratio-to-source construction is not ceremony; it is the entire content of
the measurement.

Left executable-but-refusing rather than deleted, because an instrument that was
wrong is evidence about how it was wrong, and a deleted one teaches nobody.
"""
import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "DELIVER-V5"))
from build import tag_png  # noqa: E402

REFUSED_REASON = (
    "orch_mottle_visual is REFUTED: its mid-band statistic has no source-frame\n"
    "comparison, so it charges for subject structure. It ranked lead-1-cpl high\n"
    "because that subject is a leaf and its veins sit in the 20-60px band.\n"
    "Use an instrument that ratios the master against the frames that made it:\n"
    "  experiments/V-GATHER/     (all 26, ratio vs BEST source frame)\n"
    "  experiments/V-NEVERWORSE/ (coffee-bubbles, full stack, exact)\n"
)

SHIP = Path(r"C:\dev\strehl-out\acceptance\SHIP-V4")
OUT = Path(r"C:\dev\strehl-out\DELIVER-V5\mottle-check")
CROP = 400
TILE = 128
# Mid scales, in pixels. The convictions are at 20-60 px; the band is set from
# that, before looking at any image, and printed on every sheet.
BAND_LO, BAND_HI = 20, 60

PAIRS = [
    ("lead-1-cpl", "CONVICTED 2.43x (chroma) -- worst in the corpus"),
    ("coffee-bubbles", "CONVICTED 1.4501x -- 37% over its own null"),
    ("113MSDCF", "CONVICTED 1.30x"),
    ("109MSDCF", "control: PASSES the print gate"),
    ("119MSDCF", "control: PASSES the print gate"),
]


def load(name: str) -> np.ndarray:
    p = SHIP / f"{name}--SHIP-V4.tiff"
    if not p.exists():
        raise SystemExit(f"missing master: {p}")
    a = tifffile.imread(str(p))
    if a.dtype == np.uint16:
        a = a.astype(np.float32) / 65535.0
    elif a.dtype == np.uint8:
        a = a.astype(np.float32) / 255.0
    return a


def boxblur(a: np.ndarray, r: int) -> np.ndarray:
    """Separable running-sum box blur. O(1) per pixel in the radius."""
    if r < 1:
        return a
    k = 2 * r + 1
    pad = np.pad(a, ((r, r), (0, 0)), mode="reflect")
    c = np.cumsum(pad, axis=0)
    out = (c[k:] - c[:-k]) / k
    pad = np.pad(out, ((0, 0), (r, r)), mode="reflect")
    c = np.cumsum(pad, axis=1)
    return (c[:, k:] - c[:, :-k]) / k


def midband(y: np.ndarray) -> np.ndarray:
    """Energy between BAND_LO and BAND_HI px: blur at each edge, difference."""
    return boxblur(y, BAND_LO // 2) - boxblur(y, BAND_HI // 2)


def pick_flat_site(y: np.ndarray) -> tuple[int, int]:
    """Flattest large region that is still ON the subject.

    'On the subject' matters: the flattest place in most of these frames is the
    background, where a mottle claim would be uninteresting and where the merge
    may legitimately have had nothing to work with. Require the tile's mean
    level to sit above the frame's 40th percentile so the site is lit.
    """
    h, w = y.shape
    ny, nx = h // TILE, w // TILE
    t = y[: ny * TILE, : nx * TILE].reshape(ny, TILE, nx, TILE)
    lvl = t.mean(axis=(1, 3))
    gy = np.abs(np.diff(y, axis=0))[: ny * TILE - 1, : nx * TILE]
    ge = gy[: (ny * TILE - 1) // TILE * TILE].reshape(-1, TILE, nx, TILE).mean(axis=(1, 3))
    ge = ge[:ny] if ge.shape[0] >= ny else np.pad(ge, ((0, ny - ge.shape[0]), (0, 0)), mode="edge")

    floor = np.percentile(lvl, 40)
    margin = CROP // TILE + 1
    ok = np.zeros_like(lvl, dtype=bool)
    ok[margin:ny - margin, margin:nx - margin] = True
    ok &= lvl > floor
    if not ok.any():
        raise SystemExit("no lit interior tile")
    g = np.where(ok, ge, np.inf)
    iy, ix = np.unravel_index(np.argmin(g), g.shape)
    return int(iy * TILE), int(ix * TILE)


def srgb(x: np.ndarray) -> np.ndarray:
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def to8(x: np.ndarray) -> np.ndarray:
    return np.clip(srgb(x) * 255.0 + 0.5, 0, 255).astype(np.uint8)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    written = refused = 0
    rows = []
    for name, note in PAIRS:
        p = SHIP / f"{name}--SHIP-V4.tiff"
        if not p.exists():
            print(f"  REFUSED {name}: no master on disk")
            refused += 1
            continue
        a = load(name)
        y = a[..., :3].mean(axis=2) if a.ndim == 3 else a
        cy, cx = pick_flat_site(y)
        sl = (slice(cy, cy + CROP), slice(cx, cx + CROP))

        crop = a[sl][..., :3] if a.ndim == 3 else np.dstack([a[sl]] * 3)
        ycrop = y[sl]

        # The diagnostic. Mid-band energy, scaled by a FIXED factor that is the
        # same for every sheet, so the sheets are comparable to each other. A
        # per-sheet autoscale would erase exactly the difference being tested.
        mb = midband(ycrop)
        BOOST = 12.0
        diag = np.clip(0.5 + mb * BOOST, 0, 1)
        rms = float(np.sqrt(np.mean(mb ** 2)))

        top = to8(crop)
        bot = np.dstack([np.clip(diag * 255 + 0.5, 0, 255).astype(np.uint8)] * 3)

        sheet = Image.new("RGB", (CROP, CROP * 2 + 56), (20, 20, 20))
        sheet.paste(Image.fromarray(top), (0, 28))
        sheet.paste(Image.fromarray(bot), (0, CROP + 42))
        d = ImageDraw.Draw(sheet)
        d.text((4, 8), f"{name}  --  {note}", fill=(245, 245, 245))
        d.text((4, CROP + 32),
               f"mid-band {BAND_LO}-{BAND_HI}px  x{BOOST:g}  rms={rms:.5f}  (DIAGNOSTIC, not a print)",
               fill=(245, 245, 245))
        fn = f"mottle--{name}.png"
        sheet.save(OUT / fn)
        tag_png(str(OUT / fn))
        written += 1
        rows.append((name, rms, note))
        print(f"  wrote {fn}  site y={cy} x={cx}  midband_rms={rms:.5f}  {note}")

    print()
    print("  mid-band RMS, convicted vs control (higher = blotchier):")
    for name, rms, note in sorted(rows, key=lambda r: -r[1]):
        tagl = "CONVICTED" if "CONVICTED" in note else "control  "
        print(f"    {tagl}  {name:20s} {rms:.5f}")
    print()
    print(f"  {len(PAIRS)} subjects = {written} written + {refused} refused -> {OUT}")


if __name__ == "__main__":
    raise SystemExit(REFUSED_REASON)
