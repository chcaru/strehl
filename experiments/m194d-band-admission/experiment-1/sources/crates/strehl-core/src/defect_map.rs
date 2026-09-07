//! Sensor defect maps: hot photosites (additive) and dust (multiplicative).
//!
//! A sensor defect is a property of the **camera**, not of the stack, so it is
//! measured once from calibration captures, written to a sidecar, and applied
//! to every stack that body shoots. This module is the sidecar's format, the
//! two detectors that build it, the corrector that consumes it, and the metric
//! that says whether the corrector worked.
//!
//! # The ordering, which is the whole point
//!
//! Both defects are fixed in **sensor** coordinates. The aligner warps every
//! frame by its own per-frame similarity, because focus breathing changes
//! magnification frame to frame — measured at up to **232.7 plane px**
//! corner-to-corner on `bee-3-cpl` (SYNTHESIS fact 1177). So a defect that is
//! one stationary object on the silicon lands on a **different scene point in
//! every frame**.
//!
//! [`DefectMap::apply`] therefore takes the frame's own sensor samples, before
//! any warp has touched them. Applying a sensor-coordinate map after the warp
//! would apply it at the wrong place — the map's coordinates no longer name the
//! photosites they were measured at — and the error grows with the warp. The
//! call site in `crates/strehl-cli/src/stack.rs` sits immediately after
//! `strehl_raw::decode` and before anything else reads the frame, and
//! `dust_correction_must_precede_the_warp_to_land_on_the_defect` is the planted
//! control for the ordering rather than an argument for it.
//!
//! # What the corpus already knows, and what it does not
//!
//! **The additive half is a measured null on this body and this module does not
//! pretend otherwise.** Four independent censuses of the same 242 delivered
//! dark frames — M22's 11,393, M48c's 13,650, M101's 14,604 and this module's
//! own 14,626 (`experiments/BUILD-DEFECT/data/03-hot.json`) — agree that the
//! recurrent hot-pixel population is real, and M101 then measured that it does
//! **not** matter:
//!
//! - the in-situ excess reaching a light frame is **1.5 DN** on one green
//!   plane (M101 P6);
//! - the election does not begin to prefer a planted hot pixel until between
//!   **100 and 250 DN** (M101 P11);
//! - a defect coordinate wins its own election at **0.987x** the shift
//!   control's rate against a 1.5x bar, and its elected trail is **0.931 px**
//!   against a null of **0.937 px** (M101 P9, P10).
//!
//! So [`Correction::hot`] exists, is measured, and is **off**. It ships as a
//! named, loadable, testable path because the *next* body may not be this one —
//! amplitude is what makes the null, and amplitude is per-sensor.
//!
//! **The multiplicative half is not a null, and the corpus says so in
//! writing.** M29 §6 consequence 1: *"Dust must be handled explicitly. The
//! merge does not remove it, does not dilute it, and cannot detect it.
//! Flat-field division or an explicit defect map is required. This is now a
//! design decision, not an open question."* Its measurement is that the merge
//! averages **adjacent** frames, whose relative warp is 0.07–0.22 plane px, so
//! the dilution factor `D` is **0.999 at n_eff = 3** — a dust shadow arrives in
//! the output at essentially full contrast.
//!
//! # Two different objects, two different corrections
//!
//! | | hot photosite | dust |
//! |---|---|---|
//! | physics | thermally generated charge, added before the gain | an occluder on the sensor stack, attenuating light |
//! | arithmetic | **additive**, `S -> S - c` | **multiplicative**, `S -> S * g` |
//! | amplitude scales with | ISO (through the gain), and exposure | the **signal**, so it grows with the scene |
//! | extent | one photosite (M48c: 99.8% singletons, largest cluster 3 px) | a disc of tens of quads |
//! | aperture | independent | **dependent** — the shadow sharpens and deepens as the lens stops down |
//! | measured from | dark frames | flat fields |
//!
//! The multiplicative row is why dust is the one that matters. A 1.5 DN
//! additive offset is 1.5 DN whether the scene is black or white. A **−1.8%**
//! attenuation is 1.8% of whatever is underneath it: 0.5 DN in a deep shadow
//! and **72 DN** on a 4,000 DN midtone, which is 2.4x the shot noise there.
//!
//! # The aperture caveat, stated where it can be read
//!
//! [`DefectMap::aperture_f`] is `Some` when the map came from flats at a known
//! aperture, and the corrector does **not** refuse a mismatch — it cannot, the
//! frame's aperture is not in [`crate::noise::Levels`]. What it does is record
//! the aperture in the sidecar so a mismatch is visible. MEASURED
//! (`experiments/BUILD-DEFECT/data/00-corpus-aperture.json`): the delivered
//! flats are f/5.6 at 200 mm, and **20 of the 26** corpus stacks are also
//! f/5.6 at 200 mm, 3 are f/8 and 3 are f/11. M71 §7.2's caveat that its dust
//! numbers are "a lower bound ... the corpus shoots f/8-f/11" is therefore
//! wrong for the majority of the corpus; the map is at the matched aperture for
//! 20 stacks and is a lower bound only for the other 6.

use std::collections::BTreeSet;
use std::fmt::Write as _;
use std::path::{Path, PathBuf};

/// Format magic. Bumping the version is a breaking change to the text format.
pub const MAGIC: &str = "strehl-defect-map";
/// Current sidecar format version.
///
/// **2 because v1 did not say which array its coordinates index.** A v1 map
/// records `sensor` and `covered` geometry, which is enough to check that a map
/// is being applied to the right *size* of frame and not enough to check that
/// it is being applied at the right *origin*. Those are different facts and the
/// difference is 32 columns of optical black.
///
/// This is not hypothetical. Building this module's own self-validation, a
/// script read `raw_image` where the map had been measured on
/// `raw_image_visible`; every coordinate was offset by the optical-black
/// border, and the readings that came back were **+54.8%** and **+22.2%** — a
/// dust mote reported as a bright spot. It was caught only because the sign was
/// absurd. A 4-column offset instead of a 32-column one would have produced
/// readings that were merely wrong.
///
/// v2 therefore carries a required [`CoordSpace`] key, and a map that lacks it
/// is **refused**. Refusing a v1 map is a loud failure on a file that is
/// probably fine; guessing its origin is a silent 54.8% error on a file that is
/// not. The project takes the loud one.
pub const VERSION: u32 = 2;

/// Which raw array a map's coordinates index.
///
/// A decoder hands back one buffer and two rectangles: the whole `data`
/// allocation, and the `active` sub-rectangle inside it that holds real sensor
/// readings. A coordinate pair is meaningless until you say which of those it
/// is relative to, and the two differ by the optical-black border — 4 columns
/// on the A7C II as `rawpy` crops it, 32 in the buffer `rawler` returns.
///
/// This key is **load-bearing and not decorative**: [`DefectMap::apply`]
/// branches on it to choose the origin. A key that is written, parsed, and then
/// never conditioned on is the "print, then TEST" defect this project has
/// shipped three times, and it would be especially useless here because the
/// whole reason the key exists is that the wrong origin is undetectable
/// downstream.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CoordSpace {
    /// Origin at the top-left of the **active area**. This is what
    /// `rawpy.raw_image_visible` returns and what every map this project has
    /// measured is written in.
    Active,
    /// Origin at the top-left of the **whole decoded buffer**, optical black
    /// included. This is what `rawpy.raw_image` and `rawler`'s raw buffer
    /// return.
    Full,
}

impl CoordSpace {
    /// Parse the `coords` header value.
    ///
    /// **A typo is an error, never a fallback**, for the same reason the key
    /// exists at all: a map that silently defaulted to `active` when it meant
    /// `full` would correct 4 columns to the left of every defect it names, and
    /// nothing downstream can see that.
    pub fn parse(s: &str) -> Result<CoordSpace, DefectMapError> {
        match s.trim() {
            "active" => Ok(CoordSpace::Active),
            "full" => Ok(CoordSpace::Full),
            other => Err(DefectMapError::UnknownCoordSpace {
                found: other.to_string(),
            }),
        }
    }
}

impl std::fmt::Display for CoordSpace {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(match self {
            CoordSpace::Active => "active",
            CoordSpace::Full => "full",
        })
    }
}

/// Everything that can go wrong reading, building or applying a defect map.
///
/// Every variant is a **refusal**, never a degraded correction. A truncated
/// file is an error and never a short site list; a map measured on a different
/// sensor geometry is an error and never a best-effort application at the wrong
/// coordinates. The one thing a silent default would buy here is a render that
/// is subtly wrong at 14,000 scattered coordinates, which is the least
/// detectable failure this pipeline could have.
#[derive(Debug, thiserror::Error)]
pub enum DefectMapError {
    #[error("not a strehl defect map: expected magic {MAGIC:?}, found {found:?}")]
    BadMagic { found: String },

    #[error("unsupported defect map version {found} (this build understands {VERSION})")]
    BadVersion { found: u32 },

    #[error("defect map header is missing required key {key:?}")]
    MissingKey { key: &'static str },

    #[error("defect map key {key:?} has unparsable value {value:?}")]
    BadValue { key: String, value: String },

    #[error("defect map line {line} is malformed: {detail}")]
    BadLine { line: usize, detail: String },

    #[error(
        "defect map is truncated: header declares {declared_hot} hot sites and \
         {declared_dust} dust quads, {found_hot} and {found_dust} were read, and the \
         terminating `end` record is {}",
        if *saw_end { "present but disagrees" } else { "absent" }
    )]
    Truncated {
        declared_hot: usize,
        declared_dust: usize,
        found_hot: usize,
        found_dust: usize,
        saw_end: bool,
    },

    #[error("defect map has a duplicate {kind} record at ({x}, {y})")]
    DuplicateSite {
        kind: &'static str,
        x: u32,
        y: u32,
    },

    #[error(
        "defect map {kind} record at ({x}, {y}) is outside the {w}x{h} area the map \
         declares it measured"
    )]
    SiteOutOfRange {
        kind: &'static str,
        x: u32,
        y: u32,
        w: usize,
        h: usize,
    },

    #[error(
        "defect map was measured on a {want_w}x{want_h} active area but is being applied \
         to a {got_w}x{got_h} one, a {frac:.1}% difference; the tolerated difference is \
         {bar:.1}%. A sensor-coordinate map applied to a different READOUT MODE indexes \
         different photosites, because the crop moves where (0, 0) sits on the sensor"
    )]
    SensorMismatch {
        want_w: usize,
        want_h: usize,
        got_w: usize,
        got_h: usize,
        frac: f64,
        bar: f64,
    },

    #[error(
        "defect map declares a dust gain of {gain} at quad ({x}, {y}); a dust gain must \
         be finite and in [1.0, {max}] -- below 1.0 it is darkening rather than \
         restoring, and above {max} it is amplifying by more than any measured mote"
    )]
    ImplausibleGain { x: u32, y: u32, gain: f32, max: f32 },

    #[error("defect map I/O on {path}: {source}")]
    Io {
        path: PathBuf,
        #[source]
        source: std::io::Error,
    },

    #[error(
        "unknown defect correction arm {found:?}; the arms are \"hot\", \"dust\", \
         \"both\" and \"none\""
    )]
    UnknownArm { found: String },

    #[error(
        "defect map declares coords {found:?}; the coordinate spaces are \"active\" \
         (origin at the active area, what rawpy's raw_image_visible returns) and \
         \"full\" (origin at the whole decoder buffer, optical black included)"
    )]
    UnknownCoordSpace { found: String },
}

/// The largest dust gain the format will carry.
///
/// A gain of 1.25 is a 20% shadow. The deepest single quad measured on this
/// body's flats is −3.81% (gain 1.0396) and the deepest 5x5-averaged patch is
/// −3.51%, so 1.25 is roughly **six times** anything observed and exists to
/// catch a corrupt file rather than to bound a real mote. A file that asks for
/// more than this is refused, loudly, rather than silently clamped: a clamp
/// would turn a corrupt map into a plausible render.
pub const MAX_DUST_GAIN: f32 = 1.25;

/// One hot (or, with a negative amplitude, cold) photosite.
///
/// The amplitude is stored in **electrons**, not DN, and that is the only
/// choice that survives the corpus. Dark charge is generated at the photodiode
/// *before* the analogue gain, so the same site reads `excess_e * gain(ISO)`
/// DN at every ISO; storing DN would pin the map to the ISO it was measured at.
/// M48c measured this directly: within a gain mode the excess is purely
/// proportional to `g` with an additive term consistent with zero.
///
/// **What it is NOT is a dark-current rate.** M101 P7 settled the fork: at 20x
/// the darks' exposure and the same gain the in-situ excess is **1.81x**, not
/// 20x, so ~95% of what a 1/100 s dark measures is a *fixed* per-site offset
/// (`c = 3.47 e-`) and only ~5% is thermal (`d = 15.4 e-/s`). This field
/// carries the whole 1/100 s measurement as though it were fixed, which
/// **under-corrects by the thermal term at long exposure**: at 1/5 s that is
/// 3.1 e- of a measured 6.55 e-. Modelling the thermal limb needs a dark set at
/// a second exposure and the corpus has none — all 242 delivered darks are
/// 1/100 s (M22 §1).
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct HotSite {
    /// Column in the frame's **active area**, sensor lattice.
    pub x: u32,
    /// Row in the frame's **active area**, sensor lattice.
    pub y: u32,
    /// Excess over the same-plane neighbourhood, in electrons at the
    /// calibration exposure.
    pub excess_e: f32,
}

/// One CFA quad whose light is attenuated by dust.
///
/// Stored on the **quad lattice** (half the sensor's linear resolution), and
/// the gain is applied to all four samples of the quad. That is not a
/// compression trick, it is the physics: dust sits on the sensor stack, well
/// above the colour filter array, so its shadow is achromatic to first order
/// and is far larger than a 2x2 quad. MEASURED on this body's flats — the
/// smallest connected mote is 398 quads across and the median is 749, i.e.
/// roughly 30 quads in diameter, so a quad is a 30th of the object.
///
/// Storing per-sample instead would quadruple the sidecar to describe
/// structure the optics cannot produce.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct DustQuad {
    /// Quad column, i.e. sensor column `2 * px`.
    pub px: u32,
    /// Quad row, i.e. sensor row `2 * py`.
    pub py: u32,
    /// Multiplicative restoration, `>= 1.0`. A gain of 1.02 restores a 1.96%
    /// shadow.
    pub gain: f32,
}

/// Which arms of the correction to run.
///
/// `Correction::default()` is **both arms off**, and that is deliberate: a
/// calibration file the user has not supplied cannot change a render, and a
/// calibration file the user *has* supplied should not silently change a render
/// either until they say which parts of it to believe. The byte-freeze registry
/// in `crates/strehl-cli/tests/byte-freezes.tsv` pins two renders to the byte;
/// a default-on correction would move both and the move would look like a
/// regression in whatever else was committed that day.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct Correction {
    /// Subtract the additive dark offset at hot photosites.
    ///
    /// **Measured immaterial on the A7C II** — see the module header and M101.
    pub hot: bool,
    /// Divide out the multiplicative dust shadow.
    pub dust: bool,
}

impl Correction {
    /// Neither arm. The default, and the byte-frozen path.
    pub const NONE: Correction = Correction {
        hot: false,
        dust: false,
    };
    /// Dust only — the arm the corpus supports on this body.
    pub const DUST: Correction = Correction {
        hot: false,
        dust: true,
    };
    /// Hot only.
    pub const HOT: Correction = Correction {
        hot: true,
        dust: false,
    };
    /// Both arms.
    pub const BOTH: Correction = Correction {
        hot: true,
        dust: true,
    };

    /// Parse an arm name.
    ///
    /// **A typo is an error, never a fallback.** `"dust "`, `"Dust"` and
    /// `"dusty"` are three different mistakes and all three of them would
    /// silently render the byte-frozen path if this returned a default; the
    /// user would then read a "correction applied" banner over an uncorrected
    /// image. Matching the shape of
    /// `a_typod_override_errors_rather_than_falling_back_to_the_default`
    /// elsewhere in this crate.
    pub fn parse(s: &str) -> Result<Correction, DefectMapError> {
        match s.trim() {
            "none" => Ok(Correction::NONE),
            "hot" => Ok(Correction::HOT),
            "dust" => Ok(Correction::DUST),
            "both" => Ok(Correction::BOTH),
            other => Err(DefectMapError::UnknownArm {
                found: other.to_string(),
            }),
        }
    }

    /// Whether anything at all would be done.
    pub fn is_noop(&self) -> bool {
        !self.hot && !self.dust
    }
}

/// Round-trips through [`Correction::parse`], so a printed banner naming the
/// arms is a string the caller could have typed.
impl std::fmt::Display for Correction {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(match (self.hot, self.dust) {
            (false, false) => "none",
            (true, false) => "hot",
            (false, true) => "dust",
            (true, true) => "both",
        })
    }
}

/// What a correction pass actually did, partitioned so the counts sum.
///
/// Every site in the map lands in exactly one bucket of its arm, and
/// [`CorrectionReport::check_partition`] asserts that. This exists because
/// "corrected: 0" and "examined: 0" are different failures with the same
/// printed line, and this project has shipped the confusion three times: a map
/// that loaded but covered nothing, an arm that was switched off, and a frame
/// whose active area was smaller than the map all print the same reassuring
/// zero.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct CorrectionReport {
    /// Hot sites in the map. `hot_examined == 0` means the map has no hot arm.
    pub hot_examined: usize,
    /// Corrected: the sample was inside the frame, unclipped, and moved.
    pub hot_corrected: usize,
    /// Below [`HotFloor`]: the site is in the map but its amplitude did not
    /// clear the floor this run was asked to apply.
    pub hot_below_floor: usize,
    /// The sample was at or above the white level. A clipped sample's true
    /// value is unknown; subtracting from it manufactures data.
    pub hot_clipped: usize,
    /// The site is outside this frame's active area.
    pub hot_outside: usize,
    /// The correction rounded to zero at this ISO — a real outcome, not an
    /// error, and one that would otherwise be indistinguishable from
    /// `hot_corrected`.
    pub hot_no_change: usize,

    /// Dust quads in the map.
    pub dust_examined: usize,
    /// Corrected: all four samples inside the frame, at least one moved.
    pub dust_corrected: usize,
    /// Every sample of the quad was clipped.
    pub dust_clipped: usize,
    /// The quad is outside this frame's active area.
    pub dust_outside: usize,
    /// The gain was 1.0 to within a DN on every sample of the quad.
    pub dust_no_change: usize,

    /// Individual `u16` samples whose stored value changed. The only number
    /// here that is about pixels rather than about map records.
    pub samples_changed: usize,
}

impl CorrectionReport {
    /// Fold another frame's report into this one. Used to total a whole stack.
    pub fn absorb(&mut self, o: &CorrectionReport) {
        self.hot_examined += o.hot_examined;
        self.hot_corrected += o.hot_corrected;
        self.hot_below_floor += o.hot_below_floor;
        self.hot_clipped += o.hot_clipped;
        self.hot_outside += o.hot_outside;
        self.hot_no_change += o.hot_no_change;
        self.dust_examined += o.dust_examined;
        self.dust_corrected += o.dust_corrected;
        self.dust_clipped += o.dust_clipped;
        self.dust_outside += o.dust_outside;
        self.dust_no_change += o.dust_no_change;
        self.samples_changed += o.samples_changed;
    }

    /// Every hot site landed in exactly one bucket, and likewise every dust
    /// quad. Returns `(hot_ok, dust_ok)`.
    pub fn check_partition(&self) -> (bool, bool) {
        let hot = self.hot_corrected + self.hot_below_floor + self.hot_clipped
            + self.hot_outside
            + self.hot_no_change;
        let dust =
            self.dust_corrected + self.dust_clipped + self.dust_outside + self.dust_no_change;
        (hot == self.hot_examined, dust == self.dust_examined)
    }

    /// One line for a run banner.
    pub fn describe(&self) -> String {
        format!(
            "hot {}/{} corrected (floor {}, clipped {}, outside {}, no-change {}); \
             dust {}/{} corrected (clipped {}, outside {}, no-change {}); \
             {} samples changed",
            self.hot_corrected,
            self.hot_examined,
            self.hot_below_floor,
            self.hot_clipped,
            self.hot_outside,
            self.hot_no_change,
            self.dust_corrected,
            self.dust_examined,
            self.dust_clipped,
            self.dust_outside,
            self.dust_no_change,
            self.samples_changed
        )
    }
}

