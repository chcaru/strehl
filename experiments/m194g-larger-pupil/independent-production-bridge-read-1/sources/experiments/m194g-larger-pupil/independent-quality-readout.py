"""Fixed paired-repeat quality reductions; caller admits actual files and targets."""
import math

SEEDS = (701, 709, 719, 727, 733, 739, 743, 751)
MODES = ("hard-floor", "floor-pedestal-v1")
CHANNELS = ("R", "G", "B")
WB = (1.3333333730697632, 1., 1.6666666269302368)
FACTORS = (.75, 1., .6)


def scene_readout(scene, rows, scalar, endpoint_rows, geometry, fixture, *, metrics, budget, load_rgb):
    """load_rgb returns the admitted actual post-WB DN plane array for one row.

    It must use the caller's same Budget and bound TIFF decoder. Each returned
    array is rechecked here. This kernel cannot grant source/file authority.
    """
    m, np = metrics, metrics.np
    m.require(scene in ("flat", "textured") and set(rows) == {(seed, mode) for seed in (None, *SEEDS) for mode in MODES},
              "complete paired scene population")
    width, height = geometry["output_native"]
    offset = tuple(geometry["canonical_native_offset"])
    ox, oy = offset
    masks = m.regions((height, width), offset, budget)
    m.require(scalar.shape == (240, 320) and scalar.dtype.str == "<f8", "full K0 scalar layout")
    m.finite(scalar, budget)
    if scene == "textured":
        m.require(set(endpoint_rows) == {0, 4}, "two separate endpoint references")
    else:
        m.require(not endpoint_rows, "flat does not use textured endpoint observations")

    def load(row):
        array = load_rgb(row)
        m.require(array.shape == (height, width, 3) and array.dtype.str == "<f8", "actual RGB DN layout")
        budget.watch(array, "actual paired RGB DN")
        m.finite(array, budget)
        return array

    off = {mode: load(rows[(None, mode)]) for mode in MODES}
    endpoints = {index: load(row) for index, row in endpoint_rows.items()}
    states = {mode: [m.Temporal((height, width), budget) for _ in CHANNELS] for mode in MODES}
    scratch = tuple(budget.empty((height, width), "<f8", "shared repeat scratch" + str(i)) for i in range(2))
    ideal = budget.empty((height, width), "<f8", "same-centre ideal channel")
    table, sparse, wave_rows = [], [], []
    # Store scalars only; no repeat image volume.
    mse = {}
    variance_leaves = {(mode, channel, region): [] for mode in MODES for channel in CHANNELS for region in masks}

    def ideal_channel(index):
        if scene == "flat": ideal.fill(12000. * .25 * FACTORS[index] * WB[index])
        else: np.multiply(scalar[oy:oy + height, ox:ox + width], .25 * FACTORS[index] * WB[index], out=ideal)
        return ideal

    def references(channel):
        yield "ideal", ideal_channel(channel), tuple(masks)
        if scene == "textured":
            yield "endpoint-0", endpoints[0][:, :, channel], ("endpoint-background",)
            yield "endpoint-4", endpoints[4][:, :, channel], ("endpoint-foreground",)

    def individual(seed, pair):
        for ci, channel in enumerate(CHANNELS):
            for reference, target, region_names in references(ci):
                for region in region_names:
                    for mode in MODES:
                        value = m.errors(pair[mode][:, :, ci], target, masks[region], budget)
                        table.append({"scene": scene, "seed": seed, "mode": mode, "channel": channel,
                                      "reference": reference, "region": region, **value})
                        if seed is not None: mse[(seed, mode, channel, reference, region)] = value["mse_dn2"]
            ideal_channel(ci)
            for region in ("whole", "window"):
                sparse.append({"scene": scene, "seed": seed, "population": "individual",
                               "channel": channel, "region": region, **m.sparse_pair(
                                   pair[MODES[0]][:, :, ci], pair[MODES[1]][:, :, ci], ideal, masks[region], offset, budget)})
        budget.check()

    individual(None, off)
    if scene == "textured":
        for layer in ("background", "foreground"):
            region = "surface-" + layer
            frequencies = [wave["frequency"] for wave in fixture["scene"][layer]["waves"]]
            fit = m.WaveFit(masks[region], offset, frequencies, budget)
            for ci, channel in enumerate(CHANNELS):
                truth = fit.read(ideal_channel(ci))
                for mode in MODES:
                    measured = fit.read(off[mode][:, :, ci])
                    wave_rows.append({"scene": scene, "mode": mode, "channel": channel, "region": region,
                                      "target": truth, "observed": measured,
                                      "differences": m.wave_difference(measured, truth),
                                      "full_signal_error": m.errors(off[mode][:, :, ci], ideal, masks[region], budget)})
            del fit
    for seed in SEEDS:
        pair = {mode: load(rows[(seed, mode)]) for mode in MODES}
        individual(seed, pair)
        for mode in MODES:
            for ci in range(3): states[mode][ci].add(pair[mode][:, :, ci], scratch)
        del pair

    temporal, paired_mse, paired_variance = [], [], []
    for ci, channel in enumerate(CHANNELS):
        ideal_channel(ci)
        for region in ("whole", "window"):
            sparse.append({"scene": scene, "seed": None, "population": "eight-repeat-mean",
                           "channel": channel, "region": region, **m.sparse_pair(
                               states[MODES[0]][ci].mean, states[MODES[1]][ci].mean, ideal, masks[region], offset, budget)})
        for reference, target, region_names in references(ci):
            for region in region_names:
                for mode in MODES:
                    values = [mse[(seed, mode, channel, reference, region)] for seed in SEEDS]
                    temporal.append({"scene": scene, "mode": mode, "channel": channel, "reference": reference,
                                     "region": region, **m.decomposition(states[mode][ci], target, masks[region], math.fsum(values) / 8)})
                differences = [mse[(seed, MODES[1], channel, reference, region)] - mse[(seed, MODES[0], channel, reference, region)]
                               for seed in SEEDS]
                paired_mse.append({"scene": scene, "channel": channel, "reference": reference, "region": region,
                                   "candidate_minus_baseline": m.repeat_summary(differences)})
        for mode in MODES:
            for region in masks:
                temporal.append({"scene": scene, "mode": mode, "channel": channel, "reference": "own-noise-off",
                                 "region": region, "scope": "noise-dependent algorithm bias; mode-specific reference cannot rank fidelity",
                                 **m.errors(states[mode][ci].mean, off[mode][:, :, ci], masks[region], budget)})

    # Delete matched whole repeats. Reopen actual bytes; no frame cubes.
    for seed in SEEDS:
        pair = {mode: load(rows[(seed, mode)]) for mode in MODES}
        for ci, channel in enumerate(CHANNELS):
            for region, mask in masks.items():
                for mode in MODES:
                    variance_leaves[(mode, channel, region)].append(states[mode][ci].leave_one(pair[mode][:, :, ci], scratch, mask))
        del pair
    for ci, channel in enumerate(CHANNELS):
        for region, mask in masks.items():
            before = states[MODES[0]][ci].variance_region(mask)
            after = states[MODES[1]][ci].variance_region(mask)
            first, second = (variance_leaves[(mode, channel, region)] for mode in MODES)
            paired_variance.append({"scene": scene, "channel": channel, "region": region,
                                    "baseline_variance_dn2": before, "candidate_variance_dn2": after,
                                    "candidate_minus_baseline_dn2": after - before,
                                    "candidate_over_baseline": None if before == 0 else after / before,
                                    "baseline_delete_one": m.jackknife(first), "candidate_delete_one": m.jackknife(second),
                                    "paired_delete_one": m.jackknife([b - a for a, b in zip(first, second, strict=True)])})
    budget.check()
    return {"scene": scene, "individual_errors": table, "temporal": temporal, "paired_mse": paired_mse,
            "paired_variance": paired_variance, "sparse": sparse, "noise_off_waves": wave_rows,
            "region_sites": {name: int(np.count_nonzero(mask)) for name, mask in masks.items()},
            "repeat_seeds": list(SEEDS), "channels": list(CHANNELS),
            "scope": "complete fixed diagnostics; no candidate quality pass or physical calibration claim"}
