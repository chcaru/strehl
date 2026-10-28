use super::*;
use strehl_core::plane::QuadSource;

struct LabelledCfa {
    geom: PlaneGeometry,
    data: Vec<u16>,
}
impl QuadSource for LabelledCfa {
    fn geometry(&self) -> PlaneGeometry {
        self.geom
    }
    fn quad_rows(&self, y: usize) -> (&[u16], &[u16]) {
        let stride = self.geom.width * 2;
        let start = y * 2 * stride;
        (
            &self.data[start..start + stride],
            &self.data[start + stride..start + 2 * stride],
        )
    }
}
fn guide_commission() -> Value {
    let geom = PlaneGeometry {
        width: 6,
        height: 4,
    };
    let stride = geom.width * 2;
    let mut data = vec![0u16; geom.pixels() * 4];
    for y in 0..geom.height {
        for x in 0..geom.width {
            data[2 * y * stride + 2 * x] = 2512 + (3 * x + 2 * y) as u16;
            data[2 * y * stride + 2 * x + 1] = 612 + (5 * x + 7 * y) as u16;
            data[(2 * y + 1) * stride + 2 * x] = 812 + (11 * x + 13 * y) as u16;
            data[(2 * y + 1) * stride + 2 * x + 1] = 3512 + (17 * x + 19 * y) as u16;
        }
    }
    data[1] = 500; // Individual green clamping is part of the real guide.
    let source = LabelledCfa { geom, data };
    let before = source.data.clone();
    let mut got = vec![0.; geom.pixels()];
    green_luma(&source, 512., &mut got);
    let mut wrong_source = LabelledCfa {
        geom,
        data: source.data.clone(),
    };
    for y in 0..geom.height {
        for x in 0..geom.width {
            wrong_source.data[2 * y * stride + 2 * x + 1] = source.data[2 * y * stride + 2 * x];
            wrong_source.data[(2 * y + 1) * stride + 2 * x] =
                source.data[(2 * y + 1) * stride + 2 * x + 1];
        }
    }
    let mut wrong_phase = vec![0.; geom.pixels()];
    green_luma(&wrong_source, 512., &mut wrong_phase);
    let mut expected = Vec::new();
    let mut points = Vec::new();
    for y in 0..geom.height {
        for x in 0..geom.width {
            let a = (source.data[2 * y * stride + 2 * x + 1] as f32 - 512.).max(0.);
            let b = (source.data[(2 * y + 1) * stride + 2 * x] as f32 - 512.).max(0.);
            expected.push((a + b) * 0.5);
            let physical = [
                (2 * x + 1) as f64 * 0.5 + (2 * x) as f64 * 0.5,
                (2 * y) as f64 * 0.5 + (2 * y + 1) as f64 * 0.5,
            ];
            points.push(json!({"guide":[x,y],"literal_green_centroid":physical,
            "expected_native":[2.*x as f64+0.5,2.*y as f64+0.5]}));
        }
    }
    let bits = |v: &[f32]| v.iter().map(|x| x.to_bits()).collect::<Vec<_>>();
    let exact = bits(&got) == bits(&expected);
    let wrong_phase_rejected = bits(&wrong_phase) != bits(&expected);
    let coordinates = points
        .iter()
        .all(|p| p["literal_green_centroid"] == p["expected_native"]);
    let wrong_origin_rejected = points.iter().any(|p| {
        p["literal_green_centroid"][0].as_f64().unwrap()
            != 2. * p["guide"][0].as_u64().unwrap() as f64
    });
    json!({"pass":exact&&wrong_phase_rejected&&coordinates&&wrong_origin_rejected&&source.data==before,
        "actual_green_luma_bits_exact":exact,"wrong_RB_phase_foil_rejected":wrong_phase_rejected,
        "coordinates_exact":coordinates,"wrong_missing_half_origin_rejected":wrong_origin_rejected,
        "original_u16_unchanged":source.data==before,"actual_bits":bits(&got),"expected_bits":bits(&expected),
        "wrong_phase_bits":bits(&wrong_phase),"coordinates":points,
        "phase_scope":"G1/G2 swap would cancel in mean; actual R/B substitution foil used"})
}
fn edge_json(e: &AlignEdge) -> Value {
    json!({"i":e.i,"j":e.j,"a":[f64_json(e.t.a.re),f64_json(e.t.a.im)],
        "b":[f64_json(e.t.b.re),f64_json(e.t.b.im)],"rms":f64_json(e.rms),
        "used":e.used,"lever":f64_json(e.lever)})
}

