"""R9 -- does the correction reduce fringe WIDTH, or only shift fringe COLOUR?

The orchestrator's sharpest question, and a real risk: a red-only correction on
a fringe that has a warm edge AND a cool edge could plausibly shift the hue of
the fringe without narrowing it. That would read as "different" rather than
"better" and would be a bad thing to discover after the comparison sheet.

## BARS, REGISTERED BEFORE THE RUN

  W1  FRINGE AREA. Count of pixels whose chroma exceeds a fixed absolute
      threshold, within a fixed distance of a strong luminance edge. The
      threshold is absolute and identical across arms, so this measures EXTENT,
      not amplitude.
        on < off  -> the fringe covers less of the image: a real narrowing.
        on ~ off  -> the fringe was recoloured, not removed. THE BAD OUTCOME.

  W2  FRINGE WIDTH. Chroma-weighted mean distance from the edge, over
      edge-adjacent pixels. This is the spatial second moment of the fringe and
      is the direct answer to "shifted colour vs reduced width".
        A pure recolouring leaves this UNCHANGED.

  W3  HUE-SHIFT DISCRIMINATOR. Of the edge pixels whose chroma FELL, what
      fraction fell toward neutral rather than swapping sign? A correction that
      genuinely removes red misregistration drives R-Y toward zero. A
      recolouring flips its sign. Reported as the fraction of edge pixels where
      |R-Y| decreased AND sign(R-Y) was preserved.

  W4  CONTROL -- the same three statistics on the GREEN channel deviation,
      which has no coefficient (Channel::Green has none by construction) and
      whose plane gather is bitwise identical between arms. Any apparent
      "improvement" here is the measurement moving, not the image, and bounds
      how much of W1-W3 is instrument.
"""
import os
import numpy as np
import tifffile

R7 = r"C:\dev\strehl-out\M107-chroma\r7"
OFF = os.path.join(R7, "off1.tif")
ON = os.path.join(R7, "on.tif")

CHROMA_T = 0.06   # absolute, identical across arms
EDGE_Q = 0.99     # "strong luminance edge"
NEAR = 3          # pixels from an edge


def load(p):
    a = tifffile.imread(p).astype(np.float64) / 65535.0
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return r, g, b, y


def main():
    print("=" * 70)
    print("R9 -- fringe WIDTH vs fringe COLOUR")
    print("=" * 70)

    r0, g0, b0, y0 = load(OFF)
    r1, g1, b1, y1 = load(ON)

    # Edge mask from the OFF arm only, so both arms are scored on the SAME
    # pixels. Scoring each arm on its own edges would let the mask move.
    gy, gx = np.gradient(y0)
    gm = np.hypot(gx, gy)
    edge = gm >= np.quantile(gm, EDGE_Q)

    from scipy import ndimage
    dist = ndimage.distance_transform_edt(~edge)
    near = dist <= NEAR
    print(f"\nedge pixels={int(edge.sum())}  near-edge pixels={int(near.sum())}"
          f"  ({100*near.mean():.2f}% of frame)")

    def stats(r, b, y, label):
        c = np.maximum(np.abs(r - y), np.abs(b - y))
        hot = near & (c > CHROMA_T)
        area = int(hot.sum())
        w = float((c[hot] * dist[hot]).sum() / max(c[hot].sum(), 1e-12))
        print(f"  {label}: fringe area={area:8d}  "
              f"chroma-weighted width={w:.4f} px  mean chroma={c[near].mean():.6f}")
        return area, w, c

    print(f"\nW1/W2  chroma threshold {CHROMA_T}, within {NEAR}px of an edge")
    a_off, w_off, c_off = stats(r0, b0, y0, "off")
    a_on, w_on, c_on = stats(r1, b1, y1, "on ")
    print(f"    fringe AREA  change: {100*(a_on-a_off)/a_off:+.2f}%")
    print(f"    fringe WIDTH change: {100*(w_on-w_off)/w_off:+.2f}%")
    print(f"    W1 {'PASS -- fringe covers less area (narrowing)' if a_on < a_off*0.98 else 'FAIL/AMBIGUOUS -- area not materially reduced'}")

    print("\nW3  hue-shift discriminator (red deviation on near-edge pixels)")
    d0 = (r0 - y0)[near]
    d1 = (r1 - y1)[near]
    fell = np.abs(d1) < np.abs(d0)
    same_sign = np.sign(d0) == np.sign(d1)
    frac_fell = float(fell.mean())
    frac_toward_neutral = float((fell & same_sign).sum() / max(fell.sum(), 1))
    flipped = float((~same_sign).mean())
    print(f"    |R-Y| fell on {100*frac_fell:.1f}% of near-edge pixels")
    print(f"    of those, {100*frac_toward_neutral:.1f}% kept their sign "
          f"(moved TOWARD neutral, not recoloured)")
    print(f"    sign flipped on {100*flipped:.2f}% of near-edge pixels "
          f"(high = recolouring)")
    print(f"    mean |R-Y| near edges: off={np.abs(d0).mean():.6f} "
          f"on={np.abs(d1).mean():.6f}  ({100*(np.abs(d1).mean()-np.abs(d0).mean())/np.abs(d0).mean():+.2f}%)")

    print("\nW4  CONTROL -- blue deviation, whose coefficient is None")
    e0 = (b0 - y0)[near]
    e1 = (b1 - y1)[near]
    print(f"    mean |B-Y| near edges: off={np.abs(e0).mean():.6f} "
          f"on={np.abs(e1).mean():.6f}  ({100*(np.abs(e1).mean()-np.abs(e0).mean())/np.abs(e0).mean():+.2f}%)")
    print("    (B has no coefficient; any change here is downstream demosaic")
    print("     coupling to the moved red plane, and bounds the instrument.)")

    print("\n" + "=" * 70)
    narrowed = a_on < a_off * 0.98
    toward = frac_toward_neutral > 0.90
    if narrowed and toward:
        print("VERDICT: BETTER -- fringe area falls and red moves toward neutral")
    elif not narrowed and toward:
        print("VERDICT: AMBIGUOUS -- amplitude falls but extent does not")
    else:
        print("VERDICT: RECOLOURED, NOT REMOVED -- report as such")
    print("=" * 70)


if __name__ == "__main__":
    main()
