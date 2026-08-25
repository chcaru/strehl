//! The warp sidecar: a per-frame geometric registration, stored beside a
//! bracket as inspectable text, and the gather that consumes it.
//!
//! # Why a sidecar
//!
//! M86 measured that the shipped merge combines frames with no geometric
//! registration at all, and that the owner's real 299-frame brackets drift by
//! up to **299.2 plane px** corner-to-corner (M86 fact P2). Solving that drift
//! costs ~55 s on a 299-frame stack (M86 §8), which is far too expensive to
//! repeat on every merge, and the solve is a *calibration* — the same class of
//! artefact as every other profile this project keeps as data. So the solve
//! writes a sidecar and the merge reads one.
//!
//! # The transform convention, and the one trap in it
//!
//! Every [`Similarity`] stored here is a **placement**: the transform from the
//! reference frame's coordinates to that frame's coordinates. This is exactly
//! `align::Placement[k]`, which `align.rs` documents as "a per-frame transform
//! relative to frame 0".
//!
//! [`Resampler::sample`] and [`gather_checked`] are **pulls**: they map a
//! destination coordinate to a source coordinate. A placement is already in
//! that direction, so registering frame `k` is
//!
//! ```text
//! gather_checked(frame_k, map.placement(k)?, geom, resampler, dst, cover)
//! ```
//!
//! with **no inversion anywhere**. Inverting is the single most likely bug in
//! a consumer of this module and it is silent — an inverted warp still
//! produces a plausible image, just misregistered by twice the drift. That is
//! why [`gather_checked`] is provided at all rather than leaving each consumer
//! to compose the call: so the direction is decided once, here, under test.
//!
//! # What the sidecar must carry
//!
//! A consumer has to be able to tell a good solve from a bad one, because M86
//! measured that they differ by a factor of 33 across real stacks: held-out
//! error runs from **0.353 px** on `109MSDCF` to **11.562 px** on `bee-3-cpl`
//! (M86 facts P4–P9). Those are different products and a merge should be able
//! to act on the difference. So [`Provenance`] carries the held-out error, the
//! cycle-consistency floor of the edge set that produced it, and the strategy
//! name, alongside enough stack identity to detect being pointed at the wrong
//! bracket.
//!
//! # Refusal is not identity
//!
//! M86 measured refusal rates from 0.0% to 47.5% across real stacks (M86 §7).
//! A refused frame is **not** a frame whose warp happens to be the identity —
//! it is a frame whose registration is unknown, and merging it unregistered is
//! precisely the defect this module exists to fix. [`FrameWarp`] therefore has
//! two distinct states and there is deliberately **no** accessor that turns a
//! refusal into a transform. A consumer must handle [`FrameWarp::Refused`]
//! explicitly, which in practice means dropping the frame.

use std::collections::BTreeMap;
use std::fmt::Write as _;
use std::path::Path;

use crate::align::{PlaneRef, Resampler, Similarity, SimilarityParams};
use crate::plane::PlaneGeometry;

/// Format magic. Bumping the version is a breaking change to the text format.
pub const MAGIC: &str = "strehl-warpmap";
/// Current sidecar format version.
pub const VERSION: u32 = 1;

/// Everything that can go wrong reading or building a sidecar.
///
/// Every variant is a **refusal**, never a degraded map: a truncated file is an
/// error and never a short warp list, and a stack mismatch is an error and
/// never a best-effort application of the wrong warps.
#[derive(Debug, thiserror::Error)]
pub enum WarpMapError {
    #[error("not a strehl warp map: expected magic {MAGIC:?}, found {found:?}")]
    BadMagic { found: String },

    #[error("unsupported warp map version {found} (this build understands {VERSION})")]
    BadVersion { found: u32 },

    #[error("warp map header is missing required key {key:?}")]
    MissingKey { key: &'static str },

    #[error("warp map key {key:?} has unparsable value {value:?}")]
    BadValue { key: String, value: String },

    #[error("warp map line {line} is malformed: {detail}")]
    BadLine { line: usize, detail: String },

    #[error(
        "warp map is truncated: header declares {declared} frames, {found} were read, \
         and the terminating `end` record is {}",
        if *saw_end { "present but disagrees" } else { "absent" }
    )]
    Truncated {
        declared: usize,
        found: usize,
        saw_end: bool,
    },

    #[error("warp map has a duplicate record for frame {index}")]
    DuplicateFrame { index: usize },

    #[error("warp map declares {declared} frames but has a record for frame {index}")]
    FrameOutOfRange { declared: usize, index: usize },

    #[error(
        "this warp map was fitted on stack {want_name:?} (digest {want:016x}, {want_frames} frames) \
         but was applied to {got_name:?} (digest {got:016x}, {got_frames} frames)"
    )]
    StackMismatch {
        want: u64,
        got: u64,
        want_name: String,
        got_name: String,
        want_frames: usize,
        got_frames: usize,
    },

    #[error("warp map plane is {want_w}x{want_h} but the frame being gathered is {got_w}x{got_h}")]
    GeometryMismatch {
        want_w: usize,
        want_h: usize,
        got_w: usize,
        got_h: usize,
    },

    #[error("frame {index} was refused by the alignment solve: {reason}")]
    FrameRefused { index: usize, reason: String },

    #[error("no warp is recorded for frame {index} ({frames} frames in the map)")]
    NoSuchFrame { index: usize, frames: usize },

    #[error("io error on {path:?}: {source}")]
    Io {
        path: String,
        #[source]
        source: std::io::Error,
    },
}

/// Why the solve could not place a frame.
///
/// Free text rather than an enum on purpose: the estimator's own failure modes
/// live in `align.rs` and are still moving, and a sidecar written by an older
/// build must stay readable by a newer one. The consumer's contract is only
/// that a refusal is *not* a transform.
pub type RefusalReason = String;

/// One frame's registration state.
///
/// The two states are deliberately not collapsible. See the module docs.
#[derive(Clone, Debug, PartialEq)]
pub enum FrameWarp {
    /// The frame was registered: this is its placement, reference -> frame.
    Placed(Similarity),
    /// The frame could not be registered and the merge must drop it.
    Refused(RefusalReason),
}

impl FrameWarp {
    /// The placement, or `None` if this frame was refused.
    ///
    /// There is **no** `unwrap_or(IDENTITY)` convenience anywhere in this
    /// module, and adding one would defeat the point: an identity warp for an
    /// unregistered frame is the exact defect M86 measured.
    #[inline]
    pub fn placed(&self) -> Option<Similarity> {
        match self {
            FrameWarp::Placed(t) => Some(*t),
            FrameWarp::Refused(_) => None,
        }
    }

