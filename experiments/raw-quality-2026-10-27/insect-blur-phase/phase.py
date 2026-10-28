"""Fixed original-green phase reader. Root owns all numerical execution.

This is a local correspondence instrument, not a calibrated displacement-error
model or an occlusion detector. All producing arithmetic is f32/complex64.
"""
from dataclasses import dataclass
import math


SIDE = 128
MAX_BATCH = 32
RADIUS_NATIVE = 2.0
GRID_PER_NATIVE = 64
FREQUENCY_NATIVE = (0.02, 0.20)
MIN_STRONG_BINS = 16
MIN_EFFECTIVE_BINS = 32.0
MIN_SPECTRAL_RATIO = 0.01
MIN_SCORE = 0.20
MIN_SECONDARY_GAP = 0.02
SECONDARY_EXCLUSION_NATIVE = 0.25


@dataclass(frozen=True)
class PhaseNoise:
    gain: float
    read_variance: float
    black: float = 512.0
    white: float = 15360.0

    def validate(self):
        values = (self.gain, self.read_variance, self.black, self.white)
        if not all(math.isfinite(float(v)) for v in values):
            raise ValueError("nonfinite injected noise/levels")
        if self.gain < 0 or self.read_variance <= 0:
            raise ValueError("gain>=0 and read_variance>0 required")
        if not 0 <= self.black < self.white <= 65535:
            raise ValueError("invalid original-u16 levels")


