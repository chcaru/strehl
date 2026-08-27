"""What differs between the two files, if not one pixel of the image?"""
import tifffile

for tag, p in (("shipping 9b05d0b7", r"C:\dev\strehl-out\acceptance\SHIP-V4\wrapped-text-1--SHIP-V4.tiff"),
               ("stray    F663B703", r"C:\dev\strehl-out\V-GATHER\strayprobe\STRAY.tiff")):
    with tifffile.TiffFile(p) as t:
        pg = t.pages[0]
        print("== %s ==" % tag)
        for k in sorted(pg.tags, key=lambda x: x.code):
            v = k.value
            if isinstance(v, (bytes, str)) and len(str(v)) > 160:
                v = str(v)[:160] + "..."
            if k.code in (256, 257, 258, 259, 262, 270, 271, 272, 305, 306, 315, 33432, 65000, 65001):
                print("   %-22s %s" % (k.name, v))
        print()