    #[inline]
    pub fn is_refused(&self) -> bool {
        matches!(self, FrameWarp::Refused(_))
    }
}

/// Identity of the bracket a sidecar was fitted on.
///
/// # Why filenames alone are not enough — MEASURED
///
/// `bee-2-cpl` and `bee-3-cpl` are the same subject shot at ISO 400 and
/// ISO 100, both 299 frames, both the same sensor geometry. Their frame
/// **filenames are byte-identical** (`DSC00001.ARW` …), so a digest over names,
/// a frame count and a plane size all agree between them while their warps do
/// not. Their file **sizes** differ (37,552,128 vs 39,362,560 bytes for frame
/// 1), because the raw compression tracks noise. The digest therefore mixes
/// name **and** size for every frame, which separates them without decoding
/// anything.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct StackIdentity {
    /// Directory name of the bracket, for human diagnostics only.
    pub name: String,
    /// FNV-1a over `(file name, file size)` for every frame, in listed order.
    pub digest: u64,
    /// Number of frames the digest covers.
    pub frames: usize,
}

impl StackIdentity {
    /// Build an identity from an ordered list of `(file name, byte size)`.
    ///
    /// The caller supplies the order; it must be the same order the warps are
    /// indexed in. Only the file **name** is mixed, never the full path, so a
    /// sidecar survives the bracket being moved or the drive being remounted.
    pub fn from_entries<S: AsRef<str>>(name: &str, entries: &[(S, u64)]) -> Self {
        // FNV-1a, 64-bit. Chosen because it is four lines of std-only code and
        // this is a mismatch check, not a security boundary: the threat is
        // pointing a sidecar at the wrong directory, not an adversary.
        const OFFSET: u64 = 0xcbf2_9ce4_8422_2325;
        const PRIME: u64 = 0x0000_0100_0000_01b3;
        let mut h = OFFSET;
        let mut mix = |bytes: &[u8]| {
            for &b in bytes {
                h ^= b as u64;
                h = h.wrapping_mul(PRIME);
            }
        };
        for (n, size) in entries {
            mix(n.as_ref().as_bytes());
            mix(&[0]);
            mix(&size.to_le_bytes());
            mix(&[0]);
        }
        Self {
            name: name.to_string(),
            digest: h,
            frames: entries.len(),
        }
    }

    /// Build an identity by listing a directory of frames on disk.
    ///
    /// `paths` must already be in the order the warps are indexed in.
    pub fn from_paths(name: &str, paths: &[impl AsRef<Path>]) -> Result<Self, WarpMapError> {
        let mut entries: Vec<(String, u64)> = Vec::with_capacity(paths.len());
        for p in paths {
            let p = p.as_ref();
            let md = std::fs::metadata(p).map_err(|source| WarpMapError::Io {
                path: p.display().to_string(),
                source,
            })?;
            let fname = p
                .file_name()
                .map(|s| s.to_string_lossy().into_owned())
                .unwrap_or_default();
            entries.push((fname, md.len()));
        }
        Ok(Self::from_entries(name, &entries))
    }

    /// Refuse unless `other` is the same bracket.
    pub fn check(&self, other: &StackIdentity) -> Result<(), WarpMapError> {
        if self.digest == other.digest && self.frames == other.frames {
            return Ok(());
        }
        Err(WarpMapError::StackMismatch {
            want: self.digest,
            got: other.digest,
            want_name: self.name.clone(),
            got_name: other.name.clone(),
            want_frames: self.frames,
            got_frames: other.frames,
        })
    }
}

/// How good this solve is, and what produced it.
///
/// A consumer that wants to gate on quality reads [`Provenance::heldout_px`]
/// against its own bar. M86's `T_usable` was 4.0 px; the shipped solves ranged
/// 0.353–11.562 px (M86 facts P4–P9), so this is a live distinction and not a
/// formality.
#[derive(Clone, Debug, PartialEq)]
pub struct Provenance {
    /// Which bracket the solve was fitted on.
    pub stack: StackIdentity,
    /// Name of the strategy that produced the placements, e.g. `S3-ba-unit`.
    pub strategy: String,
    /// Median held-out corner error, plane px. `None` if it was not measured.
    ///
    /// **Held-out, not fit.** A fit error on a global solve is not a measure of
    /// anything a consumer cares about.
    pub heldout_px: Option<f64>,
    /// Cycle-consistency floor of the edge set, plane px. `None` if unmeasured.
    ///
    /// This is the noise floor the estimator could not have beaten: on
    /// `bee-3-cpl` M86 measured a floor of 9.07 px under an 11.562 px solve, so
    /// most of that error is the *edges*, not the solve.
    pub cycle_floor_px: Option<f64>,
    /// Index of the frame all placements are relative to.
    pub reference: usize,
    /// Free-form note, e.g. the milestone that wrote it.
    pub note: String,
}

/// A per-frame warp sidecar.
#[derive(Clone, Debug, PartialEq)]
pub struct WarpMap {
    provenance: Provenance,
    geometry: PlaneGeometry,
    resampler: Resampler,
    warps: Vec<FrameWarp>,
}

impl WarpMap {
    /// Build a map. `warps` is indexed by frame, in the same order as the
    /// entries the [`StackIdentity`] was built from.
    pub fn new(
        provenance: Provenance,
        geometry: PlaneGeometry,
        resampler: Resampler,
        warps: Vec<FrameWarp>,
    ) -> Self {
        Self {
            provenance,
            geometry,
            resampler,
            warps,
        }
    }

    #[inline]
    pub fn provenance(&self) -> &Provenance {
        &self.provenance
    }

    #[inline]
    pub fn geometry(&self) -> PlaneGeometry {
        self.geometry
    }

    /// The resampler the solve was validated with.
    ///
    /// See [`Self::set_resampler`] for how much this choice is actually
    /// evidenced.
    #[inline]
    pub fn resampler(&self) -> Resampler {
        self.resampler
    }

    /// Override the interpolator.
    ///
    /// # How evidenced is the default? Partly — read this before trusting it
    ///
    /// The default written by `strehl align` is [`Resampler::CatmullRom`].
    /// What is **MEASURED** is that it beats bilinear on a zero-defocus
    /// self-pair: M23 measured a bilinear gather reading `R = 0.372` where
    /// truth is 1.000, and `R = 0.965` with the resampler removed entirely
    /// (M23 facts 170/172/177); M86's C2 read **0.9997** on the same construct
    /// with Catmull-Rom (M86 §6.2).
    ///
    /// What is **NOT MEASURED** is any comparison of the two on real frames at
    /// merge time, and M86 measured a reason to care: on an interpolator-free
    /// ladder the estimator's gain is flat at 0.98 down to 0.042 px of corner
    /// motion, while the *same* motion planted **through** Catmull-Rom reads
    /// 0.29 — so this resampler, like bilinear, destroys most sub-pixel
    /// displacement. That is a cost paid on every gathered pixel and nobody has
    /// yet measured it on a real merge. The choice is swappable for exactly
    /// that reason.
    #[inline]
    pub fn set_resampler(&mut self, r: Resampler) {
        self.resampler = r;
    }

