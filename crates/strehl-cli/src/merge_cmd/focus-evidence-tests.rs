use super::*;
use crate::focus_pass::FocusSource;
use strehl_core::align::{Resampler, Similarity};
use strehl_core::focus_evidence::{FocusFrame, FocusMode, MODE_CAPACITY};
use strehl_core::noise::Levels;
use strehl_core::plane::{PlaneGeometry, QuadSource};
use strehl_core::warpmap::{FrameWarp, Provenance, StackIdentity};

/// A field of `width x height` with every pixel unusable, `frames` long.
fn empty_field(width: usize, height: usize, frames: usize) -> FocusEvidence {
    let n = width * height;
    FocusEvidence {
        geometry: PlaneGeometry { width, height },
        frames: (0..frames)
            .map(|i| FocusFrame {
                acquisition: i as u64,
                global_index: i,
            })
            .collect(),
        ordinal: vec![f32::NAN; n],
        width_frames: vec![f32::NAN; n],
        prominence_sigma: vec![0.0; n],
        perplexity: vec![0.0; n],
        top_global_indices: vec![[usize::MAX; 4]; n],
        flags: vec![0; n],
        covered: vec![false; n],
        supported_frames: vec![0; n],
        modes: vec![[FocusMode::default(); MODE_CAPACITY]; n],
        unresolved_mode_prominence_sigma: vec![0.0; n],
        usable: vec![false; n],
    }
}

/// Each area takes the median ordinal of its usable pixels and their share;
/// only areas a quarter usable count as drawn; an area with no usable pixel
/// has no depth.
#[test]
fn compact_takes_the_median_of_each_areas_usable_pixels() {
    let mut field = empty_field(8, 4, 11);
    // Left area (x 0..4): 16 pixels, 5 usable with ordinals 1, 2, 3, 9, 10.
    for (x, y, ordinal) in [
        (0, 0, 1.0),
        (1, 0, 2.0),
        (2, 1, 3.0),
        (3, 2, 9.0),
        (0, 3, 10.0),
    ] {
        field.usable[y * 8 + x] = true;
        field.ordinal[y * 8 + x] = ordinal;
    }
    // A measured but unusable pixel does not count.
    field.ordinal[8 + 1] = 0.0;
    // Middle area: 3 of 16 usable, under the quarter. Right: none.
    for x in 4..7 {
        field.usable[x] = true;
        field.ordinal[x] = 5.0;
    }
    let mut wide = empty_field(12, 4, 11);
    for y in 0..4 {
        for x in 0..8 {
            wide.usable[y * 12 + x] = field.usable[y * 8 + x];
            wide.ordinal[y * 12 + x] = field.ordinal[y * 8 + x];
        }
    }
    let compact = compact(&wide, [3, 1]);
    assert_eq!(compact.lattice, [3, 1]);
    assert_eq!(compact.frames, 11);
    assert_eq!(compact.drawn, 1);
    // Median 3 of ordinals 0..=10: 3 / 10 * 254 = 76.2; 5 / 10 * 254 = 127.
    assert_eq!(compact.depth, [76, 127, NO_DEPTH]);
    // 5 / 16 and 3 / 16 of 255.
    assert_eq!(compact.share, [80, 48, 0]);
}

/// An area with one usable pixel of 1,600 keeps its depth and a share of
/// one step, never zero: a reader can always tell "measured, sparsely" from
/// "nothing usable".
#[test]
fn a_sparse_area_keeps_a_nonzero_share() {
    let mut field = empty_field(40, 40, 5);
    field.usable[820] = true;
    field.ordinal[820] = 4.0;
    let compact = compact(&field, [1, 1]);
    assert_eq!(
        (compact.depth[0], compact.share[0], compact.drawn),
        (254, 1, 0)
    );
}

