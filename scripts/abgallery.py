"""Full-frame context pairs + an index page for the A/B gallery.

The crops are the evidence; these are orientation. A 2400 px full frame is
EXACTLY where a few-pixel rim disappears, so nothing here should be used to
decide anything -- it exists so that when you look at a 100% crop you know
where on the picture you are standing.

Two things this does that matter:

  * Every panel is labelled with its arm, burned into the pixels. An unlabelled
    pair in a directory is not evidence, because a week later nobody can say
    which side was which.
  * The two arms share ONE display transform. Autoscaling each image to its own
    range would make a veil-lifted arm and a veil-present arm look equally
    contrasty, which is the exact defect being measured.
"""

import argparse
import html
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
import tifffile

LONG_EDGE = 2400


def read_u16_rgb(p: Path) -> np.ndarray:
    a = tifffile.imread(str(p))
    assert a.dtype == np.uint16, f"{p}: dtype {a.dtype}, expected uint16"
    assert a.ndim == 3 and a.shape[2] == 3, f"{p}: shape {a.shape}"
    return a


def label(bgr: np.ndarray, text: str) -> np.ndarray:
    out = bgr.copy()
    f, sc, th = cv2.FONT_HERSHEY_SIMPLEX, 1.6, 3
    (tw, tht), _ = cv2.getTextSize(text, f, sc, th)
    cv2.rectangle(out, (0, 0), (tw + 28, tht + 28), (0, 0, 0), -1)
    cv2.putText(out, text, (14, tht + 12), f, sc, (255, 255, 255), th, cv2.LINE_AA)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tiffs", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--ref", default="estimator")
    args = ap.parse_args()

    subjects: dict[str, dict[str, Path]] = {}
    for p in sorted(args.tiffs.glob("*--*.tiff")):
        subj, _, arm = p.stem.rpartition("--")
        subjects.setdefault(subj, {})[arm] = p

    args.out.mkdir(parents=True, exist_ok=True)
    full = args.out / "fullframe"
    full.mkdir(exist_ok=True)
    rows = []

    for subj, arms in sorted(subjects.items()):
        order = [args.ref] + sorted(k for k in arms if k != args.ref)
        order = [k for k in order if k in arms]
        if len(order) < 2:
            print(f"{subj}: only {order} -- recorded as incomplete, NOT dropped")
            rows.append((subj, order, False))
            continue

        panels = []
        for arm in order:
            a = read_u16_rgb(arms[arm]).astype(np.float32) / 65535.0
            h, w = a.shape[:2]
            sc = LONG_EDGE / max(h, w)
            small = cv2.resize(a, (int(w * sc), int(h * sc)), interpolation=cv2.INTER_AREA)
            u8 = np.clip(small * 255.0 + 0.5, 0, 255).astype(np.uint8)
            panels.append(label(u8[:, :, ::-1], f"{subj}   [{arm}]"))

        sep = np.full((panels[0].shape[0], 8, 3), 255, np.uint8)
        comp = panels[0]
        for p in panels[1:]:
            comp = np.hstack([comp, sep, p])
        cv2.imwrite(str(full / f"{subj}--FULL.jpg"), comp,
                    [cv2.IMWRITE_JPEG_QUALITY, 95])
        rows.append((subj, order, True))
        print(f"{subj}: full-frame pair {order}")

    # Crops, sited on the reference arm, applied unchanged to both.
    crops_root = args.out / "crops"
    for subj, order, ok in rows:
        if not ok:
            continue
        for site_on in (args.ref, [k for k in order if k != args.ref][0]):
            out = crops_root / f"{subj}--siteon-{site_on}"
            r = subprocess.run(
                [sys.executable, str(Path(__file__).with_name("crops.py")),
                 str(args.tiffs), "--subject", subj, "--ref", args.ref,
                 "--site-on", site_on, "--out", str(out), "--display", "none"],
                capture_output=True, text=True)
            print(f"{subj}: crops site-on {site_on} -> rc={r.returncode}")
            if r.returncode != 0:
                print(r.stdout[-1500:], r.stderr[-1500:])

    # Index. Crops first, because the crops are the finding.
    h = ["<!doctype html><meta charset=utf-8><title>strehl A/B: estimator vs pyramid</title>",
         "<style>body{background:#111;color:#ddd;font:14px system-ui;margin:24px}",
         "img{max-width:100%;border:1px solid #333}h2{margin-top:40px}",
         "a{color:#6cf}.n{color:#f96}</style>",
         "<h1>estimator vs pyramid &mdash; same binary, same flags, only --merge differs</h1>",
         "<p>See <a href='RUN.txt'>RUN.txt</a> for the binary sha256 and git commit, ",
         "<a href='manifest.tsv'>manifest.tsv</a> for per-render status.</p>",
         "<p class=n>Judge the 100% crops. The full frames are context only &mdash; ",
         "the rim is a few pixels wide and 2400 px averages it away.</p>"]

    for subj, order, ok in rows:
        h.append(f"<h2>{html.escape(subj)}</h2>")
        if not ok:
            h.append(f"<p class=n>INCOMPLETE &mdash; only rendered: {', '.join(order)}</p>")
            continue
        for site_on in (args.ref, [k for k in order if k != args.ref][0]):
            d = crops_root / f"{subj}--siteon-{site_on}"
            comps = sorted(d.glob("*--COMPOSITE.png")) if d.is_dir() else []
            if comps:
                h.append(f"<p>100% crops, sites chosen on <b>{site_on}</b> "
                         f"and applied unchanged to both arms "
                         f"(left {order[0]}, right {order[1]}):</p>")
            for c in comps:
                rel = c.relative_to(args.out).as_posix()
                h.append(f"<p>{html.escape(c.stem)}<br><img src='{rel}'></p>")
        h.append(f"<p>full frame (context only):<br>"
                 f"<img src='fullframe/{subj}--FULL.jpg'></p>")

    (args.out / "index.html").write_text("\n".join(h), encoding="utf-8")
    print(f"\nwrote {args.out / 'index.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
