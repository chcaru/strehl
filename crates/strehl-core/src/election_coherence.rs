//! Where the election has nothing to choose between, measured from the election.
//!
//! # Why this exists
//!
//! The veil estimator needs one predicate: *does the election have anything to
//! choose between at this pixel?* Where it does not, an extremum across frames
//! costs no detail and may reject the veil; where it does, the elected frame
//! carries real information and nothing may override it.
//!
//! The first shipped answer read the significance of the pixel's strongest
//! through-focus peak against the merge's own `--gate` cut. That cut is a
//! statement about when *averaging* is safe and carries no information about
//! veiling, and borrowing it failed on measurement: `flower-bud`'s median
//! significance sat at 2.97 against a cut of 4.0 and 83.51% of the frame was
//! eligible including the rim, while `coffee-bean`'s sat at **exactly 4.00**, so
//! the gate split that image at its own median and kept the featureless far
//! background — the half with no veil in it — while excluding the rim, which is
//! scored *peaked* because the veil gradient and the silhouette are themselves
//! content. The correction then lifted the clean far field 5.15% and moved the
//! rim 0.23%. See `docs/research/BUILD-HALO.md` section 32.
//!
//! # What this does instead
//!
//! The elected frame index **is** a depth ordering, so the question can be put
//! to the election directly rather than to a borrowed threshold:
//!
//! > Dead ground elects incoherently — neighbouring pixels pick unrelated
//! > frames from across the bracket, because there is nothing to focus on and
//! > the argmax is chasing noise. A real object elects coherently — its
//! > neighbours agree, because they are at the same depth.
//!
//! So the local **spread of the elected index** separates the two, and it does
//! so with a silhouette that brightness cannot fool: it traces a pale subject on
//! a pale ground and a dark one on a dark ground identically, because it never
//! reads luminance at all.
//!
//! # Why the threshold is a quantile
//!
//! The cut is taken as a quantile of the image's own incoherence distribution,
//! not as an absolute constant. That is the specific repair for the failure
//! above: a fixed number is a different test on every subject depending on where
//! that subject's distribution happens to fall relative to it, and one subject
//! cannot reveal the difference.
//!
//! # Why the per-pixel answer is not the gate
//!
//! Asking the question one pixel at a time and gating on the answer produced a
//! **lacework**: the correction switched on and off at the scale of individual
//! paper fibres, because whether one fibre happened to be resolved somewhere in
//! the bracket is a genuine per-pixel fact. It is also an invisible one, and a
//! correction that follows it writes visible dirt onto a smooth backdrop.
//! See `docs/research/BUILD-HALO.md` section 33 and `INCOH/pics/cb-lift.png`.
//!
//! So the gate ramps on [`incoherent_fraction`] — *what proportion of this
//! neighbourhood has nothing to choose between* — rather than on the per-pixel
//! predicate. Two things follow. The gate varies on the scale of objects
//! instead of texture, which is the scale a veil actually has; and the second
//! threshold is a **fraction**, which is the one kind of constant that is
//! genuinely comparable between subjects, so the section 32 failure cannot
//! recur through the back door of a newly-borrowed absolute number.

use crate::boxfilter::box_mean;
use crate::plane::PlaneGeometry;

/// Half-width of the coherence window, in binned pixels.
///
/// 4 gives the 9x9 window the out-of-crate measurement used
/// (`experiments/BUILD-HALO/depth_profile.py`), so the in-crate mask can be
/// compared against that result rather than being a fresh unvalidated choice.
pub const COHERENCE_RADIUS: usize = 4;

/// Local standard deviation of the elected frame index, per pixel.
///
/// High where the election is chasing noise (dead ground), low over a real
/// object at a settled depth. Returned in frames, so the numbers are readable
/// against the bracket depth.
pub fn incoherence(best_index: &[u16], geom: PlaneGeometry) -> Vec<f32> {
    let px = geom.pixels();
    assert_eq!(
        best_index.len(),
        px,
        "election index field is {} px but the plane is {px} px",
        best_index.len()
    );

    let idx: Vec<f32> = best_index.iter().map(|&k| k as f32).collect();
    let sq: Vec<f32> = idx.iter().map(|v| v * v).collect();

    let mut scratch = vec![0.0f32; px];
    let mut mean = vec![0.0f32; px];
    let mut mean_sq = vec![0.0f32; px];
    box_mean(&idx, geom, COHERENCE_RADIUS, &mut scratch, &mut mean);
    box_mean(&sq, geom, COHERENCE_RADIUS, &mut scratch, &mut mean_sq);

    mean_sq
        .iter()
        .zip(mean.iter())
        .map(|(&m2, &m)| (m2 - m * m).max(0.0).sqrt())
        .collect()
}

