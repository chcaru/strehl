// Fixed co-sited colour projection and coarse-only shared source evidence.
pub(crate) const CO_SITED_RGB: [[usize; 3]; 4] = [
    [0, 4, 5], [6, 1, 7], [8, 2, 9], [10, 11, 3],
];
pub(crate) const PROBE_PAIRS: usize = 8;
pub(crate) type ColourBands = [Vec<Vec<f32>>; 2];

#[derive(Clone, Copy, Debug, Eq, PartialEq, serde::Serialize)]
pub(crate) enum Mode { Off, Chromatic, NoChroma }

fn validate_sizes(sizes: &[LevelSize]) -> Result<()> {
    ensure!(sizes.len() >= 2 && sizes[0].width > 0 && sizes[0].height > 0
        && sizes.windows(2).all(|p| p[1] == p[0].reduced()),
        "exact nonempty pyramid sizes required");
    Ok(())
}
fn validate_bands(bands: &[Vec<f32>], sizes: &[LevelSize], nonnegative: bool) -> Result<()> {
    ensure!(bands.len() + 1 == sizes.len(), "AC band count differs");
    for (band, size) in bands.iter().zip(sizes) {
        ensure!(band.len() == size.pixels() && band.iter().all(|v|
            v.is_finite() && (!nonnegative || *v >= 0.0)), "invalid band shape/value");
    }
    Ok(())
}

/// Input slots are rounded, black-subtracted camera DN from the existing
/// phase-packed consumer. Each subtraction uses three colours at ONE site.
pub(crate) fn project_co_sited(packed: &[Vec<f32>], wb: [f32; 4]) -> Result<[Vec<f32>; 2]> {
    ensure!(packed.len() == 12 && !packed[0].is_empty()
        && packed.iter().all(|p| p.len() == packed[0].len()
            && p.iter().all(|v| v.is_finite())), "twelve finite co-sited planes required");
    ensure!(wb[..3].iter().all(|v| v.is_finite() && *v > 0.0), "invalid WB");
    let gains = [wb[0] / wb[1], 1.0, wb[2] / wb[1]];
    ensure!(gains.iter().all(|v| v.is_finite() && *v > 0.0), "invalid normalized WB");
    let mut result = [vec![0.0; packed[0].len()], vec![0.0; packed[0].len()]];
    for j in 0..packed[0].len() {
        let mut rg = 0.0f32;
        let mut bg = 0.0f32;
        for [r, g, b] in CO_SITED_RGB {
            rg += packed[r][j] * gains[0] - packed[g][j];
            bg += packed[b][j] * gains[2] - packed[g][j];
        }
        result[0][j] = rg * 0.25;
        result[1][j] = bg * 0.25;
        ensure!(result[0][j].is_finite() && result[1][j].is_finite(),
            "projection overflow");
    }
    Ok(result)
}

pub(crate) fn projected_bands(packed: &[Vec<f32>], wb: [f32; 4],
    sizes: &[LevelSize]) -> Result<ColourBands> {
    validate_sizes(sizes)?;
    let guides = project_co_sited(packed, wb)?;
    ensure!(guides[0].len() == sizes[0].pixels(), "projection geometry differs");
    let bands = guides.map(|guide| kernels::laplacian(&guide, sizes));
    for colour in &bands { validate_bands(colour, sizes, false)?; }
    Ok(bands)
}

pub(crate) fn joint_energy(bands: &ColourBands, sizes: &[LevelSize]) -> Result<Vec<Vec<f32>>> {
    validate_sizes(sizes)?;
    for colour in bands { validate_bands(colour, sizes, false)?; }
    let mut result = Vec::with_capacity(sizes.len() - 1);
    for k in 0..sizes.len() - 1 {
        let a = kernels::energy(&bands[0][k], sizes[k]);
        let b = kernels::energy(&bands[1][k], sizes[k]);
        result.push(a.iter().zip(&b).map(|(a, b)| a + b).collect());
    }
    validate_bands(&result, sizes, true)?;
    Ok(result)
}