/// The amplitude floor a correction run applies to the hot arm, in electrons.
///
/// **This is a parameter and not a constant because the map's reproducibility
/// is a function of amplitude and nothing else.** MEASURED on the 242 delivered
/// darks by splitting each ISO group's 20 frames into two interleaved halves of
/// 10 and rebuilding the whole map from each
/// (`experiments/BUILD-DEFECT/data/03-hot.json`):
///
/// | median amplitude | sites | recovered in BOTH halves |
/// |---|---|---|
/// | 1–2 e- | 124 | **0.000** |
/// | 2–4 e- | 9,532 | **0.116** |
/// | 4–8 e- | 4,859 | 0.607 |
/// | 8–16 e- | 105 | **1.000** |
/// | >= 16 e- | 6 | **1.000** |
///
/// So the 14,626-site census is *dominated* by sites that a second look at the
/// same silicon does not find. [`HotFloor::REPRODUCIBLE`] is the cut above
/// which a re-measurement recovers every site; [`HotFloor::CENSUS`] is the
/// whole map and is what M22, M48c and M101 published.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct HotFloor(pub f32);

impl HotFloor {
    /// 8 e-: the lowest stratum measured to reproduce 1.000 across an
    /// independent half of the same darks. 111 sites on this body.
    pub const REPRODUCIBLE: HotFloor = HotFloor(8.0);
    /// 0 e-: everything in the file. Comparable with the published censuses
    /// and **not** comparable with a second measurement of the same sensor.
    pub const CENSUS: HotFloor = HotFloor(0.0);
}

impl Default for HotFloor {
    fn default() -> Self {
        HotFloor::REPRODUCIBLE
    }
}

/// A camera's measured defect map.
#[derive(Debug, Clone, PartialEq)]
pub struct DefectMap {
    /// The active-area size, in sensor samples, the map was measured for.
    /// Applying to any other geometry is [`DefectMapError::SensorMismatch`].
    pub sensor_w: usize,
    pub sensor_h: usize,
    /// The sub-rectangle of that active area the calibration frames actually
    /// covered, anchored at the origin.
    ///
    /// These are not the same number, and pretending they are is a real defect
    /// waiting to happen: `rawler` reports the A7C II's active area as
    /// **7032x4688** while `rawpy`, which decoded the calibration frames,
    /// reports **7028x4688**. M48c fact 33 measured the `rawpy` columns to be
    /// `rawler`'s leading 7028, so the two agree on every column they share and
    /// the last 4 are simply **unmeasured**. A map that silently claimed to
    /// cover them would be asserting a calibration it does not have.
    pub covered_w: usize,
    pub covered_h: usize,
    /// Which raw array [`DefectMap::hot`] and [`DefectMap::dust`] coordinates
    /// index. Required in the file; see [`CoordSpace`] for the 54.8% error that
    /// made it required.
    pub coords: CoordSpace,
    /// `clean_model` of the body the map was measured on.
    pub camera: String,
    /// The aperture the dust arm was measured at, when known. See the module
    /// header: dust is aperture-dependent and the hot arm is not.
    pub aperture_f: Option<f32>,
    /// Hot photosites, sorted by `(y, x)`.
    pub hot: Vec<HotSite>,
    /// Dust quads, sorted by `(py, px)`.
    pub dust: Vec<DustQuad>,
    /// Free-form provenance, one line each, round-tripped verbatim.
    pub provenance: Vec<String>,
}

impl DefectMap {
    /// How far a frame's active area may differ from the map's before the map
    /// is refused, as a fraction of each dimension.
    ///
    /// **1%, and both margins are measured.** See [`DefectMap::check_geometry`]
    /// for the derivation: the difference this must ADMIT is 0.11% (the corpus
    /// carries two full-frame active widths, 7032 and 7040, on one body) and
    /// the difference it must REJECT is ~34% (the A7C II's APS-C crop, which
    /// moves the origin and invalidates every coordinate). 9x above one, 30x
    /// below the other, and no readout mode of this body in between.
    ///
    /// It is a fraction rather than a pixel count because the quantity that
    /// matters is "is this the same readout mode", which scales with the
    /// sensor.
    pub const MAX_ACTIVE_MISMATCH_FRAC: f64 = 0.01;

    /// An empty map for a given geometry. Applying it is a no-op that reports
    /// `examined: 0` in both arms, which is the point — a body with no
    /// calibration is distinguishable from a body with a clean one.
    pub fn empty(sensor_w: usize, sensor_h: usize, camera: &str) -> DefectMap {
        DefectMap {
            sensor_w,
            sensor_h,
            covered_w: sensor_w,
            covered_h: sensor_h,
            coords: CoordSpace::Active,
            camera: camera.to_string(),
            aperture_f: None,
            hot: Vec::new(),
            dust: Vec::new(),
            provenance: Vec::new(),
        }
    }

    /// Fraction of the sensor's samples the dust arm would touch.
    pub fn dust_area_fraction(&self) -> f64 {
        (self.dust.len() * 4) as f64 / (self.sensor_w * self.sensor_h) as f64
    }

    /// Fraction of the sensor's samples the hot arm would touch at `floor`.
    pub fn hot_area_fraction(&self, floor: HotFloor) -> f64 {
        let n = self.hot.iter().filter(|s| s.excess_e >= floor.0).count();
        n as f64 / (self.sensor_w * self.sensor_h) as f64
    }

    /// Serialise to the text sidecar format.
    pub fn to_text(&self) -> String {
        let mut s = String::with_capacity(64 * (self.hot.len() + self.dust.len()) + 1024);
        let _ = writeln!(s, "{MAGIC} {VERSION}");
        let _ = writeln!(s, "camera {}", self.camera);
        let _ = writeln!(s, "sensor {} {}", self.sensor_w, self.sensor_h);
        let _ = writeln!(s, "covered {} {}", self.covered_w, self.covered_h);
        let _ = writeln!(s, "coords {}", self.coords);
        match self.aperture_f {
            Some(f) => {
                let _ = writeln!(s, "aperture {f}");
            }
            None => {
                let _ = writeln!(s, "aperture unknown");
            }
        }
        for line in &self.provenance {
            let _ = writeln!(s, "# {line}");
        }
        let _ = writeln!(s, "hot {}", self.hot.len());
        for h in &self.hot {
            let _ = writeln!(s, "h {} {} {}", h.x, h.y, h.excess_e);
        }
        let _ = writeln!(s, "dust {}", self.dust.len());
        for d in &self.dust {
            let _ = writeln!(s, "d {} {} {}", d.px, d.py, d.gain);
        }
        let _ = writeln!(s, "end");
        s
    }

    /// Parse the text sidecar format.
    pub fn from_text(text: &str) -> Result<DefectMap, DefectMapError> {
        let mut camera: Option<String> = None;
        let mut sensor: Option<(usize, usize)> = None;
        let mut covered: Option<(usize, usize)> = None;
        let mut coords: Option<CoordSpace> = None;
        let mut aperture: Option<Option<f32>> = None;
        let mut declared_hot: Option<usize> = None;
        let mut declared_dust: Option<usize> = None;
        let mut provenance = Vec::new();
        let mut hot = Vec::new();
        let mut dust = Vec::new();
        let mut saw_end = false;
        let mut saw_magic = false;

        for (i, raw) in text.lines().enumerate() {
            let line = i + 1;
            let t = raw.trim_end();
            if t.is_empty() {
                continue;
            }
            if let Some(rest) = t.strip_prefix("# ") {
                provenance.push(rest.to_string());
                continue;
            }
            if t == "#" {
                provenance.push(String::new());
                continue;
            }
            let mut it = t.split_whitespace();
            let head = it.next().unwrap_or_default();
            if !saw_magic {
                if head != MAGIC {
                    return Err(DefectMapError::BadMagic {
                        found: head.to_string(),
                    });
                }
                let v: u32 = it
                    .next()
                    .unwrap_or_default()
                    .parse()
                    .map_err(|_| DefectMapError::BadValue {
                        key: "version".into(),
                        value: t.to_string(),
                    })?;
                if v != VERSION {
                    return Err(DefectMapError::BadVersion { found: v });
                }
                saw_magic = true;
                continue;
            }
            match head {
                "camera" => camera = Some(it.collect::<Vec<_>>().join(" ")),
                "sensor" | "covered" => {
                    let w = parse_usize(it.next(), head, t)?;
                    let h = parse_usize(it.next(), head, t)?;
                    if head == "sensor" {
                        sensor = Some((w, h));
                    } else {
                        covered = Some((w, h));
                    }
                }
                "coords" => {
                    coords = Some(CoordSpace::parse(it.next().unwrap_or_default())?);
                }
                "aperture" => {
                    let v = it.next().unwrap_or_default();
                    aperture = Some(if v == "unknown" {
                        None
                    } else {
                        Some(v.parse().map_err(|_| DefectMapError::BadValue {
                            key: "aperture".into(),
                            value: v.to_string(),
                        })?)
                    });
                }
                "hot" => declared_hot = Some(parse_usize(it.next(), "hot", t)?),
                "dust" => declared_dust = Some(parse_usize(it.next(), "dust", t)?),
                "h" => {
                    let x = parse_u32(it.next(), "h.x", t)?;
                    let y = parse_u32(it.next(), "h.y", t)?;
                    let e = parse_f32(it.next(), "h.excess_e", t)?;
                    if !e.is_finite() {
                        return Err(DefectMapError::BadValue {
                            key: "h.excess_e".into(),
                            value: t.to_string(),
                        });
                    }
                    hot.push(HotSite { x, y, excess_e: e });
                }
                "d" => {
                    let px = parse_u32(it.next(), "d.px", t)?;
                    let py = parse_u32(it.next(), "d.py", t)?;
                    let g = parse_f32(it.next(), "d.gain", t)?;
                    if !g.is_finite() || !(1.0..=MAX_DUST_GAIN).contains(&g) {
                        return Err(DefectMapError::ImplausibleGain {
                            x: px,
                            y: py,
                            gain: g,
                            max: MAX_DUST_GAIN,
                        });
                    }
                    dust.push(DustQuad { px, py, gain: g });
                }
                "end" => {
                    saw_end = true;
                }
                other => {
                    return Err(DefectMapError::BadLine {
                        line,
                        detail: format!("unknown record {other:?}"),
                    });
                }
            }
        }

        if !saw_magic {
            return Err(DefectMapError::BadMagic {
                found: String::new(),
            });
        }
        let (sensor_w, sensor_h) = sensor.ok_or(DefectMapError::MissingKey { key: "sensor" })?;
        let (covered_w, covered_h) = covered.unwrap_or((sensor_w, sensor_h));
        // REQUIRED, and deliberately not defaulted. Every map this project has
        // ever written is `active`, so defaulting to it would be right almost
        // always and silently wrong for the one file that mattered. See
        // `CoordSpace` for the +54.8% reading that a guessed origin produced.
        let coords = coords.ok_or(DefectMapError::MissingKey { key: "coords" })?;
        let declared_hot = declared_hot.ok_or(DefectMapError::MissingKey { key: "hot" })?;
        let declared_dust = declared_dust.ok_or(DefectMapError::MissingKey { key: "dust" })?;
        if !saw_end || declared_hot != hot.len() || declared_dust != dust.len() {
            return Err(DefectMapError::Truncated {
                declared_hot,
                declared_dust,
                found_hot: hot.len(),
                found_dust: dust.len(),
                saw_end,
            });
        }

        let mut seen = BTreeSet::new();
        for h in &hot {
            if h.x as usize >= covered_w || h.y as usize >= covered_h {
                return Err(DefectMapError::SiteOutOfRange {
                    kind: "hot",
                    x: h.x,
                    y: h.y,
                    w: covered_w,
                    h: covered_h,
                });
            }
            if !seen.insert((h.y, h.x)) {
                return Err(DefectMapError::DuplicateSite {
                    kind: "hot",
                    x: h.x,
                    y: h.y,
                });
            }
        }
        let mut seen = BTreeSet::new();
        for d in &dust {
            if 2 * d.px as usize + 1 >= covered_w || 2 * d.py as usize + 1 >= covered_h {
                return Err(DefectMapError::SiteOutOfRange {
                    kind: "dust",
                    x: d.px,
                    y: d.py,
                    w: covered_w / 2,
                    h: covered_h / 2,
                });
            }
            if !seen.insert((d.py, d.px)) {
                return Err(DefectMapError::DuplicateSite {
                    kind: "dust",
                    x: d.px,
                    y: d.py,
                });
            }
        }

        hot.sort_by_key(|h| (h.y, h.x));
        dust.sort_by_key(|d| (d.py, d.px));
        Ok(DefectMap {
            sensor_w,
            sensor_h,
            covered_w,
            covered_h,
            coords,
            camera: camera.unwrap_or_default(),
            aperture_f: aperture.flatten(),
            hot,
            dust,
            provenance,
        })
    }

    /// Read a sidecar from disk.
    pub fn load(path: &Path) -> Result<DefectMap, DefectMapError> {
        let text = std::fs::read_to_string(path).map_err(|source| DefectMapError::Io {
            path: path.to_path_buf(),
            source,
        })?;
        DefectMap::from_text(&text)
    }

    /// Write a sidecar to disk.
    pub fn save(&self, path: &Path) -> Result<(), DefectMapError> {
        std::fs::write(path, self.to_text()).map_err(|source| DefectMapError::Io {
            path: path.to_path_buf(),
            source,
        })
    }

    /// Check that this map's coordinates address the same photosites as a frame
    /// whose active area is `aw x ah`.
    ///
    /// # This was an exact-equality check, and exact equality was WRONG
    ///
    /// P39 (MEASURED). A census of the 26-stack corpus with the shipping
    /// decoder (`crates/strehl-cli/examples/defect-geometry-census.rs`) found
    /// **two** active-area widths on one body, both anchored at `(0, 0)` and
    /// both 4688 rows tall:
    ///
    /// ```text
    /// 7032x4688 at (0,0)   15 stacks   MATCHES the map
    /// 7040x4688 at (0,0)   11 stacks   refused by exact equality
    /// ```
    ///
    /// An exact-equality guard therefore **hard-failed 11 of 26 renders**,
    /// including `highly-angled-ruler-mm-cpl`, which carries the deepest mote
    /// reading in the corpus at -13.28%. That is not a safe default; it is a
    /// broken one. It was found by running the shipping binary on real stacks,
    /// not by reading the code.
    ///
    /// # Why the two widths are the same lattice, measured rather than assumed
    ///
    /// Both origins are `(0, 0)`, so the two active areas share every column
    /// they both declare and the wider one simply extends 8 columns further
    /// right. The claim that matters is that a map coordinate names the same
    /// photosite in both, and that was **measured, in both buckets, at the same
    /// coordinates**:
    ///
    /// | stack | bucket | site `(3434, 2305)` | p |
    /// |---|---|---|---|
    /// | `coffee-bean` | 7032 | -14.860% | 0.0025 |
    /// | `bee-3-cpl` | 7032 | -9.117% | 0.0025 |
    /// | `leaf-2-cpl` | **7040** | -8.157% | 0.0025 |
    /// | `lavendar-cpl` | **7040** | -8.387% | 0.0025 |
    /// | `couch-fibers-cpl` | **7040** | -8.467% | 0.0025 |
    /// | `highly-angled-ruler-mm-cpl` | **7040** | -8.585% | 0.0025 |
    ///
    /// The same mote reads at the same coordinate on both geometries. The
    /// lattices are co-registered at the origin.
    ///
    /// # What the guard is actually for, and where the bar comes from
    ///
    /// The failure it must catch is a **readout mode change** -- APS-C crop, or
    /// a different body -- because a crop moves where `(0, 0)` sits on the
    /// sensor and every coordinate then names a different photosite. That is a
    /// *large* change: the A7C II's APS-C crop is about **34%** narrower than
    /// its full-frame readout.
    ///
    /// So the bar is [`DefectMap::MAX_ACTIVE_MISMATCH_FRAC`], and its margin is
    /// stated rather than assumed: the difference it must **admit** is 0.11%
    /// (8 of 7032) and the difference it must **reject** is 34%. The bar sits
    /// 9x above the former and 30x below the latter. There is no readout mode
    /// of this body in between.
    ///
    /// # It is not the only thing between a stale map and a wrong correction
    ///
    /// This guard is declarative -- it compares two numbers in a header.
    /// [`SiteValidator`] is empirical: it requires the darkening to be
    /// **observed at the map's coordinates in the frames in front of it**
    /// before anything is corrected. A map that survived this check but was in
    /// fact mis-registered would find nothing at its sites and correct nothing.
    /// The two are independent, and the empirical one is the stronger.
    pub fn check_geometry(&self, aw: usize, ah: usize) -> Result<(), DefectMapError> {
        let frac = |want: usize, got: usize| -> f64 {
            if want == 0 {
                return f64::INFINITY;
            }
            (want as f64 - got as f64).abs() / want as f64
        };
        let worst = frac(self.sensor_w, aw).max(frac(self.sensor_h, ah));
        if worst > Self::MAX_ACTIVE_MISMATCH_FRAC {
            return Err(DefectMapError::SensorMismatch {
                want_w: self.sensor_w,
                want_h: self.sensor_h,
                got_w: aw,
                got_h: ah,
                frac: worst * 100.0,
                bar: Self::MAX_ACTIVE_MISMATCH_FRAC * 100.0,
            });
        }
        Ok(())
    }

    /// Apply the correction to one frame's samples, **in sensor coordinates**.
    ///
    /// `samples` is the decoder's whole buffer, `stride` its row pitch, and
    /// `(ax, ay, aw, ah)` the active-area rectangle inside it. `black` and
    /// `white` are the frame's own levels — they are firmware dependent and
    /// must never be assumed. `gain_dn_per_e` converts the hot arm's stored
    /// electrons to this frame's DN.
    ///
    /// # What it refuses to do
    ///
    /// - **A clipped sample is left alone, in both arms.** Its true value is
    ///   above the white level and unknown; subtracting a dark offset from it
    ///   or scaling it up invents a number, and the invented number then flows
    ///   into `highlight.rs`'s recovery as though it had been measured.
    /// - **Nothing is written below the black level or above the white level.**
    ///   The dust arm's gain is `>= 1`, so its only clamp is at white, and a
    ///   quad that would be pushed through white is counted as `dust_clipped`
    ///   rather than silently clamped, because a clamped dust quad is a flat
    ///   patch where there was a gradient.
    /// - **A geometry mismatch is an error.** See
    ///   [`DefectMap::check_geometry`] and
    ///   [`DefectMapError::SensorMismatch`].
    /// - **The map's [`CoordSpace`] chooses the origin.** An `active` map is
    ///   offset by `(ax, ay)`; a `full` map is not. This is the only place the
    ///   key is consumed, and it is consumed rather than merely carried
    ///   because a coordinate space that is recorded and ignored is worth
    ///   exactly as much as one that was never recorded.
    #[allow(clippy::too_many_arguments)]
    pub fn apply(
        &self,
        samples: &mut [u16],
        stride: usize,
        active: (usize, usize, usize, usize),
        black: f32,
        white: f32,
        gain_dn_per_e: f32,
        cfg: Correction,
        floor: HotFloor,
    ) -> Result<CorrectionReport, DefectMapError> {
        let (ax, ay, aw, ah) = active;
        self.check_geometry(aw, ah)?;
        // The whole content of the `coords` key: where does (0, 0) live.
        let (ox, oy) = match self.coords {
            CoordSpace::Active => (ax, ay),
            CoordSpace::Full => (0, 0),
        };
        let mut r = CorrectionReport::default();

        if cfg.hot {
            r.hot_examined = self.hot.len();
            for h in &self.hot {
                let (x, y) = (h.x as usize, h.y as usize);
                if x >= aw || y >= ah {
                    r.hot_outside += 1;
                    continue;
                }
                if h.excess_e < floor.0 {
                    r.hot_below_floor += 1;
                    continue;
                }
                let idx = (oy + y) * stride + ox + x;
                let v = samples[idx];
                if f32::from(v) >= white {
                    r.hot_clipped += 1;
                    continue;
                }
                let corrected = (f32::from(v) - h.excess_e * gain_dn_per_e).max(black);
                let out = corrected.round() as u16;
                if out == v {
                    r.hot_no_change += 1;
                } else {
                    samples[idx] = out;
                    r.hot_corrected += 1;
                    r.samples_changed += 1;
                }
            }
        }

        if cfg.dust {
            r.dust_examined = self.dust.len();
            for d in &self.dust {
                let (px, py) = (2 * d.px as usize, 2 * d.py as usize);
                if px + 1 >= aw || py + 1 >= ah {
                    r.dust_outside += 1;
                    continue;
                }
                let mut moved = 0usize;
                let mut clipped = 0usize;
                for dy in 0..2 {
                    for dx in 0..2 {
                        let idx = (oy + py + dy) * stride + ox + px + dx;
                        let v = samples[idx];
                        if f32::from(v) >= white {
                            clipped += 1;
                            continue;
                        }
                        // Dust attenuates the LIGHT, so the restoration is on
                        // the black-subtracted signal. Scaling the raw DN
                        // would scale the black pedestal too and lift the
                        // shadows by `black * (gain - 1)` -- 10 DN of lift at
                        // black 512 and gain 1.02, on every dust quad, which
                        // is 6x the entire hot-pixel effect this module also
                        // corrects.
                        let signal = (f32::from(v) - black).max(0.0);
                        let restored = signal * d.gain + black;
                        if restored >= white {
                            clipped += 1;
                            continue;
                        }
                        let out = restored.round() as u16;
                        if out != v {
                            samples[idx] = out;
                            moved += 1;
                        }
                    }
                }
                if clipped == 4 {
                    r.dust_clipped += 1;
                } else if moved == 0 {
                    r.dust_no_change += 1;
                } else {
                    r.dust_corrected += 1;
                    r.samples_changed += moved;
                }
            }
        }

        Ok(r)
    }
}

