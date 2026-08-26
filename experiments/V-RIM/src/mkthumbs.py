from pathlib import Path
from PIL import Image
src = Path(r"C:\dev\strehl-out\gallery-1cacb61")
dst = Path(r"C:\dev\strehl-out\V-RIM\thumbs"); dst.mkdir(parents=True, exist_ok=True)
for p in sorted(src.glob("*.jpg")):
    im = Image.open(p); im.thumbnail((980, 980), Image.LANCZOS)
    q = dst / p.name; im.save(q, quality=78)
    print(f"{p.name:45s} {im.size}  {q.stat().st_size//1024} KB")