/// Both projected components carry the same gathered original-noise draw.
/// Subtract paired projected coefficients BEFORE squaring. Marginal R/G/B
/// variances cannot replace this path because their covariance matters.
pub(crate) struct PairedNoiseEnergy {
    sizes: Vec<LevelSize>, sums: ColourBands, seen: usize,
}
impl PairedNoiseEnergy {
    pub(crate) fn new(sizes: &[LevelSize]) -> Result<Self> {
        validate_sizes(sizes)?;
        Ok(Self { sizes: sizes.to_vec(), sums: std::array::from_fn(|_|
            sizes[..sizes.len()-1].iter().map(|s| vec![0.0; s.pixels()]).collect()), seen: 0 })
    }
    pub(crate) fn add_pair(&mut self, a: &ColourBands, b: &ColourBands) -> Result<()> {
        ensure!(self.seen < PROBE_PAIRS, "too many noise pairs");
        for c in 0..2 {
            validate_bands(&a[c], &self.sizes, false)?;
            validate_bands(&b[c], &self.sizes, false)?;
            for k in 0..self.sums[c].len() {
                for ((sum, &av), &bv) in self.sums[c][k].iter_mut().zip(&a[c][k]).zip(&b[c][k]) {
                    let delta = av - bv;
                    *sum += delta * delta;
                    ensure!(sum.is_finite(), "paired noise sum overflow");
                }
            }
        }
        self.seen += 1;
        Ok(())
    }
    /// Energy variance without gate; the caller applies the unchanged gate once.
    pub(crate) fn finish(mut self) -> Result<Vec<Vec<f32>>> {
        ensure!(self.seen == PROBE_PAIRS, "exactly eight noise pairs required");
        for colour in &mut self.sums {
            for (k, band) in colour.iter_mut().enumerate() {
                for v in band.iter_mut() { *v /= (2 * PROBE_PAIRS) as f32; }
                *band = kernels::smooth(band, self.sizes[k]);
            }
        }
        let result: Vec<Vec<f32>> = self.sums[0].iter().zip(&self.sums[1])
            .map(|(a,b)| a.iter().zip(b).map(|(a,b)| a+b).collect()).collect();
        validate_bands(&result, &self.sizes, true)?;
        Ok(result)
    }
}

#[derive(Clone, serde::Serialize)]
pub(crate) struct WeightChanges {
    pub changed: Vec<usize>, pub chromatic_sites: Vec<usize>, pub fallback_sites: Vec<usize>,
}
/// One stack-wide admission union per OWN band, no N-frame weight volume.
pub(crate) struct AdmissionUnion {
    pub sizes: Vec<LevelSize>, pub supported: Vec<Vec<bool>>,
    source_count: usize, seen: usize,
}
impl AdmissionUnion {
    pub(crate) fn new(sizes: &[LevelSize], source_count: usize) -> Result<Self> {
        validate_sizes(sizes)?;
        ensure!((1..=16).contains(&source_count), "bounded generated source count required");
        Ok(Self { sizes:sizes.to_vec(), supported:sizes[..sizes.len()-1].iter().enumerate()
            .map(|(k,s)| if k == 0 {Vec::new()} else {vec![false; s.pixels()]}).collect(),
            source_count, seen:0 })
    }
    pub(crate) fn add(&mut self, weights: &[Vec<f32>]) -> Result<()> {
        ensure!(self.seen < self.source_count, "too many source fields");
        validate_bands(weights, &self.sizes, true)?;
        for (k, band) in weights.iter().enumerate().skip(1) {
            for (supported, &w) in self.supported[k].iter_mut().zip(band) { *supported |= w > 0.0; }
        }
        self.seen += 1;
        Ok(())
    }
    pub(crate) fn complete(&self) -> Result<()> {
        ensure!(self.seen == self.source_count, "incomplete source admission union"); Ok(())
    }
    pub(crate) fn apply(&self, canonical: &mut core::Fields, chromatic: &core::Fields,
        mode: Mode) -> Result<WeightChanges> {
        self.complete()?;
        validate_bands(&canonical.weights, &self.sizes, true)?;
        validate_bands(&chromatic.weights, &self.sizes, true)?;
        let nb = self.supported.len();
        let mut counts = WeightChanges { changed:vec![0;nb], chromatic_sites:vec![0;nb], fallback_sites:vec![0;nb] };
        for k in 0..nb {
            if k == 0 || mode != Mode::Chromatic {
                counts.fallback_sites[k] = self.sizes[k].pixels(); continue;
            }
            for (j, w) in canonical.weights[k].iter_mut().enumerate() {
                if self.supported[k][j] {
                    let new = chromatic.weights[k][j];
                    counts.changed[k] += usize::from(w.to_bits() != new.to_bits());
                    counts.chromatic_sites[k] += 1;
                    *w = new;
                } else {
                    ensure!(chromatic.weights[k][j] == 0.0, "unsupported source has a positive weight");
                    counts.fallback_sites[k] += 1;
                }
            }
        }
        Ok(counts)
    }
}