    #[inline]
    pub fn len(&self) -> usize {
        self.warps.len()
    }

    #[inline]
    pub fn is_empty(&self) -> bool {
        self.warps.is_empty()
    }

    #[inline]
    pub fn warps(&self) -> &[FrameWarp] {
        &self.warps
    }

    /// The state of frame `index`.
    #[inline]
    pub fn warp(&self, index: usize) -> Result<&FrameWarp, WarpMapError> {
        self.warps.get(index).ok_or(WarpMapError::NoSuchFrame {
            index,
            frames: self.warps.len(),
        })
    }

    /// The placement of frame `index`, refusing if the frame was refused.
    ///
    /// Use this when a missing frame is an error. Use [`Self::warp`] and match
    /// when a refusal should be handled by dropping the frame, which is what
    /// the merge should do.
    pub fn placement(&self, index: usize) -> Result<Similarity, WarpMapError> {
        match self.warp(index)? {
            FrameWarp::Placed(t) => Ok(*t),
            FrameWarp::Refused(reason) => Err(WarpMapError::FrameRefused {
                index,
                reason: reason.clone(),
            }),
        }
    }

    /// How many frames were registered.
    pub fn placed_count(&self) -> usize {
        self.warps.iter().filter(|w| !w.is_refused()).count()
    }

    /// How many frames the merge must drop.
    pub fn refused_count(&self) -> usize {
        self.warps.iter().filter(|w| w.is_refused()).count()
    }

    /// Refuse unless this sidecar belongs to `stack`.
    pub fn check_stack(&self, stack: &StackIdentity) -> Result<(), WarpMapError> {
        self.provenance.stack.check(stack)
    }
}

// ---------------------------------------------------------------------------
// gather
// ---------------------------------------------------------------------------

/// Gather `src` into the reference grid through placement `t`, dropping samples
/// that fall outside the source frame.
///
/// `t` is a **placement** — reference coordinates to source coordinates — so it
/// is passed exactly as stored, with **no inversion**. See the module docs.
///
/// Writes `f32::NAN` and `false` wherever the interpolator's support would
/// leave the source plane, rather than clamping. `align.rs` documents why in
/// [`Resampler::sample_checked`]: once frames are at different scales they no
/// longer cover the same field, and clamping smears the border pixel inward
/// into an artefact that grows with stack depth.
///
/// Returns the number of covered destination pixels.
pub fn gather_checked(
    src: PlaneRef<'_>,
    t: Similarity,
    geom: PlaneGeometry,
    resampler: Resampler,
    dst: &mut [f32],
    cover: &mut [bool],
) -> Result<usize, WarpMapError> {
    if src.width() != geom.width || src.height() != geom.height {
        return Err(WarpMapError::GeometryMismatch {
            want_w: geom.width,
            want_h: geom.height,
            got_w: src.width(),
            got_h: src.height(),
        });
    }
    assert_eq!(dst.len(), geom.pixels(), "destination is not plane-sized");
    assert_eq!(cover.len(), geom.pixels(), "coverage is not plane-sized");

    let (cx, cy) = (geom.width as f64 * 0.5, geom.height as f64 * 0.5);
    let mut covered = 0usize;
    for py in 0..geom.height {
        let lo = py * geom.width;
        let hi = lo + geom.width;
        let drow = &mut dst[lo..hi];
        let crow = &mut cover[lo..hi];
        for (px, (o, c)) in drow.iter_mut().zip(crow.iter_mut()).enumerate() {
            let (sx, sy) = t.apply_at(px as f64, py as f64, cx, cy);
            match resampler.sample_checked(src, sx, sy) {
                Some(v) => {
                    *o = v;
                    *c = true;
                    covered += 1;
                }
                None => {
                    *o = f32::NAN;
                    *c = false;
                }
            }
        }
    }
    Ok(covered)
}

/// [`gather_checked`] for a frame of a sidecar, refusing rather than
/// fabricating a transform for a refused frame.
pub fn gather_frame(
    map: &WarpMap,
    index: usize,
    src: PlaneRef<'_>,
    dst: &mut [f32],
    cover: &mut [bool],
) -> Result<usize, WarpMapError> {
    let t = map.placement(index)?;
    gather_checked(src, t, map.geometry(), map.resampler(), dst, cover)
}

// ---------------------------------------------------------------------------
// text format
// ---------------------------------------------------------------------------
//
// Line-oriented, one record per line, `#` for comments. Two properties drive
// the design:
//
//   * **Bit-exact round-trip.** Every f64 is written as its raw IEEE-754 bits
//     in hex, so a load-save-load cycle is byte-identical and a placement is
//     never silently rounded. The decimal value is written alongside, as a
//     comment field, so the file stays readable and diffable -- but it is the
//     hex that is parsed. A decimal-only format cannot round-trip f64 without
//     care and this is a calibration artefact, so it round-trips exactly.
//
//   * **Truncation is detectable.** The header declares the frame count and
//     the file ends with an `end <count>` record. A file cut short fails both
//     checks and raises `WarpMapError::Truncated`, never a short warp list.
//     This matters because a half-written sidecar is a realistic failure --
//     the writer runs for ~55 s on a 299-frame stack.

/// Write an f64 as its exact bit pattern.
fn f64_hex(v: f64) -> String {
    format!("{:016x}", v.to_bits())
}

/// Read an f64 back from its exact bit pattern.
fn hex_f64(s: &str, key: &str) -> Result<f64, WarpMapError> {
    u64::from_str_radix(s, 16)
        .map(f64::from_bits)
        .map_err(|_| WarpMapError::BadValue {
            key: key.to_string(),
            value: s.to_string(),
        })
}

