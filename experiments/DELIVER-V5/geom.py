"""Master geometry survey.  Nothing is assumed about the corpus."""
import os
import sys

import tifffile

SRC = r"C:\dev\strehl-out\acceptance\SHIP-V4"
SUFFIX = "--SHIP-V4.tiff"


def masters():
    out = []
    for f in sorted(os.listdir(SRC)):
        if f.endswith(SUFFIX):
            out.append((f[: -len(SUFFIX)], os.path.join(SRC, f)))
    return out


def main():
    rows = []
    shapes = {}
    for name, p in masters():
        with tifffile.TiffFile(p) as tf:
            pg = tf.pages[0]
            shp = tuple(pg.shape)
            dt = str(pg.dtype)
            icc = "icc" if 34675 in pg.tags else "-"
            comp = str(pg.compression)
        rows.append("%-38s %-22s %-8s %-4s %s" % (name, shp, dt, icc, comp))
        shapes.setdefault((shp, dt), []).append(name)
    print("\n".join(rows))
    print("\ndistinct (shape,dtype): %d" % len(shapes))
    for k, v in sorted(shapes.items(), key=lambda kv: -len(kv[1])):
        print("  %-30s %2d  e.g. %s" % (k, len(v), v[0]))
    print("\ntotal masters: %d" % len(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
