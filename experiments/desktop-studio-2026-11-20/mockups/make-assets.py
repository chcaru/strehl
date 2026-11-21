"""Build the mockups' imagery and illustrative data from the owner's own captures.

Reads only: large offscreen renders of the desktop (made with the installed
Strehl.exe --offscreen-screenshot), the desktop's explorer preview cache, and the
embedded camera JPEGs of one source bracket. Writes small files to
./outputs/assets, which git ignores: the pictures are private captures.

    python make-assets.py SHOTS_DIR SOURCE_BRACKET_DIR

The depth map, ridge, core-sample grid, soft-spot mask and draft proof are
computed here from the UNALIGNED embedded camera JPEGs (local Laplacian energy,
smoothed, sharpest plane per area). They illustrate the proposed displays. They
are not engine output: the application would draw the engine's recorded focus
evidence instead.
"""
import base64
import io
import json
import os
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs" / "assets"
PHOTO_RECT = (492, 40, 3426, 1996)  # the photograph inside a 3600x2250 --edit render

# index in the de-duplicated, modification-time-ordered explorer preview cache -> name
LIBRARY = {
    1: "star-sand", 3: "chia", 5: "tweezers", 7: "peacock-ore", 9: "garnet", 12: "marigold",
    14: "slide", 16: "jewel-weevil", 26: "scarab-green", 29: "elytra-brown", 33: "bubbles",
    35: "chip", 43: "weevil-blue", 57: "bee", 64: "jewel-beetle", 69: "spotted-beetle",
    71: "weevil-orange", 73: "white-beetle", 78: "net-beetle", 19: "weevil-tan",
}
TODAY = {"run-default": "today-process", "capture": "today-capture", "run-edit": "today-edit",
         "source-metadata": "today-metadata"}


def save(image, name, quality):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{name}.jpg"
    image.convert("RGB").save(path, "JPEG", quality=quality, optimize=True, progressive=True)
    print(f"{name}.jpg", image.size, path.stat().st_size)


def save_png(image, name):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{name}.png"
    image.save(path, "PNG", optimize=True)
    print(f"{name}.png", image.size, path.stat().st_size)


def renders(shots):
    hero = Image.open(shots / "hero-edit.png").crop(PHOTO_RECT)
    save(hero.resize((1500, 1000), Image.LANCZOS), "hero", 82)
    save(hero.resize((480, 320), Image.LANCZOS), "hero-small", 78)
    for name, out in (("hero-zoom-a", "detail-a"), ("hero-zoom-b", "detail-b")):
        crop = Image.open(shots / f"{name}.png").crop(PHOTO_RECT)
        save(crop.resize((960, 640), Image.LANCZOS), out, 80)
    for name, out in TODAY.items():
        path = shots / f"{name}.png"
        if path.exists():
            save(Image.open(path).resize((1400, 875), Image.LANCZOS), out, 72)


def library():
    cache = Path(os.environ["LOCALAPPDATA"]) / "Strehl" / "explorer-previews"
    seen = {}
    for path in sorted(cache.glob("*.preview"), key=lambda p: p.stat().st_mtime):
        data = path.read_bytes()
        (n,) = struct.unpack("<I", data[:4])
        head = json.loads(data[4:4 + n])
        w, h = head["size"]
        body = data[4 + n:4 + n + w * h * 4]
        if len(body) != w * h * 4:
            continue
        key = hash(body[::997])
        if key not in seen:
            seen[key] = Image.frombytes("RGBA", (w, h), body)
    for index, image in enumerate(seen.values()):
        if index in LIBRARY:
            save(image.resize((384, 256), Image.LANCZOS), f"lib-{LIBRARY[index]}", 80)


def thumb(path):
    import rawpy

    with rawpy.imread(str(path)) as raw:
        data = raw.extract_thumb()
    return Image.open(io.BytesIO(bytes(data.data))).convert("RGB")


def planes(bracket):
    files = sorted(bracket.glob("*.ARW"))
    picks = [round(i * (len(files) - 1) / 11) for i in range(12)]
    for slot, index in enumerate(picks):
        image = thumb(files[index])
        save(image.resize((300, 200), Image.LANCZOS), f"plane-{slot:02d}", 72)
        if slot in (3, 6, 9):
            save(image.resize((1200, 800), Image.LANCZOS), f"plane-{slot:02d}-large", 78)
    print("plane indices", [p + 1 for p in picks], "of", len(files))


def sharpness(gray, sigma):
    import cv2

    return cv2.GaussianBlur(np.abs(cv2.Laplacian(gray, cv2.CV_32F, ksize=3)), (0, 0), sigma)