/// Every resampler spelling this project accepts, in a stable order, for
/// `--help` text and for the error a bad name earns.
///
/// **One vocabulary, one list.** `lanczos2` shipped as a [`Resampler`] variant
/// and as a name this module round-trips, while the command line kept a
/// *second* match of its own that never listed it — so the variant was
/// reachable by hand-editing a sidecar and from no command line at all
/// (`docs/research/M118-resampler.md` §7, Y6). Two mappings for one vocabulary
/// is how that happens, so the CLI now parses through
/// [`resampler_from_name`] and this is the only list.
pub const RESAMPLER_NAMES: [&str; 5] =
    ["nearest", "bilinear", "catmull-rom", "lanczos2", "lanczos3"];

/// The sidecar spelling of a resampler. Round-trips with
/// [`resampler_from_name`], which `every_resampler_survives_a_name_round_trip`
/// asserts.
///
/// The match is exhaustive, so a new [`Resampler`] variant cannot be added
/// without being named here.
pub fn resampler_name(r: Resampler) -> &'static str {
    match r {
        Resampler::Nearest => "nearest",
        Resampler::Bilinear => "bilinear",
        Resampler::CatmullRom => "catmull-rom",
        Resampler::Lanczos2 => "lanczos2",
        Resampler::Lanczos3 => "lanczos3",
    }
}

/// The resampler a sidecar line or a command line named, or `None` when the
/// name is not one of [`RESAMPLER_NAMES`].
///
/// `None` is the *only* answer for an unrecognised name. Callers must refuse:
/// falling back to a default here would render a kernel nobody asked for and
/// make every A/B run through it unfalsifiable.
pub fn resampler_from_name(s: &str) -> Option<Resampler> {
    match s {
        "nearest" => Some(Resampler::Nearest),
        "bilinear" => Some(Resampler::Bilinear),
        "catmull-rom" => Some(Resampler::CatmullRom),
        "lanczos2" => Some(Resampler::Lanczos2),
        "lanczos3" => Some(Resampler::Lanczos3),
        _ => None,
    }
}

/// Escape a value so it survives a line-oriented format.
fn esc(s: &str) -> String {
    s.replace('\\', "\\\\")
        .replace('\n', "\\n")
        .replace('\r', "\\r")
}

fn unesc(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    let mut it = s.chars();
    while let Some(c) = it.next() {
        if c != '\\' {
            out.push(c);
            continue;
        }
        match it.next() {
            Some('n') => out.push('\n'),
            Some('r') => out.push('\r'),
            Some('\\') => out.push('\\'),
            Some(other) => out.push(other),
            None => out.push('\\'),
        }
    }
    out
}

impl WarpMap {
    /// Render the sidecar as text.
    pub fn to_text(&self) -> String {
        let p = &self.provenance;
        let mut s = String::with_capacity(128 + self.warps.len() * 96);
        let _ = writeln!(s, "{MAGIC} {VERSION}");
        let _ = writeln!(
            s,
            "# a warp sidecar: per-frame placements, reference -> frame."
        );
        let _ = writeln!(
            s,
            "# `a_re a_im b_re b_im` are f64 bit patterns; the trailing"
        );
        let _ = writeln!(s, "# decimals are a human aid and are NOT parsed.");
        let _ = writeln!(s, "stack-name {}", esc(&p.stack.name));
        let _ = writeln!(s, "stack-digest {:016x}", p.stack.digest);
        let _ = writeln!(s, "frames {}", self.warps.len());
        let _ = writeln!(s, "plane {}x{}", self.geometry.width, self.geometry.height);
        let _ = writeln!(s, "reference {}", p.reference);
        let _ = writeln!(s, "strategy {}", esc(&p.strategy));
        let _ = writeln!(s, "resampler {}", resampler_name(self.resampler));
        match p.heldout_px {
            Some(v) => {
                let _ = writeln!(s, "heldout-px {} # {v:.4}", f64_hex(v));
            }
            None => {
                let _ = writeln!(s, "heldout-px none");
            }
        }
        match p.cycle_floor_px {
            Some(v) => {
                let _ = writeln!(s, "cycle-floor-px {} # {v:.4}", f64_hex(v));
            }
            None => {
                let _ = writeln!(s, "cycle-floor-px none");
            }
        }
        let _ = writeln!(s, "note {}", esc(&p.note));
        let _ = writeln!(s, "# idx state a_re a_im b_re b_im | scale-1, rot, dx, dy");
        for (i, w) in self.warps.iter().enumerate() {
            match w {
                FrameWarp::Placed(t) => {
                    let q: SimilarityParams = t.to_params();
                    let _ = writeln!(
                        s,
                        "{i} placed {} {} {} {} # g={:+.6e} rot={:+.6e} dx={:+.4} dy={:+.4}",
                        f64_hex(t.a.re),
                        f64_hex(t.a.im),
                        f64_hex(t.b.re),
                        f64_hex(t.b.im),
                        q.g,
                        q.rot,
                        q.ax,
                        q.ay
                    );
                }
                FrameWarp::Refused(reason) => {
                    let _ = writeln!(s, "{i} refused {}", esc(reason));
                }
            }
        }
        let _ = writeln!(s, "end {}", self.warps.len());
        s
    }

    /// Parse a sidecar.
    pub fn from_text(text: &str) -> Result<Self, WarpMapError> {
        let mut header: BTreeMap<String, String> = BTreeMap::new();
        let mut records: BTreeMap<usize, FrameWarp> = BTreeMap::new();
        let mut declared: Option<usize> = None;
        let mut saw_end: Option<usize> = None;

        for (ln, raw) in text.lines().enumerate() {
            let line = raw.trim();
            if line.is_empty() || line.starts_with('#') {
                continue;
            }
            let (head, rest) = match line.split_once(' ') {
                Some((h, r)) => (h, r.trim()),
                None => (line, ""),
            };

            if ln == 0 || head == MAGIC {
                if head != MAGIC {
                    return Err(WarpMapError::BadMagic {
                        found: head.to_string(),
                    });
                }
                let v: u32 = rest.parse().map_err(|_| WarpMapError::BadValue {
                    key: "version".into(),
                    value: rest.to_string(),
                })?;
                if v != VERSION {
                    return Err(WarpMapError::BadVersion { found: v });
                }
                continue;
            }

            if head == "end" {
                let n: usize = rest
                    .split_whitespace()
                    .next()
                    .unwrap_or("")
                    .parse()
                    .map_err(|_| WarpMapError::BadValue {
                        key: "end".into(),
                        value: rest.to_string(),
                    })?;
                saw_end = Some(n);
                continue;
            }

            if let Ok(idx) = head.parse::<usize>() {
                let (state, tail) = match rest.split_once(' ') {
                    Some((s, t)) => (s, t.trim()),
                    None => (rest, ""),
                };
                let w = match state {
                    "refused" => FrameWarp::Refused(unesc(tail)),
                    "placed" => {
                        let f: Vec<&str> = tail
                            .split('#')
                            .next()
                            .unwrap_or("")
                            .split_whitespace()
                            .collect();
                        if f.len() < 4 {
                            return Err(WarpMapError::BadLine {
                                line: ln + 1,
                                detail: format!("`placed` needs 4 hex fields, found {}", f.len()),
                            });
                        }
                        FrameWarp::Placed(Similarity {
                            a: crate::align::Cx::new(
                                hex_f64(f[0], "a_re")?,
                                hex_f64(f[1], "a_im")?,
                            ),
                            b: crate::align::Cx::new(
                                hex_f64(f[2], "b_re")?,
                                hex_f64(f[3], "b_im")?,
                            ),
                        })
                    }
                    other => {
                        return Err(WarpMapError::BadLine {
                            line: ln + 1,
                            detail: format!("unknown frame state {other:?}"),
                        });
                    }
                };
                if records.insert(idx, w).is_some() {
                    return Err(WarpMapError::DuplicateFrame { index: idx });
                }
                continue;
            }

            if head == "frames" {
                declared = Some(rest.parse().map_err(|_| WarpMapError::BadValue {
                    key: "frames".into(),
                    value: rest.to_string(),
                })?);
            }
            header.insert(head.to_string(), rest.to_string());
        }

        let need = |k: &'static str| -> Result<String, WarpMapError> {
            header
                .get(k)
                .cloned()
                .ok_or(WarpMapError::MissingKey { key: k })
        };

