"""Fixed ROI truth-error tails; extrema use the first row-major tied site."""
from __future__ import annotations

import numpy as np


def samples(rgb, reference, mask, x, y):
    rgb, reference = np.asarray(rgb), np.asarray(reference)
    mask, x, y = np.asarray(mask), np.asarray(x), np.asarray(y)
    if (rgb.ndim != 3 or rgb.shape[-1] != 3 or reference.shape != rgb.shape
            or mask.shape != rgb.shape[:2] or mask.dtype != np.bool_
            or x.shape != mask.shape or y.shape != mask.shape or not mask.any()):
        raise ValueError("sparse-error requires matching RGB, nonempty bool mask and coordinate grids")
    value = rgb[mask].astype(np.float64)
    truth = reference[mask].astype(np.float64)
    coordinates = np.column_stack((x[mask], y[mask])).astype(np.float64)
    if (not np.isfinite(value).all() or not np.isfinite(truth).all()
            or not np.isfinite(coordinates).all()
            or not np.equal(coordinates, np.round(coordinates)).all()):
        raise ValueError("nonfinite samples or noninteger canonical sites in scored ROI")
    return value, truth, coordinates.astype(np.int64)


def summarize(rgb, reference, mask, x, y):
    value, truth, coordinates = samples(rgb, reference, mask, x, y)
    residual = value - truth
    result = []
    for channel in range(3):
        r = residual[:, channel]

        def point(index):
            return dict(native_xy=coordinates[index].tolist(),
                        value_dn=float(value[index, channel]),
                        truth_dn=float(truth[index, channel]),
                        signed_error_dn=float(r[index]))

        quantiles = np.quantile(np.abs(r), [0.99, 0.999], method="linear")
        result.append(dict(channel="RGB"[channel],
                           minimum_signed_error=point(int(np.argmin(r))),
                           maximum_signed_error=point(int(np.argmax(r))),
                           maximum_absolute_error=point(int(np.argmax(np.abs(r)))),
                           absolute_error_p99_dn=float(quantiles[0]),
                           absolute_error_p999_dn=float(quantiles[1])))
    return dict(mask_pixels=int(np.count_nonzero(mask)),
                quantile_method="linear", tie="first row-major site",
                channels=result)


def compare(candidate, baseline, reference, mask, x, y):
    new, truth, coordinates = samples(candidate, reference, mask, x, y)
    old, old_truth, old_coordinates = samples(baseline, reference, mask, x, y)
    if not np.array_equal(truth, old_truth) or not np.array_equal(coordinates, old_coordinates):
        raise ValueError("unpaired sparse-error reference or coordinates")
    old_error, new_error = old - truth, new - truth
    error_change = np.abs(new_error) - np.abs(old_error)
    movement = new - old
    result = []
    for channel in range(3):

        def point(index):
            return dict(native_xy=coordinates[index].tolist(),
                        baseline_dn=float(old[index, channel]),
                        candidate_dn=float(new[index, channel]),
                        truth_dn=float(truth[index, channel]),
                        baseline_signed_error_dn=float(old_error[index, channel]),
                        candidate_signed_error_dn=float(new_error[index, channel]),
                        absolute_error_change_dn=float(error_change[index, channel]),
                        output_movement_dn=float(movement[index, channel]))

        result.append(dict(channel="RGB"[channel],
                           maximum_absolute_error_change=point(int(np.argmax(error_change[:, channel]))),
                           minimum_absolute_error_change=point(int(np.argmin(error_change[:, channel]))),
                           largest_absolute_output_movement=point(int(np.argmax(np.abs(movement[:, channel]))))))
    return dict(mask_pixels=int(np.count_nonzero(mask)),
                error_change_sign="positive worsens truth error; negative improves it",
                tie="first row-major site", channels=result)
