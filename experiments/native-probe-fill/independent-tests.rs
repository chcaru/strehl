// Independent scalar reconstruction and whole-buffer comparison. No RAW access.
use super::*;
use strehl_raw::Region;
use strehl_core::plane::QuadSource;

const GOLDEN: u64 = 0x9e37_79b9_7f4a_7c15;

struct Scalar {
    state: u64,
    spare: Option<f64>,
}
impl Scalar {
    fn new(index: usize) -> Self {
        // Keep the old seed domain: index+1 must be representable in u64.
        Self { state: GOLDEN.wrapping_mul(index as u64 + 1) ^ 0x2545_f491_4f6c_dd1d, spare: None }
    }
    fn uniform(&mut self) -> f64 {
        self.state = self.state.wrapping_add(GOLDEN);
        let mut z = self.state;
        z = (z ^ (z >> 30)).wrapping_mul(0xbf58_476d_1ce4_e5b9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94d0_49bb_1331_11eb);
        f64::from(((z ^ (z >> 31)) >> 40) as u32) / f64::from(1u32 << 24)
    }
    fn normal(&mut self) -> f64 {
        if let Some(value) = self.spare.take() { return value; }
        let u = self.uniform().max(1e-12);
        let v = self.uniform();
        let radius = (-2.0 * u.ln()).sqrt();
        let theta = std::f64::consts::TAU * v;
        self.spare = Some(radius * theta.sin());
        radius * theta.cos()
    }
    fn code(&mut self, level: f64, sigma: f64) -> u16 {
        (level + sigma * self.normal()).round().clamp(0.0, f64::from(u16::MAX)) as u16
    }
}

// Active width/height, origin, right padding and bottom padding. Odd trailing
// active sensels are deliberately outside the consumed complete-quad rectangle.
const LAYOUTS: [(usize, usize, usize, usize, usize, usize); 5] = [
    (2, 2, 0, 0, 0, 0),
    (3, 3, 1, 2, 4, 3),
    (10, 6, 3, 5, 7, 4),
    (17, 11, 2, 1, 11, 6),
    (128, 96, 2, 4, 7, 7),
];
const LEVELS: [(f64, f64); 6] = [
    (2512.0, 40.0), (-0.5, 0.0), (0.5, 0.0),
    (65534.5, 0.0), (65535.5, 0.0), (32767.5, 100000.0),
];

fn fixture(layout: usize) -> Frame {
    let (w, h, ax, ay, right, bottom) = LAYOUTS[layout];
    let stride = ax + w + right;
    let rows = ay + h + bottom;
    Frame {
        data: (0..stride * rows).map(|i| 60000 + (i % 997) as u16).collect(),
        stride, buffer_height: rows,
        active: Region { x: ax, y: ay, width: w, height: h },
        levels: strehl_core::noise::Levels { black: 512.0, white: 15360.0 },
        iso: Some(160.0), wb_coeffs: [1.25, 1.0, 0.8, f32::NAN],
        xyz_to_cam_rgbe: [[0.0; 3]; 4], color_matrices: Vec::new(),
        camera: "independent probe-fill buffer fixture".into(),
        path: std::path::PathBuf::from("PROBE-FILL-NO-SUCH-RAW.ARW"),
    }
}

fn reference(frame: &Frame, level: f64, sigma: f64, seed: usize, wrong_skip: bool) -> Vec<u16> {
    let mut result = frame.data.clone();
    let mut rng = Scalar::new(seed);
    let width = frame.active.width / 2 * 2;
    let height = frame.active.height / 2 * 2;
    for y in 0..height {
        if wrong_skip && y > 0 { let _ = rng.normal(); }
        for x in 0..width {
            result[(frame.active.y + y) * frame.stride + frame.active.x + x] = rng.code(level, sigma);
        }
    }
    result
}

