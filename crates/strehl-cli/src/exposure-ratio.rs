//! One estimator of the exposure ratio between a longer and a shorter
//! exposure of one scene (capture calibration spec, 5.7, ledger row
//! `cpf-f1-highlights`).
//!
//! Used by `strehl survey` for its long and short pairs and by the highlight
//! fusion for a base group and its highlight companion, so the ratio a
//! survey reports and the ratio a render applies are one measurement.
//!
//! The scene is cut into cells of [`CELL`] x [`CELL`] photosites. A cell
//! counts, per colour, when the longer exposure's mean lies between [`LOW`]
//! and [`HIGH`] of its range, no sample of it is pinned, and the shorter
//! exposure's mean is [`SNR`] of its own standard errors above black. The
//! ratio is the median of short over long over the counted cells of all
//! colours. Cells are small on purpose: a dark subject under a deep
//! highlight group has few large patches well exposed in both, but many
//! small ones (MEASURED on the dragonfly of 2026-11-26: the 64-photosite
//! patch fit found 0 of 12 needed on every plane; these cells measure the
//! ratio within 1.8 % of commanded on all 76 of its pairs).

/// Cell side, photosites.
pub const CELL: usize = 8;
/// The longer exposure's cell mean, as a share of its range.
pub const LOW: f32 = 0.05;
pub const HIGH: f32 = 0.7;
/// The shorter exposure's cell mean, in its own standard errors.
pub const SNR: f32 = 10.0;
/// Fewer counted cells than this: the ratio is not measured.
pub const MIN_CELLS: usize = 100;

/// One colour of one cell, both means above black.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Cell {
    pub colour: usize,
    /// The longer exposure's mean and its share of the range.
    pub long: f64,
    pub long_share: f32,
    /// Any sample of the longer exposure in the cell is pinned.
    pub pinned: bool,
    /// The shorter exposure's mean and the standard error of that mean
    /// under the injected noise model.
    pub short: f64,
    pub short_se: f64,
}

impl Cell {
    /// Whether the cell measures the ratio.
    pub fn counts(&self) -> bool {
        !self.pinned
            && (LOW..=HIGH).contains(&self.long_share)
            && self.short >= f64::from(SNR) * self.short_se
            && self.long > 0.0
    }
}

/// The estimate: short over long.
#[derive(Clone, Debug, PartialEq)]
pub struct Estimate {
    /// Median over the counted cells of all colours; `None` under
    /// [`MIN_CELLS`].
    pub ratio: Option<f64>,
    /// Per colour, with a third of [`MIN_CELLS`] each.
    pub per_colour: [Option<f64>; 3],
    pub cells: usize,
    /// The medians of the counted cells taken alternately, in the order
    /// given: two halves that must agree.
    pub halves: Option<[f64; 2]>,
}

impl Estimate {
    /// How far the halves disagree, as a fraction.
    pub fn split(&self) -> Option<f64> {
        self.halves.map(|[a, b]| (a / b - 1.0).abs())
    }
}

/// The median; `None` for no values.
pub fn median(mut v: Vec<f64>) -> Option<f64> {
    if v.is_empty() {
        return None;
    }
    v.sort_by(f64::total_cmp);
    let n = v.len();
    Some(if n % 2 == 1 {
        v[n / 2]
    } else {
        0.5 * (v[n / 2 - 1] + v[n / 2])
    })
}

/// The estimate from candidate cells, in a fixed order.
pub fn estimate(cells: impl IntoIterator<Item = Cell>) -> Estimate {
    let kept: Vec<(usize, f64)> = cells
        .into_iter()
        .filter(Cell::counts)
        .map(|c| (c.colour, c.short / c.long))
        .collect();
    let per_colour = std::array::from_fn(|c| {
        let v: Vec<f64> = kept.iter().filter(|p| p.0 == c).map(|p| p.1).collect();
        (v.len() >= MIN_CELLS / 3).then(|| median(v)).flatten()
    });
    let n = kept.len();
    let enough = n >= MIN_CELLS;
    let halves = enough.then(|| {
        let half = |k: usize| median(kept.iter().skip(k).step_by(2).map(|p| p.1).collect());
        [half(0), half(1)]
    });
    Estimate {
        ratio: enough
            .then(|| median(kept.iter().map(|p| p.1).collect()))
            .flatten(),
        per_colour,
        cells: n,
        halves: halves.and_then(|[a, b]| Some([a?, b?])),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn cell(colour: usize, long: f64, short: f64) -> Cell {
        Cell {
            colour,
            long,
            long_share: (long / 10_000.0) as f32,
            pinned: false,
            short,
            short_se: 1.0,
        }
    }

    #[test]
    fn the_ratio_is_the_median_of_counted_cells() {
        let cells: Vec<Cell> = (0..300)
            .map(|i| cell(i % 3, 1000.0 + i as f64, (1000.0 + i as f64) * 0.02))
            .collect();
        let e = estimate(cells);
        assert_eq!(e.cells, 300);
        assert!((e.ratio.unwrap() - 0.02).abs() < 1e-12);
        assert!(e.split().unwrap() < 1e-9);
        assert!(
            e.per_colour
                .iter()
                .all(|c| (c.unwrap() - 0.02).abs() < 1e-12)
        );
    }

    #[test]
    fn pinned_dim_bright_and_noisy_cells_do_not_count() {
        let mut pinned = cell(0, 3000.0, 60.0);
        pinned.pinned = true;
        let dim = cell(1, 100.0, 2.0); // 1 % of the range
        let bright = cell(2, 8000.0, 160.0); // 80 %
        let noisy = cell(1, 3000.0, 5.0); // 5 standard errors
        assert!(!pinned.counts() && !dim.counts() && !bright.counts() && !noisy.counts());
        assert!(cell(1, 3000.0, 60.0).counts());
    }

    #[test]
    fn too_few_cells_measure_nothing() {
        let e = estimate((0..MIN_CELLS - 1).map(|i| cell(i % 3, 2000.0, 40.0)));
        assert_eq!(e.ratio, None);
        assert_eq!(e.halves, None);
    }

    #[test]
    fn halves_that_disagree_show_it() {
        // Alternate cells read 0.02 and 0.0206: the halves split by 2.9 %.
        let e = estimate((0..400).map(|i| {
            let r = if i % 2 == 0 { 0.02 } else { 0.0206 };
            cell(i % 3, 2000.0, 2000.0 * r)
        }));
        assert!((e.split().unwrap() - (1.0 - 0.02 / 0.0206)).abs() < 1e-9);
    }
}
