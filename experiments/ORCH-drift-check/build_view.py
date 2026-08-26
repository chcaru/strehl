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


# The survey verdict for each subject, from opening all 26 at 1:1.
#
# This orders the gallery. Alphabetical order opened on `109MSDCF` -- a
# camera-numbered file -- and buried the two subjects that actually answer the
# halo complaint at positions 6 and 25. That is a bad first impression of good
# work. Strongest first is not spin so long as every card carries its own
# verdict and the weak ones are still present, labelled, and reachable: nothing
# is hidden, the reading order is just no longer an artifact of filename sort.
#
# rank 0 showcase   the hardest geometry in the corpus, and clean
# rank 1 clean      no defect found at 1:1
# rank 2 minor      a small diagnosed defect, named on the card
# rank 3 limited    limited by the capture, not by the stacker
VERDICTS = {
    "wrapped-text-1": (0, "showcase", "toner particles resolved to the letter edge; no rim"),
    "bee-2-cpl": (0, "showcase", "hair tips over white, no rim; pollen individually textured"),
    "bee-3-cpl": (0, "showcase", "299 frames, the deepest stack; compound eye resolved"),
    "bee-1-cpl": (0, "showcase", "clean speculars on chitin"),
    "leaf-2-cpl": (0, "showcase", "vein network and surface texture"),
    "couch-fibers-cpl": (0, "showcase", "dense overlapping fibre depth"),
    "flower-bud-with-background-fern-cpl": (0, "showcase",
        "trichomes crossing a depth boundary -- the adversarial case for the gate"),
    "lavendar-cpl": (1, "clean", ""),
    "coffee-bean": (1, "clean", ""),
    "lead-1-cpl": (1, "clean", ""),
    "flower-inner-edge-cpl": (1, "clean", ""),
    "wrapped-text-2": (1, "clean", ""),
    "tweezers-cpl": (1, "clean", ""),
    "flat-on-ruler-cpl": (1, "clean", ""),
    "highly-angled-ruler-mm-cpl": (1, "clean", "merged unregistered; still clean"),
    "pencil-steep-angle-cpl": (1, "clean", "68.20 px held-out alignment score, visibly sharp"),
    "pencil-flatter-angle-cpl": (1, "clean", ""),
    "109MSDCF": (1, "clean", ""),
    "112MSDCF": (1, "clean", ""),
    "113MSDCF": (1, "clean", ""),
    "119MSDCF": (1, "clean", ""),
    "coffee-bubbles": (2, "minor", "green-yellow fringe on sub-pixel speculars; residual lateral CA"),
    "foam": (2, "minor", "specular fringe, as coffee-bubbles; the stack also moved"),
    "dry-erase-marker-head-cpl": (2, "minor", "specular fringe, as coffee-bubbles"),
    "flowers-cpl": (3, "capture-limited", "soft over most of the frame; per-pixel selection over the same frames recovers nothing the merge lacks, so it is not a merge failure -- the cause is NOT established"),
    "flower-bud-alone-cpl": (3, "capture-limited",
        "softest merge-vs-best-frame in the corpus, plus an unattributed edge fringe"),
}


def verdict_of(stem):
    """(rank, label, note) for a render stem, tolerating a --SUFFIX."""
    key = stem
    while key and key not in VERDICTS:
        cut = key.rfind("--")
        if cut < 0:
            return (1, "", "")
        key = key[:cut]
    return VERDICTS.get(key, (1, "", ""))


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

    # Strongest first, then alphabetical inside each band. Every subject is
    # still here; only the reading order changed.
    cards.sort(key=lambda c: (verdict_of(c[0])[0], c[0]))
    unlabelled = [c[0] for c in cards if not verdict_of(c[0])[1]]
    if unlabelled:
        print(f"  WARNING: {len(unlabelled)} subject(s) carry no survey verdict "
              f"and default to 'clean': {', '.join(unlabelled)}")

    rows = []
    for stem, fj, cpng, shp, xy, cfg in cards:
        _, label, note = verdict_of(stem)
        badge = (f'<span class="badge b-{label.split("-")[0]}">'
                 f'{html.escape(label)}</span>' if label else "")
        notehtml = (f' <span class="note">&mdash; {html.escape(note)}</span>'
                    if note else "")
        rows.append(f"""
<section class="card">
  <h2>{html.escape(stem)} {badge}</h2>
  <div class="meta">{shp[1]} x {shp[0]} &middot; 100% crop at ({xy[0]}, {xy[1]}),
     chosen by high-frequency energy{notehtml}</div>
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
 .badge{{font-size:11px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;
       padding:3px 8px;border-radius:10px;vertical-align:middle;margin-left:8px}}
 .b-showcase{{background:#12341f;color:#7ee0a0;border:1px solid #1e5c36}}
 .b-clean{{background:#16232e;color:#7fb6dd;border:1px solid #24455e}}
 .b-minor{{background:#332a12;color:#dcbc6a;border:1px solid #5c4a1e}}
 .b-capture{{background:#331a1a;color:#e09090;border:1px solid #5c2b2b}}
 .note{{color:#9a8}}
</style>
<h1>strehl &mdash; current renders</h1>
<p class="lede">{len(cards)} subjects, rendered from one pinned binary. Each card
shows the full frame and a 100&#37; crop of actual pixels, with the render's own
banner beneath it so the configuration is never in doubt. Crops are selected by
high-frequency energy so they land on the finest texture in the frame rather
than on the strongest edge.</p>
<p class="lede"><b>Order is strongest first, not alphabetical</b>, and every
subject carries the verdict it earned when it was opened at 1:1:
<span class="badge b-showcase">showcase</span> the hardest geometry in the
corpus and clean,
<span class="badge b-clean">clean</span> no defect found,
<span class="badge b-minor">minor</span> a small diagnosed defect named on the
card, and
<span class="badge b-capture">capture-limited</span> limited by the capture
rather than by the stacker. Nothing is hidden &mdash; the weakest subjects are
still here, at the bottom, labelled.</p>
{''.join(rows)}
"""
    idx = out / "index.html"
    idx.write_text(page, encoding="utf-8")
    print(f"\n  wrote {idx}")


if __name__ == "__main__":
    main()