        let declared = declared.ok_or(WarpMapError::MissingKey { key: "frames" })?;

        // Truncation check, before anything is handed back. A file cut short
        // fails here rather than yielding a short map.
        if saw_end != Some(declared) || records.len() != declared {
            return Err(WarpMapError::Truncated {
                declared,
                found: records.len(),
                saw_end: saw_end.is_some(),
            });
        }
        if let Some((&idx, _)) = records.iter().next_back()
            && idx >= declared
        {
            return Err(WarpMapError::FrameOutOfRange {
                declared,
                index: idx,
            });
        }

        let plane = need("plane")?;
        let (pw, ph) = plane.split_once('x').ok_or(WarpMapError::BadValue {
            key: "plane".into(),
            value: plane.clone(),
        })?;
        let geometry = PlaneGeometry {
            width: pw.trim().parse().map_err(|_| WarpMapError::BadValue {
                key: "plane".into(),
                value: plane.clone(),
            })?,
            height: ph.trim().parse().map_err(|_| WarpMapError::BadValue {
                key: "plane".into(),
                value: plane.clone(),
            })?,
        };

        let digest_s = need("stack-digest")?;
        let digest =
            u64::from_str_radix(digest_s.trim(), 16).map_err(|_| WarpMapError::BadValue {
                key: "stack-digest".into(),
                value: digest_s.clone(),
            })?;

