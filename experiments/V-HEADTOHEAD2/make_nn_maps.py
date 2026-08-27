"""Make nearest-neighbour warpmaps that are BYTE-IDENTICAL except for the kernel.

The commissioning battery found that C -- the coherent-power statistic -- rates
a nearest-neighbour rescale up to 3.2x BETTER than a bicubic one when the
rescale is applied identically to both halves.  That is the same failure mode
that killed the retracted statistic (+29%/+42% for an NN gather).  It happens
because NN aliasing is deterministic: apply it to both halves and the artefact
is common to both, so it is coherent, so C credits it.

The question that actually matters is whether that failure reaches the real
pipeline.  It might not, because the gather is applied PER FRAME at a different
sub-pixel offset for every frame, and halves A and B contain DISJOINT frames
solved SEPARATELY -- so A's NN artefacts and B's NN artefacts are at different
phases and should not be coherent.  "Should" is not a measurement.

`strehl stack --help`: "It reaches pixels through the SOLVE only.  If
STREHL_WARPMAP names a sidecar, that sidecar's own recorded resampler wins and
the run says so on stderr."  Re-solving with --resampler nearest would change
the fitted geometry as well as the kernel, confounding the arm.  So instead:
copy the sidecar and change the single line `resampler catmull-rom` to
`resampler nearest`.  Every f64 bit pattern -- every warp -- is untouched.  One
variable.
"""
import os
import sys

SRC = r"C:\dev\strehl-out\V-H2H2\warpmaps"


def main():
    n = 0
    for tag in ("113-A", "113-B", "cb-A", "cb-B"):
        src = os.path.join(SRC, f"{tag}.warpmap.txt")
        dst = os.path.join(SRC, f"{tag}-nn.warpmap.txt")
        with open(src, "rb") as f:
            raw = f.read()
        before = raw.count(b"resampler catmull-rom")
        if before != 1:
            raise RuntimeError(f"{tag}: expected exactly 1 resampler line, "
                               f"found {before}")
        out = raw.replace(b"resampler catmull-rom", b"resampler nearest")
        assert len(out) == len(raw) - len(b"catmull-rom") + len(b"nearest")
        # every other byte must be identical
        a = raw.split(b"resampler catmull-rom")
        b = out.split(b"resampler nearest")
        assert a == b, f"{tag}: something other than the kernel changed"
        with open(dst, "wb") as f:
            f.write(out)
        print(f"  {tag}: {len(raw)} -> {len(out)} bytes, "
              f"only the resampler line differs")
        n += 1
    print(f"{n} nearest-neighbour sidecars written")


if __name__ == "__main__":
    sys.exit(main())
