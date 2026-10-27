// Nested under noise_floor_gather by a test-only include after root freezes its
// preceding covariance runs. Reuses that fixture's real gather/noise utilities.
use super::*;
use strehl_core::demosaic::{Mosaic, demosaic};
use strehl_core::pyramid::Hull;

const RECON_BANDS: usize = 3;
const FOCUS: [f64; 5] = [0.0, 0.25, 0.5, 0.75, 1.0];
const RECON_REGIONS: [&str; 5] = ["all", "interior", "detail", "edge_guard", "texture"];

// A fixed analytic synthetic optical scene, not a camera-calibrated PSF.
fn cdf(x: f64) -> f64 {
    let t = 1.0 / (1.0 + 0.2316419 * x.abs());
    let tail = (-0.5 * x * x).exp() / std::f64::consts::TAU.sqrt()
        * t
        * (0.319381530
            + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429))));
    if x >= 0.0 { 1.0 - tail } else { tail }
}
fn ridge(distance: f64, width: f64, blur: f64) -> f64 {
    let total = (width * width + blur * blur).sqrt();
    width / total * (-0.5 * (distance / total).powi(2)).exp()
}
fn scene_value(
    scene: &str,
    x: f64,
    y: f64,
    focus: Option<f64>,
    detail: bool,
    texture: bool,
) -> f64 {
    let near = focus.map_or(0.0, |f| 2.8 * f.abs());
    let far = focus.map_or(0.0, |f| 2.8 * (f - 1.0).abs());
    match scene {
        "flat" => 2000.0,
        "step_lines" => {
            let base = 2000.0 + 6000.0 * cdf((x - 72.0) / (0.35f64.powi(2) + far * far).sqrt());
            let lines = if detail {
                140.0 * (ridge(x - 66.5, 0.65, near) + ridge(x - 61.0, 0.65, near))
            } else {
                0.0
            };
            base - lines
        }
        "strand_texture" => {
            let backdrop = 4200.0 + 1800.0 * cdf((x - 72.0) / (0.35f64.powi(2) + far * far).sqrt());
            let tex = if texture {
                110.0
                    * (-0.5 * far * far * (0.9f64.powi(2) + 0.4f64.powi(2))).exp()
                    * (0.9 * x + 0.4 * y).sin()
                    + 80.0
                        * (-0.5 * far * far * (0.35f64.powi(2) + 0.85f64.powi(2))).exp()
                        * (0.35 * x - 0.85 * y).sin()
            } else {
                0.0
            };
            let alpha = if detail {
                0.7 * ridge(
                    (y - 0.35 * x - 26.0) / (1.0f64 + 0.35f64.powi(2)).sqrt(),
                    0.75,
                    near,
                )
            } else {
                0.0
            };
            (backdrop + tex) * (1.0 - alpha) + 2000.0 * alpha
        }
        _ => panic!("unknown generated scene"),
    }
}
fn scene_frame(
    scene: &str,
    focus: Option<f64>,
    transform: Similarity,
    detail: bool,
    texture: bool,
) -> Frame {
    let mut frame = clean_frame("flat_shot");
    frame.wb_coeffs = [1.0, 1.0, 1.0, f32::NAN];
    let inverse = transform.invert().expect("known similarity must invert");
    let centre = SIDE as f64 / 4.0;
    for y in 0..SIDE {
        for x in 0..SIDE {
            // Generate unaligned sensor samples in the same gauge the actual
            // gather pulls from. No rendered aligned-frame volume is retained.
            let (wx, wy) = inverse.apply_at(x as f64 * 0.5, y as f64 * 0.5, centre, centre);
            frame.data[y * SIDE + x] = (512.0
                + scene_value(scene, 2.0 * wx, 2.0 * wy, focus, detail, texture))
            .round() as u16;
        }
    }
    frame
}
fn gather_four(
    mut frame: Frame,
    t: Similarity,
    domain: PyramidDomain,
    scratch: &mut WarpScratch,
) -> Result<Vec<Vec<f32>>> {
    align_cmd::warp_frame_in_place(&mut frame, t, domain.full, Resampler::CatmullRom, scratch)?;
    let mut planes = vec![vec![0.0; domain.analysis().pixels()]; 4];
    extract_planes(
        &frame.data,
        frame.stride,
        frame.active.x,
        frame.active.y,
        frame.levels.black,
        domain,
        &BAND_PLANE_OFFSETS,
        &mut planes,
    )?;
    Ok(planes)
}
fn luma_of(planes: &[Vec<f32>]) -> Vec<f32> {
    planes[1]
        .iter()
        .zip(&planes[2])
        .map(|(a, b)| 0.5 * (a + b))
        .collect()
}
fn recon_config(hull: Hull) -> MergeConfig {
    MergeConfig {
        bands: RECON_BANDS,
        gate: 2.0,
        exponent: 2.0,
        sharpen_per_octave: 1.4,
        select: SelectMode::SoftPower,
        admission: AdmissionMode::HardFloor,
        base: BaseBand::Mean,
        mean_coarse: 0,
        fallback: Fallback::Mean,
        significance_scale: 0.0,
        hull,
        ..MergeConfig::default()
    }
}
struct Reconstruction {
    merge: BandMerge,
    frame: FrameWorkspace,
    collapse: Workspace,
}
impl Reconstruction {
    fn new(size: LevelSize, mode: Mode, hull: Hull) -> Self {
        let merge = BandMerge::new(size.width, size.height, 4, recon_config(hull));
        let mut frame = FrameWorkspace::new(merge.sizes(), 4);
        frame.set_spatial_noise_floor_mode(mode);
        let collapse = Workspace::new(merge.sizes());
        Self {
            merge,
            frame,
            collapse,
        }
    }
    fn fold(&mut self, planes: &[Vec<f32>], luma: &[f32], variance: &[f32], beta: &[f32]) {
        self.frame.next_frame();
        let refs: Vec<_> = planes.iter().map(Vec::as_slice).collect();
        self.merge
            .add_frame_with_gain(&refs, luma, variance, Some(beta), &mut self.frame);
    }
    fn coarse(&self) -> Vec<(Vec<f32>, Vec<bool>)> {
        let mut out = Vec::new();
        self.merge.observe_accumulator(|o| {
            if o.level >= 2 {
                out.push((
                    (0..o.size.pixels()).map(|i| o.coefficient(i)).collect(),
                    (0..o.size.pixels()).map(|i| o.averaging(i)).collect(),
                ));
            }
        });
        out
    }
    fn finish(&mut self) -> Vec<Vec<f32>> {
        self.merge.finish(&mut self.collapse)
    }
}
fn transforms(name: &str) -> [Similarity; 5] {
    match name {
        "identity" => [Similarity::IDENTITY; 5],
        "fractional" => std::array::from_fn(|i| {
            Similarity::from_params(SimilarityParams {
                ax: [0.0, 0.25, -0.25, 0.25, -0.25][i],
                ay: [0.0, -0.25, 0.25, 0.25, -0.25][i],
                ..Default::default()
            })
        }),
        "curved" => std::array::from_fn(|i| {
            Similarity::from_params(SimilarityParams {
                g: [1.0, 0.972665, 0.94686, 0.90907, 0.85714][i] - 1.0,
                ..Default::default()
            })
        }),
        _ => panic!("unknown geometry"),
    }
}
fn recon_regions(size: LevelSize, scene: &str) -> Vec<Vec<usize>> {
    (0..RECON_REGIONS.len())
        .map(|r| {
            (0..size.pixels())
                .filter(|&i| {
                    let (x, y) = (i % size.width, i / size.width);
                    let (wx, wy) = (8.0 + 2.0 * x as f64, 8.0 + 2.0 * y as f64);
                    let interior = x >= 4 && y >= 4 && x + 4 < size.width && y + 4 < size.height;
                    match r {
                        0 => true,
                        1 => interior,
                        2 => {
                            if scene == "strand_texture" {
                                (wy - 0.35 * wx - 26.0).abs() < 5.0 && wx > 24.0 && wx < 124.0
                            } else {
                                wx >= 57.0 && wx <= 69.0 && wy >= 24.0 && wy <= 120.0
                            }
                        }
                        3 => wx >= 68.0 && wx <= 79.0 && wy >= 24.0 && wy <= 120.0,
                        _ => wx >= 84.0 && wx <= 124.0 && wy >= 82.0 && wy <= 120.0,
                    }
                })
                .collect()
        })
        .collect()
}
fn mse(actual: &[Vec<f32>], truth: &[Vec<f32>], indices: &[usize]) -> f64 {
    actual
        .iter()
        .zip(truth)
        .map(|(a, t)| {
            indices
                .iter()
                .map(|&i| (f64::from(a[i]) - f64::from(t[i])).powi(2))
                .sum::<f64>()
        })
        .sum::<f64>()
        / (indices.len() * actual.len()) as f64
}
fn projection(
    actual: &[Vec<f32>],
    truth: &[Vec<f32>],
    background: &[Vec<f32>],
    indices: &[usize],
) -> Option<f64> {
    let mut cross = 0.0;
    let mut norm = 0.0;
    for c in 0..4 {
        for &i in indices {
            let template = f64::from(truth[c][i] - background[c][i]);
            cross += f64::from(actual[c][i] - background[c][i]) * template;
            norm += template * template;
        }
    }
    (norm > 1.0).then_some(cross / norm)
}
fn save_output(out: &Path, name: &str, planes: &[Vec<f32>], size: LevelSize) -> Result<Value> {
    let mut bytes = Vec::with_capacity(4 * size.pixels() * 4);
    for p in planes {
        for v in p {
            bytes.extend_from_slice(&v.to_le_bytes());
        }
    }
    fs::write(out.join(format!("{name}.f32")), &bytes)?;
    let (width, height) = (2 * size.width, 2 * size.height);
    let mut mosaic = vec![0.0; width * height];
    for (c, &(dx, dy)) in BAND_PLANE_OFFSETS.iter().enumerate() {
        for y in 0..size.height {
            for x in 0..size.width {
                mosaic[(2 * y + dy) * width + 2 * x + dx] = planes[c][y * size.width + x] / 14848.0;
            }
        }
    }
    let mut rgb = vec![0.0; width * height * 3];
    demosaic(
        &Mosaic {
            data: &mosaic,
            width,
            height,
        },
        &mut rgb,
    );
    let display: Vec<_> = rgb
        .iter()
        .map(|&v| (srgb_encode(v.clamp(0.0, 1.0)) * 65535.0).round() as u16)
        .collect();
    crate::image_out::write_rgb16(
        &out.join(format!("{name}-display.tif")),
        width as u32,
        height as u32,
        &display,
    )?;
    Ok(
        json!({"planes":format!("{name}.f32"),"display":format!("{name}-display.tif"),
        "sha256_planes":digest(&bytes),"plane_order":"R,G1,G2,B","plane_size":[size.width,size.height],
        "display_size":[width,height],"display":"same fixed divide14848, core normal demosaic, sRGB transfer; no tone/exposure fitting"}),
    )
}
fn repeat_moments(value: &Moments) -> Value {
    json!({"mean":value.mean,"standard_error":value.se(),"independent_stack_repeats":value.n})
}
struct ImageStats {
    sum: Vec<Vec<f64>>,
    squares: Vec<Vec<f64>>,
    mse: Vec<Moments>,
    paired_delta: Vec<Moments>,
    detail: Moments,
    texture: Moments,
}
impl ImageStats {
    fn new(size: LevelSize) -> Self {
        Self {
            sum: vec![vec![0.0; size.pixels()]; 4],
            squares: vec![vec![0.0; size.pixels()]; 4],
            mse: vec![Moments::default(); RECON_REGIONS.len()],
            paired_delta: vec![Moments::default(); RECON_REGIONS.len()],
            detail: Moments::default(),
            texture: Moments::default(),
        }
    }
    fn add(
        &mut self,
        img: &[Vec<f32>],
        truth: &[Vec<f32>],
        background: &[Vec<f32>],
        no_texture: &[Vec<f32>],
        current: &[Vec<f32>],
        regions: &[Vec<usize>],
    ) {
        for c in 0..4 {
            for i in 0..img[c].len() {
                self.sum[c][i] += f64::from(img[c][i]);
                self.squares[c][i] += f64::from(img[c][i]).powi(2);
            }
        }
        for (r, indices) in regions.iter().enumerate() {
            let e = mse(img, truth, indices);
            self.mse[r].add(e);
            self.paired_delta[r].add(e - mse(current, truth, indices));
        }
        if let Some(p) = projection(img, truth, background, &regions[2]) {
            self.detail.add(p);
        }
        if let Some(p) = projection(img, truth, no_texture, &regions[4]) {
            self.texture.add(p);
        }
    }
    fn finish(
        &self,
        truth: &[Vec<f32>],
        regions: &[Vec<usize>],
        repeats: usize,
    ) -> (Vec<Vec<f32>>, Value) {
        let n = repeats as f64;
        let mean: Vec<Vec<f32>> = self
            .sum
            .iter()
            .map(|p| p.iter().map(|v| (v / n) as f32).collect())
            .collect();
        let mut report = Vec::new();
        for (r, indices) in regions.iter().enumerate() {
            let mut bias2 = 0.0;
            let mut variance = 0.0;
            for c in 0..4 {
                for &i in indices {
                    bias2 += (self.sum[c][i] / n - f64::from(truth[c][i])).powi(2);
                    variance += (self.squares[c][i] / n - (self.sum[c][i] / n).powi(2)).max(0.0);
                }
            }
            let count = (indices.len() * 4) as f64;
            bias2 /= count;
            variance /= count;
            let unbias_var = if repeats > 1 {
                variance * n / (n - 1.0)
            } else {
                0.0
            };
            assert!(
                (bias2 + variance - self.mse[r].mean).abs() < 1e-6 * self.mse[r].mean.max(1.0),
                "MSE bias/variance decomposition failed"
            );
            report.push(json!({"region":RECON_REGIONS[r],"quad_pixels":indices.len(),
                "mean_mse_dn2":repeat_moments(&self.mse[r]),"paired_mse_delta_to_current":repeat_moments(&self.paired_delta[r]),
                "squared_error_of_repeat_mean_dn2":bias2,"temporal_variance_population_dn2":variance,
                "temporal_variance_unbiased_dn2":unbias_var,
                "finite_repeat_corrected_bias2_dn2":bias2-unbias_var/n}));
        }
        (
            mean,
            json!({"regions":report,"detail_template_amplitude":repeat_moments(&self.detail),
            "texture_template_amplitude":repeat_moments(&self.texture),
            "note":"bias2 and population variance sum to measured MSE; corrected bias2 can be negative at finite repeats"}),
        )
    }
}
#[allow(clippy::too_many_arguments)]
fn reconstruction_case(
    scene: &str,
    geometry: &str,
    noisy: bool,
    repeats: usize,
    domain: PyramidDomain,
    out: &Path,
    case: usize,
) -> Result<Value> {
    let size = LevelSize {
        width: domain.rect.width,
        height: domain.rect.height,
    };
    let sizes = level_sizes(size.width, size.height, RECON_BANDS);
    ensure!(
        sizes.len() == RECON_BANDS + 1,
        "three actual bands plus base required"
    );
    let model = noise(false);
    let mut scratch = WarpScratch::new(domain.full);
    let truth = gather_four(
        scene_frame(scene, None, Similarity::IDENTITY, true, true),
        Similarity::IDENTITY,
        domain,
        &mut scratch,
    )?;
    let background = gather_four(
        scene_frame(scene, None, Similarity::IDENTITY, false, true),
        Similarity::IDENTITY,
        domain,
        &mut scratch,
    )?;
    let no_texture = gather_four(
        scene_frame(scene, None, Similarity::IDENTITY, true, false),
        Similarity::IDENTITY,
        domain,
        &mut scratch,
    )?;
    let regions = recon_regions(size, scene);
    let t = transforms(geometry);
    let directory = out.join(format!(
        "{case:02}-{scene}-{geometry}-{}",
        if noisy { "noisy" } else { "noiseless" }
    ));
    fs::create_dir(&directory)?;
    let truth_file = save_output(&directory, "truth", &truth, size)?;
    let foil: Vec<_> = truth
        .iter()
        .map(|p| smooth(&smooth(p, size), size))
        .collect();
    let foil_detail = projection(&foil, &truth, &background, &regions[2]);
    let foil_texture = projection(&foil, &truth, &no_texture, &regions[4]);
    if scene != "flat" {
        ensure!(
            (projection(&truth, &truth, &background, &regions[2]).unwrap() - 1.0).abs() < 1e-12,
            "truth detail projection must be unity"
        );
        ensure!(
            foil_detail.is_some_and(|v| v < 0.8),
            "blur foil did not fail the detail amplitude instrument"
        );
        ensure!(
            mse(&foil, &truth, &regions[2]) > 1.0,
            "blur foil detail error was not detected"
        );
    }
    let foil_file = save_output(&directory, "blur-foil", &foil, size)?;
    let mut beta = Vec::new();
    let mut transfer = vec![vec![0.0; size.pixels()]; 4];
    for (i, &transform) in t.iter().enumerate() {
        let frame = scene_frame(scene, Some(FOCUS[i]), transform, true, true);
        let mut probe = gatefloor::Probe::new(domain, RECON_BANDS);
        let values = probe.measure(
            &frame,
            37 + i,
            transform,
            Resampler::CatmullRom,
            &mut scratch,
        )?;
        let b: Vec<_> = values
            .iter()
            .copied()
            .take_while(|v| v.is_finite())
            .collect();
        ensure!(
            b.len() >= 2,
            "both changed bands need actual finite probe beta"
        );
        beta.push(b);
        let aligned = gather_four(
            scene_frame(scene, None, transform, true, true),
            transform,
            domain,
            &mut scratch,
        )?;
        for c in 0..4 {
            for j in 0..size.pixels() {
                transfer[c][j] += aligned[c][j] / 5.0;
            }
        }
    }
    let transfer_file = save_output(&directory, "all-sharp-gather-mean-null", &transfer, size)?;
    let mut stats: Vec<_> = (0..8).map(|_| ImageStats::new(size)).collect();
    let mut rng = Rng(SEED
        .wrapping_add(0x7000_0000)
        .wrapping_add(case as u64 * 0x100_0001));
    let mut source_ratio = Moments::default();
    let mut source_clipped = 0;
    let mut first_files = Vec::new();
    for repeat in 0..repeats {
        let mut engines: Vec<_> = [Hull::InputRange, Hull::Unclamped]
            .iter()
            .flat_map(|&h| MODES.iter().map(move |&m| Reconstruction::new(size, m, h)))
            .collect();
        let mut low = vec![vec![f32::INFINITY; size.pixels()]; 4];
        let mut high = vec![vec![f32::NEG_INFINITY; size.pixels()]; 4];
        for (i, &transform) in t.iter().enumerate() {
            let clean = scene_frame(scene, Some(FOCUS[i]), transform, true, true);
            let frame = if noisy {
                let (f, v, c) = noisy_frame(&clean, &model, &mut rng);
                source_ratio.add(v);
                source_clipped += c;
                f
            } else {
                clean
            };
            let planes = gather_four(frame, transform, domain, &mut scratch)?;
            let luma = luma_of(&planes);
            let mut variance = vec![0.0; luma.len()];
            luma_variance(&luma, &model, &mut variance);
            for c in 0..4 {
                for j in 0..size.pixels() {
                    low[c][j] = low[c][j].min(planes[c][j]);
                    high[c][j] = high[c][j].max(planes[c][j]);
                }
            }
            for engine in &mut engines {
                engine.fold(&planes, &luma, &variance, &beta[i]);
            }
        }
        let coarse = engines[0].coarse();
        for engine in &engines[1..] {
            assert_eq!(
                engine.coarse(),
                coarse,
                "unchanged coarse/base accumulator moved"
            );
        }
        let output: Vec<_> = engines.iter_mut().map(Reconstruction::finish).collect();
        for planes in &output[..4] {
            for c in 0..4 {
                for j in 0..size.pixels() {
                    ensure!(
                        planes[c][j] >= low[c][j] - 0.001 && planes[c][j] <= high[c][j] + 0.001,
                        "actual InputRange finish violated input envelope"
                    );
                }
            }
        }
        if !noisy && scene == "flat" {
            for group in output.chunks_exact(4) {
                for image in &group[1..] {
                    assert_eq!(
                        image, &group[0],
                        "flat noiseless spatial mode must be exact null within each hull"
                    );
                }
            }
        }
        for arm in 0..8 {
            stats[arm].add(
                &output[arm],
                &truth,
                &background,
                &no_texture,
                &output[(arm / 4) * 4],
                &regions,
            );
            if repeat == 0 {
                first_files.push(save_output(
                    &directory,
                    &format!(
                        "first-{}-{}",
                        if arm < 4 { "input-range" } else { "unclamped" },
                        ARM_NAMES[arm % 4]
                    ),
                    &output[arm],
                    size,
                )?);
            }
        }
    }
    ensure!(source_clipped == 0, "source noise clipped");
    let mut arms = Vec::new();
    for (arm, stat) in stats.iter().enumerate() {
        let (mean, report) = stat.finish(&truth, &regions, repeats);
        let image = save_output(
            &directory,
            &format!(
                "mean-{}-{}",
                if arm < 4 { "input-range" } else { "unclamped" },
                ARM_NAMES[arm % 4]
            ),
            &mean,
            size,
        )?;
        arms.push(json!({"arm":ARM_NAMES[arm%4],"hull":if arm<4 {"InputRange: primary"} else {"Unclamped: diagnostic"},
            "metrics":report,"mean_output":image,"first_output":first_files[arm]}));
    }
    let report = json!({
        "schema":"rea-reconstruction-truth-case-v1","scene":scene,"geometry":geometry,
        "noise_enabled":noisy,"repeats":repeats,"focus_positions":FOCUS,"sigma_native":"2.8*distance-to-layer-focus",
        "native_source_size":[SIDE,SIDE],"quad_crop":[4,4,size.width,size.height],
        "actual_probe_beta":beta,"coarse_beta":"band2 uses ordinary white fallback if absent in finite probe",
        "transforms_quad":t.iter().map(|x|json!({"a_re":x.a.re,"a_im":x.a.im,"b_re":x.b.re,"b_im":x.b.im})).collect::<Vec<_>>(),
        "noise_model":{"gain_dn_per_e":0.5,"read_noise_e":4.0,"prnu":false,"gaussian_shot_approximation":true},
        "source_variance_ratio":{"mean":source_ratio.mean,"standard_error":source_ratio.se(),"independent_frame_draws":source_ratio.n},"source_clipped":source_clipped,
        "truth":truth_file,"blur_foil":{"file":foil_file,"detail_projection":foil_detail,"texture_projection":foil_texture,
            "detail_mse_dn2":mse(&foil,&truth,&regions[2])},
        "all_sharp_transfer_null":{"file":transfer_file,"interior_mse_dn2":mse(&transfer,&truth,&regions[1]),
            "meaning":"same exact geometry/gather, all layers sharp; arithmetic mean, no source selector"},
        "coarse_base_accumulator_exact_across_arms":true,"input_range_envelope_verified":true,
        "arms":arms,
        "interpretation":"A generated falsifier for the finished reconstruction; no camera PSF calibration and no photographic quality conclusion."
    });
    fs::write(
        directory.join("report.json"),
        serde_json::to_vec_pretty(&report)?,
    )?;
    Ok(json!({"directory":directory.file_name().unwrap().to_string_lossy(),"report":report}))
}

