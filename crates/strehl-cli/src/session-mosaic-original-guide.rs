//! Exact identity-only specialization of the diagnostic original CFA box.
//! Each pixel keeps the generic gather's y/x/G1/G2 arithmetic order; only
//! independent rows run in parallel. No aligned frame or photographic output.
use super::*;
use rayon::prelude::*;

pub(super) fn sample_identity_box<S: QuadSource + ?Sized>(
    source: &S,
    levels: Levels,
    start: [usize; 2],
    side: usize,
) -> Option<f32> {
    let g = source.geometry();
    if side == 0
        || g.width < 2
        || g.height < 2
        || start[0].checked_add(side)? > g.width
        || start[1].checked_add(side)? > g.height
    {
        return None;
    }
    let mut sum = 0.0_f32;
    for y in start[1]..start[1] + side {
        let (r0, r1) = source.quad_rows(y);
        if r0.len() < 2 * g.width || r1.len() < 2 * g.width {
            return None;
        }
        for x in start[0]..start[0] + side {
            for value in [r0[2 * x + 1], r1[2 * x]] {
                let value = f32::from(value);
                if value >= levels.white {
                    return None;
                }
                sum += value - levels.black;
            }
        }
    }
    Some(sum / (2 * side * side) as f32)
}

pub(crate) fn original_boxes<S: QuadSource + Sync>(
    source: &S,
    levels: Levels,
    step: usize,
) -> (Vec<f32>, Vec<bool>) {
    assert!(step > 0);
    let g = source.geometry();
    let width = g.width / step;
    let height = g.height / step;
    let mut intensity = vec![0.0; width * height];
    let mut covered = vec![false; width * height];
    if width == 0 {
        return (intensity, covered);
    }
    intensity
        .par_chunks_mut(width)
        .zip(covered.par_chunks_mut(width))
        .enumerate()
        .for_each(|(y, (row, mask))| {
            for (x, (value, valid)) in row.iter_mut().zip(mask).enumerate() {
                if let Some(sample) =
                    sample_identity_box(source, levels, [x * step, y * step], step)
                {
                    *value = sample;
                    *valid = true;
                }
            }
        });
    (intensity, covered)
}

#[cfg(test)]
mod tests {
    use super::*;
    struct Original {
        g: PlaneGeometry,
        pixels: Vec<u16>,
    }
    impl QuadSource for Original {
        fn geometry(&self) -> PlaneGeometry {
            self.g
        }
        fn quad_rows(&self, y: usize) -> (&[u16], &[u16]) {
            let first = 4 * self.g.width * y;
            let second = first + 2 * self.g.width;
            (
                &self.pixels[first..second],
                &self.pixels[second..second + 2 * self.g.width],
            )
        }
    }
    #[test]
    fn identity_original_boxes_are_bit_exact_at_boundaries_clipping_and_worker_counts() {
        for (width, height) in [(32, 24), (33, 25)] {
            let g = PlaneGeometry { width, height };
            let mut source = Original {
                g,
                pixels: (0..4 * g.pixels())
                    .map(|i| ((i * 37 + 13) % 4096) as u16)
                    .collect(),
            };
            // Both green sites, including the last native quad; adjacent unused
            // CFA red/blue clipping is deliberately not a green invalidator.
            source.pixels[1] = 16383;
            source.pixels[4 * g.pixels() - 2] = 16383;
            source.pixels[0] = 16383;
            for black in [64.125_f32, 101.3, 2048.0] {
                for step in [1, 2, 3, 4, 5] {
                    let levels = Levels {
                        black,
                        white: 16000.0,
                    };
                    let gw = width / step;
                    let gh = height / step;
                    let mut expected = Vec::new();
                    let mut mask = Vec::new();
                    for y in 0..gh {
                        for x in 0..gw {
                            let value = super::super::sample_box(
                                &source,
                                levels,
                                Similarity::IDENTITY,
                                [x * step, y * step],
                                step,
                            );
                            assert_eq!(
                                sample_identity_box(&source, levels, [x * step, y * step], step)
                                    .map(f32::to_bits),
                                value.map(f32::to_bits)
                            );
                            expected.push(value.unwrap_or(0.0).to_bits());
                            mask.push(value.is_some());
                        }
                    }
                    for workers in [1, 4] {
                        let pool = rayon::ThreadPoolBuilder::new()
                            .num_threads(workers)
                            .build()
                            .unwrap();
                        let (actual, covered) =
                            pool.install(|| original_boxes(&source, levels, step));
                        assert_eq!(
                            actual.into_iter().map(f32::to_bits).collect::<Vec<_>>(),
                            expected
                        );
                        assert_eq!(covered, mask);
                    }
                }
            }
        }
    }
}