#[test]
fn independent_scalar_stream_layout_threads_and_edges() {
    let seeds = [0, 1, 17, usize::MAX - 1];
    let mut comparisons = 0;
    let mut saw_multirow = false;
    let mut saw_padding = false;
    let mut saw_odd_tail = false;
    let mut saw_wrapping_row_jump = false;
    let mut saw_low_clip = false;
    let mut saw_high_clip = false;
    for threads in [1, 2, 8] {
        let pool = rayon::ThreadPoolBuilder::new().num_threads(threads).build().unwrap();
        for layout in 0..LAYOUTS.len() {
            let original = fixture(layout);
            let full = original.geometry();
            let width = 2 * full.width;
            let height = 2 * full.height;
            assert!(width > 0 && width % 2 == 0 && height > 0);
            saw_multirow |= height >= 96;
            saw_padding |= original.active.x > 0 && original.active.y > 0 && original.stride > original.active.x + width;
            saw_odd_tail |= original.active.width > width && original.active.height > height;
            saw_wrapping_row_jump |= height > 1 && u128::from(GOLDEN) * width as u128 > u128::from(u64::MAX);
            for seed in seeds {
                for (edge, (level, sigma)) in LEVELS.into_iter().enumerate() {
                    let expected = reference(&original, level, sigma, seed, false);
                    for mode in [FillMode::Serial, FillMode::Parallel] {
                        let mut actual = original.clone();
                        pool.install(|| fill_probe_noise_mode(&mut actual, full, level, sigma, seed, mode)).unwrap();
                        let mismatch = actual.data.iter().zip(&expected).position(|(a, b)| a != b);
                        assert!(mismatch.is_none(), "whole-buffer mismatch: threads={threads} layout={layout} seed={seed} edge={edge} first={mismatch:?}");
                        assert_eq!(actual.data.len(), original.data.len());
                        assert_eq!(actual.stride, original.stride);
                        assert_eq!(actual.buffer_height, original.buffer_height);
                        assert_eq!((actual.active.x, actual.active.y, actual.active.width, actual.active.height),
                                   (original.active.x, original.active.y, original.active.width, original.active.height));
                        comparisons += 1;
                    }
                    if layout == 4 && edge == 5 {
                        for y in 0..height {
                            let row = (original.active.y + y) * original.stride + original.active.x;
                            saw_low_clip |= expected[row..row + width].contains(&0);
                            saw_high_clip |= expected[row..row + width].contains(&u16::MAX);
                        }
                    }
                    if sigma == 0.0 {
                        let literal = [0, 0, 1, 65535, 65535, 0][edge];
                        for y in 0..height {
                            let row = (original.active.y + y) * original.stride + original.active.x;
                            assert!(expected[row..row + width].iter().all(|v| *v == literal));
                        }
                    }
                }
            }
        }
    }
    assert_eq!(comparisons, 720);
    assert!(saw_multirow && saw_padding && saw_odd_tail && saw_wrapping_row_jump && saw_low_clip && saw_high_clip,
            "required stream/jump/clamp conditions were not exercised");
    let original = fixture(4);
    let right = reference(&original, 2512.0, 40.0, 17, false);
    let wrong = reference(&original, 2512.0, 40.0, 17, true);
    let first = original.active.y * original.stride + original.active.x;
    let second = first + original.stride;
    assert_eq!(&right[first..first + 128], &wrong[first..first + 128]);
    assert_ne!(&right[second..second + 128], &wrong[second..second + 128],
               "wrong row-start control did not change the actual second row");
    assert_ne!(right, wrong, "whole-buffer equality has no power against a row offset error");
    println!("independent probe-fill: {comparisons} whole-buffer comparisons; pools1/2/8; odd/padded/tiny/multirow, wrapping jump, low/high clip, wrong-row destroyer exercised");
}

#[test]
fn independent_fill_mode_parser() {
    assert!(matches!(parse_fill_mode(None).unwrap(), FillMode::Parallel));
    assert!(matches!(parse_fill_mode(Some("serial")).unwrap(), FillMode::Serial));
    assert!(matches!(parse_fill_mode(Some("parallel")).unwrap(), FillMode::Parallel));
    for value in ["unexpected", "", "Serial", " parallel", "parallel "] {
        assert!(parse_fill_mode(Some(value)).is_err());
    }
}
