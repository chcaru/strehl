"""Inspect the comparator renders without trusting anyone's summary of them."""
import sys

import numpy as np
import tifffile

FILES = [
    (r"C:\dev\macro\out\coffee-bean\stack.tif", "fork / coffee-bean"),
    (r"D:\edited\macro\test2\2026-05-09-12.12.17 ZS PMax.tif", "Zerene PMax / 113MSDCF"),
    (r"C:\dev\strehl-out\V-H2H2\lin\cb-full-g1.tiff", "strehl cb post-flip"),
    (r"C:\dev\strehl-out\V-H2H2\lin\113-full-g1.tiff", "strehl 113 post-flip"),
]


def main():
    for path, label in FILES:
        try:
            with tifffile.TiffFile(path) as tf:
                p = tf.pages[0]
                tags = {t.name: t.value for t in p.tags}
                print(f"\n{label}\n  {path}")
                print(f"  shape {p.shape} dtype {p.dtype} "
                      f"photometric {tags.get('PhotometricInterpretation')} "
                      f"planar {tags.get('PlanarConfiguration')}")
                print(f"  bits {tags.get('BitsPerSample')} "
                      f"sampleformat {tags.get('SampleFormat')} "
                      f"compression {tags.get('Compression')}")
                for k in ("Software", "ImageDescription", "Make", "Model"):
                    if k in tags:
                        v = str(tags[k])[:160].replace("\n", " ")
                        print(f"  {k}: {v}")
                if "InterColorProfile" in tags:
                    print(f"  ICC profile present, {len(tags['InterColorProfile'])} bytes")
                a = p.asarray()
                s = a[::37, ::37]
                print(f"  sample stats: min {s.min()} max {s.max()} "
                      f"mean {s.mean():.1f} median {np.median(s):.1f}")
                q = np.percentile(s.astype(np.float64), [1, 25, 50, 75, 99])
                print(f"  percentiles 1/25/50/75/99: " +
                      " ".join(f"{v:.0f}" for v in q))
        except Exception as e:
            print(f"\n{label}\n  {path}\n  FAILED: {type(e).__name__}: {e}")


if __name__ == "__main__":
    sys.exit(main())
