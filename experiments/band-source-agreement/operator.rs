// One frozen same-band membership rule. The parent module supplies anyhow macros.
use strehl_core::pyramid::{LevelSize, rb_own_guide_diagnostic as core,
    band_source_agreement_diagnostic as kernel};

#[derive(Clone, Copy, Debug, Eq, PartialEq, serde::Serialize)]
pub(crate) enum Mode { Off, Agreement, Neutral }

fn valid(values: &[f32], n: usize) -> Result<()> {
    ensure!(values.len() == n && values.iter().all(|v| v.is_finite() && *v >= 0.0),
        "invalid nonnegative band field");
    Ok(())
}

pub(crate) struct AgreementSum {
    sizes: Vec<LevelSize>, source_count: usize, seen: usize,
    denominator: Vec<Vec<f32>>,
}
impl AgreementSum {
    pub(crate) fn new(sizes: &[LevelSize], source_count: usize) -> Result<Self> {
        ensure!((1..=1024).contains(&source_count) && sizes.len() >= 2
            && sizes[0].width > 0 && sizes[0].width <= 3516
            && sizes[0].height > 0 && sizes[0].height <= 2344
            && sizes.windows(2).all(|s| s[1] == s[0].reduced()),
            "bounded source count and exact pyramid geometry required");
        // Band0 is validated but neither normalized nor retained. The terminal
        // mean has no entry: these are AC fields only.
        let denominator = sizes[..sizes.len()-1].iter().enumerate()
            .map(|(k,s)| if k == 0 { Vec::new() } else { vec![0.0;s.pixels()] }).collect();
        Ok(Self { sizes: sizes.to_vec(), source_count, seen: 0, denominator })
    }
    pub(crate) fn add(&mut self, weights: &[Vec<f32>]) -> Result<()> {
        ensure!(self.seen < self.source_count && weights.len() == self.denominator.len(),
            "source count or AC level count differs");
        for (k,w) in weights.iter().enumerate() {
            valid(w,self.sizes[k].pixels())?;
            if k == 0 { continue; }
            for (d,&v) in self.denominator[k].iter_mut().zip(w) {
                *d += v;
                ensure!(d.is_finite(), "band denominator overflow");
            }
        }
        self.seen += 1;
        Ok(())
    }
    pub(crate) fn finish(self) -> Result<BandAgreement> {
        ensure!(self.seen == self.source_count, "incomplete source denominator");
        Ok(BandAgreement { sizes:self.sizes, source_count:self.source_count,
            denominator:self.denominator })
    }
}

pub(crate) struct BandAgreement {
    pub sizes: Vec<LevelSize>, pub source_count: usize,
    pub denominator: Vec<Vec<f32>>,
}
#[derive(Clone, Debug, serde::Serialize)]
pub(crate) struct WeightChanges {
    pub changed: Vec<usize>, pub zeroed_positive: Vec<usize>,
    pub bypassed: Vec<usize>, pub rounding_fallback: Vec<usize>,
}
impl BandAgreement {
    pub(crate) fn memberships(&self, weights: &[Vec<f32>]) -> Result<Vec<Vec<f32>>> {
        ensure!(weights.len() == self.denominator.len(), "AC level count differs");
        let uniform = 1.0 / self.source_count as f32;
        let mut out = Vec::with_capacity(weights.len());
        for (k,w) in weights.iter().enumerate() {
            valid(w,self.sizes[k].pixels())?;
            if k == 0 { out.push(Vec::new()); continue; }
            ensure!(w.iter().zip(&self.denominator[k]).all(|(&w,&d)|w<=d),
                "source weight exceeds band denominator");
            out.push(w.iter().zip(&self.denominator[k]).map(|(&w,&d)|
                if d > 0.0 { w/d } else { uniform }).collect());
        }
        Ok(out)
    }
    pub(crate) fn apply(&self, fields: &mut core::Fields, mode: Mode) -> Result<WeightChanges> {
        let p = self.memberships(&fields.weights)?;
        let nb = fields.weights.len();
        let mut count = WeightChanges { changed:vec![0;nb],zeroed_positive:vec![0;nb],
            bypassed:vec![0;nb],rounding_fallback:vec![0;nb] };
        count.bypassed[0] = self.sizes[0].pixels();
        for k in 1..nb {
            if mode != Mode::Agreement {
                count.bypassed[k] = self.sizes[k].pixels();
                continue;
            }
            let q = kernel::smooth_membership(&p[k],self.sizes[k]);
            for (j,w) in fields.weights[k].iter_mut().enumerate() {
                let local = p[k][j]; let neighbour = q[j];
                ensure!(neighbour.is_finite() && neighbour >= 0.0, "invalid smoothed membership");
                // Literal zero remains zero. Uniform unsupported neighbours
                // supply no licence to admit a locally rejected source.
                if *w == 0.0 {
                    count.bypassed[k] += 1;
                    continue;
                }
                // Positive w has positive p and q in real arithmetic (the
                // filter contains its centre). Refuse to treat f32 underflow
                // as evidence to remove that coefficient; keep it canonical.
                if local == 0.0 || neighbour == 0.0 {
                    count.bypassed[k] += 1;
                    count.rounding_fallback[k] += 1;
                    continue;
                }
                if local == neighbour {
                    count.bypassed[k] += 1;
                    continue;
                }
                let factor = 2.0 * (neighbour / (local + neighbour));
                let next = *w * factor;
                ensure!(factor.is_finite() && factor > 0.0 && factor <= 2.0
                    && next.is_finite() && next >= 0.0, "invalid harmonic agreement weight");
                if next == 0.0 {
                    count.bypassed[k] += 1;
                    count.rounding_fallback[k] += 1;
                    continue;
                }
                count.changed[k] += usize::from(w.to_bits() != next.to_bits());
                *w = next;
            }
        }
        Ok(count)
    }
}