fn parse_usize(v: Option<&str>, key: &str, line: &str) -> Result<usize, DefectMapError> {
    v.unwrap_or_default()
        .parse()
        .map_err(|_| DefectMapError::BadValue {
            key: key.to_string(),
            value: line.to_string(),
        })
}

fn parse_u32(v: Option<&str>, key: &str, line: &str) -> Result<u32, DefectMapError> {
    v.unwrap_or_default()
        .parse()
        .map_err(|_| DefectMapError::BadValue {
            key: key.to_string(),
            value: line.to_string(),
        })
}

fn parse_f32(v: Option<&str>, key: &str, line: &str) -> Result<f32, DefectMapError> {
    v.unwrap_or_default()
        .parse()
        .map_err(|_| DefectMapError::BadValue {
            key: key.to_string(),
            value: line.to_string(),
        })
}

// ---------------------------------------------------------------------------
// Detectors
// ---------------------------------------------------------------------------

/// How the hot detector decides.
///
/// Every field is a threshold and every threshold is inherited from a published
/// census rather than chosen here, so that this detector's output is comparable
/// with M22's 11,393, M48c's 13,650 and M101's 14,604 rather than merely
/// similar to them. It lands at **14,626**.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct HotParams {
    /// Flag when the neighbour excess exceeds this many robust sigma.
    pub k_sigma: f32,
    /// A site must be flagged in at least this many independent groups.
    ///
    /// **Recurrence, not the sigma cut, is the discriminator.** M22 §2 measured
    /// that single-group flags are *fewer* than a Binomial independence
    /// baseline predicts — they are the threshold's own false positives — while
    /// from 3 groups upward the excess over chance is astronomical. That
    /// removed the threshold as a tuning knob, and it is why this struct's
    /// `k_sigma` can be inherited rather than swept.
    pub recurrence: usize,
    /// Sites below this amplitude are not emitted at all.
    pub min_excess_e: f32,
}

impl Default for HotParams {
    fn default() -> Self {
        HotParams {
            k_sigma: 6.0,
            recurrence: 6,
            min_excess_e: 0.0,
        }
    }
}

/// What the hot detector examined, partitioned.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct HotCensus {
    /// Photosites in the active area.
    pub examined: usize,
    /// Flagged in at least one group.
    pub flagged_once: usize,
    /// Flagged in at least `recurrence` groups.
    pub recurrent: usize,
    /// Recurrent and above `min_excess_e` — i.e. emitted.
    pub emitted: usize,
    /// Recurrent but below `min_excess_e`.
    pub below_amplitude: usize,
    /// In the one-sample border, where the 8-neighbour median is not defined
    /// without padding. Reported rather than padded: a padded border produces
    /// detections whose neighbourhood is partly its own reflection.
    pub border: usize,
}

/// Build a hot-pixel map from per-group temporal means of dark frames.
///
/// `groups[g]` is one ISO group's black-subtracted temporal mean over the whole
/// active area, `w * h` samples in row-major order, paired with that group's
/// `gain_dn_per_e`. The statistic is each sample's excess over the **median of
/// its eight same-plane neighbours** — `+/-2` in each axis, so the
/// neighbourhood never crosses a CFA plane — normalised by a robust sigma
/// (`1.4826 * MAD`) computed per group over the whole excess field.
///
/// # Why this returns nothing on a clean sensor
///
/// The bar is a conjunction of two independent requirements and each one alone
/// is satisfiable by noise. A 6-sigma cut on 33 M photosites flags ~ 33 by
/// chance per group; requiring the *same* photosite in >= 6 of 11 independently
/// captured groups drives the chance expectation to
/// `C(11,6) * p^6 * (1-p)^5 * N`, which at the measured per-group rate is
/// **2.09e-8** (M22 §2's table). `a_clean_sensor_yields_no_hot_sites` plants a
/// pure-noise input and requires zero.
pub fn detect_hot(
    groups: &[(&[f32], f32)],
    w: usize,
    h: usize,
    params: HotParams,
) -> (Vec<HotSite>, HotCensus) {
    let mut census = HotCensus {
        examined: w * h,
        ..Default::default()
    };
    if groups.is_empty() || w < 5 || h < 5 {
        return (Vec::new(), census);
    }
    census.border = w * h - (w - 4) * (h - 4);

    let n = w * h;
    let mut count = vec![0u16; n];
    let mut amps: Vec<Vec<f32>> = vec![Vec::with_capacity(groups.len()); n];

    for (mean, gain) in groups {
        assert_eq!(mean.len(), n, "group mean is not w*h samples");
        let mut excess = vec![0f32; n];
        for y in 2..h - 2 {
            for x in 2..w - 2 {
                excess[y * w + x] = neighbour_excess(mean, w, x, y);
            }
        }
        let interior: Vec<f32> = (2..h - 2)
            .flat_map(|y| (2..w - 2).map(move |x| (x, y)))
            .map(|(x, y)| excess[y * w + x])
            .collect();
        let sigma = robust_sigma(&interior);
        let cut = params.k_sigma * sigma;
        for y in 2..h - 2 {
            for x in 2..w - 2 {
                let i = y * w + x;
                if excess[i] > cut {
                    count[i] += 1;
                }
                amps[i].push(excess[i] / gain);
            }
        }
    }

    let mut sites = Vec::new();
    for y in 2..h - 2 {
        for x in 2..w - 2 {
            let i = y * w + x;
            if count[i] >= 1 {
                census.flagged_once += 1;
            }
            if (count[i] as usize) < params.recurrence {
                continue;
            }
            census.recurrent += 1;
            let e = median(&mut amps[i].clone());
            if e < params.min_excess_e {
                census.below_amplitude += 1;
                continue;
            }
            sites.push(HotSite {
                x: x as u32,
                y: y as u32,
                excess_e: e,
            });
        }
    }
    census.emitted = sites.len();
    (sites, census)
}

/// A sample's excess over the median of its eight **same-plane** neighbours.
///
/// The neighbours are at `+/-2` in each axis, never `+/-1`: a CFA plane's
/// samples sit on a 2x2 lattice, and a `+/-1` neighbourhood would compare a red
/// photosite against greens. `x` and `y` must be at least 2 from every edge.
pub fn neighbour_excess(a: &[f32], w: usize, x: usize, y: usize) -> f32 {
    let mut nb = [0f32; 8];
    let mut k = 0;
    for dy in [-2isize, 0, 2] {
        for dx in [-2isize, 0, 2] {
            if dy == 0 && dx == 0 {
                continue;
            }
            let yy = (y as isize + dy) as usize;
            let xx = (x as isize + dx) as usize;
            nb[k] = a[yy * w + xx];
            k += 1;
        }
    }
    a[y * w + x] - median(&mut nb)
}

fn median(v: &mut [f32]) -> f32 {
    if v.is_empty() {
        return 0.0;
    }
    v.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    let n = v.len();
    if n % 2 == 1 {
        v[n / 2]
    } else {
        0.5 * (v[n / 2 - 1] + v[n / 2])
    }
}

fn robust_sigma(v: &[f32]) -> f32 {
    let mut a = v.to_vec();
    let m = median(&mut a);
    let mut d: Vec<f32> = v.iter().map(|x| (x - m).abs()).collect();
    1.4826 * median(&mut d)
}

/// How the dust detector decides.
///
/// # Why each threshold is a conjunction and not a percentile
///
/// A percentile cut always returns something — it is a search that cannot fail,
/// and its least-bad candidate reads exactly like a find. Every bar here is
/// absolute, and `a_clean_flat_field_yields_no_dust` plants a clean input and
/// requires **zero** components out.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct DustParams {
    /// Half-width of the high-pass. The residual is `m / smooth(m) - 1` with
    /// `smooth` three passes of a `2*hp_radius+1` box.
    ///
    /// **This is the illumination/dust separator and its scale is the whole
    /// argument.** The flats were shot through a window under moving cloud;
    /// M71 measured the illumination as a **2.35x swing** rising at
    /// +1.6-2.0 %/s, not a gentle drift. A cloud edge is a gradient across the
    /// whole frame; a mote is tens of quads. At the shipped 30 (a 61-wide box,
    /// three passes, sigma ~15.2 quads) the high-pass removes **264.9x** of the
    /// between-capture spatial disagreement — MEASURED, 3.6194% of 64x64 block
    /// level before, 0.0137% after
    /// (`experiments/BUILD-DEFECT/data/01-dust.json`).
    pub hp_radius: usize,
    /// Half-width of the band-pass applied to the median residual before
    /// thresholding.
    ///
    /// **This is the dust/photosite separator.** Averaging a `2*bp_radius+1`
    /// square divides an isolated bad photosite's amplitude by `(2r+1)^2` while
    /// leaving a 30-quad disc essentially untouched. Without it the site set is
    /// a mixture: MEASURED on this body, thresholding the *unsmoothed* residual
    /// returns 1,314 connected components of which **885 are single quads** and
    /// only 14 are 21 quads or more. Those singletons are real — they are
    /// low-sensitivity photosites — but they are not dust, and a dust map that
    /// silently contains them is a dust map whose count means nothing.
    pub bp_radius: usize,
    /// A capture "sees" a quad when its residual is at or below `-seed_depth`.
    ///
    /// **Above the noisiest capture's residual rms, and stated that way rather
    /// than tuned.** MEASURED: the 18 delivered captures have per-capture
    /// residual rms between 0.0979% and 0.4882%, so a 0.5% seed is at or above
    /// 1x the worst capture's noise and above 5x the best one's. The first
    /// build of this map used 1.0%, which is *deeper than two of the four
    /// motes on this body* and silently missed them.
    pub seed_depth: f32,
    /// A quad is dust only if at least this many independent captures see it.
    ///
    /// **This is the confound-killer.** The 18 delivered flat captures are 9
    /// shutter speeds x 2 CPL states spread over ~40 minutes with a ~4.7 minute
    /// intermission inside every group, under moving cloud that M71 measured as
    /// a **2.35x swing**. No cloud is in the same place in 15 of 18 captures;
    /// dust is. MEASURED: rolling all 18 captures independently, so that no two
    /// correspond, returns **0 components at every one of 24 settings** of a
    /// `seed x recurrence x floor` sweep, against 4 components and 618 quads on
    /// the real arm.
    ///
    /// Rolling only *some* of the captures is not a control at all: the site
    /// test is a median over 18, so nine still-corresponding captures set it.
    /// A half-rolled control on this data read 9,966 false sites — 1.41x the
    /// real count, which looks like a *failed* control — and the same data with
    /// all 18 rolled reads 0, 0, 0.
    pub recurrence: usize,
    /// Absolute floor on the median band-passed depth. Not a percentile.
    pub floor_depth: f32,
    /// Quads within this distance of the edge are **not examined**.
    ///
    /// The high-pass replicates the edge, so near the border the smooth
    /// surface is fitted partly to a reflection of the data rather than to the
    /// data. The contaminated width is **not** `hp_radius`: three passes of a
    /// half-width-30 box have a support half-width of 90.
    ///
    /// MEASURED rather than derived, by taking the median of the median
    /// residual over whole rings at a fixed distance from the nearest edge —
    /// real dust is sparse and cannot move a ring median, so the ring profile
    /// reads the artefact alone. Ring median at distance 0 / 10 / 20 / 30 /
    /// 40 / 90 / 500 quads: **−0.9340% / −0.5194% / −0.2307% / −0.0975% /
    /// −0.0030% / +0.0236% / +0.0238%**. The artefact is gone by 40 and the
    /// interior sits at +0.02%, so the shipped 60 is 1.5x the measured reach.
    ///
    /// **This is not hypothetical.** Without the exclusion the two largest
    /// "motes" on this body sit at quad columns **20** and **3498** of 3514,
    /// are 35,794 and 35,268 quads in area, and are shallow shelves rather
    /// than discs. Worse: M71's committed dust mask
    /// (`experiments/M71-flat-fields/out/cache/dust-mask.npy`, 2,898 quads,
    /// published with "enrichment 2278x, roll control PASS") is **99.93%
    /// within 40 quads of an edge and 100% within 90**, against an area-share
    /// null of 5.61% and 12.41% — **17.8x enriched toward the border**, median
    /// distance-from-edge **2 quads**. A roll control cannot catch that,
    /// because rolling moves the shelf off the border that made it. See
    /// `docs/research/BUILD-DEFECT.md`.
    pub border: usize,
    /// A connected component smaller than this is not dust.
    ///
    /// DERIVED from the optics, before the data was looked at. A mote sitting
    /// `t` above the photosites throws a shadow of diameter `t / N` at
    /// f-number `N`; at the A7C II's ~2 mm stack and the flats' f/5.6 that is
    /// ~0.36 mm = 89 sensor px = **44 quads across**, i.e. of order 1,500
    /// quads in area. The shipped 25 is a floor **sixty times below** the
    /// predicted object, chosen to be unable to reject a real mote rather than
    /// to be near one.
    pub min_component: usize,
    /// The fraction of a defect's true depth that survives the high-pass.
    ///
    /// **This is a calibration, not a fudge, and it must be measured per map
    /// rather than assumed.** The high-pass divides by `smooth(m)`, and a dust
    /// disc large enough to matter also enters its own smoothed denominator, so
    /// the residual under-reads the true attenuation. The size of the
    /// under-read depends on the ratio of the mote's area to the smoothing
    /// kernel's, which is a property of *this* radius and *this* body's motes.
    ///
    /// `1.0` means "assume the operator is lossless", which is the safe default
    /// because it can only ever **under**-correct. The shipped map replaces it
    /// with a value measured by planting synthetic discs of known depth into
    /// the real cached flats and pushing them through the identical operator —
    /// see `experiments/BUILD-DEFECT/src/04-build-map.py`. M29 §5 warns
    /// specifically against adopting an uncalibrated empirical constant here;
    /// that is how M29 itself went wrong.
    pub attenuation: f32,
}

impl Default for DustParams {
    fn default() -> Self {
        DustParams {
            hp_radius: 30,
            bp_radius: 2,
            seed_depth: 0.005,
            recurrence: 15,
            floor_depth: 0.005,
            border: 60,
            min_component: 25,
            attenuation: 1.0,
        }
    }
}

/// What the dust detector examined, partitioned.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct DustCensus {
    /// Quads in the covered area.
    pub examined: usize,
    /// Excluded because they sit inside `border`.
    pub border: usize,
    /// Passed the recurrence bar.
    pub recurrent: usize,
    /// Passed recurrence and the depth floor.
    pub deep: usize,
    /// Connected components found among those.
    pub components: usize,
    /// Components rejected for being smaller than `min_component`.
    pub components_too_small: usize,
    /// Quads emitted.
    pub emitted: usize,
}

/// Build a dust map from per-capture normalised flat-field means.
///
/// `captures[c]` is one flat capture's per-quad temporal mean, already divided
/// by its own spatial mean so that whole-frame illumination level is gone,
/// `w * h` quads in row-major order.
///
/// The pipeline is: high-pass each capture at `hp_radius` (kills illumination
/// *structure*); take the per-quad **median** across captures (kills a capture
/// that saw a bird, a hand, or a cloud edge); band-pass at `bp_radius` (kills
/// isolated bad photosites); then require **both** an absolute depth and
/// recurrence across captures; then require a connected component of the size
/// the optics predict.
pub fn detect_dust(
    captures: &[&[f32]],
    w: usize,
    h: usize,
    params: DustParams,
) -> (Vec<DustQuad>, DustCensus) {
    let n = w * h;
    let mut census = DustCensus {
        examined: n,
        ..Default::default()
    };
    if captures.is_empty() {
        return (Vec::new(), census);
    }
    let b = params.border;
    if w <= 2 * b || h <= 2 * b {
        census.border = n;
        return (Vec::new(), census);
    }
    census.border = n - (w - 2 * b) * (h - 2 * b);

    // 1. high-pass each capture, and count how many see each quad
    let mut seen = vec![0u16; n];
    let mut stack: Vec<Vec<f32>> = Vec::with_capacity(captures.len());
    for c in captures {
        assert_eq!(c.len(), n, "capture is not w*h quads");
        let sm = box_smooth(c, w, h, params.hp_radius, 3);
        let mut r = vec![0f32; n];
        for i in 0..n {
            r[i] = if sm[i].abs() > f32::EPSILON {
                c[i] / sm[i] - 1.0
            } else {
                0.0
            };
        }
        for i in 0..n {
            if r[i] <= -params.seed_depth {
                seen[i] += 1;
            }
        }
        stack.push(r);
    }

    // 2. per-quad median across captures, then band-pass
    let mut med = vec![0f32; n];
    let mut buf = vec![0f32; captures.len()];
    for i in 0..n {
        for (k, s) in stack.iter().enumerate() {
            buf[k] = s[i];
        }
        med[i] = median(&mut buf);
    }
    let band = box_smooth(&med, w, h, params.bp_radius, 1);

    // 3. the two absolute bars, inside the border
    let mut hit = vec![false; n];
    for y in b..h - b {
        for x in b..w - b {
            let i = y * w + x;
            let rec = (seen[i] as usize) >= params.recurrence;
            if rec {
                census.recurrent += 1;
            }
            if rec && band[i] <= -params.floor_depth {
                census.deep += 1;
                hit[i] = true;
            }
        }
    }

    // 4. connected components, and the size floor the optics predict
    let mut label = vec![0u32; n];
    let mut next = 0u32;
    let mut stackq: Vec<usize> = Vec::new();
    let mut sizes: Vec<usize> = vec![0];
    for i in 0..n {
        if !hit[i] || label[i] != 0 {
            continue;
        }
        next += 1;
        sizes.push(0);
        stackq.push(i);
        label[i] = next;
        while let Some(j) = stackq.pop() {
            sizes[next as usize] += 1;
            let (x, y) = (j % w, j / w);
            for (dx, dy) in [(-1i32, 0i32), (1, 0), (0, -1), (0, 1)] {
                let nx = x as i32 + dx;
                let ny = y as i32 + dy;
                if nx < 0 || ny < 0 || nx >= w as i32 || ny >= h as i32 {
                    continue;
                }
                let k = ny as usize * w + nx as usize;
                if hit[k] && label[k] == 0 {
                    label[k] = next;
                    stackq.push(k);
                }
            }
        }
    }
    census.components = next as usize;

    let mut out = Vec::new();
    for l in 1..=next {
        if sizes[l as usize] < params.min_component {
            census.components_too_small += 1;
        }
    }
    for y in b..h - b {
        for x in b..w - b {
            let i = y * w + x;
            let l = label[i];
            if l == 0 || sizes[l as usize] < params.min_component {
                continue;
            }
            // The gain restores the measured attenuation. `med` rather than
            // `band` is used here on purpose: `band` selected the object, and a
            // band-passed value would under-correct the centre of a mote by
            // the amount the smoothing pulled it toward the rim. Selecting
            // with one statistic and correcting with another is deliberate and
            // is the only place in this module where they differ.
            let g = 1.0 / (1.0 + med[i] / params.attenuation.max(1e-3));
            if !g.is_finite() || !(1.0..=MAX_DUST_GAIN).contains(&g) {
                continue;
            }
            out.push(DustQuad {
                px: x as u32,
                py: y as u32,
                gain: g,
            });
        }
    }
    census.emitted = out.len();
    (out, census)
}

