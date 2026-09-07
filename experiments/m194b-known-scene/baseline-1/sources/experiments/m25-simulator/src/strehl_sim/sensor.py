"""The sensor: pixel aperture, CFA sampling, and the noise chain.

Order of operations, and why it is this order
---------------------------------------------
A photosite integrates irradiance over **its own area** through **its own
colour filter**, then is read out.  So:

  1. render the continuous irradiance for each colour channel on the
     supersampled latent grid, already convolved with the optical PSF;
  2. integrate each channel over one sensor pixel's active area -- a box
     average of `S x S` latent samples.  This is the pixel-aperture MTF and it
     must happen at the sensor pitch;
  3. **take one channel per photosite** according to the RGGB pattern.

Step 3 is not "render RGB then mosaic naively": the mosaicking is a *choice of
which already-correctly-integrated channel to keep*, which is exactly what the
hardware does.  What would be wrong is to build a full-colour image at sensor
resolution and then decimate each channel onto its own half-pitch lattice
*after* any inter-channel mixing, or to apply the optical blur after sampling.
Neither happens here.

The consequence the simulator must get right is that the green lattice
Nyquist is 0.25 cyc/sensor-px while the diffraction cutoff at marked f/11
(N_eff 33) is 0.282 cyc/sensor-px, so a little green-lattice aliasing is real
and is reproduced rather than suppressed.

Noise chain (all in electrons until the last step):

    e_obs = Poisson(e_signal) + Normal(0, RN_e)
    DN    = e_obs * g + black + FPN + hot
    out   = clip(round(DN), 0, white)   as uint16

with `g = ISO / 436.8` DN/e- and `RN_e` 4.20 below ISO 400, 1.47 at or above
(fact 14).
"""

from __future__ import annotations

import numpy as np

from .config import Sensor, fpn_sigma_dn

# (x, y) offset within the 2x2 quad for each plane of an RGGB mosaic.
RGGB_OFFSET = {"R": (0, 0), "G1": (1, 0), "G2": (0, 1), "B": (1, 1)}
RGGB_CHANNEL = {"R": 0, "G1": 1, "G2": 1, "B": 2}


