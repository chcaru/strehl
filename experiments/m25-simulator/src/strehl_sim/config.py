"""The rig profile: every number here is a MEASURED value from this project's
own corpus, with its source named.  Nothing in this file is a guess unless the
docstring says so, and the two guesses are marked ARGUED.

Sources are `docs/research/SYNTHESIS.md` §4 fact numbers and the M-documents.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# --------------------------------------------------------------------- sensor

@dataclass(frozen=True)
class Sensor:
    """Sony A7C II (`ILCE-7CM2`).  MEASURED: M1 (levels, active area), M4
    (read noise, dual gain, FPN), M22 (hot pixels), fact 14."""

    model: str = "ILCE-7CM2"
    pixel_pitch_um: float = 5.12          # fact 4.1 / rule "Reference rig"
    width: int = 7032                     # active area, rawler
    height: int = 4688
    black: float = 512.0                  # M1, M4 §6 (median exactly 512)
    white: float = 15360.0                # fact 14 -- usable, NOT 16383
    # RGGB, raw_pattern [[0,1],[3,2]]: (0,0)=R (1,0)=G1 (0,1)=G2 (1,1)=B in (x,y).
    cfa: str = "RGGB"

    gain_divisor: float = 436.8           # g = ISO / 436.8 DN/e-  (fact 14, F)
    # M25 fact 200: this body's analog gain does NOT change below ISO 100.
    # M4's dark sigma_temporal is 0.9866 DN @ISO50 vs 0.9845 @ISO100 (ratio
    # 1.0021, model demands 0.5), and photon transfer on real signal puts both
    # ISO-50 stacks within 2-13 % of g(100) and 105-126 % away from g(50).
    # ISO 50 is an extended (pulled) ISO.  Set to None for uncorrected fact 14.
    base_iso: float | None = 100.0
    read_noise_e_low: float = 4.20        # below ISO 400
    read_noise_e_high: float = 1.47       # at/above ISO 400
    second_base_iso: float = 400.0

    # M22 fact 160/161.  Recurrence-defined map: 11,393 px = 0.0346 % of the
    # sensor, contributing +3.0 DN MEAN and 0.0 DN MEDIAN excess in real 1.3 s
    # frames, with only 3 px sensor-wide above +100 DN.
    hot_fraction: float = 0.000346
    hot_mean_dn: float = 3.0
    hot_median_dn: float = 0.0

    def gain_dn_per_e(self, iso: float) -> float:
        eff = iso if self.base_iso is None else max(iso, self.base_iso)
        return eff / self.gain_divisor

    def read_noise_e(self, iso: float) -> float:
        return (self.read_noise_e_high if iso >= self.second_base_iso
                else self.read_noise_e_low)


# M4 §7: sigma_FPN (DSNU, offset fixed pattern) in DN, per ISO, bias-corrected.
# These are per-plane means of R/G1/G2/B.
FPN_SIGMA_DN = {
    50: 0.3730, 100: 0.3768, 200: 0.3420, 250: 0.4053, 400: 0.3756,
    500: 0.3966, 640: 0.3939, 800: 0.4633, 1000: 0.5036, 1600: 0.6996,
    2000: 0.8592,
}

# M4 §8.1: sigma_temporal in DN per ISO, model-free, mean over the four planes.
# Used only as a cross-check on the simulator's own noise (never as an input).
TEMPORAL_SIGMA_DN = {
    50: 0.9866, 100: 0.9845, 200: 1.7416, 250: 2.1629, 400: 1.1986,
    500: 1.4680, 640: 1.8080, 800: 2.2465, 1000: 2.8085, 1600: 4.4054,
    2000: 5.5330,
}


def fpn_sigma_dn(iso: float) -> float:
    """Interpolate M4's measured DSNU against ISO (log-linear in ISO)."""
    import numpy as np

    isos = np.array(sorted(FPN_SIGMA_DN), dtype=float)
    vals = np.array([FPN_SIGMA_DN[int(i)] for i in isos], dtype=float)
    return float(np.interp(np.log(iso), np.log(isos), vals))