/// `npass` passes of a `2*radius+1`-wide separable box mean, edge-replicated.
pub fn box_smooth(a: &[f32], w: usize, h: usize, radius: usize, npass: usize) -> Vec<f32> {
    let mut cur = a.to_vec();
    if radius == 0 {
        return cur;
    }
    let win = 2 * radius + 1;
    let mut tmp = vec![0f32; w * h];
    for _ in 0..npass {
        // horizontal
        for y in 0..h {
            let row = &cur[y * w..y * w + w];
            for x in 0..w {
                let mut s = 0f64;
                for k in 0..win {
                    let xx = (x + k).saturating_sub(radius).min(w - 1);
                    s += f64::from(row[xx]);
                }
                tmp[y * w + x] = (s / win as f64) as f32;
            }
        }
        // vertical
        for x in 0..w {
            for y in 0..h {
                let mut s = 0f64;
                for k in 0..win {
                    let yy = (y + k).saturating_sub(radius).min(h - 1);
                    s += f64::from(tmp[yy * w + x]);
                }
                cur[y * w + x] = (s / win as f64) as f32;
            }
        }
    }
    cur
}

// ---------------------------------------------------------------------------
// The metric
// ---------------------------------------------------------------------------

/// What a defect metric read.
///
/// Both a **signed** and an **absolute** mean are reported, and the absolute
/// one is the acceptance number. That is not belt and braces; it is the whole
/// reason this metric can charge for an over-correction.
///
/// This project has shipped the other design and been burned by it: a sharpness
/// statistic *bounded below by zero* could never charge for a halo, and every
/// commissioning arm was a degradation, so nothing noticed. A defect metric
/// scored on `max(excess, 0)` — or on the signed mean alone — reads a
/// **perfectly over-corrected** frame as better than clean, because the
/// residual has changed sign rather than shrunk.
/// `the_metric_charges_for_over_correction_and_is_not_bounded_below` is the
/// planted control.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct DefectResidual {
    /// Mean signed residual at the sites. Negative means still-dark, positive
    /// means over-corrected.
    pub mean_signed: f64,
    /// Mean |residual|. **The acceptance number.**
    pub mean_abs: f64,
    /// Root-mean-square residual, which weights the deep sites the eye finds.
    pub rms: f64,
    /// Sites actually scored.
    pub n: usize,
    /// Sites in the set that could not be scored — outside the frame, or in the
    /// two-quad border where the local reference is undefined.
    pub n_unscored: usize,
}

impl DefectResidual {
    /// An empty reading. `n == 0` is distinguishable from a clean one.
    pub const EMPTY: DefectResidual = DefectResidual {
        mean_signed: 0.0,
        mean_abs: 0.0,
        rms: 0.0,
        n: 0,
        n_unscored: 0,
    };
}

/// Score the **multiplicative** residual at a set of quads.
///
/// For each quad, the green-luma level of the quad is compared against the
/// median of a ring of same-parity quads at `ref_radius`, and the reading is
/// the fractional difference. A clean frame reads ~0; a frame with an
/// uncorrected 2% shadow reads ~-0.02; a frame corrected with twice the right
/// gain reads ~+0.02 and is scored **just as badly** by `mean_abs`.
///
/// # The direction this can be fooled in
///
/// It is a **local relative** statistic, so it is blind to any attenuation
/// broader than `ref_radius` — a uniform 2% loss over the whole frame reads
/// zero. That is correct for dust and wrong for vignetting, and it is why this
/// metric must never be quoted as a flat-field figure of merit. It is also
/// scene-modulated: M29 §2 measured that a self-ratio static map responds to
/// `depth * (g / blur(g))` at the defect, so on a real subject a shadow sitting
/// on a locally dark region reads shallower than the same shadow on a locally
/// bright one, by up to **3.4x** across the range M29 measured. Use it to
/// compare two renders of the *same* scene, never two scenes.
pub fn dust_residual(
    samples: &[u16],
    stride: usize,
    active: (usize, usize, usize, usize),
    black: f32,
    quads: &[(u32, u32)],
    ref_radius: usize,
) -> DefectResidual {
    let (ax, ay, aw, ah) = active;
    let mut signed = 0f64;
    let mut abs = 0f64;
    let mut sq = 0f64;
    let mut n = 0usize;
    let mut unscored = 0usize;
    let r = ref_radius.max(1);
    for &(px, py) in quads {
        let (px, py) = (px as usize, py as usize);
        if 2 * px + 1 >= aw || 2 * py + 1 >= ah || px < r || py < r || px + r >= aw / 2 || py + r >= ah / 2
        {
            unscored += 1;
            continue;
        }
        let luma = |qx: usize, qy: usize| -> f64 {
            let i = (ay + 2 * qy) * stride + ax + 2 * qx;
            let g1 = f64::from(samples[i + 1]) - f64::from(black);
            let g2 = f64::from(samples[i + stride]) - f64::from(black);
            0.5 * (g1.max(0.0) + g2.max(0.0))
        };
        let here = luma(px, py);
        let mut ring = [0f64; 8];
        let mut k = 0;
        for (dx, dy) in [
            (-1i64, -1i64),
            (0, -1),
            (1, -1),
            (-1, 0),
            (1, 0),
            (-1, 1),
            (0, 1),
            (1, 1),
        ] {
            let qx = (px as i64 + dx * r as i64) as usize;
            let qy = (py as i64 + dy * r as i64) as usize;
            ring[k] = luma(qx, qy);
            k += 1;
        }
        ring.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
        let refv = 0.5 * (ring[3] + ring[4]);
        if refv <= 0.0 {
            unscored += 1;
            continue;
        }
        let d = here / refv - 1.0;
        signed += d;
        abs += d.abs();
        sq += d * d;
        n += 1;
    }
    if n == 0 {
        return DefectResidual {
            n_unscored: unscored,
            ..DefectResidual::EMPTY
        };
    }
    DefectResidual {
        mean_signed: signed / n as f64,
        mean_abs: abs / n as f64,
        rms: (sq / n as f64).sqrt(),
        n,
        n_unscored: unscored,
    }
}

/// Score the **additive** residual at a set of photosites, in DN.
///
/// Same shape as [`dust_residual`] and the same anti-perversity property: the
/// acceptance number is `mean_abs`, so subtracting too much is charged for at
/// the same rate as not subtracting at all.
pub fn hot_residual(
    samples: &[u16],
    stride: usize,
    active: (usize, usize, usize, usize),
    sites: &[(u32, u32)],
) -> DefectResidual {
    let (ax, ay, aw, ah) = active;
    let mut signed = 0f64;
    let mut abs = 0f64;
    let mut sq = 0f64;
    let mut n = 0usize;
    let mut unscored = 0usize;
    for &(x, y) in sites {
        let (x, y) = (x as usize, y as usize);
        if x < 2 || y < 2 || x + 2 >= aw || y + 2 >= ah {
            unscored += 1;
            continue;
        }
        let at = |xx: usize, yy: usize| f64::from(samples[(ay + yy) * stride + ax + xx]);
        let mut nb = [0f64; 8];
        let mut k = 0;
        for dy in [-2i64, 0, 2] {
            for dx in [-2i64, 0, 2] {
                if dx == 0 && dy == 0 {
                    continue;
                }
                nb[k] = at((x as i64 + dx) as usize, (y as i64 + dy) as usize);
                k += 1;
            }
        }
        nb.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
        let d = at(x, y) - 0.5 * (nb[3] + nb[4]);
        signed += d;
        abs += d.abs();
        sq += d * d;
        n += 1;
    }
    if n == 0 {
        return DefectResidual {
            n_unscored: unscored,
            ..DefectResidual::EMPTY
        };
    }
    DefectResidual {
        mean_signed: signed / n as f64,
        mean_abs: abs / n as f64,
        rms: (sq / n as f64).sqrt(),
        n,
        n_unscored: unscored,
    }
}

// ---------------------------------------------------------------------------
// Self-validation: does this stack's own data show the defect the map names?
// ---------------------------------------------------------------------------

/// One connected mote: the quads of a single dust particle's shadow.
///
/// The map stores 1,135 loose quads. A *particle* is a connected group of them,
/// and it is the particle, not the quad, that self-validation reasons about —
/// a quad is a 30th of a mote's diameter and has no independent existence.
#[derive(Debug, Clone, PartialEq)]
pub struct Mote {
    /// Indices into [`DefectMap::dust`].
    pub quads: Vec<usize>,
    /// Centroid, in quad coordinates, rounded.
    pub cx: u32,
    pub cy: u32,
    /// The deepest gain in the group.
    pub peak_gain: f32,
    /// Median fractional depth over the core disc, as the **map** states it:
    /// `median(1/gain - 1)` over quads within [`ValidateParams::core_radius`]
    /// of the centroid. Negative.
    ///
    /// This is the map's own claim about the mote, in the same units the
    /// frames are measured in, and it is the denominator of the amplitude
    /// rescale. It is derived from the gains rather than stored beside them so
    /// that it cannot disagree with the gains it describes.
    pub map_depth: f64,
}

/// Thresholds for the self-validation check.
///
/// Every constant here is inherited from the commissioned Python in
/// `experiments/BUILD-DEFECT/src/20-selfvalidate.py` and
/// `24-stationarity.py` rather than re-chosen, so the Rust's verdicts are
/// comparable with the measurements in `docs/research/BUILD-DEFECT.md` §11
/// rather than merely similar to them.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct ValidateParams {
    /// Radius of the low-pass that defines "local background". 64 quads is
    /// ~4x the largest mote radius, so a mote cannot flatten its own reference.
    pub hp_radius: usize,
    /// Passes of that low-pass. Two box passes approximate a Gaussian well
    /// enough that the residual has no box artefacts at the core.
    pub hp_pass: usize,
    /// Radius of the mild smoothing applied to the residual, to stop a single
    /// noisy quad from setting the core median.
    pub bp_radius: usize,
    /// Radius of the disc whose median is the reading.
    pub core_radius: usize,
    /// Inner and outer radius of the annulus the null is drawn from. Inner is
    /// outside any mote; outer is inside the region whose illumination and
    /// texture resemble the site's.
    pub annulus_in: usize,
    pub annulus_out: usize,
    /// Null sample size. `p` is quantised at `1/(n+1)`, so 400 gives a floor
    /// of 0.0025 and [`Self::p_bar`] sits exactly on it: the test can only
    /// pass when **no** null sample was as deep as the site.
    pub n_null: usize,
    /// Significance bar. See [`Self::n_null`].
    pub p_bar: f64,
    /// Depth bar, as a positive fraction. A site must read at least this dark.
    ///
    /// **Both bars, not either.** In one improvement arm the corrected site
    /// still had the lowest reading in its neighbourhood — `p` alone would have
    /// been perverse and re-fired on an already-corrected mote — and the depth
    /// floor is what stopped it.
    pub depth_floor: f64,
    /// Fraction of individual frames that must show the darkening.
    ///
    /// **MEASURED load-bearing** (`experiments/BUILD-DEFECT/out/25-drift-sweep.log`).
    /// A planted -8% disc *moving* with the bracket's own magnification drift
    /// still cleared `p` **and** `depth_floor` at scales 1.012–1.020 on
    /// `leaf-2-cpl` (30 quads of travel, depth -6.718%, p 0.0025) and 1.016–1.020
    /// on `lavendar-cpl`. Only this bar rejected it. Without it the correction
    /// would have brightened real moving subject detail.
    pub presence_bar: f64,
    /// Depth, as a positive fraction, at which a single frame counts as
    /// "showing" the darkening.
    pub frame_floor: f64,
    /// Half-width of the window cropped around each site.
    ///
    /// The statistic is local — nothing outside `annulus_out` plus the
    /// low-pass support can influence it — so it is computed on a crop.
    /// MEASURED: a 560-quad half-window agrees with the full frame to
    /// **0.0000 pp** and is **23.5x** cheaper
    /// (`experiments/BUILD-DEFECT/out/21-depth-aperture.log`).
    pub window: usize,
    /// Seed for the null's offset sampler.
    ///
    /// Fixed, because the byte-freeze registry pins two renders to the byte
    /// and a correction whose gate consulted an unseeded RNG would render
    /// differently on consecutive runs of identical input.
    pub seed: u64,
}

impl Default for ValidateParams {
    fn default() -> Self {
        ValidateParams {
            hp_radius: 64,
            hp_pass: 2,
            bp_radius: 3,
            core_radius: 8,
            annulus_in: 60,
            annulus_out: 400,
            n_null: 400,
            p_bar: 0.0025,
            depth_floor: 0.015,
            presence_bar: 0.75,
            frame_floor: 0.010,
            window: 560,
            seed: 0x5445_5354_4d4f_5445,
        }
    }
}

/// Why a site was or was not corrected. Exactly one applies.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SiteOutcome {
    /// All three bars cleared. The site is corrected, at the depth measured
    /// here rather than the depth the map remembers.
    Confirmed,
    /// The darkening is not significant against the local null. Either the
    /// sensor was cleaned, or the background is too busy for the site to be
    /// measurable — and the second case is also the case where the mote cannot
    /// be seen, so skipping is right in both.
    NotSignificant,
    /// Significant but shallower than [`ValidateParams::depth_floor`].
    TooShallow,
    /// Deep and significant in the pooled median but absent from too many
    /// individual frames: it moves, so it is subject detail and not dust.
    NotStationary,
    /// The site is too near the frame edge for the annulus to be sampled, so
    /// the null could not be formed. Refusing to guess.
    Unmeasurable,
}

impl SiteOutcome {
    /// Only [`SiteOutcome::Confirmed`] corrects.
    pub fn corrects(self) -> bool {
        matches!(self, SiteOutcome::Confirmed)
    }
}

/// What the check read at one nominated site.
#[derive(Debug, Clone, PartialEq)]
pub struct SiteVerdict {
    /// Quad centroid of the mote this verdict is about.
    pub cx: u32,
    pub cy: u32,
    /// Pooled (across-frame median) fractional depth at the core. Negative.
    pub depth: f64,
    /// What the map claimed the depth was. Negative.
    pub map_depth: f64,
    /// Fraction of the null that was at least as dark as the site.
    pub p: f64,
    /// Fraction of frames that individually showed the darkening.
    pub presence: f64,
    /// The decision.
    pub outcome: SiteOutcome,
    /// Exponent applied to every gain in the mote, `ln(1-|d_meas|) /
    /// ln(1-|d_map|)`. 1.0 means the frames agreed with the map exactly.
    pub scale: f64,
}

/// A counted partition of every nominated site. The buckets sum to `examined`.
///
/// Same discipline as [`CorrectionReport`], for the same reason: "0 sites
/// corrected" and "0 sites examined" are different failures, and on a
/// default-ON correction the difference is "your sensor is clean" versus "the
/// feature silently did nothing".
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct ValidationReport {
    pub examined: usize,
    pub confirmed: usize,
    pub not_significant: usize,
    pub too_shallow: usize,
    pub not_stationary: usize,
    pub unmeasurable: usize,
    /// Frames the verdicts were formed from.
    pub frames: usize,
}

impl ValidationReport {
    /// Every site landed in exactly one bucket.
    pub fn check_partition(&self) -> bool {
        self.confirmed
            + self.not_significant
            + self.too_shallow
            + self.not_stationary
            + self.unmeasurable
            == self.examined
    }

    /// One line for a run banner.
    pub fn describe(&self) -> String {
        format!(
            "{}/{} sites confirmed from {} frames (not significant {}, too shallow {}, \
             not stationary {}, unmeasurable {})",
            self.confirmed,
            self.examined,
            self.frames,
            self.not_significant,
            self.too_shallow,
            self.not_stationary,
            self.unmeasurable
        )
    }
}

/// A small deterministic PRNG for the null's offset sampler.
///
/// Deterministic because the byte-freeze registry pins renders to the byte, and
/// a gate that consulted `thread_rng` would make two runs of identical input
/// disagree about whether to correct. `SplitMix64`, which is four lines and has
/// no dependency.
struct SplitMix64(u64);

impl SplitMix64 {
    fn next_u64(&mut self) -> u64 {
        self.0 = self.0.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = self.0;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ (z >> 31)
    }

    /// Uniform in `[0, 1)`.
    fn next_f64(&mut self) -> f64 {
        (self.next_u64() >> 11) as f64 / (1u64 << 53) as f64
    }
}

/// Accumulates the evidence for a map's motes over a sample of frames.
///
/// # Where this reads, and why the warp cannot touch it
///
/// [`SiteValidator::observe`] takes a **quad-mean of the black-subtracted raw
/// active area** — the same lattice the map is written on and the same lattice
/// [`DefectMap::apply`] corrects on — and it is fed from the decoder directly,
/// **before any geometric transform**. So the question "does the check read
/// before or after the warp?" has a structural answer rather than a careful
/// one: there is no warp on this path at all. The aligner cannot move a site
/// out from under its own verdict because the aligner has not run.
///
/// # Cost
///
/// MEASURED at **0.016 s/frame/site** on a 560-quad window against 0.370 s for
/// the full frame (`experiments/BUILD-DEFECT/out/21-depth-aperture.log`). Two
/// sites over 8 frames is **0.26 s of compute** — one frame's share of a
/// 0.26 s/frame budget — plus the ~2.5 s to decode the 8 frames, which is the
/// dominant term and is why the sample is 8 frames and not the whole bracket.
pub struct SiteValidator {
    params: ValidateParams,
    motes: Vec<Mote>,
    /// Per site, per frame: the residual crop around the site.
    crops: Vec<Vec<Vec<f32>>>,
    /// Per site: crop origin and size in quad coordinates.
    windows: Vec<(usize, usize, usize, usize)>,
    frames: usize,
}

impl SiteValidator {
    /// Prepare to validate every mote in `map`.
    pub fn new(map: &DefectMap, params: ValidateParams) -> SiteValidator {
        let motes = map.motes(params.core_radius);
        SiteValidator {
            params,
            crops: vec![Vec::new(); motes.len()],
            windows: vec![(0, 0, 0, 0); motes.len()],
            motes,
            frames: 0,
        }
    }

    /// The motes this validator will rule on.
    pub fn motes(&self) -> &[Mote] {
        &self.motes
    }

    /// Observe one frame.
    ///
    /// `quad` is `qw * qh` black-subtracted quad means; build it with
    /// [`quad_mean`].
    pub fn observe(&mut self, quad: &[f32], qw: usize, qh: usize) {
        let p = self.params;
        for (i, m) in self.motes.iter().enumerate() {
            let x0 = (m.cx as usize).saturating_sub(p.window);
            let y0 = (m.cy as usize).saturating_sub(p.window);
            let x1 = (m.cx as usize + p.window + 1).min(qw);
            let y1 = (m.cy as usize + p.window + 1).min(qh);
            let (cw, ch) = (x1 - x0, y1 - y0);
            let mut crop = vec![0f32; cw * ch];
            for y in 0..ch {
                crop[y * cw..y * cw + cw]
                    .copy_from_slice(&quad[(y0 + y) * qw + x0..(y0 + y) * qw + x0 + cw]);
            }
            self.windows[i] = (x0, y0, cw, ch);
            self.crops[i].push(residual_field(&crop, cw, ch, p));
        }
        self.frames += 1;
    }

