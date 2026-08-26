import sys
import numpy as np
import tifffile

for p in sys.argv[1:]:
    with tifffile.TiffFile(p) as tf:
        s = tf.series[0]
        pg = tf.pages[0]
        tags = {t.name: t.value for t in pg.tags.values()}
        print(f"{p}")
        print(f"   shape={s.shape} dtype={s.dtype} photometric={tags.get('PhotometricInterpretation')}")
        print(f"   bits={tags.get('BitsPerSample')} spp={tags.get('SamplesPerPixel')} "
              f"planar={tags.get('PlanarConfiguration')} compression={tags.get('Compression')}")
        desc = tags.get("ImageDescription")
        if desc:
            print(f"   desc={str(desc)[:300]}")
        sw = tags.get("Software")
        if sw:
            print(f"   software={sw}")