# --------------------------------------------------------------------- optics

@dataclass(frozen=True)
class Optics:
    """The composed path: FE 100mm F2.8 Macro GM OSS + 2x Viltrox TC.

    MEASURED: fact 27 (`B = 1 + m/p` in [2.41, 3.06], p ~ 1.0-1.4 at m ~ 2.0),
    fact 28 (EXIF FNumber is the MARKED aperture, not bellows-corrected).
    """

    n_marked: float = 11.0                # EXIF FNumber
    magnification: float = 2.0            # m, fact 12/27
    pupil_ratio: float = 1.0              # p, fact 27: 1.0-1.4; 1.0 is the
                                          # low end and the harsher one
    wavelength_nm: float = 535.0          # green; R/B set in render

    @property
    def bellows(self) -> float:
        return 1.0 + self.magnification / self.pupil_ratio

    @property
    def n_eff(self) -> float:
        return self.n_marked * self.bellows

    def cutoff_cyc_per_px(self, pixel_pitch_um: float,
                          wavelength_nm: float | None = None) -> float:
        """Incoherent diffraction cutoff, cycles per SENSOR pixel.

        `f_c = pitch / (lambda * N_eff)`.  At marked f/11, m=2, p=1 this is
        0.282 cyc/px against M5's measured knee at 0.2762 cyc/px (fact 27).
        """
        lam = self.wavelength_nm if wavelength_nm is None else wavelength_nm
        return pixel_pitch_um / (lam * 1e-3 * self.n_eff)


# Per-channel wavelengths, used for the DIFFRACTION term only.  Longitudinal
# chromatic aberration (a per-channel focus shift) is NOT modelled by default
# -- see the failure axes in the report.
LAMBDA_NM = {"R": 610.0, "G": 535.0, "B": 470.0}


# ------------------------------------------------------------------- geometry

@dataclass(frozen=True)
class Breathing:
    """In-camera focus bracketing: a 4-parameter similarity per frame.

    MEASURED: fact 17 (4 params suffice; affine and quadratic buy <=6%),
    fact 1 (-1.012 % over 33 frames on one stack, -1.835 % on another),
    fact 48 (the scale centre is PER STACK: (-27,-131), (+425,-449),
    (-106,-378) sensor px from centre), fact 1's supersession (drift is NOT a
    low-order polynomial in frame index).

    `total_log_scale` is the log of the frame-(N-1)/frame-0 scale ratio.  The
    per-frame series is supplied explicitly by the caller; the linear default
    is a GENERATOR CONVENIENCE and is explicitly NOT a model of the measured
    drift -- see the report's failure axes.
    """

    total_scale_change: float = -0.01012   # fact 1, 119MSDCF
    centre_x_px: float = -22.0             # fact 5 corrected by M3, 109MSDCF
    centre_y_px: float = -113.0
    rotation_rad: float = 0.0              # fact 17: unmeasurable, <=0.21 px
    tx_px: float = 0.0
    ty_px: float = 0.0


# --------------------------------------------------------- per-stack currency

@dataclass(frozen=True)
class Capture:
    """The per-stack quantities that must be FITTED, never baked (rule 5)."""

    iso: float = 160.0
    n_frames: int = 22
    # Defocus blur growth in SENSOR px of CoC diameter per frame of focus step.
    # MEASURED indirectly: M20 fact 144 ("blur-per-focus-step, measured in
    # pixels, is aperture-invariant").  The value itself is a per-stack
    # quantity -- see `fit_coc_per_frame` in `calibrate.py`.
    coc_px_per_frame: float = 3.0
    # Peak-to-peak per-frame photometric gain excursion (fact 180: 0.91 % on
    # 109MSDCF, up to 11.70 % on coffee-bean).  0.0 disables.
    gain_pp: float = 0.0


A7C2 = Sensor()
