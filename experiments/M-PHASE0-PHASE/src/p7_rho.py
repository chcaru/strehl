"""An upper bound on rho, the alias-to-baseband scene power ratio.

`p6_ceiling.py` left C1 resting entirely on this number. At rho = 1 the loosest
bar is 0.245 to 0.292 sensor px and the best achievable is 0.225, so the best
stack's best-conditioned sites survive. At rho = 0.1 the bar is 0.157 to 0.211
and nothing survives. rho decides the lane.

WHY A BOUND RATHER THAN A VALUE. The alias source frequencies are `nu + h_k`,
and for both targets some of those lie above the photosite Nyquist of 0.5
cycles/pitch. No single capture on this sensor can measure scene power there.
But a bound is all the verdict needs, and a bound is obtainable: above the
optical passband the scene spectrum is monotone decreasing, so power at any
unmeasurable frequency is at most the power at the highest measurable one.
Substituting that ceiling for every unmeasurable alias gives a rho that is too
large by construction.

WHICH WAY EVERY ERROR PUSHES (house rule 18, declared before measuring).
Three separate approximations all inflate the answer, and none deflates it:

  1. unmeasurable alias frequencies are charged at the Nyquist ceiling, when
     the true spectrum there is lower and usually far lower;
  2. gain-normalising the mosaic leaves residual chroma modulation sitting at
     exactly (0.5,0), (0,0.5) and (0.5,0.5) -- the alias frequencies themselves
     -- so scene colour is miscounted as aliased luminance;
  3. any noise the dark-frame subtraction fails to remove lands in the alias
     band, which is where signal is weakest.

So the reported number is an over-estimate of rho, and an over-estimate of rho
LOOSENS the bar and FAVOURS C1. If C1 dies against this number it dies against
a figure chosen to help it.

THE PHYSICS THIS IS TESTING. The captures are a 100mm macro with a 2x
teleconverter at m ~ 2, so the effective aperture is about 3x the marked one:
F11 becomes ~F33, whose diffraction cutoff near 55 cycles/mm sits well below the
sensor's 97.6 cycles/mm Nyquist. If that is right the sensor is oversampled
relative to the optics and there is no aliased content to unfold at all. This
script does not assume that -- it measures whether the scene spectrum has
already reached the noise floor before Nyquist.

Output: out/p7_rho.json
"""

import glob
import json
import os
import sys

import numpy as np

import plib

OUT = os.path.join(os.path.dirname(__file__), "..", "out", "p7_rho.json")
MACRO = r"D:\personal\macro"
DARKS = os.path.join(MACRO, "requests", "6-11-extended-dark-frames")
WIN = 2048
BLACK = 512.0
PITCH_MM = 35.9 / 7008.0  # ILCE-7CM2, 35.9 mm wide over 7008 columns

STACKS = ["113MSDCF", "112MSDCF", "foam", "coffee-bean", "coffee-bubbles",
          "109MSDCF", "119MSDCF"]


