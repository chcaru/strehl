r"""V-ADJ13 arm MASTER: what the 13 unresolved subjects read TODAY, and what the
same masters read AT THE WINDOW THE EXPIRED ACQUITTALS WERE MEASURED IN.

WHY THIS EXISTS SEPARATELY FROM THE GATE

Six acquittals expired. Three expired because `flattest()` chose a different
window, and the gate is explicit that comparing two values measured in two
different places is a category error. But the gate cannot tell a WINDOW MOVE
from a RENDER CHANGE, because it only ever measures today's render in today's
window. Those are different findings with different remedies:

    WINDOW MOVE     the render is unchanged where the acquittal was adjudicated;
                    `flattest()` found a flatter place. Re-adjudicate at the new
                    window; nothing about the product moved.
    RENDER CHANGE   the same pixels read differently than they did. The
                    acquittal is void on its merits and the merge has to be
                    re-examined.

The discriminator is one measurement the gate never takes: today's master,
evaluated AT THE OLD RECORDED WINDOW. If that reproduces the recorded value,
the pixels did not move and the window did.

Statistics are IMPORTED from the gate's own modules, never re-typed
(orch_blotch.blotch_ratio/flattest/lum_of, orch_chroma.chroma_blotch), so a
number here and a number from `orch_printready.py` are the same number.

READ-ONLY on DELIVER-V6 and on D:\personal\macro. Writes one JSON under
C:\dev\strehl-out\V-ADJ13.

usage: python vadj_master.py [subject ...]
"""
import json
import pathlib
import sys

import numpy as np
import tifffile

ORCH = r"C:\dev\blog\death-of-software\projects\strehl\experiments\ORCH-drift-check"
if ORCH not in sys.path:
    sys.path.insert(0, ORCH)

from orch_blotch import blotch_ratio, flattest, lum_of      # noqa: E402
from orch_blotch import WIN as BWIN                         # noqa: E402
from orch_chroma import chroma_blotch                       # noqa: E402
from orch_chroma import WIN as CWIN                         # noqa: E402

MASTERS = pathlib.Path(r"C:\dev\strehl-out\DELIVER-V6\masters")
BASELINE = pathlib.Path(ORCH).parents[0] / "V-REVIEW" / "vr_baseline.json"
OUT = pathlib.Path(r"C:\dev\strehl-out\V-ADJ13")

SUBJECTS = [
    # the six whose acquittal EXPIRED
    "112MSDCF", "113MSDCF", "coffee-bubbles", "couch-fibers-cpl",
    "flower-inner-edge-cpl", "foam",
    # the seven that stand at REVIEW, never adjudicated
    "chia-seeds-cpl", "dime-flat-narrow-slices-cpl", "duck-tape-side-layers-cpl",
    "maldon-sea-salt-cpl", "medication-pill-cpl", "pottery-art-glazed-cpl",
    "unpopped-popcorn-kernels-cpl",
]


