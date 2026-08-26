"""Build a viewable gallery from a render directory.

Deliberately simple and pointed at a directory rather than hard-coded to one
gallery, because the previous builder was wired to SHIP-V1 and every re-render
needed the script edited.

For each subject it emits a downsized full frame and a 100% crop taken at the
most detailed part of the image, plus an index page. It reads the .err sidecar
next to each render and prints the CONFIGURATION on the page, because a gallery
that does not say what produced it is how SHIP-V1's provenance got lost.

The crop is chosen by high-frequency energy, not by gradient energy: an edge has
a 1/f spectrum and scores high on gradient while containing little fine texture,
so a gradient-chosen crop lands on the biggest edge rather than the finest
detail.
"""
import argparse
import html
import pathlib
import sys

import numpy as np
import tifffile
from PIL import Image

CROP = 800


def hf_energy(g):
    """High-frequency energy of a 2-D block, via its own spectrum."""
    w = np.hanning(g.shape[0])[:, None] * np.hanning(g.shape[1])[None, :]
    F = np.abs(np.fft.rfft2((g - g.mean()) * w))
    fy = np.fft.fftfreq(g.shape[0])[:, None]
    fx = np.fft.rfftfreq(g.shape[1])[None, :]
    r = np.sqrt(fy ** 2 + fx ** 2)
    return float((F[(r > 0.20) & (r <= 0.45)] ** 2).sum())


def pick_crop(lum):
    """Return (y0, x0) of the CROP-sized block with the most fine texture."""
    h, w = lum.shape
    step = CROP
    best, by, bx = -1.0, max(0, h // 2 - CROP // 2), max(0, w // 2 - CROP // 2)
    for y in range(0, max(1, h - CROP), step):
        for x in range(0, max(1, w - CROP), step):
            blk = lum[y:y + CROP, x:x + CROP]
            if blk.shape != (CROP, CROP):
                continue
            # subsample for speed; the ranking is what matters, not the value
            e = hf_energy(blk[::2, ::2])
            if e > best:
                best, by, bx = e, y, x
    return by, bx, best


def config_of(err_path):
    if not err_path.exists():
        return "(no sidecar -- provenance unknown)"
    keep = []
    for line in err_path.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        for k in ("merge backend", "noise gate", "frames", "alignment",
                  "exposure ", "output", "colour", "resolution"):
            if s.startswith(k):
                keep.append(s)
                break
        if len(keep) >= 6:
            break
    return "\n".join(keep) if keep else "(sidecar had no recognisable banner)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", nargs="?", default=r"C:\dev\strehl-out\GALLERY-NOW")
    ap.add_argument("out", nargs="?", default=r"C:\dev\strehl-out\VIEW-NOW")
    a = ap.parse_args()
    src, out = pathlib.Path(a.src), pathlib.Path(a.out)
    assets = out / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    tifs = sorted(src.glob("*.tif")) + sorted(src.glob("*.tiff"))
    if not tifs:
        sys.exit(f"no renders in {src}")
    print(f"  {len(tifs)} renders in {src}")

    cards = []
    for p in tifs:
        stem = p.stem
        a16 = tifffile.imread(str(p))
        f = a16.astype(np.float32)
        lum = 0.2126 * f[..., 0] + 0.7152 * f[..., 1] + 0.0722 * f[..., 2]
        v8 = (f / 65535.0 * 255.0).clip(0, 255).astype(np.uint8)

        full = Image.fromarray(v8)
        fw = 1400
        full_s = full.resize((fw, int(round(full.height * fw / full.width))),
                             Image.LANCZOS)
        fp = assets / f"{stem}--full.jpg"
        full_s.save(fp, quality=88, optimize=True)

        y0, x0, e = pick_crop(lum)
        crop = Image.fromarray(v8[y0:y0 + CROP, x0:x0 + CROP])
        cp = assets / f"{stem}--1to1.png"
        crop.save(cp)

        cfg = config_of(p.with_suffix(".err"))
        cards.append((stem, fp.name, cp.name, a16.shape, (x0, y0), cfg))
        print(f"    {stem:<44} crop at ({x0},{y0})  hf={e:.3g}")

    rows = []
    for stem, fj, cpng, shp, xy, cfg in cards:
        rows.append(f"""
<section class="card">
  <h2>{html.escape(stem)}</h2>
  <div class="meta">{shp[1]} x {shp[0]} &middot; 100% crop at ({xy[0]}, {xy[1]}),
     chosen by high-frequency energy</div>
  <div class="pair">
    <figure><img src="assets/{fj}" loading="lazy"><figcaption>full frame</figcaption></figure>
    <figure><img src="assets/{cpng}" loading="lazy"><figcaption>100% crop &mdash; actual pixels</figcaption></figure>
  </div>
  <pre class="cfg">{html.escape(cfg)}</pre>
</section>""")

    page = f"""<!doctype html><meta charset="utf-8">
<title>strehl &mdash; current renders</title>
<style>
 body{{background:#111;color:#ddd;font:15px/1.55 -apple-system,Segoe UI,sans-serif;
      margin:0;padding:32px}}
 h1{{font-weight:600;letter-spacing:-.02em}}
 .lede{{color:#9aa;max-width:64ch;margin-bottom:34px}}
 .card{{border-top:1px solid #2a2a2a;padding:26px 0}}
 h2{{margin:0 0 4px;font-size:19px;color:#eee}}
 .meta{{color:#888;font-size:13px;margin-bottom:14px}}
 .pair{{display:flex;gap:18px;flex-wrap:wrap}}
 figure{{margin:0}}
 img{{max-width:min(700px,46vw);height:auto;background:#000;display:block}}
 figcaption{{color:#7d8590;font-size:12px;padding-top:6px}}
 .cfg{{background:#0b0b0b;border:1px solid #262626;color:#8b9;padding:10px 12px;
       font-size:12px;white-space:pre-wrap;margin-top:14px;border-radius:4px}}
</style>
<h1>strehl &mdash; current renders</h1>
<p class="lede">{len(cards)} subjects, rendered from one pinned binary. Each card
shows the full frame and a 100&#37; crop of actual pixels, with the render's own
banner beneath it so the configuration is never in doubt. Crops are selected by
high-frequency energy so they land on the finest texture in the frame rather
than on the strongest edge.</p>
{''.join(rows)}
"""
    idx = out / "index.html"
    idx.write_text(page, encoding="utf-8")
    print(f"\n  wrote {idx}")


if __name__ == "__main__":
    main()
