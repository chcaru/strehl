"""Is the ICC "no move" result a pass, or is the profile being ignored?

`printqa.py` reports that 23 of 26 masters round-trip through their own
embedded profile at 0 DN and 3 at 1 DN. That is the result the print claim
rests on: it says the embedded profile agrees with the encoded data.

But a transform that silently ignored the embedded profile would report
exactly the same thing, and this project has shipped enough instruments whose
green reading meant "nothing happened" rather than "nothing was wrong".

So: run the SAME code path with a deliberately WRONG profile substituted for
the embedded one. A wide-gamut display profile (DCI-P3) standing in for sRGB
must move colour a long way. If it does not, the null is inert and every ICC
statement in the print report is void.

Magnitude alone is not quite enough, though: a transform that corrupted
pixels arbitrarily would also move them a long way. So a second arm requires
the movement to be a genuine, INVERTIBLE colour transform -- sRGB -> P3 ->
sRGB must return to where it started. Large one-way movement plus a clean
round trip is reinterpretation; large movement without it is damage.

RETRACTED ARM, recorded because the retraction is the finding: this control
first asserted a SIGN -- that sRGB data mislabelled P3 must desaturate when
converted to sRGB. It measured mean chroma 20.14 -> 18.83, i.e. it did
desaturate, but the reasoning behind the prediction was wrong, so the
agreement was luck. The substituted profile is a DISPLAY profile whose tone
curve is not sRGB's piecewise curve, and mean chroma over a whole frame moves
with lightness as well as with saturation. The sign therefore mixes a TRC
change with a gamut change and is not predictable a priori. Inverting the
assertion to match the observation would have been fitting the control to the
data; it was removed instead.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageCms

sys.path.insert(0, str(Path(__file__).resolve().parent))

from printqa import SRGB_ICM, embedded_profile, read_master, rgb_to_lab  # noqa: E402

P3_ICM = Path(r"C:\Windows\System32\spool\drivers\color\Alienware_AW3225QF_DCI-P3.icm")

SUBJECT = Path(r"C:\dev\strehl-out\SHIP-V2-ICC\flower-inner-edge-cpl--SHIP-V2-ICC.tiff")
"""The most saturated master in the corpus (45.97% of pixels lose >5 Lab units
of chroma to SWOP). A control has to be run where the effect it is looking for
would be largest, or a small reading is uninformative."""


def chroma(rgb8: np.ndarray) -> float:
    lab = rgb_to_lab(rgb8.astype(np.float64) / 255.0)
    return float(np.hypot(lab[..., 1], lab[..., 2]).mean())


def convert(rgb8: np.ndarray, src_profile, dst_profile) -> np.ndarray:
    tr = ImageCms.buildTransform(src_profile, dst_profile, "RGB", "RGB", renderingIntent=1)
    return np.asarray(ImageCms.applyTransform(Image.fromarray(rgb8, "RGB"), tr))


def main() -> int:
    srgb = ImageCms.getOpenProfile(str(SRGB_ICM))
    rgb8 = (read_master(SUBJECT) >> 8).astype(np.uint8)

    prof = embedded_profile(SUBJECT)
    if prof is None:
        print("FAIL  no embedded profile; the control cannot run")
        return 1
    embedded = ImageCms.getOpenProfile(io.BytesIO(prof))
    p3 = ImageCms.getOpenProfile(str(P3_ICM))

    print("=" * 78)
    print("ICC POTENCY CONTROL")
    print("=" * 78)
    print(f"subject : {SUBJECT.name}")
    print(f"embedded: {ImageCms.getProfileDescription(embedded).strip()}")
    print(f"wrong   : {ImageCms.getProfileDescription(p3).strip()}")
    print()

    base_c = chroma(rgb8)

    true_out = convert(rgb8, embedded, srgb)
    true_dn = int(np.abs(true_out.astype(np.int16) - rgb8.astype(np.int16)).max())
    true_c = chroma(true_out)

    wrong_out = convert(rgb8, p3, srgb)
    wrong_dn = int(np.abs(wrong_out.astype(np.int16) - rgb8.astype(np.int16)).max())
    wrong_c = chroma(wrong_out)

    print(f"  ARM A  embedded profile -> sRGB : max |dDN| = {true_dn:3d}   "
          f"mean chroma {base_c:.2f} -> {true_c:.2f}")
    print(f"  ARM B  DCI-P3 (WRONG)   -> sRGB : max |dDN| = {wrong_dn:3d}   "
          f"mean chroma {base_c:.2f} -> {wrong_c:.2f}")
    print()

    ok = True
    if wrong_dn < 8:
        print(f"  FAIL  the wrong profile moved pixels by only {wrong_dn} DN. The")
        print("        transform is not honouring the profile, so ARM A's small")
        print("        number means nothing and the ICC result is VOID.")
        ok = False
    else:
        print(f"  PASS  potency: the wrong profile moves colour by {wrong_dn} DN, so")
        print("        this code path demonstrably reads the profile it is given.")

    rt = convert(convert(rgb8, srgb, p3), p3, srgb)
    rt_dn = int(np.abs(rt.astype(np.int16) - rgb8.astype(np.int16)).max())
    print(f"  ARM C  sRGB -> P3 -> sRGB       : max |dDN| = {rt_dn:3d}   "
          f"mean chroma {base_c:.2f} -> {chroma(rt):.2f}")
    print()
    if rt_dn > 4:
        print(f"  FAIL  round trip through P3 lost {rt_dn} DN. ARM B's movement is")
        print("        not an invertible reinterpretation, so it may be damage")
        print("        rather than colour management.")
        ok = False
    else:
        print(f"  PASS  round trip returns within {rt_dn} DN, so ARM B's {wrong_dn} DN is a")
        print("        real colorimetric reinterpretation and not corruption.")

    if true_dn > 1:
        print(f"  FAIL  ARM A moved {true_dn} DN; the embedded profile does not match")
        print("        the encoded data.")
        ok = False
    else:
        print(f"  PASS  ARM A moves {true_dn} DN -- and now that ARM B proves the path")
        print("        is live, that zero is a real no-op, not an ignored profile.")

    print("=" * 78)
    print("COMMISSIONED -- ICC null is potent" if ok else "NOT COMMISSIONED")
    print("=" * 78)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