class Reader:
    def __init__(self, torch, device="cpu"):
        self.t = torch
        self.device = torch.device(device)
        if self.device.type not in ("cpu", "cuda"):
            raise ValueError("only CPU or CUDA f32 execution supported")
        if torch.is_autocast_enabled(self.device.type):
            raise ValueError("autocast is outside this fixed f32 reader")
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        t = torch
        axis = t.hann_window(SIDE, periodic=False, dtype=t.float32, device=self.device)
        self.window = axis[:, None] * axis[None, :]
        self.window_fft = t.fft.fft2(self.window)
        freq = t.fft.fftfreq(SIDE, d=2.0, dtype=t.float32, device=self.device)
        self.fx = freq[None, :].expand(SIDE, SIDE)
        self.fy = freq[:, None].expand(SIDE, SIDE)
        radius2 = self.fx * self.fx + self.fy * self.fy
        self.band = ((radius2 >= FREQUENCY_NATIVE[0] ** 2)
                     & (radius2 < FREQUENCY_NATIVE[1] ** 2))
        n = int(2 * RADIUS_NATIVE * GRID_PER_NATIVE) + 1
        self.offsets = t.arange(n, dtype=t.float32, device=self.device) / GRID_PER_NATIVE - RADIUS_NATIVE
        self.grid_size = n
        self.matrices = {}
        for power in (1, 2):
            phase = (self.offsets[:, None] * freq[None, :]) * (2.0 * math.pi * power)
            self.matrices[power] = t.complex(t.cos(phase), t.sin(phase))
        self.pair_count = 0

    def metadata(self):
        return {
            "schema": 1, "backend": "torch-f32-complex64", "device": str(self.device),
            "side_same_phase": SIDE, "same_phase_pitch_native": 2,
            "max_batch": MAX_BATCH, "window": "symmetric Hann, arithmetic mean removed first",
            "frequency_native": list(FREQUENCY_NATIVE), "powers": [1, 2],
            "residual_radius_native": RADIUS_NATIVE, "grid_per_native": GRID_PER_NATIVE,
            "min_strong_conjugate_bins": MIN_STRONG_BINS,
            "min_effective_conjugate_bins": MIN_EFFECTIVE_BINS,
            "min_spectral_eigen_ratio": MIN_SPECTRAL_RATIO,
            "min_normalized_score": MIN_SCORE, "min_secondary_gap": MIN_SECONDARY_GAP,
            "secondary_exclusion_native": SECONDARY_EXCLUSION_NATIVE,
            "weight": "product of max(P-N,0)/(max(P-N,0)+N), identical for both powers",
            "noise": "injected gain*max(raw-black,0)+read_variance; exact linear demeaning/window propagation",
            "clipped_label_semantics": "configured zero/working-white admission, not measured physical sensor saturation",
            "quantization_variance_added": False, "interpolation": False, "source_rgb": False,
            "source_storage": "u16", "arithmetic": "f32/complex64",
            "tf32_matmul": bool(self.t.backends.cuda.matmul.allow_tf32),
            "tf32_cudnn": bool(self.t.backends.cudnn.allow_tf32),
            "pair_count": self.pair_count,
            "effective_bins_are_independent_observations": False,
            "confidence_calibrated": False, "physical_error_identified": False,
        }

    def _coordinates(self, values, batch, name, *, integer=False):
        t = self.t
        a = t.as_tensor(values, dtype=t.float32, device=self.device)
        if a.shape == (2,):
            a = a[None, :].expand(batch, 2)
        if a.shape != (batch, 2) or not bool(t.isfinite(a).all().item()):
            raise ValueError(f"{name} must be finite xy or Bx2")
        if integer and not bool((a == a.round()).all().item()):
            raise ValueError(f"{name} must use integer native pixels")
        return a

    def _source(self, values, name):
        t = self.t
        a = t.as_tensor(values)
        if a.dtype != t.uint16 or a.ndim != 3 or tuple(a.shape[1:]) != (SIDE, SIDE):
            raise ValueError(f"{name} requires Bx128x128 original uint16")
        if not 1 <= a.shape[0] <= MAX_BATCH:
            raise ValueError("batch outside fixed1..32 bound")
        # Copy before subtraction: never alias or mutate original cached storage.
        return a.to(device=self.device, dtype=t.float32, copy=True)

    def _fft_and_noise(self, raw, noise):
        t = self.t
        signal = raw - float(noise.black)
        variance = signal.clamp_min(0.0) * float(noise.gain) + float(noise.read_variance)
        demeaned = signal - signal.mean(dim=(-2, -1), keepdim=True)
        spectrum = t.fft.fft2(demeaned * self.window)
        # Linear row of FFT(window*(x-mean(x))):
        # w[n]*exp(-ikn) - FFT(w)[k]/M. This includes its shared mean covariance.
        m = float(SIDE * SIDE)
        first = (variance * (self.window * self.window)).sum(dim=(-2, -1), keepdim=True)
        vw = t.fft.fft2(variance * self.window)
        cross = (self.window_fft.conj() * vw).real * (2.0 / m)
        last = (self.window_fft.real.square() + self.window_fft.imag.square())
        last = last * (variance.sum(dim=(-2, -1), keepdim=True) / (m * m))
        fft_noise = first - cross + last
        # The analytic variance is nonnegative; only roundoff at suppressed DC
        # can make it negative. Band-supported values must be strictly positive.
        if not bool((fft_noise[:, self.band] > 0).all().item()):
            raise ValueError("nonpositive propagated spectral variance in fixed band")
        if spectrum.dtype != t.complex64 or fft_noise.dtype != t.float32:
            raise RuntimeError("reader arithmetic dtype drift")
        return spectrum, fft_noise.clamp_min(t.finfo(t.float32).tiny)

    def compare(self, reference_u16, moving_u16, noise, **kwargs):
        t = self.t
        a, b = t.as_tensor(reference_u16), t.as_tensor(moving_u16)
        if a.shape != (SIDE, SIDE) or b.shape != (SIDE, SIDE):
            raise ValueError("compare requires two128x128 original phases")
        return self.compare_batch(a[None], b[None], noise, **kwargs)[0]

    def compare_batch(self, reference_u16, moving_u16, noise, *, seed_native_xy=(0, 0),
                      phase="G1", reference_origin_native_xy=None,
                      moving_origin_native_xy=None, return_surfaces=False):
        """Return a list of complete p1/p2 records, in input pair order.

        Seed is integer PATCH displacement in native units. Returned total
        displacement adds moving-origin minus reference-origin. This seeded
        local branch does not resolve the global half-period ambiguity.
        Optional score surfaces are CPU float32 tensors, not JSON values.
        """
        noise.validate()
        if phase not in ("G1", "G2"):
            raise ValueError("only separately observed physical G1/G2 are supported")
        t = self.t
        if t.is_autocast_enabled(self.device.type) or t.backends.cuda.matmul.allow_tf32 or t.backends.cudnn.allow_tf32:
            raise ValueError("autocast/TF32 state changed outside frozen f32 contract")
        with t.no_grad():
            a, b = self._source(reference_u16, "reference"), self._source(moving_u16, "moving")
            if a.shape != b.shape:
                raise ValueError("pair batch shapes differ")
            batch = a.shape[0]
            offset = (1, 0) if phase == "G1" else (0, 1)
            oa = self._coordinates(offset if reference_origin_native_xy is None else reference_origin_native_xy,
                                   batch, "reference origin", integer=True)
            ob = self._coordinates(offset if moving_origin_native_xy is None else moving_origin_native_xy,
                                   batch, "moving origin", integer=True)
            for origin in (oa, ob):
                if not bool(((origin.remainder(2) == t.tensor(offset, device=self.device)).all()).item()):
                    raise ValueError("original physical phase/origin mismatch")
            seed = self._coordinates(seed_native_xy, batch, "seed", integer=True)
            # Caller supplies the local branch, including deliberately wrong
            # branches in controls. This reader cannot certify a global branch.
            if not bool((seed.abs() <= 4096).all().item()):
                raise ValueError("seed exceeds bounded native-coordinate support")
            clipped = ((a <= 0) | (a >= noise.white)).sum(dim=(-2, -1))
            clipped += ((b <= 0) | (b >= noise.white)).sum(dim=(-2, -1))
            fa, na = self._fft_and_noise(a, noise)
            fb, nb = self._fft_and_noise(b, noise)
            pa = fa.real.square() + fa.imag.square()
            pb = fb.real.square() + fb.imag.square()
            sa, sb = (pa - na).clamp_min(0), (pb - nb).clamp_min(0)
            weight = (sa / (sa + na)) * (sb / (sb + nb)) * self.band
            cross = fb * fa.conj()
            magnitude = cross.abs()
            unit = cross / magnitude.clamp_min(t.finfo(t.float32).tiny)
            weight = t.where(magnitude > 0, weight, t.zeros_like(weight))
            sums = weight.sum(dim=(-2, -1))
            safe_sum = sums.clamp_min(t.finfo(t.float32).tiny)
            effective = sums.square() / weight.square().sum(dim=(-2, -1)).clamp_min(t.finfo(t.float32).tiny)
            strong = (self.band & (pa > 4 * na) & (pb > 4 * nb)).sum(dim=(-2, -1))
            moments = t.stack(((weight * self.fx.square()).sum((-2, -1)),
                               (weight * self.fx * self.fy).sum((-2, -1)),
                               (weight * self.fy.square()).sum((-2, -1))), dim=-1) / safe_sum[:, None]
            matrix = t.stack((moments[:, 0], moments[:, 1], moments[:, 1], moments[:, 2]), dim=-1).reshape(batch, 2, 2)
            eigen = t.linalg.eigvalsh(matrix)
            spectral_ratio = eigen[:, 0] / eigen[:, 1].clamp_min(t.finfo(t.float32).tiny)
            shared_values = t.stack((oa[:, 0], oa[:, 1], ob[:, 0], ob[:, 1], seed[:, 0], seed[:, 1],
                                     clipped.float(), strong.float(), effective, sums,
                                     eigen[:, 0], eigen[:, 1], spectral_ratio,
                                     na[:, self.band].mean(dim=1), nb[:, self.band].mean(dim=1)), dim=1).cpu().tolist()
            shared = []
            for values in shared_values:
                ax, ay, bx, by, sx, sy, clip_count, strong_count, ess, weight_sum, eig0, eig1, rank_ratio, noise_a, noise_b = values
                reasons = []
                if int(clip_count):
                    reasons.append("CLIPPED_SOURCE")
                if int(strong_count) < MIN_STRONG_BINS or ess < MIN_EFFECTIVE_BINS:
                    reasons.append("INSUFFICIENT_FREQUENCY_SUPPORT")
                if rank_ratio < MIN_SPECTRAL_RATIO:
                    reasons.append("SPECTRAL_RANK")
                shared.append({
                    "phase": phase, "reference_origin_native_xy": [ax, ay],
                    "moving_origin_native_xy": [bx, by], "seed_native_xy": [sx, sy],
                    "clipped_sample_count": int(clip_count),
                    "clipped_count_is_working_limit_admission": True,
                    "strong_conjugate_bin_count": int(strong_count),
                    "effective_conjugate_bins": ess,
                    "weight_sum": weight_sum, "spectral_eigenvalues": [eig0, eig1],
                    "spectral_eigen_ratio": rank_ratio,
                    "noise_power_band_mean_reference": noise_a,
                    "noise_power_band_mean_moving": noise_b,
                    "shared_refusals": reasons, "independent_bins_claimed": False,
                })
            records = [{"schema": 1, "shared": s, "physical_error_identified": False} for s in shared]
            for power in (1, 2):
                phasor = unit if power == 1 else unit * unit
                # Exact integer periodic reduction avoids unnecessary large-angle
                # f32 error, while output displacement retains the declared seed.
                periodic_seed = seed.remainder(2 * SIDE // power)
                seeded_phase = (self.fx * periodic_seed[:, 0, None, None] + self.fy * periodic_seed[:, 1, None, None]) * (2 * math.pi * power)
                seeded = phasor * t.complex(t.cos(seeded_phase), t.sin(seeded_phase)) * weight
                dft = self.matrices[power]
                surface = (dft @ seeded @ dft.transpose(0, 1)).real / safe_sum[:, None, None]
                if not bool(t.isfinite(surface).all().item()):
                    raise RuntimeError("nonfinite local phase score")
                pooled = t.nn.functional.max_pool2d(surface[:, None], 3, stride=1, padding=1)[:, 0]
                local_maxima = surface >= pooled
                flat_indices = surface.reshape(batch, -1).argmax(dim=1)
                iy = t.div(flat_indices, self.grid_size, rounding_mode="floor")
                ix = flat_indices.remainder(self.grid_size)
                dy, dx = self.offsets[iy], self.offsets[ix]
                residual = t.stack((dx, dy), dim=1)
                patch = seed + residual
                total = ob - oa + patch
                peak = surface.reshape(batch, -1).gather(1, flat_indices[:, None])[:, 0]
                distance2 = ((self.offsets[None, :, None] - dy[:, None, None]).square()
                             + (self.offsets[None, None, :] - dx[:, None, None]).square())
                rivals = local_maxima & (distance2 > SECONDARY_EXCLUSION_NATIVE ** 2)
                rival_count = rivals.sum(dim=(-2, -1))
                second_raw = surface.masked_fill(~rivals, -float("inf")).flatten(1).amax(dim=1)
                second = t.where(rival_count > 0, second_raw, t.zeros_like(second_raw))
                phase_patch = periodic_seed + residual
                peak_phase = (self.fx * phase_patch[:, 0, None, None] + self.fy * phase_patch[:, 1, None, None]) * (2 * math.pi * power)
                rotated = (phasor * t.complex(t.cos(peak_phase), t.sin(peak_phase))).real * weight
                hxx = (rotated * self.fx.square()).sum(dim=(-2, -1)) * (2 * math.pi * power) ** 2 / safe_sum
                hxy = (rotated * self.fx * self.fy).sum(dim=(-2, -1)) * (2 * math.pi * power) ** 2 / safe_sum
                hyy = (rotated * self.fy.square()).sum(dim=(-2, -1)) * (2 * math.pi * power) ** 2 / safe_sum
                hessian = t.stack((hxx, hxy, hxy, hyy), dim=-1).reshape(batch, 2, 2)
                curvature = t.linalg.eigvalsh(hessian)
                diagnostics = t.stack((total[:, 0], total[:, 1], patch[:, 0], patch[:, 1], dx, dy,
                                       peak, iy.float(), ix.float(), rival_count.float(), second,
                                       curvature[:, 0], curvature[:, 1]), dim=1).cpu().tolist()
                saved_surfaces = surface.detach().cpu() if return_surfaces else None
                for k, values in enumerate(diagnostics):
                    tx, ty, px, py, rx, ry, score, row, column, rivals_n, second_value, curvature0, curvature1 = values
                    iy_int, ix_int = int(row), int(column)
                    second_value = second_value if rivals_n else None
                    boundary = ix_int in (0, self.grid_size - 1) or iy_int in (0, self.grid_size - 1)
                    reasons = list(shared[k]["shared_refusals"])
                    if boundary:
                        reasons.append("SEARCH_BOUNDARY")
                    if score < MIN_SCORE:
                        reasons.append("LOW_PHASE_SCORE")
                    if curvature0 <= 0:
                        reasons.append("NONPOSITIVE_PEAK_CURVATURE")
                    if second_value is not None and score - second_value <= MIN_SECONDARY_GAP:
                        reasons.append("AMBIGUOUS_LOCAL_PEAK")
                    result = {
                        "power": power, "status": "ACCEPTED_LOCAL_CORRESPONDENCE" if not reasons else "REFUSED",
                        "accepted": not reasons, "refusals": reasons,
                        "displacement_native_xy": [tx, ty],
                        "patch_displacement_native_xy": [px, py], "residual_native_xy": [rx, ry],
                        "score": score, "peak_grid_yx": [iy_int, ix_int], "search_boundary": boundary,
                        "secondary_local_maximum_count": int(rivals_n), "secondary_score": second_value,
                        "secondary_gap": None if second_value is None else score - second_value,
                        "negative_score_hessian_eigenvalues_native": [curvature0, curvature1],
                        "spectral_eigen_ratio": shared[k]["spectral_eigen_ratio"],
                        "seeded_branch_only": True, "physical_error_identified": False,
                    }
                    if return_surfaces:
                        result["score_surface"] = saved_surfaces[k].clone()
                    records[k][f"p{power}"] = result
            self.pair_count += batch
            return records