def focus_layers(bracket):
    """Illustrative depth evidence from the unaligned camera JPEGs (see the module note)."""
    import cv2

    files = sorted(bracket.glob("*.ARW"))
    picks = list(range(0, len(files), 3))
    w, h = 480, 320
    pw, ph = 720, 480
    cut = int(len(picks) * 0.42)
    energy = np.zeros((len(picks), h, w), np.float32)
    best = np.full((ph, pw), -1.0, np.float32)
    proof = np.zeros((ph, pw, 3), np.float32)
    for slot, index in enumerate(picks):
        image = thumb(files[index])
        full = np.asarray(image, np.float32).mean(axis=2)
        energy[slot] = cv2.resize(sharpness(full, 5.0), (w, h), interpolation=cv2.INTER_AREA)
        if slot <= cut:
            mid = np.asarray(image.resize((pw, ph), Image.LANCZOS), np.float32)
            score = sharpness(mid.mean(axis=2), 5.0)
            take = score > best
            best[take] = score[take]
            proof[take] = mid[take]
    save(Image.fromarray(np.clip(proof, 0, 255).astype(np.uint8)), "proof-partial", 78)

    peak = energy.max(axis=0)
    order = cv2.medianBlur(energy.argmax(axis=0).astype(np.uint8), 9)
    floor = np.percentile(peak, 70)
    support = np.clip((peak - floor) / (np.percentile(peak, 99) - floor), 0, 1)
    colour = cv2.applyColorMap((255 - order.astype(np.float32) * 255 / (len(picks) - 1)).astype(np.uint8),
                               cv2.COLORMAP_PLASMA)[:, :, ::-1]
    alpha = (np.clip(support * 3, 0, 1) * 235).astype(np.uint8)
    save_png(Image.fromarray(np.dstack([colour, alpha]), "RGBA"), "lens-depth")

    hero = np.asarray(Image.open(OUT / "hero.jpg").convert("L").resize((w, h), Image.LANCZOS), np.float32)
    subject = cv2.GaussianBlur(hero, (0, 0), 2.0) > 26
    soft = subject & (peak < np.percentile(peak[subject], 10))
    soft = cv2.morphologyEx(soft.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)).astype(bool)
    yy, xx = np.mgrid[0:h, 0:w]
    hatch = ((xx + yy) // 3) % 2 == 0
    rgba = np.zeros((h, w, 4), np.uint8)
    rgba[soft & hatch] = (255, 143, 63, 235)
    rgba[soft & ~hatch] = (255, 143, 63, 70)
    save_png(Image.fromarray(rgba, "RGBA"), "lens-soft")
    print("soft share of subject", round(float(soft.sum()) / max(1, int(subject.sum())), 4))

    owned = np.array([(peak * (order == p)).sum() for p in range(len(picks))], np.float32)
    ridge = np.convolve(owned, np.ones(3) / 3, mode="same")
    gw, gh = 24, 16
    cells = energy.reshape(len(picks), gh, h // gh, gw, w // gw).mean(axis=(2, 4))
    strength = cells.max(axis=0) - cells.min(axis=0)
    shaped = np.clip((cells - cells.min(axis=0)) / np.maximum(strength, 1e-6), 0, 1) ** 2.0
    grid = (shaped * 255).astype(np.uint8)
    data = {
        "planes": len(files), "sampled": len(picks), "grid_w": gw, "grid_h": gh,
        "ridge": [round(float(v), 4) for v in ridge / ridge.max()],
        "strength": [round(float(v), 4) for v in (strength / strength.max()).ravel()],
        "grid": base64.b64encode(np.ascontiguousarray(grid.transpose(1, 2, 0)).tobytes()).decode("ascii"),
    }
    (OUT / "data.json").write_text(json.dumps(data), encoding="utf-8")
    print("data.json", (OUT / "data.json").stat().st_size)

    live = np.asarray(Image.open(OUT / "plane-06-large.jpg").convert("L"), np.float32)
    edges = np.abs(cv2.Laplacian(cv2.GaussianBlur(live, (0, 0), 1.0), cv2.CV_32F, ksize=3))
    mask = cv2.dilate((edges > np.percentile(edges, 98.6)).astype(np.uint8), np.ones((2, 2), np.uint8)).astype(bool)
    peaking = np.zeros(live.shape + (4,), np.uint8)
    peaking[mask] = (64, 224, 255, 255)
    save_png(Image.fromarray(peaking, "RGBA"), "peaking")


if __name__ == "__main__":
    shots_dir, bracket_dir = Path(sys.argv[1]), Path(sys.argv[2])
    renders(shots_dir)
    library()
    planes(bracket_dir)
    focus_layers(bracket_dir)