        let opt = |k: &'static str| -> Result<Option<f64>, WarpMapError> {
            match header.get(k) {
                None => Ok(None),
                Some(v) => {
                    let tok = v.split('#').next().unwrap_or("").trim();
                    if tok == "none" || tok.is_empty() {
                        Ok(None)
                    } else {
                        hex_f64(tok, k).map(Some)
                    }
                }
            }
        };

        let resampler_s = need("resampler")?;
        let resampler = resampler_from_name(resampler_s.trim()).ok_or(WarpMapError::BadValue {
            key: "resampler".into(),
            value: resampler_s.clone(),
        })?;

        let provenance = Provenance {
            stack: StackIdentity {
                name: unesc(&need("stack-name")?),
                digest,
                frames: declared,
            },
            strategy: unesc(&need("strategy")?),
            heldout_px: opt("heldout-px")?,
            cycle_floor_px: opt("cycle-floor-px")?,
            reference: need("reference")?
                .trim()
                .parse()
                .map_err(|_| WarpMapError::BadValue {
                    key: "reference".into(),
                    value: "?".into(),
                })?,
            note: header.get("note").map(|s| unesc(s)).unwrap_or_default(),
        };

        let warps = (0..declared)
            .map(|i| {
                records.remove(&i).ok_or(WarpMapError::NoSuchFrame {
                    index: i,
                    frames: declared,
                })
            })
            .collect::<Result<Vec<_>, _>>()?;

        Ok(WarpMap {
            provenance,
            geometry,
            resampler,
            warps,
        })
    }

    /// Write the sidecar to a file.
    pub fn save(&self, path: impl AsRef<Path>) -> Result<(), WarpMapError> {
        let path = path.as_ref();
        std::fs::write(path, self.to_text()).map_err(|source| WarpMapError::Io {
            path: path.display().to_string(),
            source,
        })
    }

    /// Read a sidecar from a file.
    pub fn load(path: impl AsRef<Path>) -> Result<Self, WarpMapError> {
        let path = path.as_ref();
        let text = std::fs::read_to_string(path).map_err(|source| WarpMapError::Io {
            path: path.display().to_string(),
            source,
        })?;
        Self::from_text(&text)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// The real CFA plane of the reference rig, so that every plane-px figure
    /// asserted here is directly comparable to the ones M86 reports.
    fn rig_geom() -> PlaneGeometry {
        PlaneGeometry {
            width: 3516,
            height: 2344,
        }
    }

    fn ident(name: &str) -> StackIdentity {
        StackIdentity::from_entries(
            name,
            &[
                ("DSC00001.ARW", 37_552_128u64),
                ("DSC00002.ARW", 37_556_224),
            ],
        )
    }

    fn sim(g: f64, rot: f64, ax: f64, ay: f64) -> Similarity {
        Similarity::from_params(SimilarityParams { ax, ay, g, rot })
    }

    fn demo_map() -> WarpMap {
        let warps = vec![
            FrameWarp::Placed(Similarity::IDENTITY),
            FrameWarp::Placed(sim(1.234_567_890_123e-4, -2.5e-5, 3.75, -1.125)),
            FrameWarp::Refused("CoarseStageFailed { level: 0 }".to_string()),
            FrameWarp::Placed(sim(-7.3e-4, 1.1e-6, -12.5, 44.25)),
        ];
        WarpMap::new(
            Provenance {
                stack: StackIdentity {
                    frames: 4,
                    ..ident("bee-3-cpl")
                },
                strategy: "S3-ba-unit".into(),
                heldout_px: Some(11.562),
                cycle_floor_px: Some(9.07),
                reference: 0,
                note: "M86b".into(),
            },
            rig_geom(),
            Resampler::CatmullRom,
            warps,
        )
    }

    // -- W1: round-trip -----------------------------------------------------

    /// `RESAMPLER_NAMES` is what a user is *told to type*, so a variant missing
    /// from it is a variant nobody can reach — which is exactly what happened
    /// to `lanczos2` (M118 §7, Y6: shipped, round-tripping, and unreachable
    /// from any command line).
    ///
    /// The compile-time half of the guard is [`resampler_name`]'s exhaustive
    /// match; this is the half that catches a variant named but not listed.
    #[test]
    fn every_listed_resampler_name_maps_to_a_distinct_variant() {
        let mut seen = Vec::new();
        for name in RESAMPLER_NAMES {
            let r = resampler_from_name(name)
                .unwrap_or_else(|| panic!("{name} is offered but does not parse"));
            assert_eq!(resampler_name(r), name, "{name} did not round-trip");
            assert!(!seen.contains(&r), "{name} is a second spelling of {r:?}");
            seen.push(r);
        }
        for r in [
            Resampler::Nearest,
            Resampler::Bilinear,
            Resampler::CatmullRom,
            Resampler::Lanczos2,
            Resampler::Lanczos3,
        ] {
            assert!(
                seen.contains(&r),
                "{r:?} ships but RESAMPLER_NAMES does not offer it, so no command \
                 line can select it"
            );
        }
    }

    /// Gate W1. A sidecar written then read yields **bit-identical** warps.
    ///
    /// Bit-identical, not approximately equal: the assertion is on
    /// `f64::to_bits`, so a format that round-tripped through a decimal with
    /// too few digits would fail here even though the values printed the same.
    #[test]
    fn w1_round_trip_is_bit_identical() {
        let a = demo_map();
        let b = WarpMap::from_text(&a.to_text()).expect("round trip");
        assert_eq!(a.len(), b.len());
        for (i, (x, y)) in a.warps().iter().zip(b.warps()).enumerate() {
            match (x, y) {
                (FrameWarp::Placed(p), FrameWarp::Placed(q)) => {
                    assert_eq!(p.a.re.to_bits(), q.a.re.to_bits(), "frame {i} a_re");
                    assert_eq!(p.a.im.to_bits(), q.a.im.to_bits(), "frame {i} a_im");
                    assert_eq!(p.b.re.to_bits(), q.b.re.to_bits(), "frame {i} b_re");
                    assert_eq!(p.b.im.to_bits(), q.b.im.to_bits(), "frame {i} b_im");
                }
                (FrameWarp::Refused(r), FrameWarp::Refused(s)) => assert_eq!(r, s),
                _ => panic!("frame {i} changed state across a round trip"),
            }
        }
        assert_eq!(a.provenance(), b.provenance());
        assert_eq!(a.resampler(), b.resampler());
        assert_eq!(a.geometry(), b.geometry());
        // and the text itself is a fixed point
        assert_eq!(a.to_text(), b.to_text());
    }

    /// Gate W1, named corruption 1: a flipped hex digit in `a_re` must change
    /// the loaded warp. Registered in advance as the input that must fail a
    /// round-trip, so that W1 is not merely asserting that two identical
    /// operations agree.
    #[test]
    fn w1_control_a_flipped_hex_digit_is_detected() {
        let a = demo_map();
        let text = a.to_text();
        let scale = f64_hex(a.placement(1).unwrap().a.re);
        assert!(
            text.contains(&scale),
            "the hex field must actually be in the file"
        );
        // flip the last nibble
        let mut broken = scale.clone();
        let last = broken.pop().unwrap();
        let flipped = if last == '0' { '1' } else { '0' };
        broken.push(flipped);
        let text = text.replace(&scale, &broken);
        let b = WarpMap::from_text(&text).expect("still parses");
        assert_ne!(
            a.placement(1).unwrap().a.re.to_bits(),
            b.placement(1).unwrap().a.re.to_bits(),
            "a flipped hex digit must change the warp; if this fails the hex \
             field is not what is being parsed and W1 proves nothing"
        );
    }

    /// Gate W1, named corruption 2: truncation is a **typed error**, never a
    /// short warp list. A sidecar is written over ~55 s on a 299-frame stack,
    /// so a half-written file is a realistic failure.
    #[test]
    fn w1_control_truncation_is_a_typed_error_not_a_short_map() {
        let full = demo_map().to_text();
        let mut lines: Vec<&str> = full.lines().collect();
        lines.truncate(lines.len() - 2); // drop `end` and the last frame
        let cut = lines.join("\n");
        match WarpMap::from_text(&cut) {
            Err(WarpMapError::Truncated {
                declared,
                found,
                saw_end,
            }) => {
                assert_eq!(declared, 4);
                assert_eq!(found, 3);
                assert!(!saw_end);
            }
            Err(other) => panic!("wrong error for a truncated file: {other}"),
            Ok(m) => panic!("truncated file parsed as a {}-frame map", m.len()),
        }
    }

    #[test]
    fn w1_bad_magic_and_version_are_refused() {
        assert!(matches!(
            WarpMap::from_text("not-a-warpmap 1\nframes 0\nend 0\n"),
            Err(WarpMapError::BadMagic { .. })
        ));
        let bumped = demo_map().to_text().replacen(
            &format!("{MAGIC} {VERSION}"),
            &format!("{MAGIC} {}", VERSION + 7),
            1,
        );
        assert!(matches!(
            WarpMap::from_text(&bumped),
            Err(WarpMapError::BadVersion { found }) if found == VERSION + 7
        ));
    }

    // -- W3: wrong-stack detection ------------------------------------------

    /// Gate W3. The identity must separate `bee-2-cpl` from `bee-3-cpl`.
    ///
    /// MEASURED: those two brackets are the same subject at ISO 400 and
    /// ISO 100, both 299 frames, both the same plane, and their frame
    /// **filenames are byte-identical**. Only the file sizes differ
    /// (37,552,128 vs 39,362,560 bytes for frame 1). A digest over names alone
    /// -- or a check on frame count or geometry -- passes on this pair, which
    /// is why the digest mixes size.
    #[test]
    fn w3_wrong_stack_is_detected_when_names_and_counts_agree() {
        let bee3 = StackIdentity::from_entries(
            "bee-3-cpl",
            &[
                ("DSC00001.ARW", 37_552_128u64),
                ("DSC00002.ARW", 37_556_224),
            ],
        );
        let bee2 = StackIdentity::from_entries(
            "bee-2-cpl",
            &[
                ("DSC00001.ARW", 39_362_560u64),
                ("DSC00002.ARW", 39_366_656),
            ],
        );
        assert_eq!(bee3.frames, bee2.frames, "the trap: same frame count");
        assert_ne!(bee3.digest, bee2.digest, "sizes must separate them");
        assert!(matches!(
            bee3.check(&bee2),
            Err(WarpMapError::StackMismatch { .. })
        ));
        assert!(bee3.check(&bee3.clone()).is_ok());
    }

    /// The digest must also fire on a *reordered* bracket, since the warp
    /// index is positional.
    #[test]
    fn w3_reordering_frames_changes_the_digest() {
        let a = StackIdentity::from_entries("s", &[("a.ARW", 10u64), ("b.ARW", 20)]);
        let b = StackIdentity::from_entries("s", &[("b.ARW", 20u64), ("a.ARW", 10)]);
        assert_ne!(a.digest, b.digest);
    }

    /// A map refuses a foreign stack through its own front door too.
    #[test]
    fn w3_map_check_stack_refuses_a_foreign_bracket() {
        let m = demo_map();
        let foreign = StackIdentity::from_entries(
            "bee-2-cpl",
            &[
                ("DSC00001.ARW", 39_362_560u64),
                ("DSC00002.ARW", 39_366_656),
            ],
        );
        assert!(matches!(
            m.check_stack(&foreign),
            Err(WarpMapError::StackMismatch { .. })
        ));
    }

    // -- W4: refusal is not identity ----------------------------------------

    /// Gate W4. A refused frame and an identity-placed frame are distinct
    /// states, and no accessor collapses them.
    #[test]
    fn w4_refusal_and_identity_are_distinct_states() {
        let m = demo_map();
        assert_eq!(m.warp(0).unwrap().placed(), Some(Similarity::IDENTITY));
        assert_eq!(m.warp(2).unwrap().placed(), None);
        assert!(m.warp(2).unwrap().is_refused());
        assert!(!m.warp(0).unwrap().is_refused());
        assert_ne!(m.warp(0).unwrap(), m.warp(2).unwrap());
        assert_eq!(m.placed_count(), 3);
        assert_eq!(m.refused_count(), 1);
        // the typed way of asking also refuses
        match m.placement(2) {
            Err(WarpMapError::FrameRefused { index, .. }) => assert_eq!(index, 2),
            other => panic!("a refused frame yielded {other:?}"),
        }
        // and refusals survive a round trip as refusals
        let b = WarpMap::from_text(&m.to_text()).unwrap();
        assert!(b.warp(2).unwrap().is_refused());
    }

    #[test]
    fn w4_out_of_range_frames_are_refused() {
        let m = demo_map();
        assert!(matches!(m.warp(4), Err(WarpMapError::NoSuchFrame { .. })));
    }
}