def measure(rgb, old_blotch_yx=None, old_chroma_yx=None):
    """Gate terms, plus the same terms forced into the old recorded windows."""
    lum = lum_of(rgb)
    y, x = flattest(lum)
    r, bd, nd, md = blotch_ratio(lum[y:y + BWIN, x:x + BWIN])
    out = {
        "blotch": float(r), "blotch_band_dn": float(bd),
        "blotch_noise_dn": float(nd), "blotch_mean_dn": float(md),
        "blotch_window_yx": [int(y), int(x)],
        "shape": [int(rgb.shape[0]), int(rgb.shape[1])],
    }
    if old_blotch_yx is not None:
        oy, ox = int(old_blotch_yx[0]), int(old_blotch_yx[1])
        if oy + BWIN <= lum.shape[0] and ox + BWIN <= lum.shape[1]:
            r2, bd2, nd2, md2 = blotch_ratio(lum[oy:oy + BWIN, ox:ox + BWIN])
            out["blotch_at_old_window"] = float(r2)
            out["blotch_band_dn_at_old_window"] = float(bd2)
            out["blotch_noise_dn_at_old_window"] = float(nd2)
            out["blotch_mean_dn_at_old_window"] = float(md2)
        else:
            out["blotch_at_old_window"] = None
        out["old_blotch_window_yx"] = [oy, ox]
    del lum

    cb = chroma_blotch(rgb)
    if cb is not None:
        out["chroma"] = float(cb[0])
        out["chroma_a_rms"] = float(cb[1])
        out["chroma_b_rms"] = float(cb[2])
        # THE GATE NEVER RECORDS THIS. orch_printready.verdict() puts
        # blotch_window_yx into `meas` and not chroma_window_yx, so
        # check_acquittal's window test is dead on chroma: `wnow` is always
        # None and the moved-window branch cannot fire. Recorded here because a
        # chroma acquittal that expired on VALUE may have moved WINDOW too, and
        # that is the same category error the blotch check exists to catch.
        out["chroma_window_yx"] = [int(cb[4][0]), int(cb[4][1])]
    if old_chroma_yx is not None:
        oy, ox = int(old_chroma_yx[0]), int(old_chroma_yx[1])
        if oy + CWIN <= rgb.shape[0] and ox + CWIN <= rgb.shape[1]:
            cb2 = chroma_blotch(rgb, (oy, ox))
            out["chroma_at_old_window"] = float(cb2[0]) if cb2 else None
        else:
            out["chroma_at_old_window"] = None
        out["old_chroma_window_yx"] = [oy, ox]

    hi = rgb >= 65500
    out["clip"] = float((hi.sum(axis=2) == 3).mean())
    out["crush"] = float((rgb <= 35).mean())
    return out


def main(argv):
    want = argv or SUBJECTS
    base = {}
    if BASELINE.is_file():
        base = json.load(open(BASELINE, encoding="utf-8")).get("subjects", {})
    OUT.mkdir(parents=True, exist_ok=True)
    rows = {}
    for s in want:
        p = MASTERS / ("%s.tiff" % s)
        if not p.is_file():
            print("%-30s NO MASTER at %s" % (s, p))
            continue
        rec = (base.get(s) or {}).get("master") or {}
        a = tifffile.imread(str(p))
        rgb = a[:, :, :3].astype(np.float32)
        del a
        m = measure(rgb, rec.get("blotch_window_yx"), rec.get("chroma_window_yx"))
        del rgb
        m["master_path"] = str(p)
        rows[s] = m
        old_b = rec.get("blotch")
        old_c = rec.get("chroma")
        print("%-30s blotch %.5f @%s" % (s, m["blotch"], m["blotch_window_yx"]), end="")
        if old_b is not None:
            print("  | RECORDED %.5f @%s" % (old_b, rec.get("blotch_window_yx")), end="")
        if m.get("blotch_at_old_window") is not None and old_b is not None:
            print("  | today@OLDWIN %.5f (%+.2f%% vs record)"
                  % (m["blotch_at_old_window"],
                     100.0 * (m["blotch_at_old_window"] - old_b) / old_b), end="")
        print()
        print("%-30s chroma %.5f @%s" % ("", m.get("chroma", float("nan")),
                                         m.get("chroma_window_yx")), end="")
        if old_c is not None:
            print("  | RECORDED %.5f @%s" % (old_c, rec.get("chroma_window_yx")), end="")
        if m.get("chroma_at_old_window") is not None and old_c is not None:
            print("  | today@OLDWIN %.5f (%+.2f%% vs record)"
                  % (m["chroma_at_old_window"],
                     100.0 * (m["chroma_at_old_window"] - old_c) / old_c), end="")
        print()
        sys.stdout.flush()
        with open(OUT / "vadj_master.json", "w", encoding="utf-8") as fh:
            json.dump(rows, fh, indent=1, sort_keys=True)
    print("\nwrote %s" % (OUT / "vadj_master.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