    /// Rule on every site.
    ///
    /// Returns one verdict per mote, in mote order, plus the partitioned count.
    pub fn finish(&self) -> (Vec<SiteVerdict>, ValidationReport) {
        let p = self.params;
        let mut out = Vec::with_capacity(self.motes.len());
        let mut rep = ValidationReport {
            examined: self.motes.len(),
            frames: self.frames,
            ..Default::default()
        };
        for (i, m) in self.motes.iter().enumerate() {
            let (x0, y0, cw, ch) = self.windows[i];
            let (lx, ly) = (m.cx as usize - x0, m.cy as usize - y0);
            let frames = &self.crops[i];

            // Per-frame depth -> presence. This is the only statistic that
            // needs the frames kept apart rather than pooled, and it is the
            // one that separates a mote from moving subject detail.
            let per: Vec<f64> = frames
                .iter()
                .map(|f| core_median(f, cw, ch, lx, ly, p.core_radius))
                .collect();
            let presence = if per.is_empty() {
                0.0
            } else {
                per.iter().filter(|d| **d <= -p.frame_floor).count() as f64 / per.len() as f64
            };

            // Pooled: the per-pixel median across frames. Rejects a single
            // frame's cosmic ray or a subject feature that visits once.
            let pooled = pixelwise_median(frames, cw * ch);
            let depth = core_median(&pooled, cw, ch, lx, ly, p.core_radius);
            let (pv, n_null) = local_null_p(&pooled, cw, ch, lx, ly, depth, p);

            let outcome = if frames.is_empty() || n_null < p.n_null {
                // The annulus could not be filled: the site is too near an
                // edge for a null to exist. A p-value from 40 samples is not
                // the p-value this was commissioned at, so it is refused
                // rather than reported at reduced confidence.
                SiteOutcome::Unmeasurable
            } else if pv > p.p_bar {
                SiteOutcome::NotSignificant
            } else if depth > -p.depth_floor {
                SiteOutcome::TooShallow
            } else if presence < p.presence_bar {
                SiteOutcome::NotStationary
            } else {
                SiteOutcome::Confirmed
            };
            match outcome {
                SiteOutcome::Confirmed => rep.confirmed += 1,
                SiteOutcome::NotSignificant => rep.not_significant += 1,
                SiteOutcome::TooShallow => rep.too_shallow += 1,
                SiteOutcome::NotStationary => rep.not_stationary += 1,
                SiteOutcome::Unmeasurable => rep.unmeasurable += 1,
            }
            out.push(SiteVerdict {
                cx: m.cx,
                cy: m.cy,
                depth,
                map_depth: m.map_depth,
                p: pv,
                presence,
                outcome,
                scale: depth_scale(depth, m.map_depth),
            });
        }
        (out, rep)
    }
}

/// The exponent that takes the map's profile to the measured amplitude.
///
/// # Why the amplitude comes from the frames and not from the map
///
/// A dust map records the depth of a mote **at the aperture and on the date it
/// was measured**. MEASURED across ten subject stacks, the depth at one fixed
/// sensor site varies **1.91x** — from -7.737% on `leaf-2-cpl` to -14.758% on
/// `coffee-bean` — because a smaller aperture projects a sharper, deeper shadow
/// of the same particle
/// (`experiments/BUILD-DEFECT/out/21-depth-aperture.log`).
///
/// So a map-gain correction is wrong in **both** directions. On the deepest
/// stack it leaves 6.6 points of mote uncorrected; on a shallower one it
/// over-corrects and **manufactures a bright spot** where the mote was, which
/// is the same failure as manufacturing the mote, inverted. Scaling to the
/// depth measured in the frames in front of it lands all five firing stacks
/// under **0.7% residual, including the f/8 one**.
///
/// The scaling is in log-gain space because attenuation composes
/// multiplicatively: a particle whose shadow is `t` deep at one aperture and
/// `t^s` deep at another has its whole profile raised to `s`, so the shape the
/// map measured is preserved and only the amplitude moves.
///
/// A degenerate `map_depth` (a mote the map says is not dark) returns 1.0
/// rather than dividing by zero, which leaves the map's gains untouched — the
/// conservative direction.
pub fn depth_scale(measured: f64, map_depth: f64) -> f64 {
    let dm = measured.abs().min(0.95);
    let d0 = map_depth.abs().min(0.95);
    if d0 <= 1e-9 || dm <= 1e-9 {
        return 1.0;
    }
    let s = (1.0 / (1.0 - dm)).ln() / (1.0 / (1.0 - d0)).ln();
    if s.is_finite() {
        s.clamp(0.0, 8.0)
    } else {
        1.0
    }
}

/// Black-subtracted 2x2 quad means of a frame's active area.
///
/// The lattice the map, the check and the correction all share. Reading the
/// **active area** and not the whole decoder buffer is the entire content of
/// [`CoordSpace`], and getting it wrong once produced a +54.8% reading.
pub fn quad_mean(
    samples: &[u16],
    stride: usize,
    active: (usize, usize, usize, usize),
    black: f32,
) -> (Vec<f32>, usize, usize) {
    let (ax, ay, aw, ah) = active;
    let (qw, qh) = (aw / 2, ah / 2);
    let mut out = vec![0f32; qw * qh];
    for qy in 0..qh {
        let r0 = (ay + 2 * qy) * stride + ax;
        let r1 = r0 + stride;
        for qx in 0..qw {
            let i = 2 * qx;
            let s = f32::from(samples[r0 + i])
                + f32::from(samples[r0 + i + 1])
                + f32::from(samples[r1 + i])
                + f32::from(samples[r1 + i + 1]);
            out[qy * qw + qx] = 0.25 * s - black;
        }
    }
    (out, qw, qh)
}

/// `q / lowpass(q) - 1`, mildly smoothed: the local multiplicative residual.
///
/// Quads whose local background is at or below zero signal are set to 0 rather
/// than to a ratio against a floor, because a ratio there is arbitrarily large
/// and would dominate a median it has no information about.
fn residual_field(q: &[f32], w: usize, h: usize, p: ValidateParams) -> Vec<f32> {
    let lo = box_smooth(q, w, h, p.hp_radius, p.hp_pass);
    let mut r = vec![0f32; w * h];
    for i in 0..w * h {
        r[i] = if lo[i] > 1.0 { q[i] / lo[i] - 1.0 } else { 0.0 };
    }
    box_smooth(&r, w, h, p.bp_radius, 1)
}

/// Median of the residual over a disc. The reading.
fn core_median(f: &[f32], w: usize, h: usize, cx: usize, cy: usize, r: usize) -> f64 {
    let mut v: Vec<f32> = Vec::with_capacity((2 * r + 1) * (2 * r + 1));
    let y0 = cy.saturating_sub(r);
    let x0 = cx.saturating_sub(r);
    let y1 = (cy + r + 1).min(h);
    let x1 = (cx + r + 1).min(w);
    for y in y0..y1 {
        for x in x0..x1 {
            let (dy, dx) = (y as i64 - cy as i64, x as i64 - cx as i64);
            if dy * dy + dx * dx <= (r * r) as i64 {
                v.push(f[y * w + x]);
            }
        }
    }
    if v.is_empty() {
        return 0.0;
    }
    f64::from(median(&mut v))
}

/// Per-pixel median across frames.
fn pixelwise_median(frames: &[Vec<f32>], n: usize) -> Vec<f32> {
    let mut out = vec![0f32; n];
    let mut col = vec![0f32; frames.len()];
    for (i, o) in out.iter_mut().enumerate() {
        for (k, f) in frames.iter().enumerate() {
            col[k] = f[i];
        }
        *o = median(&mut col);
    }
    out
}

/// How often a disc drawn from the surrounding annulus is at least as dark as
/// the site.
///
/// # This search is able to return nothing
///
/// AGENTS.md rule 12. The null is drawn from the site's **own neighbourhood**,
/// not from a global model, so a busy or textured background produces a wide
/// null and the site fails to clear it — which is exactly what happened on
/// `tweezers-cpl` (p = 0.3092) and `wrapped-text-1` (p = 0.2519), whose control
/// sites read -8.4% and -15.3% of ordinary subject structure. Those stacks are
/// not corrected, and they are the stacks in which V-EYES independently reports
/// the mote **cannot be seen**. Power and visibility are governed by the same
/// quantity, so the check declines precisely where declining costs nothing.
///
/// Returns `(p, n)`. A caller that gets `n < n_null` did not get a p-value it
/// can use; see [`SiteOutcome::Unmeasurable`].
fn local_null_p(
    f: &[f32],
    w: usize,
    h: usize,
    cx: usize,
    cy: usize,
    v: f64,
    p: ValidateParams,
) -> (f64, usize) {
    let mut rng = SplitMix64(p.seed);
    let mut at_least = 0usize;
    let mut got = 0usize;
    let mut tries = 0usize;
    let r = p.core_radius as i64;
    while got < p.n_null && tries < 40 * p.n_null {
        tries += 1;
        let a = rng.next_f64() * std::f64::consts::TAU;
        let d = p.annulus_in as f64 + rng.next_f64() * (p.annulus_out - p.annulus_in) as f64;
        let oy = cy as f64 + d * a.sin();
        let ox = cx as f64 + d * a.cos();
        if oy < r as f64 || ox < r as f64 || oy >= (h as i64 - r) as f64 || ox >= (w as i64 - r) as f64
        {
            continue;
        }
        let m = core_median(f, w, h, ox as usize, oy as usize, p.core_radius);
        if m <= v {
            at_least += 1;
        }
        got += 1;
    }
    ((1.0 + at_least as f64) / (1.0 + got as f64), got)
}

impl DefectMap {
    /// Group the dust quads into connected motes (8-connectivity).
    ///
    /// `core_radius` is the disc the [`Mote::map_depth`] median is taken over,
    /// and must match the one the check will use, or the map's claim and the
    /// frames' measurement would be medians of different things.
    pub fn motes(&self, core_radius: usize) -> Vec<Mote> {
        let n = self.dust.len();
        let mut parent: Vec<usize> = (0..n).collect();
        fn find(p: &mut [usize], mut a: usize) -> usize {
            while p[a] != a {
                p[a] = p[p[a]];
                a = p[a];
            }
            a
        }
        // The quads are sorted by (py, px), so an index by coordinate makes
        // the neighbour lookup a binary search rather than an n^2 scan.
        let key: Vec<(u32, u32)> = self.dust.iter().map(|d| (d.py, d.px)).collect();
        for (i, d) in self.dust.iter().enumerate() {
            for dy in 0..=1u32 {
                for dx in [-1i64, 0, 1] {
                    if dy == 0 && dx <= 0 {
                        continue;
                    }
                    let ny = d.py + dy;
                    let nx = d.px as i64 + dx;
                    if nx < 0 {
                        continue;
                    }
                    if let Ok(j) = key.binary_search(&(ny, nx as u32)) {
                        let (a, b) = (find(&mut parent, i), find(&mut parent, j));
                        if a != b {
                            parent[a] = b;
                        }
                    }
                }
            }
        }
        let mut groups: std::collections::BTreeMap<usize, Vec<usize>> = Default::default();
        for i in 0..n {
            let root = find(&mut parent, i);
            groups.entry(root).or_default().push(i);
        }
        let mut out = Vec::with_capacity(groups.len());
        for quads in groups.into_values() {
            let (mut sx, mut sy) = (0f64, 0f64);
            let mut peak = 1f32;
            for &i in &quads {
                sx += f64::from(self.dust[i].px);
                sy += f64::from(self.dust[i].py);
                peak = peak.max(self.dust[i].gain);
            }
            let cx = (sx / quads.len() as f64).round() as u32;
            let cy = (sy / quads.len() as f64).round() as u32;
            // The map's own claim about this mote's core, in depth units.
            let mut core: Vec<f32> = quads
                .iter()
                .filter(|&&i| {
                    let dx = self.dust[i].px as i64 - cx as i64;
                    let dy = self.dust[i].py as i64 - cy as i64;
                    dx * dx + dy * dy <= (core_radius * core_radius) as i64
                })
                .map(|&i| 1.0 / self.dust[i].gain - 1.0)
                .collect();
            let map_depth = if core.is_empty() {
                0.0
            } else {
                f64::from(median(&mut core))
            };
            out.push(Mote {
                quads,
                cx,
                cy,
                peak_gain: peak,
                map_depth,
            });
        }
        out.sort_by_key(|m| (m.cy, m.cx));
        out
    }

    /// A copy of this map carrying only the motes the frames confirmed, with
    /// every gain rescaled to the depth those frames measured.
    ///
    /// **Shape from the map, amplitude from the data.** The map knows the
    /// profile of the particle — which quads, and how the depth falls off
    /// across them — because it was built from 160 flat fields and a subject
    /// stack cannot see that. The frames know how deep the shadow is *today, at
    /// this aperture*, which the map cannot. Each supplies the half it is
    /// entitled to.
    ///
    /// Verdicts must be the ones [`SiteValidator::finish`] returned for **this**
    /// map, in mote order; anything else is a programming error and is caught
    /// by the length check rather than silently mis-applied.
    pub fn validated(
        &self,
        verdicts: &[SiteVerdict],
        core_radius: usize,
    ) -> Result<DefectMap, DefectMapError> {
        let motes = self.motes(core_radius);
        if verdicts.len() != motes.len() {
            return Err(DefectMapError::BadValue {
                key: "verdicts".into(),
                value: format!(
                    "{} verdicts for a map with {} motes",
                    verdicts.len(),
                    motes.len()
                ),
            });
        }
        let mut dust = Vec::new();
        for (m, v) in motes.iter().zip(verdicts) {
            if !v.outcome.corrects() {
                continue;
            }
            for &i in &m.quads {
                let d = &self.dust[i];
                // exp(ln(g) * s): the profile raised to the measured exponent.
                let g = (f64::from(d.gain).ln() * v.scale).exp() as f32;
                // The format's plausibility bar still applies to a computed
                // gain. A frame that measured an absurd depth must not be able
                // to write a gain the parser would have refused from a file.
                let g = g.clamp(1.0, MAX_DUST_GAIN);
                if g > 1.0 {
                    dust.push(DustQuad {
                        px: d.px,
                        py: d.py,
                        gain: g,
                    });
                }
            }
        }
        dust.sort_by_key(|d| (d.py, d.px));
        Ok(DefectMap {
            dust,
            ..self.clone()
        })
    }
}

/// The canonical dust map for the body this project was built on.
///
/// Embedded rather than shipped beside the binary because the correction is
/// **default-ON**, and a default-on correction that depends on a file the user
/// has to find is not on by default. Only the dust arm is here: the hot arm is
/// 14,626 sites that M101 measured to be an immaterial null on this body, so
/// compiling it in would spend 300 KB to move nothing.
///
/// Applying it to another body is prevented twice over — by the `camera` match
/// in [`DefectMap::embedded_for`], and, if some other body ever shares both the
/// model string and the geometry, by self-validation, which will not find these
/// motes in frames that do not contain them.
pub const EMBEDDED_DUST_MAP: &str = include_str!("defect-map-ILCE-7CM2-dust.txt");

impl DefectMap {
    /// The embedded map for `camera`, or `None` if this build has none.
    ///
    /// The match is exact. A near-miss returns `None` and the render is
    /// uncorrected, which is the safe direction: a map is a statement about one
    /// piece of silicon, and "probably the same sensor" is not a measurement.
    pub fn embedded_for(camera: &str) -> Option<DefectMap> {
        let m = DefectMap::from_text(EMBEDDED_DUST_MAP)
            .expect("the embedded defect map is parsed by a unit test");
        if m.camera == camera.trim() {
            Some(m)
        } else {
            None
        }
    }
}

// ---------------------------------------------------------------------------
// Commissioning
// ---------------------------------------------------------------------------

/// The commissioning suite for the defect map.
///
/// # Why every arm comes in three
///
/// AGENTS.md rule 24, and the reason it exists: *a commissioning suite that
/// only plants degradations cannot distinguish a metric that is **blind** to a
/// defect from one that is **perverse** on it.* Both read "no change" when you
/// plant a degradation and look only for the metric to get worse.
///
/// So every arm here is a triple:
///
/// 1. **RED** - plant a known defect, require the metric to fire.
/// 2. **GREEN** - feed a known-clean input, require the metric not to fire, and
///    require the *detector* to return nothing.
/// 3. **RIGHT WAY** - plant a known **improvement** (the same defect, corrected
///    by a ladder of increasing gains) and require the metric to move toward
///    clean, monotonically, and then back away past the right gain. Plus the
///    perversity arm: plant an **over**-correction and require the metric to
///    get *worse*, which is the single check a zero-bounded statistic cannot
///    pass.
#[cfg(test)]
mod tests {
    use super::*;

    // ---- synthetic sensor ------------------------------------------------

    const W: usize = 240;
    const H: usize = 180;
    const BLACK: f32 = 512.0;
    const WHITE: u16 = 15360;
    const LEVEL: u16 = 4512; // 4000 DN above black, a midtone

    /// A deterministic LCG, so a failure is reproducible from the test name
    /// alone. `rand` is not a dependency of this crate and adding one to make a
    /// test shake is not a trade this project makes.
    struct Lcg(u64);
    impl Lcg {
        fn next_f32(&mut self) -> f32 {
            self.0 = self.0.wrapping_mul(6364136223846793005).wrapping_add(1);
            ((self.0 >> 33) as f32 / (1u64 << 31) as f32) - 0.5
        }
        /// Approximately Gaussian, by the sum of four uniforms.
        fn noise(&mut self, sd: f32) -> f32 {
            let s: f32 = (0..4).map(|_| self.next_f32()).sum();
            s * sd / 0.5774
        }
    }

    /// A flat, uniformly lit sensor with shot-like noise. No defects.
    fn clean_frame(seed: u64, sd: f32) -> Vec<u16> {
        let mut r = Lcg(seed);
        (0..W * H)
            .map(|_| (f32::from(LEVEL) + r.noise(sd)).round().clamp(0.0, 65535.0) as u16)
            .collect()
    }

    /// A filled disc of quads centred at `(cx, cy)`.
    fn disc(cx: usize, cy: usize, rad: usize) -> Vec<(u32, u32)> {
        let mut v = Vec::new();
        for qy in cy.saturating_sub(rad)..(cy + rad + 1).min(H / 2) {
            for qx in cx.saturating_sub(rad)..(cx + rad + 1).min(W / 2) {
                let dx = qx as f64 - cx as f64;
                let dy = qy as f64 - cy as f64;
                if dx * dx + dy * dy <= (rad * rad) as f64 {
                    v.push((qx as u32, qy as u32));
                }
            }
        }
        v
    }

    /// Attenuate every sample of each quad by `depth` - multiplicative, on the
    /// black-subtracted signal, exactly as real dust does.
    fn plant_dust(f: &mut [u16], quads: &[(u32, u32)], depth: f32) {
        for &(qx, qy) in quads {
            for dy in 0..2 {
                for dx in 0..2 {
                    let i = (2 * qy as usize + dy) * W + 2 * qx as usize + dx;
                    let s = (f32::from(f[i]) - BLACK).max(0.0);
                    f[i] = (s * (1.0 - depth) + BLACK).round() as u16;
                }
            }
        }
    }

    fn active() -> (usize, usize, usize, usize) {
        (0, 0, W, H)
    }

    // ---- format ----------------------------------------------------------

    #[test]
    fn a_map_round_trips_through_the_text_format() {
        let mut m = DefectMap::empty(W, H, "ILCE-7CM2");
        m.aperture_f = Some(5.6);
        m.provenance.push("built by the commissioning suite".into());
        m.hot.push(HotSite {
            x: 10,
            y: 20,
            excess_e: 6.25,
        });
        m.dust.push(DustQuad {
            px: 5,
            py: 6,
            gain: 1.0184,
        });
        let back = DefectMap::from_text(&m.to_text()).expect("round trip");
        assert_eq!(back, m);
    }

    #[test]
    fn a_truncated_map_errors_rather_than_loading_a_short_site_list() {
        let mut m = DefectMap::empty(W, H, "x");
        m.hot.push(HotSite {
            x: 1,
            y: 1,
            excess_e: 9.0,
        });
        m.hot.push(HotSite {
            x: 2,
            y: 2,
            excess_e: 9.0,
        });
        let text = m.to_text();
        // Drop the last hot record and the `end` marker, as a half-written
        // file would be.
        let cut: String = text
            .lines()
            .filter(|l| !l.starts_with("h 2 2") && *l != "end")
            .collect::<Vec<_>>()
            .join("\n");
        match DefectMap::from_text(&cut) {
            Err(DefectMapError::Truncated {
                declared_hot,
                found_hot,
                saw_end,
                ..
            }) => {
                assert_eq!(declared_hot, 2);
                assert_eq!(found_hot, 1);
                assert!(!saw_end);
            }
            other => panic!("expected Truncated, got {other:?}"),
        }
    }