/// The `q`-quantile of a field, with `q` in `[0, 1]`.
///
/// Used to take the veil's per-pixel cut from the image's own distribution
/// instead of a constant borrowed from another subsystem.
pub fn quantile(field: &[f32], q: f32) -> f32 {
    if field.is_empty() {
        return 0.0;
    }
    let mut v: Vec<f32> = field.iter().copied().filter(|x| x.is_finite()).collect();
    if v.is_empty() {
        return 0.0;
    }
    v.sort_unstable_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    let i = (((v.len() - 1) as f64) * (q.clamp(0.0, 1.0) as f64)).round() as usize;
    v[i]
}

/// Radius of the support window, in binned pixels.
///
/// Chosen to be large against the texture the per-pixel predicate follows
/// (paper fibre, ~10-30 px) and small against the objects a veil surrounds
/// (~1400 px for `coffee-bean`), so the gate tracks the second and ignores the
/// first. A 49x49 window.
pub const SUPPORT_RADIUS: usize = 24;

/// Fraction of the neighbourhood whose election is incoherent, in `[0, 1]`.
///
/// This, not the per-pixel predicate, is what the veil ramps on. `cut` is the
/// per-pixel threshold, which must come from [`quantile`] of this image's own
/// distribution; the fraction it is turned into is then directly comparable
/// across subjects, because a proportion carries no scene units.
pub fn incoherent_fraction(sd: &[f32], geom: PlaneGeometry, cut: f32) -> Vec<f32> {
    fraction_within(sd, geom, cut, SUPPORT_RADIUS, true)
}

/// Radius of the veil's reach, in binned pixels.
///
/// A veil is cast BY something. Its strength therefore falls off with distance
/// from the occluder casting it, and the measured fall-off is ~250 px
/// (`docs/research/ORCH-veiling.md` section 12).
pub const REACH_RADIUS: usize = 192;

/// How much coherently-elected content — real, resolved, at a settled depth —
/// lies within veiling reach of each pixel.
///
/// # Why this is not the geometric gate that was refuted
///
/// The eligibility test stays exactly where the specification put it: content,
/// via [`incoherent_fraction`]. This is not eligibility. It is the **amplitude**
/// of a physical term, and that term genuinely decays with distance from the
/// occluder, because there is nothing out on open ground for a foreground to
/// veil with.
///
/// Without it the correction is applied wherever it is *safe* rather than
/// wherever it is *needed*, and those are different sets: dead ground 900 px
/// from the subject is maximally safe and carries no veil at all. Measured on
/// `coffee-bean`, treating it lifted the clean far field 6.04%, which turns a
/// shape correction into a gain change and pushed every outer band backwards.
/// See `docs/research/BUILD-HALO.md` section 33.
pub fn occluder_proximity(sd: &[f32], geom: PlaneGeometry, cut: f32) -> Vec<f32> {
    fraction_within(sd, geom, cut, REACH_RADIUS, false)
}

