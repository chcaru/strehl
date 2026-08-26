import sys, os
from PIL import Image, ImageCms
Image.MAX_IMAGE_PIXELS = None
p = sys.argv[1]
im = Image.open(p)
print("path       :", os.path.basename(p))
print("format     :", im.format)
print("mode       :", im.mode)
print("size       :", im.size)
icc = im.info.get("icc_profile")
print("icc bytes  :", len(icc) if icc else None)
if icc:
    import io
    pr = ImageCms.ImageCmsProfile(io.BytesIO(icc))
    print("icc name   :", ImageCms.getProfileName(pr).strip())
    print("icc desc   :", ImageCms.getProfileDescription(pr).strip())
for k in sorted(im.tag_v2.keys()) if hasattr(im,"tag_v2") else []:
    from PIL.TiffTags import TAGS
    nm = TAGS.get(k, str(k))
    v = im.tag_v2[k]
    s = str(v)
    if len(s) > 90: s = s[:90] + "..."
    print(f"  tag {k:<6} {nm:<28} {s}")