    #[test]
    fn a_typod_record_errors_rather_than_falling_back_to_the_default() {
        let text = format!(
            "{MAGIC} {VERSION}\ncamera x\nsensor 4 4\ncovered 4 4\ncoords active\naperture unknown\n\
             hott 0\ndust 0\nend\n"
        );
        match DefectMap::from_text(&text) {
            Err(DefectMapError::BadLine { detail, .. }) => {
                assert!(detail.contains("hott"), "{detail}");
            }
            other => panic!("expected BadLine, got {other:?}"),
        }
    }

    #[test]
    fn a_typod_correction_arm_errors_rather_than_falling_back_to_the_default() {
        assert_eq!(Correction::parse("dust").unwrap(), Correction::DUST);
        assert_eq!(Correction::parse("none").unwrap(), Correction::NONE);
        for bad in ["Dust", "dusty", "hot,dust", "", "all"] {
            match Correction::parse(bad) {
                Err(DefectMapError::UnknownArm { found }) => assert_eq!(found, bad.trim()),
                other => panic!("{bad:?} should not parse, got {other:?}"),
            }
        }
    }

    #[test]
    fn an_implausible_gain_is_refused_rather_than_clamped() {
        let text = format!(
            "{MAGIC} {VERSION}\ncamera x\nsensor 40 40\ncovered 40 40\ncoords active\naperture 5.6\n\
             hot 0\ndust 1\nd 3 3 2.5\nend\n"
        );
        match DefectMap::from_text(&text) {
            Err(DefectMapError::ImplausibleGain { gain, .. }) => assert_eq!(gain, 2.5),
            other => panic!("expected ImplausibleGain, got {other:?}"),
        }
        // ...and a gain below 1.0, which would DARKEN, is refused too.
        let text = text.replace("2.5", "0.98");
        assert!(matches!(
            DefectMap::from_text(&text),
            Err(DefectMapError::ImplausibleGain { .. })
        ));
    }

    #[test]
    fn a_map_for_another_readout_mode_is_refused_but_a_wider_active_area_is_not() {
        // P39. This test used to demand EXACT equality, and exact equality was
        // wrong: the shipping decoder reports two full-frame active widths on
        // one body (7032 for 15 corpus stacks, 7040 for 11), both at origin
        // (0, 0), and the same motes read at the same coordinates in both. An
        // exact-equality guard hard-failed 11 of 26 renders. See
        // `DefectMap::check_geometry`.
        //
        // Both arms are here on purpose. A guard tested only where it fires
        // cannot be distinguished from a guard that fires always -- which is
        // exactly the state this one was in when it broke 11 renders, because
        // every test it had planted a mismatch.
        let m = DefectMap::empty(W, H, "x");

        // ARM 1: ADMIT. The corpus difference, scaled -- 0.11% of 7032 is
        // sub-pixel at 240, so use the largest width still inside the bar.
        let admit_w = W + (W as f64 * DefectMap::MAX_ACTIVE_MISMATCH_FRAC) as usize;
        assert!(admit_w > W, "the tolerance must admit SOMETHING wider");
        m.check_geometry(admit_w, H).unwrap_or_else(|e| {
            panic!("a {admit_w}x{H} frame was refused against a {W}x{H} map: {e}")
        });

        // The real corpus geometries, unscaled, against the real map size.
        let real = DefectMap::empty(7032, 4688, "ILCE-7CM2");
        real.check_geometry(7032, 4688)
            .expect("the map's own geometry was refused");
        real.check_geometry(7040, 4688).expect(
            "7040x4688 was refused -- this is 11 of 26 corpus stacks and the \
             motes are measured at the same coordinates there",
        );

        // ARM 2: REJECT. An APS-C crop moves the origin, so every coordinate
        // names a different photosite. ~34% narrower on this body.
        let err = real
            .check_geometry(4616, 3080)
            .expect_err("an APS-C-scale readout was accepted");
        match err {
            DefectMapError::SensorMismatch { frac, bar, .. } => {
                assert!(
                    frac > bar,
                    "the refusal reports {frac:.2}% against a {bar:.2}% bar, which \
                     does not justify itself"
                );
                assert!(
                    frac > 30.0,
                    "an APS-C crop should be tens of percent, not {frac:.2}%"
                );
            }
            other => panic!("expected SensorMismatch, got {other:?}"),
        }

        // ARM 3: REJECT, through `apply`, so the guard is known to be reached
        // from the path that writes pixels and not merely to exist.
        let mut f = clean_frame(1, 8.0);
        let err = m
            .apply(
                &mut f,
                W,
                (0, 0, W / 2, H),
                BLACK,
                f32::from(WHITE),
                0.229,
                Correction::BOTH,
                HotFloor::CENSUS,
            )
            .unwrap_err();
        assert!(
            matches!(err, DefectMapError::SensorMismatch { .. }),
            "{err}"
        );
    }

    // ---- the correction: partition and inertness -------------------------

    #[test]
    fn the_default_correction_is_off_and_changes_no_byte() {
        assert_eq!(Correction::default(), Correction::NONE);
        assert!(Correction::default().is_noop());
        let quads = disc(40, 30, 6);
        let mut m = DefectMap::empty(W, H, "x");
        m.dust = quads
            .iter()
            .map(|&(px, py)| DustQuad {
                px,
                py,
                gain: 1.02,
            })
            .collect();
        m.hot.push(HotSite {
            x: 100,
            y: 100,
            excess_e: 40.0,
        });
        let before = clean_frame(7, 8.0);
        let mut after = before.clone();
        let r = m
            .apply(
                &mut after,
                W,
                active(),
                BLACK,
                f32::from(WHITE),
                0.229,
                Correction::default(),
                HotFloor::CENSUS,
            )
            .unwrap();
        assert_eq!(before, after, "the default correction moved bytes");
        // ...and the report says EXAMINED ZERO, not CORRECTED ZERO.
        assert_eq!(r.hot_examined, 0);
        assert_eq!(r.dust_examined, 0);
        assert_eq!(r.samples_changed, 0);
    }

    #[test]
    fn every_site_lands_in_exactly_one_counted_outcome() {
        let mut m = DefectMap::empty(W, H, "x");
        // In-range, deep enough.
        m.hot.push(HotSite {
            x: 50,
            y: 50,
            excess_e: 40.0,
        });
        // In-range, below the floor.
        m.hot.push(HotSite {
            x: 51,
            y: 50,
            excess_e: 1.0,
        });
        // In-range but on a clipped sample.
        m.hot.push(HotSite {
            x: 52,
            y: 50,
            excess_e: 40.0,
        });
        // In-range, deep enough, but rounds to no change at this gain.
        m.hot.push(HotSite {
            x: 53,
            y: 50,
            excess_e: 8.5,
        });
        m.dust.push(DustQuad {
            px: 30,
            py: 30,
            gain: 1.02,
        });
        m.dust.push(DustQuad {
            px: 31,
            py: 30,
            gain: 1.000001,
        });
        m.dust.push(DustQuad {
            px: 32,
            py: 30,
            gain: 1.02,
        });

        let mut f = clean_frame(3, 0.0);
        f[50 * W + 52] = WHITE; // clipped hot
        for dy in 0..2 {
            for dx in 0..2 {
                f[(60 + dy) * W + 64 + dx] = WHITE; // clipped dust quad (32,30)
            }
        }
        let r = m
            .apply(
                &mut f,
                W,
                active(),
                BLACK,
                f32::from(WHITE),
                0.02, // a tiny gain, so 8.5 e- rounds to 0 DN
                Correction::BOTH,
                HotFloor::REPRODUCIBLE,
            )
            .unwrap();
        assert_eq!(r.check_partition(), (true, true), "{r:?}");
        assert_eq!(r.hot_examined, 4);
        assert_eq!(r.hot_corrected, 1, "{}", r.describe());
        assert_eq!(r.hot_below_floor, 1);
        assert_eq!(r.hot_clipped, 1);
        assert_eq!(r.hot_no_change, 1);
        assert_eq!(r.dust_examined, 3);
        assert_eq!(r.dust_corrected, 1, "{}", r.describe());
        assert_eq!(r.dust_no_change, 1);
        assert_eq!(r.dust_clipped, 1);
    }

    #[test]
    fn the_dust_gain_is_applied_to_the_signal_and_not_to_the_black_pedestal() {
        // A quad sitting exactly AT black must stay at black: there is no
        // light there to restore. Scaling the raw DN instead would lift it to
        // black * gain, which at black 512 and gain 1.05 is +26 DN of
        // fabricated shadow detail.
        let mut m = DefectMap::empty(W, H, "x");
        m.dust.push(DustQuad {
            px: 10,
            py: 10,
            gain: 1.05,
        });
        let mut f = vec![BLACK as u16; W * H];
        let r = m
            .apply(
                &mut f,
                W,
                active(),
                BLACK,
                f32::from(WHITE),
                0.229,
                Correction::DUST,
                HotFloor::CENSUS,
            )
            .unwrap();
        assert_eq!(f[20 * W + 20], BLACK as u16);
        assert_eq!(r.dust_no_change, 1);
        assert_eq!(r.samples_changed, 0);
    }

    // ---- METRIC COMMISSIONING: dust --------------------------------------

    /// **GREEN.** A clean frame must read at the noise floor, and that floor
    /// must be quoted rather than assumed, because every RED bar below is a
    /// multiple of it.
    #[test]
    fn the_dust_metric_reads_a_clean_frame_as_green() {
        let quads = disc(40, 30, 6);
        let f = clean_frame(11, 8.0);
        let m = dust_residual(&f, W, active(), BLACK, &quads, 12);
        assert!(
            m.mean_abs < 0.004,
            "clean frame read {:.5} abs; the metric has a bias",
            m.mean_abs
        );
        assert!(m.n >= 100, "only {} of {} quads scored", m.n, quads.len());
    }

    /// **RED.** A planted shadow must fire, and in the right direction.
    #[test]
    fn the_dust_metric_reads_a_planted_shadow_as_red() {
        let quads = disc(40, 30, 6);
        let clean = clean_frame(11, 8.0);
        let base = dust_residual(&clean, W, active(), BLACK, &quads, 12);
        let mut f = clean.clone();
        plant_dust(&mut f, &quads, 0.02);
        let hit = dust_residual(&f, W, active(), BLACK, &quads, 12);
        assert!(
            hit.mean_signed < -0.012,
            "a 2% shadow read {:.5} signed",
            hit.mean_signed
        );
        assert!(
            hit.mean_abs > 4.0 * base.mean_abs.max(1e-4),
            "planted {:.5} vs clean {:.5}: not separated",
            hit.mean_abs,
            base.mean_abs
        );
    }

    /// **RIGHT WAY.** The arm a degradation-only suite cannot run.
    #[test]
    fn the_dust_metric_moves_the_right_way_for_a_planted_improvement() {
        let quads = disc(40, 30, 6);
        let clean = clean_frame(11, 8.0);
        let mut planted = clean.clone();
        plant_dust(&mut planted, &quads, 0.02);

        let mut m = DefectMap::empty(W, H, "x");
        let readings: Vec<(f32, f64, f64)> = [0.0f32, 0.5, 1.0, 1.5, 2.0]
            .iter()
            .map(|&frac| {
                m.dust = quads
                    .iter()
                    .map(|&(px, py)| DustQuad {
                        px,
                        py,
                        gain: 1.0 + frac * (1.0 / 0.98 - 1.0),
                    })
                    .collect();
                let mut f = planted.clone();
                m.apply(
                    &mut f,
                    W,
                    active(),
                    BLACK,
                    f32::from(WHITE),
                    0.229,
                    Correction::DUST,
                    HotFloor::CENSUS,
                )
                .unwrap();
                let r = dust_residual(&f, W, active(), BLACK, &quads, 12);
                (frac, r.mean_signed, r.mean_abs)
            })
            .collect();

        // Monotone improvement up to the right gain...
        for w in readings[..3].windows(2) {
            assert!(
                w[1].2 < w[0].2,
                "correcting harder made the ABS metric worse: {:?} -> {:?}",
                w[0],
                w[1]
            );
        }
        // ...and the signed residual crosses zero and keeps rising, which is
        // what proves the metric is not saturating.
        assert!(readings[0].1 < -0.012, "{readings:?}");
        assert!(readings[2].1.abs() < 0.004, "{readings:?}");
        assert!(readings[4].1 > 0.012, "{readings:?}");
    }

    /// **NOT PERVERSE.** The specific defect AGENTS.md rule 24 was written
    /// about: a statistic bounded below by zero reads an over-correction as
    /// perfect.
    #[test]
    fn the_metric_charges_for_over_correction_and_is_not_bounded_below() {
        let quads = disc(40, 30, 6);
        let clean = clean_frame(11, 8.0);
        let mut planted = clean.clone();
        plant_dust(&mut planted, &quads, 0.02);

        let under = dust_residual(&planted, W, active(), BLACK, &quads, 12);

        let mut m = DefectMap::empty(W, H, "x");
        m.dust = quads
            .iter()
            .map(|&(px, py)| DustQuad {
                px,
                py,
                // Twice the right restoration.
                gain: 1.0 + 2.0 * (1.0 / 0.98 - 1.0),
            })
            .collect();
        let mut over_f = planted.clone();
        m.apply(
            &mut over_f,
            W,
            active(),
            BLACK,
            f32::from(WHITE),
            0.229,
            Correction::DUST,
            HotFloor::CENSUS,
        )
        .unwrap();
        let over = dust_residual(&over_f, W, active(), BLACK, &quads, 12);

        assert!(
            over.mean_signed > 0.0,
            "over-correction did not change the sign: {over:?}"
        );
        assert!(
            over.mean_abs > 0.7 * under.mean_abs,
            "over-correcting by 2x read {:.5} against an uncorrected {:.5}; the metric \
             is perverse or blind",
            over.mean_abs,
            under.mean_abs
        );
        // And a correct correction must beat BOTH.
        m.dust = quads
            .iter()
            .map(|&(px, py)| DustQuad {
                px,
                py,
                gain: 1.0 / 0.98,
            })
            .collect();
        let mut right_f = planted.clone();
        m.apply(
            &mut right_f,
            W,
            active(),
            BLACK,
            f32::from(WHITE),
            0.229,
            Correction::DUST,
            HotFloor::CENSUS,
        )
        .unwrap();
        let right = dust_residual(&right_f, W, active(), BLACK, &quads, 12);
        assert!(right.mean_abs < under.mean_abs, "{right:?} vs {under:?}");
        assert!(right.mean_abs < over.mean_abs, "{right:?} vs {over:?}");
    }

    /// **GREEN, on the corrector rather than the metric.** Correcting a clean
    /// frame must cost no more than the gain applied - the arm that catches a
    /// correction which is fine on its own defects and destructive elsewhere.
    #[test]
    fn correcting_a_clean_frame_costs_no_more_than_the_gain_applied() {
        let quads = disc(40, 30, 6);
        let clean = clean_frame(23, 8.0);
        let before = dust_residual(&clean, W, active(), BLACK, &quads, 12);
        let mut m = DefectMap::empty(W, H, "x");
        // The real map's median gain, applied where there is no dust.
        m.dust = quads
            .iter()
            .map(|&(px, py)| DustQuad {
                px,
                py,
                gain: 1.0116,
            })
            .collect();
        let mut f = clean.clone();
        m.apply(
            &mut f,
            W,
            active(),
            BLACK,
            f32::from(WHITE),
            0.229,
            Correction::DUST,
            HotFloor::CENSUS,
        )
        .unwrap();
        let after = dust_residual(&f, W, active(), BLACK, &quads, 12);
        assert!(
            after.mean_abs < 0.0116 + before.mean_abs + 0.002,
            "clean-frame cost {:.5} exceeds the applied gain: {after:?}",
            after.mean_abs
        );
        assert!(after.mean_signed > 0.008, "{after:?}");
    }

    // ---- METRIC COMMISSIONING: hot ---------------------------------------

    #[test]
    fn the_hot_metric_reads_clean_green_planted_red_and_charges_for_over_subtraction() {
        let sites: Vec<(u32, u32)> = (0..64).map(|k| (20 + 3 * k, 40 + 2 * (k % 7))).collect();
        let clean = clean_frame(31, 8.0);
        let green = hot_residual(&clean, W, active(), &sites);
        assert!(green.mean_abs < 8.0, "clean read {:.3} DN", green.mean_abs);

        let amp = 60.0f32;
        let mut planted = clean.clone();
        for &(x, y) in &sites {
            let i = y as usize * W + x as usize;
            planted[i] = (f32::from(planted[i]) + amp) as u16;
        }
        let red = hot_residual(&planted, W, active(), &sites);
        assert!(
            red.mean_signed > 0.7 * f64::from(amp),
            "planted {amp} DN read {:.3}",
            red.mean_signed
        );

        let mut m = DefectMap::empty(W, H, "x");
        m.hot = sites
            .iter()
            .map(|&(x, y)| HotSite {
                x,
                y,
                excess_e: amp / 0.229,
            })
            .collect();
        let mut fixed_f = planted.clone();
        m.apply(
            &mut fixed_f,
            W,
            active(),
            BLACK,
            f32::from(WHITE),
            0.229,
            Correction::HOT,
            HotFloor::REPRODUCIBLE,
        )
        .unwrap();
        let fixed = hot_residual(&fixed_f, W, active(), &sites);
        assert!(fixed.mean_abs < red.mean_abs, "{fixed:?} vs {red:?}");

        // Over-subtract by 2x: must be charged for, not rewarded.
        m.hot = sites
            .iter()
            .map(|&(x, y)| HotSite {
                x,
                y,
                excess_e: 2.0 * amp / 0.229,
            })
            .collect();
        let mut over_f = planted.clone();
        m.apply(
            &mut over_f,
            W,
            active(),
            BLACK,
            f32::from(WHITE),
            0.229,
            Correction::HOT,
            HotFloor::REPRODUCIBLE,
        )
        .unwrap();
        let over = hot_residual(&over_f, W, active(), &sites);
        assert!(over.mean_signed < 0.0, "sign did not flip: {over:?}");
        assert!(
            over.mean_abs > 0.7 * red.mean_abs,
            "over-subtracting read {:.3} against an uncorrected {:.3}",
            over.mean_abs,
            red.mean_abs
        );
        assert!(fixed.mean_abs < over.mean_abs, "{fixed:?} vs {over:?}");
    }

    // ---- DETECTOR COMMISSIONING: the search must be able to fail ---------

    #[test]
    fn a_clean_sensor_yields_no_hot_sites() {
        let mut r = Lcg(101);
        let groups: Vec<Vec<f32>> = (0..11)
            .map(|_| (0..64 * 64).map(|_| r.noise(0.45)).collect())
            .collect();
        let refs: Vec<(&[f32], f32)> = groups.iter().map(|g| (g.as_slice(), 0.229)).collect();
        let (sites, census) = detect_hot(&refs, 64, 64, HotParams::default());
        assert!(
            sites.is_empty(),
            "{} hot sites found in pure noise: the search cannot fail",
            sites.len()
        );
        assert_eq!(census.examined, 64 * 64);
        assert_eq!(census.recurrent, 0);
        assert!(census.border > 0);
    }