#[test]
#[ignore = "root-owned actual alignment observer controls"]
fn generated_controls() -> Result<()> {
    let out = PathBuf::from(std::env::var("STREHL_INSECT_PLACEMENT_CONTROL_OUT")?);
    std::fs::create_dir(&out)?;
    let guide = guide_commission();
    let geom = PlaneGeometry {
        width: 192,
        height: 128,
    };
    let detail: Vec<f32> = (0..geom.pixels())
        .map(|i| {
            let (x, y) = ((i % geom.width) as f32, (i / geom.width) as f32);
            120. + 25. * (x / 4.7 + y / 7.1).sin() + 19. * (x / 11.3 - y / 3.9).cos()
        })
        .collect();
    let mut seed = 0x93a761d2_u32;
    let noise = (0..geom.pixels())
        .map(|_| {
            seed = seed.wrapping_mul(1664525).wrapping_add(1013904223);
            80. + (seed >> 24) as f32 * 0.3
        })
        .collect();
    // Three identical static guides form one cycle. This is observer parity,
    // not a deep-track accuracy or extra-acquisition-information control.
    let st = Stack {
        geom,
        planes: vec![
            detail.clone(),
            detail.clone(),
            detail,
            vec![100.; geom.pixels()],
            noise,
        ],
    };
    let before: Vec<String> = st.planes.iter().map(|p| guide_hash(p)).collect();
    let pairs: Vec<(usize, usize)> = (0..5)
        .flat_map(|i| (i + 1..5).map(move |j| (i, j)))
        .collect();
    let cfg = AlignConfig {
        coarse_factors: vec![2],
        coarse_tile: 12,
        coarse_grid: (4, 3),
        coarse_radius: 3,
        fine_tile: 24,
        fine_grid: (5, 4),
        fine_radius: 3,
        margin: 12,
        min_tiles: 6,
        min_contrast: 2.,
        min_peak: 0.8,
        fine_iters: 3,
        ..AlignConfig::shallow()
    };
    let ordinary = measure_edges(&st, &pairs, &cfg, 2)?;
    let captured = Mutex::new(Vec::<PairMeasurementTrace>::new());
    let collector = |record| captured.lock().unwrap().push(record);
    let observed = measure_edges_traced(&st, &pairs, &cfg, 2, None, Some(&collector))?;
    let mut traces = captured.into_inner().unwrap();
    traces.sort_by_key(|p| p.ordinal);
    let ordinary_rows: Vec<Value> = ordinary.iter().map(edge_json).collect();
    let observed_rows: Vec<Value> = observed.iter().map(edge_json).collect();
    let edge_exact = ordinary_rows == observed_rows;
    let accepted: Vec<(usize, usize)> = observed.iter().map(|e| (e.i, e.j)).collect();
    let census = traces.len() == pairs.len()
        && traces.iter().enumerate().all(|(k, t)| {
            t.ordinal == k && (t.i, t.j) == pairs[k] && t.unavailable.is_none() && t.core.is_some()
        });
    let mut selected = true;
    let mut saw_refusal = false;
    let mut saw_selected = false;
    for t in &traces {
        if let Some(core) = &t.core {
            if core.result.is_ok() {
                saw_selected = true;
                selected &= core
                    .selected_fine_pass
                    .and_then(|i| core.fine_passes.get(i))
                    .is_some_and(|p| result_json(&p.stage.result) == result_json(&core.result));
            } else {
                saw_refusal = true;
                selected &= core.selected_fine_pass.is_none();
            }
        }
    }
    let entries: Vec<(String, u64)> = (0..5)
        .map(|i| (format!("control-{i}.ARW"), (geom.pixels() * 4) as u64))
        .collect();
    let identity = StackIdentity::from_entries("observer-parity-static", &entries);
    let map0 = finish_measured_map(
        identity.clone(),
        geom,
        5,
        0,
        &[1, 2, 3, 4],
        Resampler::CatmullRom,
        &ordinary,
        None,
    )?;
    let map1 = finish_measured_map(
        identity,
        geom,
        5,
        0,
        &[1, 2, 3, 4],
        Resampler::CatmullRom,
        &observed,
        None,
    )?;
    let w0: Vec<Value> = map0.warps().iter().map(warp_json).collect();
    let w1: Vec<Value> = map1.warps().iter().map(warp_json).collect();
    let map_exact = w0 == w1 && map0.to_text() == map1.to_text();
    let states = matches!(map1.warps()[0], FrameWarp::Placed(_))
        && matches!(map1.warps()[1], FrameWarp::Placed(_))
        && matches!(map1.warps()[2], FrameWarp::Placed(_))
        && matches!(map1.warps()[3], FrameWarp::Refused(_))
        && matches!(map1.warps()[4], FrameWarp::Refused(_));
    let after: Vec<String> = st.planes.iter().map(|p| guide_hash(p)).collect();
    let unchanged = before == after;
    let pass = guide["pass"] == true
        && edge_exact
        && census
        && selected
        && saw_refusal
        && saw_selected
        && accepted == vec![(0, 1), (0, 2), (1, 2)]
        && map_exact
        && states
        && unchanged;
    let receipt = json!({"status":"COMPLETE_INSECT_PLACEMENT_CONTROLS","all_cases_completed":true,
        "mechanical_pass":pass,"all_pass":pass,"guide_commission":guide,
        "config":config_json(&cfg),"workers":2,"requested_pairs":pairs,
        "edge_bits_exact":edge_exact,"ordinary_edges":ordinary_rows,"observed_edges":observed_rows,
        "pair_census_exact":census,"selected_pass_exact":selected,"saw_refusal":saw_refusal,
        "traces":traces.iter().map(pair_json).collect::<Vec<_>>(),
        "normal_solve_map_exact":map_exact,"placed_and_refused_states_correct":states,
        "ordinary_placements":w0,"observed_placements":w1,
        "connected_component_cycle_rank":1,"guide_hashes_before":before,"guide_hashes_after":after,
        "original_guide_bytes_unchanged":unchanged,"RAW_reads":0,"photographic_admission":false,
        "placement_improvement_claimed":false,"scope":"static parity only; no curved-track accuracy claim"});
    write_json(&out.join("screen.json"), &receipt)?;
    ensure!(
        pass,
        "actual observer mechanics refused; complete evidence retained"
    );
    Ok(())
}