def pixel_aperture_integrate(latent: np.ndarray, supersample: int) -> np.ndarray:
    """Box-average `S x S` latent samples into one sensor pixel.

    Works on (H, W) or (H, W, C).  H and W must be multiples of `S`.
    """
    s = supersample
    if latent.ndim == 2:
        h, w = latent.shape
        return latent.reshape(h // s, s, w // s, s).mean(axis=(1, 3))
    h, w, c = latent.shape
    return latent.reshape(h // s, s, w // s, s, c).mean(axis=(1, 3))


def mosaic(channels: np.ndarray) -> np.ndarray:
    """RGGB mosaic: pick one channel per photosite.

    `channels` is (H, W, 3) at SENSOR resolution, in electrons.  Returns
    (H, W) with `R` at (0,0), `G1` at (1,0), `G2` at (0,1), `B` at (1,1) in
    (x, y), matching `raw_pattern = [[0,1],[3,2]]`.
    """
    h, w, _ = channels.shape
    out = np.empty((h, w), dtype=channels.dtype)
    out[0::2, 0::2] = channels[0::2, 0::2, 0]   # R
    out[0::2, 1::2] = channels[0::2, 1::2, 1]   # G1
    out[1::2, 0::2] = channels[1::2, 0::2, 1]   # G2
    out[1::2, 1::2] = channels[1::2, 1::2, 2]   # B
    return out


class FixedPattern:
    """The sensor's time-invariant defects: DSNU and the hot-pixel population.

    Built once per simulated *sensor*, not per frame -- that is the whole point
    of "fixed" pattern, and a simulator that redraws it per frame would let a
    frame average remove something that in reality does not average away
    (M4 §4).
    """

    def __init__(self, shape, iso: float, sensor: Sensor,
                 seed: int = 12345,
                 row_frac: float = 1 / 3, col_frac: float = 1 / 3):
        """`row_frac` / `col_frac` split DSNU variance into row, column and
        per-pixel parts.

        MEASURED: M4 §7 gives the total sigma_FPN per ISO; M5 §"root cause"
        establishes that the pattern is **not spectrally white** and carries
        row/column structure at low frequency.  The 1/3 : 1/3 : 1/3 split is
        ARGUED, not measured -- M4 published a scalar, not a decomposition.
        It is a knob so that the report can state what it is.
        """
        rng = np.random.default_rng(seed)
        h, w = shape
        total = fpn_sigma_dn(iso)
        pix_frac = max(0.0, 1.0 - row_frac - col_frac)
        s_row = total * np.sqrt(row_frac)
        s_col = total * np.sqrt(col_frac)
        s_pix = total * np.sqrt(pix_frac)

        self.dsnu = (rng.normal(0.0, s_row, size=(h, 1)).astype(np.float32)
                     + rng.normal(0.0, s_col, size=(1, w)).astype(np.float32)
                     + rng.normal(0.0, s_pix, size=(h, w)).astype(np.float32))
        self.sigma_fpn_dn = total

        # Hot pixels.  MEASURED (M22 fact 160/161): 0.0346 % of the sensor,
        # excess +3.0 DN MEAN and 0.0 DN MEDIAN, only ~3 px sensor-wide above
        # +100 DN.  A median of exactly zero with a positive mean means the
        # distribution is a point mass at ~0 plus a heavy tail, so that is what
        # is drawn: half the map contributes nothing and the rest is lognormal,
        # scaled to hit the measured mean.
        n_hot = int(round(sensor.hot_fraction * h * w))
        self.hot = np.zeros((h, w), np.float32)
        if n_hot > 0:
            idx = rng.choice(h * w, size=n_hot, replace=False)
            live = np.zeros(n_hot, bool)
            live[rng.choice(n_hot, size=n_hot // 2, replace=False)] = True
            mag = np.zeros(n_hot, np.float64)
            k = int(live.sum())
            if k:
                # sigma 2.0 in log space puts ~3 px per full sensor above
                # +100 DN at the measured hot-pixel count, matching fact 161.
                draw = rng.lognormal(mean=0.0, sigma=2.0, size=k)
                # M22's +3.0 DN is the mean excess ACROSS THE FLAGGED PIXELS,
                # not across the sensor -- a sensor-wide mean of 3.0 DN at a
                # 0.0346 % hot fraction would be 8670 DN per hot pixel, which
                # is above the white level.  Getting this wrong once produced
                # a hot map with 0.001 DN of effect; see the report.
                draw *= (sensor.hot_mean_dn * n_hot / max(draw.sum(), 1e-9))
                mag[live] = draw
            flat = self.hot.reshape(-1)
            flat[idx] = mag.astype(np.float32)
            self.hot_idx = idx
        else:
            self.hot_idx = np.zeros(0, np.int64)
        self.n_hot = n_hot


def expose(electrons: np.ndarray, iso: float, sensor: Sensor,
           fixed: FixedPattern | None, rng: np.random.Generator,
           shot: bool = True, read: bool = True,
           gain_dn_per_e: float | None = None) -> np.ndarray:
    """Electrons in, raw DN out (uint16).

    `gain_dn_per_e` overrides the calibrated `ISO/436.8` -- the hook the
    negative control (Gate 2) uses to mis-specify `g`.
    """
    g = sensor.gain_dn_per_e(iso) if gain_dn_per_e is None else gain_dn_per_e
    rn = sensor.read_noise_e(iso)

    e = np.maximum(electrons, 0.0)
    if shot:
        e = rng.poisson(e).astype(np.float64)
    if read:
        e = e + rng.normal(0.0, rn, size=e.shape)

    dn = e * g + sensor.black
    if fixed is not None:
        dn = dn + fixed.dsnu + fixed.hot
    return np.clip(np.rint(dn), 0.0, sensor.white).astype(np.uint16)


def green_planes(raw: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """`(G1, G2)` from an RGGB frame or stack, matching
    `raw_image_visible[0::2,1::2]` and `[1::2,0::2]` -- the convention every
    committed analysis script uses.  Indexed with `...` so a (K, H, W) stack
    is not silently sliced along the frame axis."""
    return raw[..., 0::2, 1::2], raw[..., 1::2, 0::2]