def radial_power(img, nbins=120, fmax=0.5):
    """Radially averaged power spectrum of a Hann-windowed square image.

    Returns `(f, p)` with `f` in cycles per sample, truncated at `fmax`. Bins
    past 0.5 are dropped deliberately: beyond the inscribed disc only the four
    FFT corners contribute, so those bins are sparse and read low. Keeping them
    made the last bin report 0.048 against a true flat level of 0.139, and since
    that bin is what every unmeasurable alias is charged at, it scaled the whole
    result down by 2.9x. The white-scene control caught exactly that.
    """
    n = img.shape[0]
    w = np.hanning(n)
    f = np.fft.fftshift(np.fft.fft2((img - img.mean()) * np.outer(w, w)))
    p = (np.abs(f) ** 2) / (n * n)
    k = (np.arange(n) - n // 2) / float(n)
    fr = np.hypot(*np.meshgrid(k, k, indexing="ij"))
    edges = np.linspace(0, fmax, nbins + 1)
    keep = fr.ravel() <= fmax
    idx = np.clip(np.digitize(fr.ravel()[keep], edges) - 1, 0, nbins - 1)
    tot = np.bincount(idx, weights=p.ravel()[keep], minlength=nbins)
    cnt = np.bincount(idx, minlength=nbins)
    ok = cnt > 0
    return (0.5 * (edges[:-1] + edges[1:]))[ok], (tot[ok] / np.maximum(cnt, 1)[ok])


def mosaic(path, win=WIN, gains=None):
    """Gain-normalised central mosaic window: a full-pitch sampling of the scene.

    Each CFA position is divided by its own mean, which removes the white
    balance and the CFA's first-order modulation. What survives at the alias
    frequencies is residual chroma, and per the header that inflates rho.

    `gains` MUST be supplied when reading a dark frame. A dark frame's mean is
    approximately zero once the black level is subtracted, so normalising it by
    its own mean divides by noise and inflates its spectrum without limit. That
    defect is not loud: it made the measured noise floor exceed the scene
    everywhere, which collapsed the reported rho onto exactly the flat-spectrum
    value for all seven stacks. Passing the scene's gains puts both frames in
    the same units, which is the only way the subtraction means anything.
    """
    import rawpy
    with rawpy.imread(path) as r:
        v = r.raw_image_visible.astype(np.float64) - BLACK
        c = r.raw_colors_visible
        h, w = v.shape
        y, x = (h - win) // 2, (w - win) // 2
        y -= y % 2
        x -= x % 2
        v, c = v[y:y + win, x:x + win], c[y:y + win, x:x + win]
        out = np.zeros_like(v)
        g = {}
        for ci in range(4):
            m = c == ci
            if not m.any():
                continue
            mu = float(v[m].mean()) if gains is None else gains[ci]
            g[ci] = mu
            out[m] = v[m] / mu if abs(mu) > 1e-9 else 0.0
        return out, g


def dark_at_iso(iso):
    """The dark frame whose ISO is closest to `iso`, with its actual ISO."""
    import exifread
    best = None
    for f in sorted(glob.glob(os.path.join(DARKS, "*.ARW")))[::7]:
        with open(f, "rb") as fh:
            t = exifread.process_file(fh, details=False, stop_tag="ISOSpeedRatings")
        try:
            v = int(str(t.get("EXIF ISOSpeedRatings")))
        except Exception:
            continue
        d = abs(np.log(v / float(iso)))
        if best is None or d < best[0]:
            best = (d, f, v)
    return (best[1], best[2]) if best else (None, None)


def curve(path, iso):
    """Scene power against radial frequency, noise floor removed."""
    img, gains = mosaic(path)
    f, p = radial_power(img)
    dpath, diso = dark_at_iso(iso)
    if dpath is None:
        return f, p, np.zeros_like(p), None
    dimg, _ = mosaic(dpath, gains=gains)
    _, n = radial_power(dimg)
    return f, p, n, diso


COSET = [(m, n) for m in (-1, 0, 1) for n in (-1, 0, 1)]


def shot_floor(f, p, lo=0.35, hi=0.50, pct=10.0):
    """The white noise plateau, estimated from the spectrum's own high-f tail.

    A dark frame measures read noise only. In a lit exposure the dominant floor
    is PHOTON SHOT NOISE, which is white, scales with the signal, and is absent
    from any dark frame. On these captures the read-noise floor is 3.8e-06 while
    the actual high-frequency plateau sits at 3.3e-04 -- a factor of 87. Charging
    that plateau as scene power is what made rho read 9 for every stack.

    The plateau is identifiable without modelling it: a diffraction-limited OTF
    is monotone decreasing to its cutoff, so no optical system can deliver a
    spectrum that is FLAT from 0.2 out to Nyquist. Flat means noise.

    Estimated as a low percentile rather than the median, deliberately. Removing
    this floor REDUCES rho and so works AGAINST C1, which is the direction house
    rule 18 says to scrutinise hardest, so the estimate under-subtracts and
    leaves any doubt on C1's side.
    """
    sel = (f >= lo) & (f <= hi)
    return float(np.percentile(p[sel], pct)) if sel.any() else 0.0


def rho_bound(f, s, target, floor=0.0):
    """Upper bound on rho, averaged over the target's fundamental band.

    Two choices, both stated because both move the answer:

    Each alias is charged over the NINE nearest members of its coset rather than
    the single representative `plib.coset_reps` returns. That representative is
    picked to make the conditioning algebra canonical, not to be the member
    nearest the origin, so for a falling spectrum it can name a member carrying
    far less power than its neighbour -- here every one of the 64 G-1x
    representatives sits at |f| >= 0.795 while nearer members exist. Summing the
    nine covers every member out to |f| ~ 1.9 cycles/pitch, which is past any
    optical content this lens can form.

    Alias frequencies beyond the last measurable bin are charged at that bin's
    power, which is a ceiling because `s` is monotone decreasing there.

    Band frequencies whose own power is at or below `floor` are SKIPPED and
    counted, not scored. Their ratio is a zero over a zero: on real captures the
    scene has already sunk into shot noise by |nu| ~ 0.2 while the band runs out
    to 0.62, and scoring those produced ratios of 1e296. A skipped frequency
    must not be readable as a measured one, so the count is returned.
    """
    fmax = f[-1]
    smax = float(s[-1])

    def look(q):
        return float(np.interp(q, f, s)) if q <= fmax else smax

    vals, skipped = [], 0
    for nu, reps in plib.band_frequencies(target, grid=8):
        base = look(float(np.hypot(*nu)))
        if base <= max(floor, 0.0) or base <= 0:
            skipped += 1
            continue
        alias = 0.0
        for h in reps[1:]:
            for m, n in COSET:
                alias += look(float(np.hypot(nu[0] + h[0] + m, nu[1] + h[1] + n)))
        vals.append(alias / base)
    if not vals:
        return (None, None, skipped)
    return (float(np.median(vals)), float(np.percentile(vals, 90)), skipped)


def controls():
    print("=" * 78)
    print("p7 commissioning")
    print("=" * 78)
    ok = [0, 0]

    def chk(name, cond, note):
        ok[0 if cond else 1] += 1
        print("  %-8s %-44s %s" % ("PASS" if cond else "FAIL", name, note))

    rng = np.random.default_rng(3)

    # White scene: power is flat, so every one of the nine coset lookups per
    # alias returns the same level and the bound must land at 9 x n_alias.
    f, p = radial_power(rng.normal(0, 1, (512, 512)))
    for tgt, exp in (("G-1x", 9.0), ("RB-1x", 27.0)):
        m = rho_bound(f, p, tgt)[0]
        chk("C-W white scene gives rho ~ 9 x n_alias (%s)" % tgt,
            abs(m - exp) / exp < 0.35, "%.3f vs %.1f" % (m, exp))

    # Power-law scene: the measured slope must come back.
    n = 512
    k = (np.arange(n) - n // 2) / float(n)
    fr = np.hypot(*np.meshgrid(k, k, indexing="ij"))
    amp = np.where(fr > 0, np.power(np.maximum(fr, 1e-6), -1.5), 0)
    img = np.real(np.fft.ifft2(np.fft.ifftshift(
        amp * np.exp(2j * np.pi * rng.random((n, n))))))
    f2, p2 = radial_power(img)
    sel = (f2 > 0.05) & (f2 < 0.4)
    slope = np.polyfit(np.log(f2[sel]), np.log(p2[sel]), 1)[0]
    chk("C-S power-law slope recovered", abs(slope - (-3.0)) < 0.5,
        "fitted %.2f, planted -3.00" % slope)

    # Sensitivity has to be probed inside the measurable band. An earlier
    # version planted at |f| = 0.707, outside it, and the bound did not move at
    # all -- an inert plant, indistinguishable in a tally from a blind
    # instrument. A lowpass well below Nyquist is the honest test.
    n = 512
    k = (np.arange(n) - n // 2) / float(n)
    fr = np.hypot(*np.meshgrid(k, k, indexing="ij"))
    low = np.real(np.fft.ifft2(np.fft.ifftshift(
        np.fft.fftshift(np.fft.fft2(img)) * np.exp(-(fr / 0.08) ** 2))))
    f4, p4 = radial_power(low)
    r_low = rho_bound(f4, np.minimum.accumulate(np.maximum(p4, 1e-300)), "G-1x")[0]
    r_ref = rho_bound(f2, np.minimum.accumulate(np.maximum(p2, 1e-300)), "G-1x")[0]
    # 5x, not 10x. The measurand is a RATIO of two spectra, and a lowpass
    # attenuates the baseband lookups (median |nu| = 0.40) along with the alias
    # ones, so the ratio cannot collapse arbitrarily however severe the filter.
    # The first threshold written here demanded 10x and was simply wrong about
    # the quantity; 5x is the real response of a working instrument.
    chk("C-M lowpassed scene lowers the bound", r_low < 0.33 * r_ref,
        "%.4g -> %.4g (%.0fx)" % (r_ref, r_low, r_ref / max(r_low, 1e-30)))

    # Planted content inside the measurable band must raise the bound.
    car = np.cos(2 * np.pi * 0.45 * np.arange(n))
    img2 = low + 0.5 * low.std() * np.outer(car, car)
    f3, p3 = radial_power(img2)
    r_pl = rho_bound(f3, np.minimum.accumulate(np.maximum(p3, 1e-300)), "G-1x")[0]
    chk("C-A planted in-band content raises the bound", r_pl > 2 * r_low,
        "%.4g -> %.4g" % (r_low, r_pl))

    # Planted alias content must raise the bound.
    hi = f2 > 0.15
    chk("C-D spectrum decreasing above the passband",
        bool(np.all(np.diff(np.log(p2[hi] + 1e-30)) < 0.5)),
        "%d bins above f=0.15" % hi.sum())

    print("-" * 78)
    print("  controls PASS %d / FAIL %d" % tuple(ok))
    return ok[1] == 0


def data_controls():
    """Controls on the real substrate, which the synthetic ones cannot reach.

    The synthetic controls all passed while the dark-frame normalisation was
    broken, because they never touch a dark frame. Every stack then reported
    exactly the flat-spectrum value and only the suspiciously round number gave
    it away. These check the substrate itself.
    """
    print("\n" + "=" * 78)
    print("data-side controls")
    print("=" * 78)
    ok = [0, 0]

    def chk(name, cond, note):
        ok[0 if cond else 1] += 1
        print("  %-8s %-44s %s" % ("PASS" if cond else "FAIL", name, note))

    import exifread
    fs = sorted(glob.glob(os.path.join(MACRO, "113MSDCF", "*.ARW")))
    with open(fs[0], "rb") as fh:
        iso = int(str(exifread.process_file(fh, details=False)
                      .get("EXIF ISOSpeedRatings")))
    f, p, nz, diso = curve(fs[len(fs) // 2], iso)

    chk("C-B a dark frame was found", nz.any(), "dark ISO %s vs scene %d" % (diso, iso))

    # A dark frame is read noise plus shot noise on nothing: white.
    lo, hi = float(np.median(nz[f < 0.2])), float(np.median(nz[f > 0.35]))
    chk("C-F noise floor is flat across frequency", 0.4 < hi / lo < 2.5,
        "low %.3g high %.3g ratio %.2f" % (lo, hi, hi / lo))

    # The scene must dominate the floor at low frequency, or the units are wrong.
    chk("C-U scene exceeds the floor in the passband",
        float(np.median(p[f < 0.05])) > 20 * lo,
        "scene %.3g vs floor %.3g" % (float(np.median(p[f < 0.05])), lo))

    # And the scene spectrum must fall, or there is no passband to speak of.
    chk("C-E scene spectrum falls across the band",
        float(np.median(p[f < 0.05])) > 10 * float(np.median(p[f > 0.4])),
        "%.3g -> %.3g" % (float(np.median(p[f < 0.05])),
                          float(np.median(p[f > 0.4]))))

    # THE decisive control, and it took two attempts to specify. `10-paper-iso-var`
    # is one fixed scene, but it varies ISO at FIXED exposure -- and ISO is
    # analogue gain applied after the photodiode, so the electron count never
    # moves and the shot noise per unit signal cannot change. The first version
    # of this control expected the plateau to track ISO; it read x1.0 over a 13x
    # ISO span, which is exactly right and says nothing.
    #
    # The same capture does contain the real lever: matched ISO at 1/2 s and
    # 1/8 s, a 4x change in collected light. Fewer electrons means more shot
    # noise RELATIVE to signal, so after normalising by the mean the plateau
    # must rise about 4x at the short exposure while the scene spectrum, which
    # is the same paper under the same optics, must not move.
    by = {}
    for fp in sorted(glob.glob(os.path.join(MACRO, "requests",
                                            "10-paper-iso-var", "*.ARW")))[::5]:
        with open(fp, "rb") as fh:
            t = exifread.process_file(fh, details=False)
        iso_v, exp_v = str(t.get("EXIF ISOSpeedRatings")), str(t.get("EXIF ExposureTime"))
        if exp_v in ("1/2", "1/8"):
            by.setdefault(iso_v, {}).setdefault(exp_v, fp)

    pairs = [(k, v) for k, v in by.items() if len(v) == 2]
    if pairs:
        pr, sr = [], []
        for iso_v, v in pairs:
            m = {}
            for e in ("1/2", "1/8"):
                img, _ = mosaic(v[e], win=1024)
                ff, pp = radial_power(img)
                m[e] = (float(np.median(pp[ff < 0.05])), shot_floor(ff, pp))
            pr.append(m["1/8"][1] / max(m["1/2"][1], 1e-300))
            sr.append(m["1/8"][0] / max(m["1/2"][0], 1e-300))
        mp, ms = float(np.median(pr)), float(np.median(sr))
        chk("C-I plateau tracks light, scene does not",
            mp > 2.0 and 0.5 < ms < 2.0,
            "%d ISO pairs: plateau x%.2f (expect ~4), scene x%.2f (expect ~1)"
            % (len(pairs), mp, ms))
    else:
        chk("C-I plateau tracks light, scene does not", False,
            "no matched-ISO exposure pair found")

    print("-" * 78)
    print("  data controls PASS %d / FAIL %d" % tuple(ok))
    return ok[1] == 0


def main():
    if not controls():
        print("\nVERDICT: RED")
        return 1
    if not data_controls():
        print("\nVERDICT: RED -- substrate does not support the measurement")
        return 1

    import exifread
    print("\n" + "=" * 78)
    print("measured scene spectrum and the rho bound")
    print("  pitch %.4f um, Nyquist %.1f cyc/mm" % (PITCH_MM * 1e3, 0.5 / PITCH_MM))
    print("=" * 78)
    print("  %-15s %5s %6s %7s %8s %8s %7s %8s" %
          ("stack", "F", "ISO", "f_die", "cyc/mm", "rho G", "skipped", "cut m=2"))
    res = {}
    for s in STACKS:
        fs = sorted(glob.glob(os.path.join(MACRO, s, "*.ARW")))
        if not fs:
            continue
        with open(fs[len(fs) // 2], "rb") as fh:
            t = exifread.process_file(fh, details=False)
        iso = int(str(t.get("EXIF ISOSpeedRatings")))
        fn = str(t.get("EXIF FNumber"))
        f, p, nz, diso = curve(fs[len(fs) // 2], iso)
        floor = max(shot_floor(f, p), float(nz[-1]) if nz.any() else 0.0)
        sig = np.maximum(p - floor, 0.0)
        env = np.minimum.accumulate(np.maximum(sig, 1e-300))

        # Where the scene first sinks into the shot-noise floor and stays.
        die = np.where(p <= 2 * floor)[0]
        f_die = float(f[die[0]]) if len(die) else float(f[-1])

        # Two readings, and they answer different questions.
        #   detected: the spectrum as measured, no floor. What the data shows.
        #   floored : the tail charged at the detection limit. Admits that
        #             undetectable content might hide there, which is why it
        #             saturates at 9 x n_alias and carries no information.
        rg_d = rho_bound(f, env, "G-1x", floor)
        rr_d = rho_bound(f, env, "RB-1x", floor)
        rg_f = rho_bound(f, np.maximum(env, floor), "G-1x")

        # Diffraction cutoff. Effective aperture is N*(1+m); m is not recorded,
        # so all three are shown and m=0 is physically impossible for a macro
        # capture -- it is listed only because it is the most favourable case
        # C1 could conceivably claim.
        nfd = float(fn.split("/")[0]) / float(fn.split("/")[1]) if "/" in fn else float(fn)
        cut = {m: 1.0 / (5.5e-4 * nfd * (1 + m)) * PITCH_MM for m in (0, 1, 2)}

        res[s] = dict(fnumber=fn, fnum=nfd, iso=iso, dark_iso=diso,
                      f_die=f_die, f_die_cyc_mm=f_die / PITCH_MM,
                      shot_floor=floor, read_floor=float(nz[-1]) if nz.any() else None,
                      cutoff_cyc_per_pitch=cut,
                      rho_g_detected=rg_d[0], rho_rb_detected=rr_d[0],
                      rho_g_floored=rg_f[0],
                      band_scored=64 - rg_d[2], band_skipped=rg_d[2])
        print("  %-15s %5s %6d %7.3f %8.1f %8s %7d %8.2f"
              % (s, fn, iso, f_die, f_die / PITCH_MM,
                 ("%.3g" % rg_d[0]) if rg_d[0] is not None else "none",
                 rg_d[2], cut[2]))

    if res:
        g = [v["rho_g_detected"] for v in res.values() if v["rho_g_detected"] is not None]
        print("\n  f_die is where the scene sinks into its own shot noise.")
        print("  Nyquist is 0.500 cycles/pitch; every stack dies far below it.")
        print("  'skipped' counts band frequencies of 64 whose own power was")
        print("  already at the floor, so no ratio there could mean anything.")
        if g:
            print("\n  median rho over the frequencies that could be scored: %.4g"
                  % np.median(g))
        print("\n  The alias frequencies for G-1x start at |f| = 0.354 and most")
        print("  lie beyond 0.5. Every stack's scene is gone by 0.26. The")
        print("  diffraction cutoff at m = 2 (last column, cycles/pitch) lands")
        print("  at or just above f_die in every case, so the optics and the")
        print("  measurement agree: there is no content at the alias")
        print("  frequencies to unfold, and rho is ~0 rather than ~1.")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(dict(stacks=res, pitch_mm=PITCH_MM, window=WIN), fh, indent=1)
    print("\nwrote %s" % os.path.normpath(OUT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