#[cfg(test)]
mod gather_tests {
    use super::*;
    use crate::align::gather_into;

    fn sim(g: f64, rot: f64, ax: f64, ay: f64) -> Similarity {
        Similarity::from_params(SimilarityParams { ax, ay, g, rot })
    }

    /// A band-limited synthetic texture. Sinusoids rather than noise so that
    /// the interpolator is being asked to reconstruct something it can
    /// actually represent -- a white-noise target defeats any resampler and
    /// would measure the target, not the gather.
    fn texture(geom: PlaneGeometry) -> Vec<f32> {
        let mut v = vec![0f32; geom.pixels()];
        for y in 0..geom.height {
            for x in 0..geom.width {
                let (fx, fy) = (x as f64, y as f64);
                let s = (fx * 0.11).sin() * (fy * 0.07).cos()
                    + 0.6 * (fx * 0.031 + fy * 0.043).sin()
                    + 0.35 * (fx * 0.005 - fy * 0.017).cos();
                v[y * geom.width + x] = (0.5 + 0.15 * s) as f32;
            }
        }
        v
    }

    fn median(mut v: Vec<f64>) -> f64 {
        v.sort_by(|a, b| a.partial_cmp(b).unwrap());
        if v.is_empty() {
            f64::NAN
        } else {
            v[v.len() / 2]
        }
    }

    /// Median |a - b| over the interior, skipping uncovered pixels.
    ///
    /// The margin keeps the comparison away from the ring where two scaled
    /// frames genuinely do not overlap, which is a real property of the
    /// geometry and not an error of the gather.
    fn median_abs_diff(a: &[f32], b: &[f32], geom: PlaneGeometry, margin: usize) -> f64 {
        let mut d = Vec::new();
        for y in margin..geom.height - margin {
            for x in margin..geom.width - margin {
                let i = y * geom.width + x;
                if a[i].is_finite() && b[i].is_finite() {
                    d.push((a[i] - b[i]).abs() as f64);
                }
            }
        }
        median(d)
    }

    struct W2 {
        ratio: f64,
        covered: usize,
    }

    /// Plant `plant`, then try to undo it with `undo`, and report the residual
    /// as a fraction of the damage the plant did.
    ///
    /// `ratio` near 0 means `undo` recovered the original; near 1 means it
    /// achieved nothing; above 1 means it made things worse, which is what an
    /// inverted warp does.
    fn w2_trial(geom: PlaneGeometry, plant: Similarity, undo: Similarity) -> W2 {
        let orig = texture(geom);
        let oref = PlaneRef::from_geometry(&orig, geom).unwrap();

        // The frame the camera would have given us: `orig` pushed forward
        // through `plant`, built as a pull through the EXACT inverse. A
        // linearised inverse here is the trap M86 documented -- at a 1% scale
        // the difference between `-(s-1)` and `1/s - 1` is 0.83 plane px on
        // the rig plane, larger than the effect being measured.
        let inv = plant.invert().expect("plant is singular");
        let mut warped = vec![0f32; geom.pixels()];
        gather_into(oref, inv, geom, Resampler::CatmullRom, &mut warped);
        let wref = PlaneRef::from_geometry(&warped, geom).unwrap();

        let mut got = vec![0f32; geom.pixels()];
        let mut cover = vec![false; geom.pixels()];
        let covered = gather_checked(
            wref,
            undo,
            geom,
            Resampler::CatmullRom,
            &mut got,
            &mut cover,
        )
        .unwrap();

        let margin = 12;
        let damage = median_abs_diff(&warped, &orig, geom, margin);
        let residual = median_abs_diff(&got, &orig, geom, margin);
        W2 {
            ratio: residual / damage,
            covered,
        }
    }

