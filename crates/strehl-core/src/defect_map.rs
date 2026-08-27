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
pub const VERSION: u32 = 1;

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
         to a {got_w}x{got_h} one; a sensor-coordinate map applied to a different \
         geometry corrects the wrong photosites"
    )]
    SensorMismatch {
        want_w: usize,
        want_h: usize,
        got_w: usize,
        got_h: usize,
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
    /// An empty map for a given geometry. Applying it is a no-op that reports
    /// `examined: 0` in both arms, which is the point — a body with no
    /// calibration is distinguishable from a body with a clean one.
    pub fn empty(sensor_w: usize, sensor_h: usize, camera: &str) -> DefectMap {
        DefectMap {
            sensor_w,
            sensor_h,
            covered_w: sensor_w,
            covered_h: sensor_h,
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
    ///   [`DefectMapError::SensorMismatch`].
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
        if aw != self.sensor_w || ah != self.sensor_h {
            return Err(DefectMapError::SensorMismatch {
                want_w: self.sensor_w,
                want_h: self.sensor_h,
                got_w: aw,
                got_h: ah,
            });
        }
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
                let idx = (ay + y) * stride + ax + x;
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
                        let idx = (ay + py + dy) * stride + ax + px + dx;
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
            "{MAGIC} {VERSION}\ncamera x\nsensor 4 4\ncovered 4 4\naperture unknown\n\
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
            "{MAGIC} {VERSION}\ncamera x\nsensor 40 40\ncovered 40 40\naperture 5.6\n\
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
    fn a_map_for_another_sensor_geometry_is_refused_rather_than_applied() {
        let m = DefectMap::empty(W, H, "x");
        let mut f = clean_frame(1, 8.0);
        let err = m
            .apply(
                &mut f,
                W,
                (0, 0, W - 2, H),
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
}