    #[test]
    fn a_planted_hot_pixel_is_found_with_its_amplitude_in_electrons() {
        let mut r = Lcg(202);
        // Two gain regimes, so the electron conversion is actually exercised:
        // the same site must read the same amplitude in e- from a 0.229 DN/e-
        // group and from a 0.916 DN/e- one.
        //
        // **40 e- and not 12, and the difference is a measurement.** At 12 e-
        // this test found only 2 of its 3 plants, because 12 e- x 0.229 DN/e-
        // = 2.75 DN is *below* the detector's own 6-sigma cut in the low-gain
        // groups (sigma of the neighbour-excess field here is 0.49 DN, so the
        // cut is 2.9 DN), leaving only the 4 high-gain groups to flag it
        // against a recurrence bar of 6. The two that were "found" were found
        // by noise in two extra groups. A test tuned to sit on that boundary
        // measures the RNG, not the detector.
        //
        // The floor that implies is `6 * sigma_excess / gain`, and it is a
        // property of the *input's* noise rather than of this code: these
        // synthetic groups carry a per-sample sd of 0.45 DN, which is a single
        // dark frame. The real detector is fed 20-frame temporal means whose
        // sd is 0.45/sqrt(20) = 0.10 DN, so its real floor is ~2.9 e- at
        // ISO 100 -- which is why the delivered darks yield sites down in the
        // 2-4 e- stratum at all.
        let gains = [0.229f32, 0.229, 0.916, 0.916, 0.229, 0.916, 0.229, 0.916];
        let planted = [(20usize, 30usize), (40, 12), (55, 55)];
        let amp_e = 40.0f32;
        let groups: Vec<Vec<f32>> = gains
            .iter()
            .map(|&g| {
                let mut a: Vec<f32> = (0..64 * 64).map(|_| r.noise(0.45)).collect();
                for &(x, y) in &planted {
                    a[y * 64 + x] += amp_e * g;
                }
                a
            })
            .collect();
        let refs: Vec<(&[f32], f32)> = groups
            .iter()
            .zip(gains.iter())
            .map(|(a, &g)| (a.as_slice(), g))
            .collect();
        let (sites, census) = detect_hot(&refs, 64, 64, HotParams::default());
        assert_eq!(sites.len(), 3, "{census:?}");
        for s in &sites {
            assert!(
                (s.excess_e - amp_e).abs() < 1.5,
                "amplitude read {:.2} e-, expected {amp_e}",
                s.excess_e
            );
            assert!(planted.contains(&(s.x as usize, s.y as usize)));
        }
        assert_eq!(census.emitted, 3);
        assert_eq!(census.recurrent, 3);
        // ...and the amplitude floor is honoured: asking for more than was
        // planted must return NOTHING, not the least-bad candidate.
        let (none, census) = detect_hot(
            &refs,
            64,
            64,
            HotParams {
                min_excess_e: 2.0 * amp_e,
                ..HotParams::default()
            },
        );
        assert!(none.is_empty(), "{census:?}");
        assert_eq!(census.below_amplitude, 3);
        assert_eq!(census.recurrent, 3);
    }

    #[test]
    fn the_hot_neighbourhood_never_crosses_a_cfa_plane() {
        // A checkerboard of two plane levels with NO defect. A +/-1
        // neighbourhood would read every sample as a huge outlier; the +/-2
        // one must read exactly zero.
        let mut a = vec![0f32; 64 * 64];
        for y in 0..64 {
            for x in 0..64 {
                a[y * 64 + x] = if (x % 2) ^ (y % 2) == 0 { 100.0 } else { 900.0 };
            }
        }
        for y in 2..62 {
            for x in 2..62 {
                assert_eq!(neighbour_excess(&a, 64, x, y), 0.0, "at ({x},{y})");
            }
        }
    }

    /// Eighteen captures of a clean but **differently lit** field: exactly the
    /// confound the real flats have, with no dust in them at all.
    #[test]
    fn a_clean_flat_field_yields_no_dust() {
        let (w, h) = (200usize, 160usize);
        let mut r = Lcg(303);
        let caps: Vec<Vec<f32>> = (0..18)
            .map(|c| {
                let ax = 0.6 * (c as f32 * 1.7).sin();
                let ay = 0.6 * (c as f32 * 2.3).cos();
                (0..w * h)
                    .map(|i| {
                        let (x, y) = ((i % w) as f32 / w as f32, (i / w) as f32 / h as f32);
                        1.0 + ax * (x - 0.5) + ay * (y - 0.5) + r.noise(0.001)
                    })
                    .collect()
            })
            .collect();
        let refs: Vec<&[f32]> = caps.iter().map(|c| c.as_slice()).collect();
        let p = DustParams {
            hp_radius: 12,
            border: 13,
            ..DustParams::default()
        };
        let (dust, census) = detect_dust(&refs, w, h, p);
        assert!(
            dust.is_empty(),
            "{} dust quads found in a clean but unevenly lit field ({} components): \
             the illumination confound is not separated",
            dust.len(),
            census.components
        );
        assert_eq!(census.emitted, 0);
        assert_eq!(census.examined, w * h);
        assert!(census.border > 0, "the border was not excluded");
    }

    #[test]
    fn a_planted_mote_is_found_and_its_gain_restores_it() {
        let (w, h) = (200usize, 160usize);
        let mut r = Lcg(404);
        let mut quads = Vec::new();
        for qy in 70..90 {
            for qx in 90..110 {
                let dx = qx as f64 - 100.0;
                let dy = qy as f64 - 80.0;
                if dx * dx + dy * dy <= 81.0 {
                    quads.push((qx, qy));
                }
            }
        }
        let depth = 0.025f32;
        let caps: Vec<Vec<f32>> = (0..18)
            .map(|c| {
                let ax = 0.6 * (c as f32 * 1.7).sin();
                let ay = 0.6 * (c as f32 * 2.3).cos();
                let mut a: Vec<f32> = (0..w * h)
                    .map(|i| {
                        let (x, y) = ((i % w) as f32 / w as f32, (i / w) as f32 / h as f32);
                        1.0 + ax * (x - 0.5) + ay * (y - 0.5) + r.noise(0.001)
                    })
                    .collect();
                for &(qx, qy) in &quads {
                    a[qy * w + qx] *= 1.0 - depth;
                }
                a
            })
            .collect();
        let refs: Vec<&[f32]> = caps.iter().map(|c| c.as_slice()).collect();
        let p = DustParams {
            hp_radius: 12,
            border: 13,
            ..DustParams::default()
        };
        let (dust, census) = detect_dust(&refs, w, h, p);
        assert!(!dust.is_empty(), "the planted mote was not found: {census:?}");
        assert_eq!(census.components, 1, "{census:?}");
        let found: BTreeSet<(usize, usize)> =
            dust.iter().map(|d| (d.px as usize, d.py as usize)).collect();
        let planted: BTreeSet<(usize, usize)> = quads.iter().copied().collect();
        let inter = found.intersection(&planted).count();
        assert!(
            inter as f64 / planted.len() as f64 > 0.55,
            "recall {:.2} ({inter} of {})",
            inter as f64 / planted.len() as f64,
            planted.len()
        );
        assert!(
            found.difference(&planted).count() as f64 / found.len() as f64 <= 0.35,
            "too many quads outside the planted mote: {} of {}",
            found.difference(&planted).count(),
            found.len()
        );
        // The gain must restore what was planted, to within the attenuation
        // the high-pass itself applies to an object of this size.
        let mut gains: Vec<f32> = dust
            .iter()
            .filter(|d| planted.contains(&(d.px as usize, d.py as usize)))
            .map(|d| d.gain)
            .collect();
        let g = median(&mut gains);
        let want = 1.0 / (1.0 - depth);
        assert!(
            (g - want).abs() / (want - 1.0) < 0.35,
            "median gain {g:.5} against a planted {want:.5}"
        );
    }

    /// The mixture problem, planted: 400 single-quad multiplicative deficits,
    /// deeper than any real mote, and nothing extended. The band-pass and the
    /// component floor must reject all of them.
    #[test]
    fn an_isolated_bad_photosite_is_not_reported_as_dust() {
        let (w, h) = (200usize, 160usize);
        let mut r = Lcg(505);
        let mut bad = Vec::new();
        let mut s = 12345u64;
        for _ in 0..400 {
            s = s.wrapping_mul(6364136223846793005).wrapping_add(1);
            let x = 20 + (s >> 33) as usize % 160;
            s = s.wrapping_mul(6364136223846793005).wrapping_add(1);
            let y = 20 + (s >> 33) as usize % 120;
            bad.push((x, y));
        }
        let caps: Vec<Vec<f32>> = (0..18)
            .map(|c| {
                let ax = 0.6 * (c as f32 * 1.7).sin();
                let mut a: Vec<f32> = (0..w * h)
                    .map(|i| {
                        let x = (i % w) as f32 / w as f32;
                        1.0 + ax * (x - 0.5) + r.noise(0.001)
                    })
                    .collect();
                for &(x, y) in &bad {
                    a[y * w + x] *= 0.955; // -4.5%, deeper than any real mote
                }
                a
            })
            .collect();
        let refs: Vec<&[f32]> = caps.iter().map(|c| c.as_slice()).collect();
        let p = DustParams {
            hp_radius: 12,
            border: 13,
            ..DustParams::default()
        };
        let (dust, census) = detect_dust(&refs, w, h, p);
        assert!(
            dust.is_empty(),
            "{} quads reported as dust from {} isolated bad photosites \
             ({} components, {} rejected as too small)",
            dust.len(),
            bad.len(),
            census.components,
            census.components_too_small
        );
    }

    /// Seventeen clean captures and **one** with a deep, dust-shaped blob. The
    /// recurrence bar must reject it - this is the moving-cloud confound the
    /// delivered flats actually have.
    #[test]
    fn a_capture_that_saw_a_cloud_edge_cannot_create_a_site_on_its_own() {
        let (w, h) = (200usize, 160usize);
        let mut r = Lcg(606);
        let caps: Vec<Vec<f32>> = (0..18)
            .map(|c| {
                let mut a: Vec<f32> = (0..w * h).map(|_| 1.0 + r.noise(0.001)).collect();
                if c == 0 {
                    for qy in 70..90 {
                        for qx in 90..110 {
                            let dx = qx as f64 - 100.0;
                            let dy = qy as f64 - 80.0;
                            if dx * dx + dy * dy <= 81.0 {
                                a[qy * w + qx] *= 0.94;
                            }
                        }
                    }
                }
                a
            })
            .collect();
        let refs: Vec<&[f32]> = caps.iter().map(|c| c.as_slice()).collect();
        let p = DustParams {
            hp_radius: 12,
            border: 13,
            ..DustParams::default()
        };
        let (dust, _) = detect_dust(&refs, w, h, p);
        assert!(
            dust.is_empty(),
            "{} quads survived from a single capture: recurrence is not binding",
            dust.len()
        );
    }

    // ---- THE ORDERING CLAIM ----------------------------------------------

    /// The claim the whole module rests on: a sensor-coordinate correction
    /// must be applied **before** the geometric warp.
    ///
    /// Planted, not argued. A dust shadow is stamped into the sensor frame; the
    /// frame is then shifted by a warp of the size the aligner actually applies
    /// (up to 232.7 plane px on `bee-3-cpl`, so 20 quads is a modest one), and
    /// the two orderings are compared by the commissioned metric at the
    /// shadow's **post-warp** location.
    #[test]
    fn dust_correction_must_precede_the_warp_to_land_on_the_defect() {
        let quads = disc(40, 30, 7);
        let shift_q = 20usize; // quads
        let clean = clean_frame(77, 8.0);

        let mut sensor = clean.clone();
        plant_dust(&mut sensor, &quads, 0.02);

        let mut m = DefectMap::empty(W, H, "x");
        m.dust = quads
            .iter()
            .map(|&(px, py)| DustQuad {
                px,
                py,
                gain: 1.0 / 0.98,
            })
            .collect();

        // A whole-quad translation, so the comparison is about ORDER and not
        // about resampling.
        let warp = |src: &[u16]| -> Vec<u16> {
            let mut d = vec![LEVEL; W * H];
            for y in 0..H {
                for x in 0..W {
                    let sx = x + 2 * shift_q;
                    if sx < W {
                        d[y * W + x] = src[y * W + sx];
                    }
                }
            }
            d
        };

        // Where the shadow is AFTER the warp.
        let moved: Vec<(u32, u32)> = quads
            .iter()
            .map(|&(px, py)| (px - shift_q as u32, py))
            .collect();

        // (a) correct in sensor coordinates, then warp.
        let mut before_f = sensor.clone();
        m.apply(
            &mut before_f,
            W,
            active(),
            BLACK,
            f32::from(WHITE),
            0.229,
            Correction::DUST,
            HotFloor::CENSUS,
        )
        .unwrap();
        let before_f = warp(&before_f);
        let r_before = dust_residual(&before_f, W, active(), BLACK, &moved, 12);

        // (b) warp, then apply the same sensor-coordinate map.
        let mut after_f = warp(&sensor);
        m.apply(
            &mut after_f,
            W,
            active(),
            BLACK,
            f32::from(WHITE),
            0.229,
            Correction::DUST,
            HotFloor::CENSUS,
        )
        .unwrap();
        let r_after = dust_residual(&after_f, W, active(), BLACK, &moved, 12);

        // ...and (c) do nothing, as the inertness control.
        let none_f = warp(&sensor);
        let r_none = dust_residual(&none_f, W, active(), BLACK, &moved, 12);

        assert!(
            r_before.mean_abs < 0.35 * r_none.mean_abs,
            "correct-then-warp did not clear the shadow: {:.5} vs uncorrected {:.5}",
            r_before.mean_abs,
            r_none.mean_abs
        );
        assert!(
            r_after.mean_abs > 0.8 * r_none.mean_abs,
            "warp-then-correct should have left the shadow essentially untouched, \
             read {:.5} vs uncorrected {:.5}",
            r_after.mean_abs,
            r_none.mean_abs
        );
        assert!(
            r_after.mean_abs > 2.0 * r_before.mean_abs,
            "the ordering does not matter on this input, which means the control is \
             not exercising the claim: before {:.5}, after {:.5}",
            r_before.mean_abs,
            r_after.mean_abs
        );
    }

    /// The inertness control for the one above. With an **identity** warp the
    /// two orderings must be bit-identical; if they are not, the difference
    /// measured above is an artefact of the harness rather than of the warp.
    #[test]
    fn with_an_identity_warp_the_two_orderings_are_bit_identical() {
        let quads = disc(40, 30, 7);
        let clean = clean_frame(78, 8.0);
        let mut sensor = clean.clone();
        plant_dust(&mut sensor, &quads, 0.02);
        let mut m = DefectMap::empty(W, H, "x");
        m.dust = quads
            .iter()
            .map(|&(px, py)| DustQuad {
                px,
                py,
                gain: 1.0 / 0.98,
            })
            .collect();
        let go = |f: &[u16]| {
            let mut f = f.to_vec();
            m.apply(
                &mut f,
                W,
                active(),
                BLACK,
                f32::from(WHITE),
                0.229,
                Correction::DUST,
                HotFloor::CENSUS,
            )
            .unwrap();
            f
        };
        assert_eq!(go(&sensor), go(&sensor.clone()));
    }

    // -----------------------------------------------------------------
    // Self-validation
    // -----------------------------------------------------------------
    //
    // A larger synthetic sensor than the correction tests use, because the
    // check is a *spatial* statistic: it needs room for a 100-quad annulus
    // around the site and a low-pass whose support does not reach the frame
    // edge. 600x600 samples is 300x300 quads.

    const VW: usize = 600;
    const VH: usize = 600;
    const VSITE: (usize, usize) = (150, 150); // quad coordinates
    const VRAD: usize = 7; // planted mote radius, in quads
    const VDEPTH: f64 = 0.08;

    /// The check's thresholds, scaled to the synthetic sensor.
    ///
    /// Every ratio that matters is preserved: the annulus is 5x-25x the core
    /// radius (real: 7.5x-50x), the low-pass is ~2.3x the mote radius (real:
    /// 4.6x), and `p_bar` sits exactly on the null's quantisation floor
    /// `1/(n+1)`, so the site must beat **every** null sample, as it must in
    /// the field.
    fn vparams() -> ValidateParams {
        ValidateParams {
            hp_radius: 16,
            hp_pass: 2,
            bp_radius: 1,
            core_radius: 4,
            annulus_in: 20,
            annulus_out: 100,
            n_null: 200,
            p_bar: 1.0 / 201.0,
            depth_floor: 0.015,
            presence_bar: 0.75,
            frame_floor: 0.010,
            window: 140,
            seed: 20_250_101,
        }
    }

    /// A frame with a **smooth illumination gradient** and shot-like noise.
    ///
    /// The gradient is deliberate. The flats this project's dust map came from
    /// were shot under moving cloud, so the standing risk is reading an
    /// illumination drift as a defect. A 15% ramp across the frame is far
    /// larger than any mote, and every arm below runs on top of it: if the
    /// high-pass did not separate the two, the clean arm would fire.
    fn vframe(seed: u64, sd: f32) -> Vec<u16> {
        let mut r = Lcg(seed);
        let mut out = vec![0u16; VW * VH];
        for y in 0..VH {
            for x in 0..VW {
                let ramp = 1.0 + 0.15 * (x as f32 / VW as f32) + 0.07 * (y as f32 / VH as f32);
                let v = BLACK + (f32::from(LEVEL) - BLACK) * ramp + r.noise(sd);
                out[y * VW + x] = v.round().clamp(0.0, 65535.0) as u16;
            }
        }
        out
    }

    /// Multiplicatively attenuate a disc of quads, as dust does.
    fn vplant(f: &mut [u16], cx: usize, cy: usize, rad: usize, depth: f64) {
        for qy in cy.saturating_sub(rad)..(cy + rad + 1).min(VH / 2) {
            for qx in cx.saturating_sub(rad)..(cx + rad + 1).min(VW / 2) {
                let dx = qx as f64 - cx as f64;
                let dy = qy as f64 - cy as f64;
                if dx * dx + dy * dy > (rad * rad) as f64 {
                    continue;
                }
                for dy2 in 0..2 {
                    for dx2 in 0..2 {
                        let i = (2 * qy + dy2) * VW + 2 * qx + dx2;
                        let s = (f32::from(f[i]) - BLACK).max(0.0);
                        f[i] = (s * (1.0 - depth as f32) + BLACK).round() as u16;
                    }
                }
            }
        }
    }

    /// A map naming exactly the planted mote, at the depth it was planted.
    fn vmap(depth: f64) -> DefectMap {
        let mut m = DefectMap::empty(VW, VH, "x");
        let (cx, cy) = VSITE;
        for qy in cy - VRAD..=cy + VRAD {
            for qx in cx - VRAD..=cx + VRAD {
                let dx = qx as f64 - cx as f64;
                let dy = qy as f64 - cy as f64;
                if dx * dx + dy * dy <= (VRAD * VRAD) as f64 {
                    m.dust.push(DustQuad {
                        px: qx as u32,
                        py: qy as u32,
                        gain: (1.0 / (1.0 - depth)) as f32,
                    });
                }
            }
        }
        m.dust.sort_by_key(|d| (d.py, d.px));
        m
    }

    /// Run the check over a set of frames and return the single site's verdict.
    fn vjudge(map: &DefectMap, frames: &[Vec<u16>]) -> (SiteVerdict, ValidationReport) {
        let p = vparams();
        let mut v = SiteValidator::new(map, p);
        for f in frames {
            let (q, qw, qh) = quad_mean(f, VW, (0, 0, VW, VH), BLACK);
            v.observe(&q, qw, qh);
        }
        let (verdicts, rep) = v.finish();
        assert_eq!(verdicts.len(), 1, "one planted mote, one verdict");
        assert!(rep.check_partition(), "verdict buckets must sum: {rep:?}");
        (verdicts.into_iter().next().unwrap(), rep)
    }

    /// 8 frames with the mote pinned in sensor coordinates: real dust.
    fn vframes_fixed(depth: f64) -> Vec<Vec<u16>> {
        (0..8)
            .map(|k| {
                let mut f = vframe(700 + k, 18.0);
                vplant(&mut f, VSITE.0, VSITE.1, VRAD, depth);
                f
            })
            .collect()
    }

    /// 8 frames with a feature of the *same depth and size* translating across
    /// the site: subject detail under the bracket's magnification drift.
    fn vframes_moving(depth: f64, travel: usize) -> Vec<Vec<u16>> {
        (0..8)
            .map(|k| {
                let mut f = vframe(700 + k, 18.0);
                let off = (travel * k as usize) / 7;
                vplant(&mut f, VSITE.0 + off, VSITE.1, VRAD, depth);
                f
            })
            .collect()
    }

    /// RED. A mote that is really there, under a 15% illumination gradient,
    /// is confirmed -- and the depth it reports is the depth that was planted.
    #[test]
    fn self_validation_confirms_a_planted_mote_under_an_illumination_gradient() {
        let map = vmap(VDEPTH);
        let (v, rep) = vjudge(&map, &vframes_fixed(VDEPTH));
        assert_eq!(
            v.outcome,
            SiteOutcome::Confirmed,
            "planted mote must be confirmed, got {:?} (depth {:.4}, p {:.4}, presence {:.2})",
            v.outcome,
            v.depth,
            v.p,
            v.presence
        );
        assert_eq!(rep.confirmed, 1);
        assert!(
            (v.depth + VDEPTH).abs() < 0.02,
            "measured depth {:.4} should be near the planted -{:.4}",
            v.depth,
            VDEPTH
        );
        assert!(
            (v.scale - 1.0).abs() < 0.35,
            "map and frames agree, so the amplitude scale should be ~1, got {:.3}",
            v.scale
        );
    }