#[test]
#[ignore = "root schedules bounded actual-finish synthetic screen; fresh output directory required"]
fn actual_reconstruction_truth_screen() -> Result<()> {
    let out = PathBuf::from(
        std::env::var_os("STREHL_RECON_NOISE_OUT")
            .context("set new absolute STREHL_RECON_NOISE_OUT")?,
    );
    ensure!(
        out.is_absolute() && !out.exists(),
        "new absolute output directory required"
    );
    let repeats: usize = std::env::var("STREHL_RECON_NOISE_REPEATS")
        .unwrap_or_else(|_| "16".into())
        .parse()?;
    ensure!(
        [16, 32].contains(&repeats),
        "use16 or32 independent noisy repeats"
    );
    ensure!(
        align_cmd::fullres_gather_enabled(),
        "normal full-resolution gather required"
    );
    ensure!(
        std::env::var("STREHL_FIX_CA").as_deref() == Ok("0"),
        "synthetic CA must be off"
    );
    ensure!(
        std::env::var("STREHL_GATE_FLOOR_SCALE").is_err(),
        "unset gate-floor scaling"
    );
    ensure!(
        std::env::var("STREHL_DEMOSAIC").is_err(),
        "unset demosaic override for normal display"
    );
    let full = PlaneGeometry {
        width: SIDE / 2,
        height: SIDE / 2,
    };
    let domain = PyramidDomain::cropped(
        full,
        align_cmd::CropRect {
            x: 4,
            y: 4,
            width: ANALYSIS_SIDE,
            height: ANALYSIS_SIDE,
        },
    )?;
    fs::create_dir(&out)?;
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let files = [
        "experiments/rea-a7c2-2026-10-24-c/noise-floor-reconstruction.rs",
        "experiments/rea-a7c2-2026-10-24-c/noise-floor-gather.rs",
        "crates/strehl-cli/src/merge_cmd.rs",
        "crates/strehl-cli/src/align_cmd.rs",
        "crates/strehl-cli/src/merge_cmd/gatefloor.rs",
        "crates/strehl-core/src/pyramid.rs",
        "crates/strehl-core/src/spatial-noise-floor.rs",
        "crates/strehl-core/src/demosaic.rs",
    ];
    let hashes: Vec<_> = files
        .iter()
        .map(|f| -> Result<Value> {
            Ok(json!({"path":f,"sha256":digest(&fs::read(root.join(f))?)}))
        })
        .collect::<Result<_>>()?;
    let exe = std::env::current_exe()?;
    let env: std::collections::BTreeMap<_, _> = std::env::vars()
        .filter(|(k, _)| k.starts_with("STREHL_") || k == "RAYON_NUM_THREADS")
        .collect();
    fs::write(
        out.join("plan.json"),
        serde_json::to_vec_pretty(&json!({
            "schema":"rea-reconstruction-truth-plan-v1","status":"RUNNING until summary.json exists",
            "source_hashes":hashes,"executable":exe,"executable_sha256":digest(&fs::read(&exe)?),
            "software":crate::SOFTWARE,"environment":env,"rayon_threads":rayon::current_num_threads(),
            "scenes":["flat","step_lines","strand_texture"],"geometry":["identity","fractional","curved"],
            "noiseless_repeats":1,"noisy_repeats":repeats,"frames_per_stack":5,
            "actual_consumer":"4CFA planes; actual u16 gather and injected noise; actual BandMerge finish; normal core demosaic once",
            "config":{"bands":3,"gate":2,"exponent":2,"ramp":1.4,"base":"Mean","admission":"HardFloor","mean_coarse":0,
                "hulls":["InputRange: primary","Unclamped: diagnostic"],"sharpening":false},
            "truth":"fixed analytic Gaussian-layer toy, inverse exact placement in source sensor; no fitted reference or raw-band argmax",
            "display":"128x128 native, identical fixed transfer; mean and first repeat saved for every arm",
            "acceptance":"falsifier only; blur foil must lose detail; quantify paired MSE,bias,variance,detail and texture. No quality win asserted by passing test.",
        }))?,
    )?;
    let mut reports = Vec::new();
    for scene in ["flat", "step_lines", "strand_texture"] {
        for geometry in ["identity", "fractional", "curved"] {
            for noisy in [false, true] {
                eprintln!(
                    "reconstruction case {}/18: {scene}/{geometry}/{}",
                    reports.len() + 1,
                    if noisy { "noisy" } else { "noiseless" }
                );
                reports.push(reconstruction_case(
                    scene,
                    geometry,
                    noisy,
                    if noisy { repeats } else { 1 },
                    domain,
                    &out,
                    reports.len(),
                )?);
            }
        }
    }
    fs::write(
        out.join("summary.json"),
        serde_json::to_vec_pretty(&json!({
            "schema":"rea-reconstruction-truth-summary-v1","status":"COMPLETE","quality_claim":false,"cases":reports,
        }))?,
    )?;
    Ok(())
}
