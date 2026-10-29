//! Bounded multi-window full-track census. Each original is loaded once per
//! track phase and reused across all windows; no aligned source volume.
use super::*;
struct WindowState {
    domain: SamplingDomain,
    builder: FocusEvidenceBuilder,
    sampler: NativeSampler,
    field: FocusField,
    green: Vec<f32>,
    fine: Vec<f32>,
    regularized: Vec<f32>,
    scratch: Vec<f32>,
    masks: Vec<u32>,
    valid: Vec<bool>,
}
impl WindowState {
    fn new(domain: SamplingDomain, frames: &[FocusFrame]) -> Result<Self> {
        let geometry = PlaneGeometry {
            width: domain.width,
            height: domain.height,
        };
        let n = geometry.pixels();
        Ok(Self {
            domain,
            builder: FocusEvidenceBuilder::new(
                geometry,
                frames.to_vec(),
                FocusEvidencePolicy::default(),
                64 << 20,
            )?,
            sampler: NativeSampler::new(domain)?,
            field: FocusField::new(geometry),
            green: vec![0.; n],
            fine: vec![0.; n],
            regularized: vec![0.; n],
            scratch: vec![0.; n],
            masks: vec![0; n],
            valid: vec![false; n],
        })
    }
    fn observe(
        &mut self,
        source: Option<&CachedSource>,
        placement: Option<Similarity>,
        ordinal: usize,
        frame: FocusFrame,
        phase: usize,
        noise: &NoiseModel,
        profile: Option<&OpticalProfile>,
        map: &WarpMap,
    ) -> Result<()> {
        let geometry = PlaneGeometry {
            width: self.domain.width,
            height: self.domain.height,
        };
        if let (Some(source), Some(placement)) = (source, placement) {
            let s = self.sampler.gather(
                source,
                source.levels(),
                placement,
                profile,
                map.resampler(),
            )?;
            green(&s.planes, &mut self.green);
            complete_support(
                &s.support,
                geometry,
                window_radius() + 1 + REGULARISER_RADIUS,
                &mut self.masks,
                &mut self.valid,
            )?;
            self.field
                .compute_with_fine(&self.green, noise, FINE_WINDOW_RADIUS, &mut self.fine);
            regularise(
                self.field.values(),
                geometry,
                &mut self.scratch,
                &mut self.regularized,
            );
        } else {
            self.valid.fill(false);
            self.fine.fill(0.);
            self.regularized.fill(0.);
        }
        if phase == 0 {
            self.builder
                .observe_anchor(ordinal, frame, &self.regularized, &self.valid)?;
        } else {
            self.builder.observe_shape(
                ordinal,
                frame,
                &self.fine,
                &self.regularized,
                &self.valid,
            )?;
        }
        Ok(())
    }
}
fn census_domain(
    full: PlaneGeometry,
    origin: [usize; 2],
    size: usize,
    halo: usize,
) -> Result<SamplingDomain> {
    let [x, y] = origin;
    ensure!(
        x / 2 >= halo && y / 2 >= halo,
        "census origins need complete focus halo"
    );
    // A physical ROI may begin at either CFA parity. Floor-half anchors the
    // surrounding guide domain, while the original sensor origin is retained
    // by the output and nearest-guide coordinate calculations.
    let domain = SamplingDomain {
        full,
        x: x / 2 - halo,
        y: y / 2 - halo,
        width: size / 2 + 2 * halo + 2,
        height: size / 2 + 2 * halo + 2,
    };
    domain.validate()?;
    ensure!(
        domain.width * 2 <= 384 && domain.height * 2 <= 384,
        "expanded census domain exceeds384sensor"
    );
    Ok(domain)
}
#[cfg(test)]
mod domain_tests {
    use super::*;
    #[test]
    fn census_odd_physical_origins_preserve_full_guide_gauge_and_complete_halo() {
        let full = PlaneGeometry {
            width: 3516,
            height: 2344,
        };
        let halo = window_radius() + 1 + REGULARISER_RADIUS + 3;
        for origin in [[4105, 3245], [5305, 1945], [4105, 545], [4104, 3244]] {
            let d = census_domain(full, origin, 192, halo).unwrap();
            for axis in 0..2 {
                let start = if axis == 0 { d.x } else { d.y };
                let length = if axis == 0 { d.width } else { d.height };
                let first = (origin[axis] as f64 - 0.5) * 0.5 - start as f64;
                let last = ((origin[axis] + 191) as f64 - 0.5) * 0.5 - start as f64;
                assert!(first >= halo as f64 - 0.25);
                assert!(length as f64 - 1. - last >= halo as f64);
                assert_eq!(2. * (first + start as f64) + 0.5, origin[axis] as f64);
            }
        }
        assert!(census_domain(full, [1, 1], 192, halo).is_err());
        assert!(census_domain(full, [7000, 4600], 192, halo).is_err());
    }
}
#[allow(clippy::too_many_arguments)]
pub(super) fn run(
    args: &Args,
    session: &ResolvedSession,
    ids: &[SourceIdentity],
    map: &WarpMap,
    noise: &NoiseModel,
    profile: Option<&OpticalProfile>,
    calibration: &Value,
    alignment: &Value,
) -> Result<()> {
    let started = Instant::now();
    ensure!(
        !args.census_rois.is_empty()
            && args.census_rois.len() % 2 == 0
            && args.census_rois.len() <= 6,
        "census accepts one to three x,y pairs"
    );
    ensure!(
        args.size <= 192 && args.workers <= 4,
        "census authorized at <=192 sensor side and <=4 workers"
    );
    let g = map.geometry();
    let halo = window_radius() + 1 + REGULARISER_RADIUS + 3;
    let origins: Vec<[usize; 2]> = args
        .census_rois
        .chunks_exact(2)
        .map(|v| [v[0], v[1]])
        .collect();
    let domains = origins
        .iter()
        .map(|&origin| census_domain(g, origin, args.size, halo))
        .collect::<Result<Vec<_>>>()?;
    // Reserve cache, complete full-source sampler masks, all builders and input
    // rasters simultaneously; the master is dropped before original cache loads.
    let mut workspace = 0usize;
    for &d in &domains {
        let geometry = PlaneGeometry {
            width: d.width,
            height: d.height,
        };
        let track = session
            .passes
            .iter()
            .map(|p| p.global_range.len())
            .max()
            .unwrap();
        workspace = workspace
            .checked_add(strehl_cli::session_sampling::sampling_bytes(d)?)
            .and_then(|b| {
                b.checked_add(FocusEvidenceBuilder::reservation_bytes(geometry, track).ok()?)
            })
            .and_then(|b| b.checked_add(geometry.pixels() * 32))
            .context("census reservation overflow")?;
    }
    let reserved = CACHE_BUDGET
        .checked_add(512 << 20)
        .and_then(|b| b.checked_add(workspace))
        .context("census reservation overflow")?;
    ensure!(reserved <= TOTAL_LIMIT, "census reservation exceeds2GiB");
    let out = session.ensure_fresh_output(&args.out)?;
    fs::create_dir(&out)?;
    let report = json_read(&args.render_dir.join("render-report.json"))?;
    let crop = report["canvas"].as_array().context("canvas")?;
    let mx = 2 * crop[0].as_u64().context("canvas x")? as usize;
    let my = 2 * crop[1].as_u64().context("canvas y")? as usize;
    let master = strehl_edit::load_tiff(&args.render_dir.join("master.tiff"))?;
    ensure!(
        master.origin == ImageOrigin::SceneLinear,
        "native census is not scene linear"
    );
    let reference = report["development_reference_pass"]
        .as_u64()
        .context("development reference")? as usize;
    let cal = calibration
        .get(reference)
        .context("development reference outside calibration")?;
    let wb: [f32; 3] = serde_json::from_value(cal["white_balance"].clone())?;
    let matrix: [[f32; 3]; 3] = serde_json::from_value(cal["color_matrix"][0].clone())?;
    let levels = Levels {
        black: cal["noise_planes"][0]["black"].as_f64().context("black")? as f32,
        white: cal["noise_planes"][0]["white"].as_f64().context("white")? as f32,
    };
    let render = color::camera_to_srgb(matrix)
        .context("camera matrix")?
        .with_saturation(levels, wb, 1.);
    let inverse = inverse(*render.matrix())?;
    let knee = strehl_core::highlight::knee().unwrap_or(1.);
    let mut roi_reports = Vec::new();
    for (roi, &[x, y]) in origins.iter().enumerate() {
        ensure!(
            x >= mx
                && y >= my
                && x + args.size <= mx + master.width as usize
                && y + args.size <= my + master.height as usize,
            "census outside native master"
        );
        let dir = out.join(format!("roi-{roi}"));
        fs::create_dir(&dir)?;
        let mut pixels = Vec::with_capacity(args.size * args.size * 3);
        let mut eligible = Vec::with_capacity(args.size * args.size);
        for yy in 0..args.size {
            for xx in 0..args.size {
                let p = ((y - my + yy) * master.width as usize + x - mx + xx) * 3;
                let rgb: [f32; 3] = master.pixels[p..p + 3].try_into().unwrap();
                pixels.extend(rgb);
                eligible.push(u8::from(
                    native_camera_pixel(rgb, &render, inverse, wb, levels, knee).is_some(),
                ));
            }
        }
        strehl_edit::save_linear_tiff(
            &dir.join("native.tiff"),
            &LinearImage {
                width: args.size as u32,
                height: args.size as u32,
                pixels,
                origin: ImageOrigin::SceneLinear,
                baseline: master.baseline,
                baked_recipe: None,
            },
        )?;
        write_new(&dir.join("native-linear-eligible.u8"), &eligible)?;
        let d = domains[roi];
        roi_reports.push(json!({"index":roi,"roi_sensor":[x,y,args.size,args.size],"focus_domain_quad":[d.x,d.y,d.width,d.height],"radius_from_fitting_center_sensor":((x+args.size/2) as f64-g.width as f64-0.5).hypot((y+args.size/2) as f64-g.height as f64-0.5),"passes":[]}));
    }
    drop(master);
    let binding = if args.historical_cache {
        Some(historical_cache::binding()?)
    } else {
        None
    };
    let mut cache = if args.historical_cache {
        OriginalCache::Historical(historical_cache::HistoricalCache::new(
            &args.cache,
            ids,
            CACHE_BUDGET,
            g,
        )?)
    } else {
        OriginalCache::Current(SourceCache::new(&args.cache, session, CACHE_BUDGET)?)
    };
    for id in ids {
        ensure!(
            cache.cache_path(id)?.is_file(),
            "missing original cache {}",
            id.path.display()
        );
    }
    for pass in 0..session.passes.len() {
        let frames: Vec<_> = session.passes[pass]
            .global_range
            .clone()
            .map(|global_index| FocusFrame {
                acquisition: global_index as u64,
                global_index,
            })
            .collect();
        let mut states = domains
            .iter()
            .map(|&d| WindowState::new(d, &frames))
            .collect::<Result<Vec<_>>>()?;
        for phase in 0..2 {
            if phase == 1 {
                for state in &mut states {
                    state.builder.begin_shape_pass()?;
                }
            }
            for (ordinal, &frame) in frames.iter().enumerate() {
                let placement = map.warps()[frame.global_index].placed();
                let source = if placement.is_some() {
                    Some(
                        cache
                            .load(&ids[frame.global_index])?
                            .context("census original miss; decode prohibited")?,
                    )
                } else {
                    None
                };
                for state in &mut states {
                    state.observe(
                        source.as_deref(),
                        placement,
                        ordinal,
                        frame,
                        phase,
                        noise,
                        profile,
                        map,
                    )?;
                }
                if ordinal % 50 == 0 || ordinal + 1 == frames.len() {
                    eprintln!(
                        "batch census pass{pass} phase{phase}: {}/{} originals, {} windows",
                        ordinal + 1,
                        frames.len(),
                        states.len()
                    );
                }
            }
        }
        for (roi, state) in states.into_iter().enumerate() {
            let field = state.builder.finish()?;
            let dir = out.join(format!("roi-{roi}"));
            for (name, values) in [
                ("ordinal", &field.ordinal),
                ("width", &field.width_frames),
                ("prominence", &field.prominence_sigma),
                ("perplexity", &field.perplexity),
                ("unresolved", &field.unresolved_mode_prominence_sigma),
            ] {
                write_f32(
                    &dir.join(format!("focus-pass-{pass}-{name}.f32")),
                    values.iter().copied(),
                )?;
            }
            write_new(
                &dir.join(format!("focus-pass-{pass}-flags.u8")),
                &field.flags,
            )?;
            write_f32(
                &dir.join(format!("focus-pass-{pass}-mode-ordinals.f32")),
                field.modes.iter().flatten().map(|m| m.ordinal),
            )?;
            write_f32(
                &dir.join(format!("focus-pass-{pass}-mode-prominence.f32")),
                field.modes.iter().flatten().map(|m| m.prominence_sigma),
            )?;
            write_new(
                &dir.join(format!("focus-pass-{pass}-mode-boundary.u8")),
                &field
                    .modes
                    .iter()
                    .flatten()
                    .map(|m| u8::from(m.boundary))
                    .collect::<Vec<_>>(),
            )?;
            let flag_counts: Vec<_> = (0..7)
                .map(|b| field.flags.iter().filter(|v| **v & (1 << b) != 0).count())
                .collect();
            roi_reports[roi]["passes"].as_array_mut().unwrap().push(json!({"pass_index":pass,"global_range":[session.passes[pass].global_range.start,session.passes[pass].global_range.end],"usable_expanded_quad_pixels":field.usable.iter().filter(|v|**v).count(),"flag_bits_1_2_4_8_16_32_64":flag_counts}));
        }
    }
    let stats = cache.stats();
    ensure!(stats.decodes == 0, "unexpected RAW decode");
    let result = json!({"schema":"strehl.sr-focus-census.v1","command":std::env::args().collect::<Vec<_>>(),"build":env!("STREHL_BUILD_ID"),"source_sha256":hex(&Sha256::digest(include_bytes!("focus-census.rs"))),"input_render":args.render_dir,"alignment_sha256":hash(&args.render_dir.join("alignment.json"))?,"warpmap_sha256":alignment["warpmap_sha256"],"full_guide_geometry":[g.width,g.height],"rois":roi_reports,"sampling_policy":"all windows consume one loaded original per track phase; 2 complete focus phases per pass; no candidate reconstruction","focus_policy":"unchanged shared FocusEvidencePolicy default, complete filter support, all modes and flags exported","raw_decodes":stats.decodes,"cache_disk_hits":stats.disk_hits,"cache_peak_cfa_bytes":stats.peak_resident_cfa_bytes,"historical_binding":binding,"reserved_bytes":reserved,"workers":args.workers,"seconds":started.elapsed().as_secs_f64(),"photographic_gain":"not evaluated; source/ROI selection evidence only"});
    write_new(
        &out.join("report.json"),
        &serde_json::to_vec_pretty(&result)?,
    )?;
    println!("{}", serde_json::to_string_pretty(&result)?);
    Ok(())
}