    /// GREEN, and the whole reason this feature can ship default-ON: a map that
    /// names a site the frames do not confirm corrects **nothing**.
    ///
    /// This is the staleness arm. The objection to a default-on dust map is
    /// that the sensor may have been cleaned since it was measured, in which
    /// case the correction brightens a spot where nothing is wrong and
    /// manufactures the exact defect it exists to remove. A map that is
    /// *required to observe the darkening first* cannot do that -- the failure
    /// mode becomes unreachable rather than merely unlikely.
    #[test]
    fn self_validation_skips_a_site_the_frames_do_not_confirm() {
        let map = vmap(VDEPTH);
        let clean: Vec<Vec<u16>> = (0..8).map(|k| vframe(700 + k, 18.0)).collect();
        let (v, rep) = vjudge(&map, &clean);
        assert!(
            !v.outcome.corrects(),
            "a cleaned sensor must not be corrected, got {:?} (depth {:.4}, p {:.4})",
            v.outcome,
            v.depth,
            v.p
        );
        assert_eq!(rep.confirmed, 0);
        assert_eq!(rep.examined, 1, "examined 0 and confirmed 0 are different");
        let validated = map.validated(&[v], vparams().core_radius).unwrap();
        assert!(
            validated.dust.is_empty(),
            "a skipped site must leave no quads to correct"
        );
    }

    /// The counterfactual that makes the arm above mean something.
    ///
    /// Without the guard, applying the map to clean frames does not do nothing
    /// -- it plants a **bright** spot of very nearly the depth it was trying to
    /// remove. Measured here, and measured at +8.64% to +16.44% on real stacks
    /// (`experiments/BUILD-DEFECT/out/22-selfvalidating.log`).
    #[test]
    fn an_unguarded_map_manufactures_a_bright_spot_on_a_clean_sensor() {
        let map = vmap(VDEPTH);
        let p = vparams();
        let mut clean = vframe(4242, 18.0);
        let read = |f: &[u16]| -> f64 {
            let (q, qw, qh) = quad_mean(f, VW, (0, 0, VW, VH), BLACK);
            let r = residual_field(&q, qw, qh, p);
            core_median(&r, qw, qh, VSITE.0, VSITE.1, p.core_radius)
        };
        let before = read(&clean);
        map.apply(
            &mut clean,
            VW,
            (0, 0, VW, VH),
            BLACK,
            f32::from(WHITE),
            1.0,
            Correction::DUST,
            HotFloor::CENSUS,
        )
        .unwrap();
        let after = read(&clean);
        assert!(
            after - before > 0.05,
            "an unguarded map on a clean sensor must manufacture a bright spot: \
             {before:.4} -> {after:.4}"
        );
    }

    /// RIGHT WAY. Plant a known **improvement** and require the check to stop
    /// firing -- and require the residual to actually shrink.
    ///
    /// AGENTS.md rule 24. A battery of degradations cannot tell a blind check
    /// from a perverse one. This is the arm that would fail if the check
    /// scored a corrected mote as *more* defective, which is not hypothetical:
    /// on the real corpus the corrected site was still the darkest thing in its
    /// own neighbourhood, so `p` alone re-fired on it and only the depth floor
    /// stopped a second correction being stacked on the first.
    #[test]
    fn self_validation_stops_firing_once_the_mote_has_been_corrected() {
        let map = vmap(VDEPTH);
        let p = vparams();
        let mut frames = vframes_fixed(VDEPTH);
        let (v, _) = vjudge(&map, &frames);
        assert_eq!(v.outcome, SiteOutcome::Confirmed, "arm needs a firing site");

        let before = v.depth;
        let corrected = map.validated(&[v], p.core_radius).unwrap();
        assert!(!corrected.dust.is_empty());
        for f in frames.iter_mut() {
            corrected
                .apply(
                    f,
                    VW,
                    (0, 0, VW, VH),
                    BLACK,
                    f32::from(WHITE),
                    1.0,
                    Correction::DUST,
                    HotFloor::CENSUS,
                )
                .unwrap();
        }
        let (after, _) = vjudge(&map, &frames);
        assert!(
            after.depth.abs() < before.abs() * 0.35,
            "the correction must shrink the residual: {:.4} -> {:.4}",
            before,
            after.depth
        );
        assert!(
            !after.outcome.corrects(),
            "an already-corrected mote must not fire again, got {:?} at {:.4}",
            after.outcome,
            after.depth
        );
    }

    /// PERVERSE. A **bright** blemish of the same size and amplitude must not
    /// read as a mote.
    ///
    /// The check is a signed statistic and this is the arm that proves it. A
    /// version bounded below at zero, or one scored on `|residual|`, would fire
    /// here and brighten a spot that was already too bright -- the failure this
    /// project has now caught twice, in `tri.blur_equiv` and `overshoot_frac`.
    #[test]
    fn self_validation_does_not_fire_on_a_bright_blemish() {
        let map = vmap(VDEPTH);
        let frames: Vec<Vec<u16>> = (0..8)
            .map(|k| {
                let mut f = vframe(700 + k, 18.0);
                vplant(&mut f, VSITE.0, VSITE.1, VRAD, -VDEPTH);
                f
            })
            .collect();
        let (v, _) = vjudge(&map, &frames);
        assert!(
            !v.outcome.corrects(),
            "a BRIGHT spot must not be read as dust, got {:?} at depth {:.4}",
            v.outcome,
            v.depth
        );
        assert!(
            v.depth > 0.0,
            "the reading must be signed and positive here, got {:.4}",
            v.depth
        );
    }

    /// STATIONARITY, and the arm that earns the `presence` bar its place.
    ///
    /// A dark feature of the **same depth and the same radius** as the mote,
    /// translating across the site as the bracket breathes, must not be
    /// corrected -- otherwise the correction brightens real subject detail: an
    /// eye, a dark hair, a shadow edge that happens to land on the mote's
    /// coordinates.
    ///
    /// The assertion is `NotStationary` **specifically**, not merely "did not
    /// fire", and that is the point of the test. [`SiteValidator::finish`]
    /// checks the bars in order, so a `NotStationary` verdict is proof that
    /// `p` and `depth_floor` both **passed** and only presence rejected. If a
    /// future edit made presence a no-op this test would report `Confirmed`;
    /// if it made the travel large enough that any bar would do, it would
    /// report `NotSignificant` and the test would also fail.
    ///
    /// MEASURED on real frames the same way: at 30 quads of travel on
    /// `leaf-2-cpl` a moving -8% disc read depth -6.718% at p = 0.0025 --
    /// clearing both other bars -- and presence 0.62 rejected it
    /// (`experiments/BUILD-DEFECT/out/25-drift-sweep.log`).
    #[test]
    fn self_validation_rejects_a_dark_feature_that_moves_with_the_subject() {
        let map = vmap(VDEPTH);
        let (v, rep) = vjudge(&map, &vframes_moving(VDEPTH, 12));
        assert_eq!(
            v.outcome,
            SiteOutcome::NotStationary,
            "a moving dark feature must be rejected BY THE PRESENCE BAR \
             (depth {:.4}, p {:.4}, presence {:.2}); Confirmed means presence \
             is a no-op, NotSignificant means the fixture moved too far to be \
             testing presence at all",
            v.depth,
            v.p,
            v.presence
        );
        assert_eq!(rep.not_stationary, 1);
        assert!(
            v.presence < vparams().presence_bar,
            "presence {:.2} must be under the bar",
            v.presence
        );
    }

    /// The positive control for the arm above: identical depth, identical
    /// radius, identical frames, **zero travel**. Only motion differs.
    ///
    /// Without this, "the moving arm did not fire" could mean the fixture is
    /// simply undetectable.
    #[test]
    fn the_same_feature_held_still_is_confirmed_so_only_motion_separates_them() {
        let map = vmap(VDEPTH);
        let (still, _) = vjudge(&map, &vframes_moving(VDEPTH, 0));
        assert_eq!(
            still.outcome,
            SiteOutcome::Confirmed,
            "zero-travel control must fire (depth {:.4}, p {:.4}, presence {:.2})",
            still.depth,
            still.p,
            still.presence
        );
        assert!(still.presence >= vparams().presence_bar);
    }

    /// The amplitude comes from the frames, not from the map.
    ///
    /// A mote **twice as deep** as the map remembers -- which is what a smaller
    /// aperture does, MEASURED at 1.91x across ten real stacks -- must produce a
    /// stronger correction than the map alone would have applied, and must land
    /// near zero residual rather than 6.6 points short of it.
    #[test]
    fn the_correction_scales_to_the_depth_the_frames_show_not_the_map() {
        let p = vparams();
        let map = vmap(VDEPTH);
        let deep = 0.145; // ~1.8x the map's depth, as f/8 reads against an f/5.6 map
        let mut frames = vframes_fixed(deep);
        let (v, _) = vjudge(&map, &frames);
        assert_eq!(v.outcome, SiteOutcome::Confirmed);
        assert!(
            v.scale > 1.3,
            "a deeper mote must scale the profile up, got {:.3}",
            v.scale
        );
        let scaled = map.validated(&[v], p.core_radius).unwrap();
        let map_peak = map.dust.iter().fold(1f32, |a, d| a.max(d.gain));
        let new_peak = scaled.dust.iter().fold(1f32, |a, d| a.max(d.gain));
        assert!(
            new_peak > map_peak * 1.05,
            "scaled peak gain {new_peak:.4} must exceed the map's {map_peak:.4}"
        );
        for f in frames.iter_mut() {
            scaled
                .apply(
                    f,
                    VW,
                    (0, 0, VW, VH),
                    BLACK,
                    f32::from(WHITE),
                    1.0,
                    Correction::DUST,
                    HotFloor::CENSUS,
                )
                .unwrap();
        }
        let (after, _) = vjudge(&map, &frames);
        assert!(
            after.depth.abs() < 0.03,
            "scaling to the measured depth must clear the mote, left {:.4}",
            after.depth
        );

        // And the counterfactual: the map's own gains leave most of it behind.
        let mut unscaled = vframes_fixed(deep);
        for f in unscaled.iter_mut() {
            map.apply(
                f,
                VW,
                (0, 0, VW, VH),
                BLACK,
                f32::from(WHITE),
                1.0,
                Correction::DUST,
                HotFloor::CENSUS,
            )
            .unwrap();
        }
        let (map_gain_only, _) = vjudge(&map, &unscaled);
        assert!(
            map_gain_only.depth.abs() > after.depth.abs() * 2.0,
            "map-gain correction should leave much more behind ({:.4}) than \
             frame-scaled ({:.4})",
            map_gain_only.depth,
            after.depth
        );
    }

    /// A depth the frames read as *shallower* than the map must scale the
    /// correction **down**, not apply the map's gain and overshoot into a
    /// bright spot. Manufacturing the inverse defect is the same failure as
    /// manufacturing the defect.
    #[test]
    fn a_shallower_mote_than_the_map_remembers_scales_the_correction_down() {
        let p = vparams();
        let map = vmap(VDEPTH);
        let shallow = 0.035;
        let mut frames = vframes_fixed(shallow);
        let (v, _) = vjudge(&map, &frames);
        assert_eq!(v.outcome, SiteOutcome::Confirmed);
        assert!(v.scale < 0.75, "must scale down, got {:.3}", v.scale);
        let scaled = map.validated(&[v], p.core_radius).unwrap();
        for f in frames.iter_mut() {
            scaled
                .apply(
                    f,
                    VW,
                    (0, 0, VW, VH),
                    BLACK,
                    f32::from(WHITE),
                    1.0,
                    Correction::DUST,
                    HotFloor::CENSUS,
                )
                .unwrap();
        }
        let (after, _) = vjudge(&map, &frames);
        assert!(
            after.depth < 0.02,
            "scaling down must not overshoot into a bright spot, left {:.4}",
            after.depth
        );
    }

    /// The verdicts partition, and the buckets are distinguishable.
    #[test]
    fn every_nominated_site_lands_in_exactly_one_counted_bucket() {
        let map = vmap(VDEPTH);
        let clean: Vec<Vec<u16>> = (0..8).map(|k| vframe(700 + k, 18.0)).collect();
        for (name, frames) in [
            ("fixed", vframes_fixed(VDEPTH)),
            ("clean", clean),
            ("moving", vframes_moving(VDEPTH, 12)),
        ] {
            let (_, rep) = vjudge(&map, &frames);
            assert!(rep.check_partition(), "{name}: {rep:?}");
            assert_eq!(rep.examined, 1, "{name}");
            assert_eq!(rep.frames, 8, "{name}");
        }
    }

    /// Motes are the unit of decision, not quads.
    #[test]
    fn dust_quads_group_into_connected_motes() {
        let mut m = DefectMap::empty(VW, VH, "x");
        for (cx, cy) in [(40usize, 40usize), (200usize, 200usize)] {
            for qy in cy - 3..=cy + 3 {
                for qx in cx - 3..=cx + 3 {
                    m.dust.push(DustQuad {
                        px: qx as u32,
                        py: qy as u32,
                        gain: 1.05,
                    });
                }
            }
        }
        m.dust.sort_by_key(|d| (d.py, d.px));
        let motes = m.motes(4);
        assert_eq!(motes.len(), 2, "two separated blobs are two motes");
        assert_eq!((motes[0].cx, motes[0].cy), (40, 40));
        assert_eq!((motes[1].cx, motes[1].cy), (200, 200));
        assert_eq!(
            motes.iter().map(|x| x.quads.len()).sum::<usize>(),
            m.dust.len(),
            "every quad belongs to exactly one mote"
        );
        let want = 1.0 / 1.05f64 - 1.0;
        assert!(
            (motes[0].map_depth - want).abs() < 1e-6,
            "map_depth must agree with the gains it describes: {:.6} vs {want:.6}",
            motes[0].map_depth
        );
    }

    /// The embedded canonical map parses, and is gated on the body.
    #[test]
    fn the_embedded_map_parses_and_only_matches_the_body_it_was_measured_on() {
        let m = DefectMap::from_text(EMBEDDED_DUST_MAP).expect("embedded map must parse");
        assert_eq!(m.camera, "ILCE-7CM2");
        assert_eq!(m.coords, CoordSpace::Active);
        assert_eq!(m.hot.len(), 0, "the hot arm is a measured null on this body");
        assert_eq!(m.dust.len(), 1135);
        assert_eq!((m.sensor_w, m.sensor_h), (7032, 4688));
        let motes = m.motes(8);
        assert_eq!(motes.len(), 2, "this body has two confirmed motes");
        // Against the depths BUILD-DEFECT.md S2 published from the flats:
        // -3.63% and -8.24%.
        let depths: Vec<f64> = motes.iter().map(|x| x.map_depth).collect();
        assert!(
            depths.iter().any(|d| (d + 0.0363).abs() < 0.005),
            "mote 1 should read near -3.63%, got {depths:?}"
        );
        assert!(
            depths.iter().any(|d| (d + 0.0824).abs() < 0.005),
            "mote 2 should read near -8.24%, got {depths:?}"
        );
        assert!(DefectMap::embedded_for("ILCE-7CM2").is_some());
        assert!(
            DefectMap::embedded_for("ILCE-7M4").is_none(),
            "a map is a statement about one piece of silicon"
        );
    }

    // -----------------------------------------------------------------
    // The coordinate-space key
    // -----------------------------------------------------------------

    /// A map that does not say which array its coordinates index is REFUSED.
    ///
    /// The alternative is guessing, and guessing wrong produced a +54.8%
    /// reading -- a dust mote reported as a bright spot -- when this module's
    /// own self-validation was built. A loud failure on a v1 map that was
    /// probably fine is cheaper than a silent 54.8% error on one that was not.
    #[test]
    fn a_map_without_a_coords_key_errors_rather_than_guessing_the_origin() {
        let m = DefectMap::empty(4, 4, "x");
        let text = m.to_text();
        let cut: String = text
            .lines()
            .filter(|l| !l.starts_with("coords"))
            .collect::<Vec<_>>()
            .join("\n");
        match DefectMap::from_text(&cut) {
            Err(DefectMapError::MissingKey { key }) => assert_eq!(key, "coords"),
            other => panic!("expected MissingKey coords, got {other:?}"),
        }
    }

    /// And a typo in it is an error, not a fallback to the common case.
    #[test]
    fn a_typod_coords_value_errors_rather_than_falling_back_to_the_default() {
        for bad in ["visible", "Active", "raw_image", ""] {
            let text = format!(
                "{MAGIC} {VERSION}\ncamera x\nsensor 4 4\ncovered 4 4\ncoords {bad}\n\
                 aperture unknown\nhot 0\ndust 0\nend\n"
            );
            match DefectMap::from_text(&text) {
                Err(DefectMapError::UnknownCoordSpace { found }) => assert_eq!(found, bad),
                other => panic!("coords {bad:?} should be refused, got {other:?}"),
            }
        }
    }

    /// The key is **consumed**, not merely carried: the two spaces correct
    /// different photosites.
    ///
    /// A `coords` key that parsed and was then ignored would be worth exactly
    /// as much as no key at all, and would read as a fix in the diff. This is
    /// the test that fails if [`DefectMap::apply`] stops branching on it.
    #[test]
    fn the_coords_key_changes_which_photosites_are_corrected() {
        const S: usize = 24; // stride, wider than the active area
        const A: usize = 16; // active width and height
        const OFF: usize = 4; // optical-black border
        let base = vec![LEVEL; S * S];

        let mut active_map = DefectMap::empty(A, A, "x");
        active_map.dust.push(DustQuad {
            px: 1,
            py: 1,
            gain: 1.2,
        });
        let mut full_map = active_map.clone();
        full_map.coords = CoordSpace::Full;

        let go = |m: &DefectMap| -> Vec<u16> {
            let mut v = base.clone();
            m.apply(
                &mut v,
                S,
                (OFF, OFF, A, A),
                BLACK,
                f32::from(WHITE),
                1.0,
                Correction::DUST,
                HotFloor::CENSUS,
            )
            .unwrap();
            v
        };
        let (a, b) = (go(&active_map), go(&full_map));
        let moved = |v: &[u16]| -> Vec<usize> {
            v.iter()
                .enumerate()
                .filter(|(i, x)| **x != base[*i])
                .map(|(i, _)| i)
                .collect()
        };
        let (ma, mb) = (moved(&a), moved(&b));
        assert_eq!(ma.len(), 4, "one quad, four samples");
        assert_eq!(mb.len(), 4);
        assert_ne!(
            ma, mb,
            "active and full coordinate spaces must correct different samples"
        );
        assert_eq!(ma[0], (OFF + 2) * S + OFF + 2, "active: offset by the origin");
        assert_eq!(mb[0], 2 * S + 2, "full: not offset");
    }

    /// Round-tripping preserves the key.
    #[test]
    fn the_coords_key_round_trips() {
        for space in [CoordSpace::Active, CoordSpace::Full] {
            let mut m = DefectMap::empty(8, 8, "x");
            m.coords = space;
            let back = DefectMap::from_text(&m.to_text()).expect("round trip");
            assert_eq!(back.coords, space);
            assert_eq!(back, m);
        }
    }

    /// `depth_scale` is the identity when the frames agree with the map, and is
    /// monotone in the measured depth. A degenerate map depth returns 1.0
    /// rather than dividing by zero.
    #[test]
    fn the_amplitude_scale_is_the_identity_when_map_and_frames_agree() {
        assert!((depth_scale(-0.08, -0.08) - 1.0).abs() < 1e-9);
        assert!(depth_scale(-0.16, -0.08) > 1.0);
        assert!(depth_scale(-0.04, -0.08) < 1.0);
        assert_eq!(depth_scale(-0.08, 0.0), 1.0, "no divide by zero");
        assert_eq!(depth_scale(0.0, -0.08), 1.0);
        let mut last = 0.0;
        for k in 1..20 {
            let s = depth_scale(-(k as f64) * 0.01, -0.08);
            assert!(s > last, "must increase with measured depth");
            last = s;
        }
    }
}