/// The summary's documented layout, its truncated text and the framing
/// limit of readers that predate it.
#[test]
fn the_summary_says_why_in_a_bounded_record() {
    let summary = Summary {
        usable: false,
        reason: Reason::Memory,
        text: "\u{e9}".repeat(700),
        frames: 299,
        field: [3504, 2336],
        usable_pixels: 7,
        covered_pixels: 9,
        seconds: 1.5,
        reservation_bytes: 1 << 33,
        flag_pixels: [1, 2, 3, 4, 5, 6, 7],
    };
    let bytes = summary.bytes();
    assert_eq!(&bytes[..4], &[1, 0, 3, 0]);
    let u32_at = |at: usize| u32::from_le_bytes(bytes[at..at + 4].try_into().unwrap());
    assert_eq!(
        [u32_at(4), u32_at(8), u32_at(12), u32_at(16), u32_at(20)],
        [299, 3504, 2336, 7, 9]
    );
    assert_eq!(f32::from_le_bytes(bytes[24..28].try_into().unwrap()), 1.5);
    assert_eq!(
        u64::from_le_bytes(bytes[28..36].try_into().unwrap()),
        1 << 33
    );
    let flags: Vec<u32> = (0..7).map(|k| u32_at(36 + 4 * k)).collect();
    assert_eq!(flags, [1, 2, 3, 4, 5, 6, 7]);
    let text = u16::from_le_bytes([bytes[64], bytes[65]]) as usize;
    assert_eq!(text, 1024, "cut at a character boundary");
    assert_eq!(bytes.len(), 66 + text);
    assert!(std::str::from_utf8(&bytes[66..]).is_ok());
    assert!(bytes.len() <= crate::ui_progress::MAX_FOCUS_SUMMARY_BYTES);
}

const W: usize = 192;
const H: usize = 128;
const FRAMES: usize = 10;
const LEVELS: Levels = Levels {
    black: 512.0,
    white: 16383.0,
};

/// A synthetic grey CFA frame: a fixed texture blurred by a box of radius
/// `|k - sharp|`, with `sharp` the left half's sharp frame or the right
/// half's (`None`: no texture at all).
struct Plant {
    rows: Vec<u16>,
}

impl Plant {
    fn new(k: usize, left: Option<usize>, right: Option<usize>) -> Self {
        let texture = |x: usize, y: usize| -> f32 {
            let h = (x as u32).wrapping_mul(2_654_435_761) ^ (y as u32).wrapping_mul(40_503);
            if (h >> 13) & 1 == 1 { 1.0 } else { -1.0 }
        };
        let mut quad = vec![0f32; W * H];
        for y in 0..H {
            for x in 0..W {
                let sharp = if x < W / 2 { left } else { right };
                let value = match sharp {
                    None => 0.0,
                    Some(s) => {
                        let r = k.abs_diff(s) as isize;
                        let mut sum = 0.0;
                        let mut n = 0.0;
                        for dy in -r..=r {
                            for dx in -r..=r {
                                let (sx, sy) = (x as isize + dx, y as isize + dy);
                                if (0..W as isize).contains(&sx) && (0..H as isize).contains(&sy) {
                                    sum += texture(sx as usize, sy as usize);
                                    n += 1.0;
                                }
                            }
                        }
                        sum / n
                    }
                };
                quad[y * W + x] = 4000.0 + 2500.0 * value;
            }
        }
        let mut rows = vec![0u16; 4 * W * H];
        for y in 0..H {
            for x in 0..W {
                let v = quad[y * W + x].round() as u16;
                for (dy, dx) in [(0, 0), (0, 1), (1, 0), (1, 1)] {
                    rows[(2 * y + dy) * 2 * W + 2 * x + dx] = v;
                }
            }
        }
        Self { rows }
    }
}

impl QuadSource for Plant {
    fn geometry(&self) -> PlaneGeometry {
        PlaneGeometry {
            width: W,
            height: H,
        }
    }
    fn quad_rows(&self, py: usize) -> (&[u16], &[u16]) {
        let row = 2 * W;
        (
            &self.rows[2 * py * row..(2 * py + 1) * row],
            &self.rows[(2 * py + 1) * row..(2 * py + 2) * row],
        )
    }
}

impl FocusSource for Plant {
    fn quad(&self) -> &dyn QuadSource {
        self
    }
    fn camera(&self) -> &str {
        "plant"
    }
    fn iso(&self) -> Option<f32> {
        Some(100.0)
    }
    fn levels(&self) -> Levels {
        LEVELS
    }
}

struct Plants {
    left: Option<usize>,
    right: Option<usize>,
    loads: usize,
    made: std::collections::HashMap<usize, Vec<u16>>,
}