    /// Gate W2. A planted similarity, gathered through, is undone.
    ///
    /// Registered bar: `ratio <= 0.25`. This is the gate that proves the
    /// gather is *correct* rather than merely self-consistent -- a round-trip
    /// alone would pass even with the transform inverted.
    #[test]
    fn w2_a_planted_warp_is_undone() {
        let geom = PlaneGeometry {
            width: 400,
            height: 300,
        };
        let plant = sim(0.01, 0.0, 8.0, -3.0);
        let corner = plant.corner_err(Similarity::IDENTITY, geom);
        assert!(
            corner > 2.0,
            "the plant must be a real displacement, got {corner:.3} px"
        );

        let r = w2_trial(geom, plant, plant);
        assert!(
            r.ratio <= 0.25,
            "W2: planted warp not undone: ratio {:.4} > 0.25 bar",
            r.ratio
        );
        assert!(r.covered > geom.pixels() * 9 / 10, "coverage collapsed");
    }

    /// Gate W2, control 1 -- **inversion**. Gathering with `S.invert()`
    /// instead of `S` must NOT pass.
    ///
    /// This is the most likely bug in a consumer of this module and it is
    /// silent: an inverted warp still yields a plausible image, misregistered
    /// by roughly twice the drift. Registered bar: `ratio >= 0.9`.
    #[test]
    fn w2_control_an_inverted_warp_fails_the_gate() {
        let geom = PlaneGeometry {
            width: 400,
            height: 300,
        };
        let plant = sim(0.01, 0.0, 8.0, -3.0);
        let r = w2_trial(geom, plant, plant.invert().unwrap());
        assert!(
            r.ratio >= 0.9,
            "the inversion control PASSED the gate at ratio {:.4}; W2 therefore \
             cannot tell a correct warp from an inverted one and proves nothing",
            r.ratio
        );
    }

    /// Gate W2, control 2 -- **transposition**. Swapping the x and y
    /// translation must NOT pass. Equally silent, equally easy to write.
    #[test]
    fn w2_control_a_transposed_warp_fails_the_gate() {
        let geom = PlaneGeometry {
            width: 400,
            height: 300,
        };
        let plant = sim(0.01, 0.0, 8.0, -3.0);
        let p = plant.to_params();
        let transposed = sim(p.g, p.rot, p.ay, p.ax);
        let r = w2_trial(geom, plant, transposed);
        assert!(
            r.ratio >= 0.9,
            "the transposition control PASSED the gate at ratio {:.4}",
            r.ratio
        );
    }

    /// The gate is reached *through* the sidecar, not around it: the placement
    /// is written to text, read back, and the gather runs off the loaded map.
    #[test]
    fn w2_the_gate_holds_through_a_serialised_sidecar() {
        let geom = PlaneGeometry {
            width: 400,
            height: 300,
        };
        let plant = sim(0.01, 0.0, 8.0, -3.0);
        let map = WarpMap::new(
            Provenance {
                stack: StackIdentity::from_entries("synthetic", &[("f0", 1u64), ("f1", 2)]),
                strategy: "planted".into(),
                heldout_px: None,
                cycle_floor_px: None,
                reference: 0,
                note: "W2".into(),
            },
            geom,
            Resampler::CatmullRom,
            vec![
                FrameWarp::Placed(Similarity::IDENTITY),
                FrameWarp::Placed(plant),
            ],
        );
        let loaded = WarpMap::from_text(&map.to_text()).unwrap();

        let orig = texture(geom);
        let oref = PlaneRef::from_geometry(&orig, geom).unwrap();
        let mut warped = vec![0f32; geom.pixels()];
        gather_into(
            oref,
            plant.invert().unwrap(),
            geom,
            Resampler::CatmullRom,
            &mut warped,
        );
        let wref = PlaneRef::from_geometry(&warped, geom).unwrap();

        let mut got = vec![0f32; geom.pixels()];
        let mut cover = vec![false; geom.pixels()];
        gather_frame(&loaded, 1, wref, &mut got, &mut cover).unwrap();

        let damage = median_abs_diff(&warped, &orig, geom, 12);
        let residual = median_abs_diff(&got, &orig, geom, 12);
        assert!(residual / damage <= 0.25, "ratio {:.4}", residual / damage);
    }

    /// Uncovered destination pixels are NaN and unflagged, never a clamped
    /// edge pixel smeared inward.
    #[test]
    fn gather_marks_uncovered_pixels_instead_of_clamping() {
        let geom = PlaneGeometry {
            width: 120,
            height: 90,
        };
        let orig = texture(geom);
        let oref = PlaneRef::from_geometry(&orig, geom).unwrap();
        let t = sim(0.0, 0.0, 60.0, 40.0);
        let mut got = vec![0f32; geom.pixels()];
        let mut cover = vec![false; geom.pixels()];
        let covered =
            gather_checked(oref, t, geom, Resampler::CatmullRom, &mut got, &mut cover).unwrap();
        assert!(covered < geom.pixels(), "nothing fell off the plane");
        assert!(covered > 0, "everything fell off the plane");
        for i in 0..geom.pixels() {
            assert_eq!(
                cover[i],
                got[i].is_finite(),
                "coverage disagrees with NaN at {i}"
            );
        }
    }

    /// A frame whose plane does not match the map is refused, not gathered.
    #[test]
    fn gather_refuses_a_geometry_mismatch() {
        let geom = PlaneGeometry {
            width: 120,
            height: 90,
        };
        let other = PlaneGeometry {
            width: 121,
            height: 90,
        };
        let data = texture(other);
        let r = PlaneRef::from_geometry(&data, other).unwrap();
        let mut got = vec![0f32; geom.pixels()];
        let mut cover = vec![false; geom.pixels()];
        let e = gather_checked(
            r,
            Similarity::IDENTITY,
            geom,
            Resampler::CatmullRom,
            &mut got,
            &mut cover,
        );
        assert!(matches!(e, Err(WarpMapError::GeometryMismatch { .. })));
    }

    /// A refused frame cannot be gathered at all.
    #[test]
    fn gather_refuses_a_refused_frame() {
        let geom = PlaneGeometry {
            width: 120,
            height: 90,
        };
        let map = WarpMap::new(
            Provenance {
                stack: StackIdentity::from_entries("s", &[("f0", 1u64)]),
                strategy: "x".into(),
                heldout_px: None,
                cycle_floor_px: None,
                reference: 0,
                note: String::new(),
            },
            geom,
            Resampler::CatmullRom,
            vec![FrameWarp::Refused("no".into())],
        );
        let data = texture(geom);
        let r = PlaneRef::from_geometry(&data, geom).unwrap();
        let mut got = vec![0f32; geom.pixels()];
        let mut cover = vec![false; geom.pixels()];
        assert!(matches!(
            gather_frame(&map, 0, r, &mut got, &mut cover),
            Err(WarpMapError::FrameRefused { .. })
        ));
    }
}
