//! Bounded original-CFA region gather for reconstruction guides and admission.
//! The source rectangle is transient, unaligned, and reused one color at a time.
//! Values and clip footprints use the same owned core samplers as NativeSampler.
use crate::session_sampling::{SampledCfa, SamplingDomain, footprint_clipped};
use anyhow::{Result, ensure};
use strehl_core::{
    CfaPlane,
    align::{PlaneRef, Resampler, Similarity},
    noise::Levels,
    optics::{OpticalProfile, cfa_site_channel},
    plane::{PlaneGeometry, QuadSource},
};

#[derive(Clone, Copy, Debug)]
struct Rect {
    x: usize,
    y: usize,
    width: usize,
    height: usize,
}
impl Rect {
    fn geometry(self) -> PlaneGeometry {
        PlaneGeometry {
            width: self.width,
            height: self.height,
        }
    }
}
fn validate_pull(t: Similarity) -> Result<()> {
    ensure!(
        [t.a.re, t.a.im, t.b.re, t.b.im]
            .into_iter()
            .all(f64::is_finite)
            && t.a.norm_sq().is_finite()
            && t.a.norm_sq() > 0.,
        "invalid region sampling pull"
    );
    Ok(())
}
fn validate_domain(domain: SamplingDomain) -> Result<()> {
    domain.validate()?;
    // Integer crop origins must remain exactly representable in f64. This is
    // substantially beyond practical decoded image dimensions.
    ensure!(
        domain.full.width <= u32::MAX as usize && domain.full.height <= u32::MAX as usize,
        "region sampling geometry exceeds exact integer coordinate contract"
    );
    Ok(())
}
fn point(
    domain: SamplingDomain,
    t: Similarity,
    site: (f64, f64),
    x: usize,
    y: usize,
) -> (f64, f64) {
    let p = t.apply_at(
        (domain.x + x) as f64 + site.0,
        (domain.y + y) as f64 + site.1,
        domain.full.width as f64 * 0.5,
        domain.full.height as f64 * 0.5,
    );
    (p.0 - site.0, p.1 - site.1)
}
fn rectangle(domain: SamplingDomain, t: Similarity, site: (f64, f64)) -> Result<Option<Rect>> {
    validate_pull(t)?;
    let points = [
        point(domain, t, site, 0, 0),
        point(domain, t, site, domain.width - 1, 0),
        point(domain, t, site, 0, domain.height - 1),
        point(domain, t, site, domain.width - 1, domain.height - 1),
    ];
    ensure!(
        points.iter().all(|p| p.0.is_finite() && p.1.is_finite()),
        "region pull overflows coordinates"
    );
    let axis = |component: usize, size: usize| {
        let values = points.map(|p| if component == 0 { p.0 } else { p.1 });
        let lo = values.into_iter().fold(f64::INFINITY, f64::min);
        let hi = values.into_iter().fold(f64::NEG_INFINITY, f64::max);
        // Four original-plane pixels enclose every six-tap kernel, its final
        // legal endpoint cell, and floating rounding of affine corner extrema.
        let begin = (lo.floor() - 4.).clamp(0., size as f64) as usize;
        let end = (hi.ceil() + 5.).clamp(0., size as f64) as usize;
        (begin, end)
    };
    let (x, ex) = axis(0, domain.full.width);
    let (y, ey) = axis(1, domain.full.height);
    Ok((ex > x && ey > y).then_some(Rect {
        x,
        y,
        width: ex.saturating_sub(x),
        height: ey.saturating_sub(y),
    }))
}
fn cfa_pull(pulls: [Similarity; 3], color: CfaPlane) -> Similarity {
    match color {
        CfaPlane::R => pulls[0],
        CfaPlane::B => pulls[2],
        _ => pulls[1],
    }
}
/// Exact pixel-buffer peak, excluding Vec headers/allocator overhead. Caller
/// reserves its originals separately. Fails before source access or allocation.
pub fn reservation_bytes(domain: SamplingDomain, pulls: [Similarity; 3]) -> Result<usize> {
    validate_domain(domain)?;
    let mut maximum = 0usize;
    for color in CfaPlane::ALL {
        let (dx, dy) = color.rggb_offset();
        if let Some(r) = rectangle(
            domain,
            cfa_pull(pulls, color),
            (dx as f64 * 0.5 - 0.25, dy as f64 * 0.5 - 0.25),
        )? {
            maximum = maximum.max(
                r.width
                    .checked_mul(r.height)
                    .ok_or_else(|| anyhow::anyhow!("region rectangle overflows"))?,
            );
        }
    }
    let bytes = domain
        .pixels()
        .checked_mul(19)
        .and_then(|v| maximum.checked_mul(5).and_then(|n| v.checked_add(n)))
        .ok_or_else(|| anyhow::anyhow!("region sampling memory overflows"))?;
    ensure!(
        bytes <= isize::MAX as usize,
        "region sampling exceeds addressable memory"
    );
    Ok(bytes)
}
/// Output storage is reusable; each call allocates only one bounded, original
/// source-color rectangle. No complete source f32 plane or aligned volume.
pub struct RegionSampler {
    domain: SamplingDomain,
    budget_bytes: usize,
    peak_bytes: usize,
    output: SampledCfa,
}
impl RegionSampler {
    pub fn new(domain: SamplingDomain, budget_bytes: usize) -> Result<Self> {
        validate_domain(domain)?;
        let bytes = domain.pixels() * 19;
        ensure!(
            bytes <= budget_bytes,
            "region output exceeds sampling budget"
        );
        Ok(Self {
            domain,
            budget_bytes,
            peak_bytes: bytes,
            output: SampledCfa {
                planes: std::array::from_fn(|_| vec![0.; domain.pixels()]),
                coverage: vec![false; domain.pixels()],
                clipped: vec![false; domain.pixels()],
                support: vec![false; domain.pixels()],
            },
        })
    }
    pub fn peak_reserved_bytes(&self) -> usize {
        self.peak_bytes
    }
    pub fn gather<S: QuadSource + ?Sized>(
        &mut self,
        source: &S,
        levels: Levels,
        placement: Similarity,
        profile: Option<&OpticalProfile>,
        resampler: Resampler,
    ) -> Result<&SampledCfa> {
        validate_pull(placement)?;
        let pulls = std::array::from_fn(|channel| {
            let (dx, dy) = match channel {
                0 => (0, 0),
                1 => (1, 0),
                _ => (1, 1),
            };
            OpticalProfile::compose(profile, cfa_site_channel(dx, dy), placement)
        });
        self.gather_pulls(source, levels, pulls, resampler)
    }
    /// Pulls are exact composed R,G,B transforms in the FULL green-luma guide
    /// gauge, as returned by the geometry certificate. Both green sites share
    /// the green transform but retain their distinct physical site coordinates.
    pub fn gather_pulls<S: QuadSource + ?Sized>(
        &mut self,
        source: &S,
        levels: Levels,
        pulls: [Similarity; 3],
        resampler: Resampler,
    ) -> Result<&SampledCfa> {
        let domain = self.domain;
        ensure!(
            source.geometry() == domain.full,
            "source geometry differs from region full gauge"
        );
        ensure!(
            levels.black.is_finite()
                && levels.white.is_finite()
                && levels.white > levels.black
                && levels.white > 0.
                && levels.white <= 65535.,
            "invalid region source levels"
        );
        let reserved = reservation_bytes(domain, pulls)?;
        ensure!(
            reserved <= self.budget_bytes,
            "original region exceeds sampling budget"
        );
        self.peak_bytes = self.peak_bytes.max(reserved);
        self.output.coverage.fill(true);
        self.output.clipped.fill(false);
        self.output.support.fill(false);
        for (ci, color) in CfaPlane::ALL.into_iter().enumerate() {
            let (dx, dy) = color.rggb_offset();
            let site = (dx as f64 * 0.5 - 0.25, dy as f64 * 0.5 - 0.25);
            let transform = cfa_pull(pulls, color);
            let Some(rect) = rectangle(domain, transform, site)? else {
                self.output.planes[ci].fill(0.);
                self.output.coverage.fill(false);
                continue;
            };
            let geometry = rect.geometry();
            let mut values = vec![0.; geometry.pixels()];
            let mut clipping = vec![false; geometry.pixels()];
            let mut any_clipped = false;
            for y in 0..rect.height {
                let (r0, r1) = source.quad_rows(rect.y + y);
                let row = if dy == 0 { r0 } else { r1 };
                ensure!(
                    row.len() >= 2 * domain.full.width,
                    "short active region CFA row"
                );
                for x in 0..rect.width {
                    let raw = f32::from(row[2 * (rect.x + x) + dx]);
                    let i = y * rect.width + x;
                    values[i] = raw - levels.black;
                    clipping[i] = raw >= levels.white;
                    any_clipped |= clipping[i];
                }
            }
            let plane =
                PlaneRef::from_geometry(&values, geometry).expect("checked region dimensions");
            let s = resampler.support();
            for y in 0..domain.height {
                for x in 0..domain.width {
                    let i = y * domain.width + x;
                    let (sx, sy) = point(domain, transform, site, x, y);
                    // Preserve original-domain support exactly. The integer crop
                    // only changes the array origin; it never recenters the warp.
                    let covered = sx >= s - 0.5
                        && sy >= s - 0.5
                        && sx <= domain.full.width as f64 - 0.5 - s
                        && sy <= domain.full.height as f64 - 0.5 - s;
                    if covered {
                        let (lx, ly) = (sx - rect.x as f64, sy - rect.y as f64);
                        let value = resampler.sample_checked(plane, lx, ly).ok_or_else(|| {
                            anyhow::anyhow!("region halo omitted original interpolation support")
                        })?;
                        self.output.planes[ci][i] = value;
                        self.output.clipped[i] |= any_clipped
                            && footprint_clipped(&clipping, geometry, lx, ly, resampler);
                    } else {
                        self.output.planes[ci][i] = 0.;
                        self.output.coverage[i] = false;
                    }
                }
            }
        }
        for i in 0..domain.pixels() {
            self.output.support[i] = self.output.coverage[i] && !self.output.clipped[i];
        }
        Ok(&self.output)
    }
}
#[cfg(test)]
#[path = "session-reconstruction-sampling-tests.rs"]
mod tests;
