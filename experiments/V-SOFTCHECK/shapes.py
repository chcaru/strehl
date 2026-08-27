import tifffile, glob, os
for f in [r"C:\dev\strehl-out\acceptance\SHIP-V4\113MSDCF--SHIP-V4.tiff",
          r"C:\dev\strehl-out\V-SOFTCHECK\lin\113MSDCF\master.tiff",
          r"C:\dev\strehl-out\V-SOFTCHECK\lin\119MSDCF\master.tiff",
          r"C:\dev\strehl-out\V-SOFTCHECK\srgb\119MSDCF\master.tiff"]:
    if os.path.exists(f):
        with tifffile.TiffFile(f) as t:
            s=t.series[0]
            print(f"{s.shape}  {s.dtype}  {os.path.basename(os.path.dirname(f))}/{os.path.basename(f)}")
    else:
        print(f"MISSING {f}")