impl FocusFrames for Plants {
    type Source = Plant;
    fn load(&mut self, global_index: usize) -> Result<Plant> {
        self.loads += 1;
        let (left, right) = (self.left, self.right);
        let rows = self
            .made
            .entry(global_index)
            .or_insert_with(|| Plant::new(global_index, left, right).rows)
            .clone();
        Ok(Plant { rows })
    }
}

fn identity_map() -> WarpMap {
    let entries: Vec<(String, u64)> = (0..FRAMES).map(|i| (format!("{i}"), 1)).collect();
    WarpMap::new(
        Provenance {
            stack: StackIdentity::from_entries("plant", &entries),
            strategy: "identity".into(),
            heldout_px: None,
            cycle_floor_px: None,
            reference: 0,
            note: String::new(),
        },
        PlaneGeometry {
            width: W,
            height: H,
        },
        Resampler::CatmullRom,
        (0..FRAMES)
            .map(|_| FrameWarp::Placed(Similarity::IDENTITY))
            .collect(),
    )
}

fn run_plant(left: Option<usize>, right: Option<usize>) -> (Compact, usize) {
    let mut frames = Plants {
        left,
        right,
        loads: 0,
        made: Default::default(),
    };
    let full = PlaneGeometry {
        width: W,
        height: H,
    };
    let noise = strehl_core::profile::fallback(100.0, LEVELS);
    let sweep: Vec<usize> = (0..FRAMES).collect();
    let pass = crate::focus_pass::compute(
        &mut frames,
        &sweep,
        &identity_map(),
        SamplingDomain::full(full),
        &noise,
        None,
        usize::MAX / 2,
        "plant",
    )
    .unwrap();
    (compact(&pass.field, [8, 4]), frames.loads)
}

/// Positive control: a plant whose left half is sharp at frame 2 and right
/// half at frame 7 reads as that order in the areas away from the seam and
/// the border, each frame read twice plus the lead. Negative control: a
/// textureless plant has nothing usable.
#[test]
fn the_pass_recovers_a_planted_order_and_refuses_a_flat_one() {
    let (compact, loads) = run_plant(Some(2), Some(7));
    assert_eq!(loads, 2 * FRAMES + 1);
    let at = |i: usize, j: usize| compact.depth[j * 8 + i];
    let ordinal = |byte: u8| byte as f32 / 254.0 * (FRAMES - 1) as f32;
    for j in 1..3 {
        assert!(
            (ordinal(at(1, j)) - 2.0).abs() < 0.5,
            "left {:?}",
            compact.depth
        );
        assert!(
            (ordinal(at(6, j)) - 7.0).abs() < 0.5,
            "right {:?}",
            compact.depth
        );
    }
    assert!(compact.drawn >= 8, "{:?}", compact.share);
    let (flat, _) = run_plant(None, None);
    assert_eq!(flat.drawn, 0);
    assert!(
        flat.depth.iter().all(|&d| d == NO_DEPTH),
        "{:?}",
        flat.depth
    );
    assert!(flat.share.iter().all(|&s| s == 0));
}

/// The pass's reservation at the owner's planes (quad grids): A7C II
/// 3504 x 2336 and A7CR 4752 x 3168, at 299 and 1,444 frames. The frame
/// count adds only 128 bytes a frame; the plane sets the cost.
#[test]
fn the_reservation_is_set_by_the_plane() {
    let gib = |n: usize| n as f64 / (1u64 << 30) as f64;
    let at = |width, height, frames| {
        let full = PlaneGeometry { width, height };
        crate::focus_pass::reservation_bytes(SamplingDomain::full(full), frames).unwrap()
    };
    for (name, width, height) in [("a7c2", 3504, 2336), ("a7cr", 4752, 3168)] {
        let (a, b) = (at(width, height, 299), at(width, height, 1444));
        println!(
            "focus_reservation {name} {width}x{height} bytes_per_pixel={:.1} frames299={:.3}GiB frames1444={:.3}GiB",
            a as f64 / (width * height) as f64,
            gib(a),
            gib(b)
        );
        assert_eq!(b - a, 128 * (1444 - 299));
    }
}