/// Fraction of the `radius` neighbourhood on one side of `cut`.
fn fraction_within(
    sd: &[f32],
    geom: PlaneGeometry,
    cut: f32,
    radius: usize,
    above: bool,
) -> Vec<f32> {
    let px = geom.pixels();
    assert_eq!(
        sd.len(),
        px,
        "incoherence field is {} px but the plane is {px} px",
        sd.len()
    );
    let bin: Vec<f32> = sd
        .iter()
        .map(|&v| f32::from(u8::from((v > cut) == above)))
        .collect();
    let mut scratch = vec![0.0f32; px];
    let mut out = vec![0.0f32; px];
    box_mean(&bin, geom, radius, &mut scratch, &mut out);
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn geom(w: usize, h: usize) -> PlaneGeometry {
        PlaneGeometry {
            width: w,
            height: h,
        }
    }

    #[test]
    fn a_settled_depth_is_coherent_and_dead_ground_is_not() {
        let (w, h) = (64, 64);
        let mut idx = vec![100u16; w * h];
        // Right half is dead ground: the election alternates wildly between
        // opposite ends of the bracket, exactly as an argmax over noise does.
        for y in 0..h {
            for x in (w / 2)..w {
                idx[y * w + x] = if (x + y) % 2 == 0 { 0 } else { 200 };
            }
        }
        let sd = incoherence(&idx, geom(w, h));

        let object = sd[32 * w + 8];
        let dead = sd[32 * w + 56];
        assert!(
            object < 1.0,
            "a region at one settled depth must be coherent, got sd {object}"
        );
        assert!(
            dead > 50.0,
            "dead ground electing across the bracket must be incoherent, got sd {dead}"
        );
    }

    #[test]
    fn the_mask_does_not_read_luminance() {
        // The same election, described twice. If the statistic depended on
        // brightness in any way these could differ; it cannot, because no
        // luminance is passed in at all. This pins the property the
        // luminance-threshold silhouettes failed.
        let (w, h) = (32, 32);
        let idx = vec![7u16; w * h];
        let a = incoherence(&idx, geom(w, h));
        let b = incoherence(&idx, geom(w, h));
        assert_eq!(a, b);
        assert!(a.iter().all(|&v| v < 1e-6), "a constant depth has no spread");
    }

    #[test]
    fn the_quantile_tracks_the_distribution_rather_than_a_constant() {
        // The whole point of a quantile cut: the same q lands at a different
        // absolute value on a different image, which is what a borrowed
        // constant cannot do.
        let a: Vec<f32> = (0..=100).map(|i| i as f32).collect();
        let b: Vec<f32> = (0..=100).map(|i| i as f32 * 10.0).collect();
        assert_eq!(quantile(&a, 0.55), 55.0);
        assert_eq!(quantile(&b, 0.55), 550.0);
        assert_eq!(quantile(&a, 0.0), 0.0);
        assert_eq!(quantile(&a, 1.0), 100.0);
    }

    #[test]
    fn reach_falls_off_with_distance_from_resolved_content() {
        // The section 33 repair for the far-field lift. A resolved object on the
        // left, dead ground everywhere else. Proximity must be high beside the
        // object and vanish out on open ground -- otherwise the envelope is
        // applied where it is safe rather than where it is needed.
        let (w, h) = (1024, 64);
        let mut sd = vec![100.0f32; w * h];
        for y in 0..h {
            for x in 0..64 {
                sd[y * w + x] = 0.0;
            }
        }
        let prox = occluder_proximity(&sd, geom(w, h), 50.0);

        let beside = prox[32 * w + 70];
        let far = prox[32 * w + 1000];
        assert!(
            beside > 0.05,
            "a pixel beside resolved content must be within reach, got {beside}"
        );
        assert!(
            far < 1e-6,
            "open ground far from any occluder has nothing to veil it, got {far}"
        );
        assert!(beside > far, "reach must fall off with distance");
    }

    #[test]
    fn non_finite_samples_do_not_poison_the_quantile() {
        let v = vec![1.0, f32::NAN, 2.0, f32::INFINITY, 3.0];
        assert_eq!(quantile(&v, 0.5), 2.0);
    }

    #[test]
    fn a_lacework_of_specks_does_not_open_the_gate_but_a_region_does() {
        // The section 33 repair, pinned. Left half is scattered single-pixel
        // incoherence -- the paper-fibre case, which must stay shut. Right half
        // is a solid incoherent region -- dead ground, which must open.
        let (w, h) = (256, 128);
        let mut sd = vec![0.0f32; w * h];
        for y in 0..h {
            for x in 0..w {
                if x < w / 2 {
                    if x % 7 == 0 && y % 7 == 0 {
                        sd[y * w + x] = 100.0;
                    }
                } else {
                    sd[y * w + x] = 100.0;
                }
            }
        }
        let occ = incoherent_fraction(&sd, geom(w, h), 50.0);

        let speckled = occ[64 * w + 40];
        let solid = occ[64 * w + 200];
        assert!(
            speckled < 0.10,
            "a scatter of specks must not read as dead ground, got {speckled}"
        );
        assert!(
            solid > 0.95,
            "a solid incoherent region must read as dead ground, got {solid}"
        );
    }
}
