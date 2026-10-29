//! Descriptive original-sample export. Never feeds fitting or admission.
use super::*;
use strehl_core::plane::QuadSource;

fn original_bytes(
    source: &dyn QuadSource,
    origin: [usize; 2],
    side: usize,
    parity: [usize; 2],
) -> Result<Vec<u8>> {
    let g = source.geometry();
    ensure!(
        parity.iter().all(|&v| v <= 1)
            && origin[0].checked_add(side).is_some_and(|v| v <= g.width)
            && origin[1].checked_add(side).is_some_and(|v| v <= g.height),
        "original plane rectangle or CFA parity outside active area"
    );
    let mut bytes = Vec::with_capacity(side * side * 2);
    for py in origin[1]..origin[1] + side {
        let (top, bottom) = source.quad_rows(py);
        let row = if parity[1] == 0 { top } else { bottom };
        for px in origin[0]..origin[0] + side {
            bytes.extend_from_slice(&row[2 * px + parity[0]].to_le_bytes());
        }
    }
    Ok(bytes)
}

pub(super) fn export(inputs: &Inputs, out: &Path) -> Result<()> {
    let l = inputs.lattice;
    let center = l.position(l.width / 2, l.height / 2);
    let side = l.width / 2;
    let mut records = Vec::new();
    for (i, original) in inputs.originals.iter().enumerate() {
        for (plane, color, parity) in [
            (0, 0, [0, 0]),
            (1, 1, [1, 0]),
            (2, 2, [1, 1]),
            (3, 1, [0, 1]),
        ] {
            let p = sensor_pull(inputs.pulls[i][color], l.full, center);
            let x = ((p[0] - parity[0] as f64) * 0.5).round() as isize - side as isize / 2;
            let y = ((p[1] - parity[1] as f64) * 0.5).round() as isize - side as isize / 2;
            let g = original.geometry();
            ensure!(
                x >= 0 && y >= 0 && x as usize + side <= g.width && y as usize + side <= g.height,
                "original diagnostic patch outside active area"
            );
            let bytes = original_bytes(original.as_ref(), [x as usize, y as usize], side, parity)?;
            let name = format!("original-{}-plane-{plane}.u16", inputs.acquisitions[i]);
            write_new(&out.join(&name), &bytes)?;
            let pn = inputs.noise[plane];
            records.push(json!({
                "acquisition": inputs.acquisitions[i], "plane": plane,
                "origin_quad": [x,y], "side_quad": side, "parity_sensor": parity,
                "source_pull": {"a":[inputs.pulls[i][color].a.re,inputs.pulls[i][color].a.im],
                                "b":[inputs.pulls[i][color].b.re,inputs.pulls[i][color].b.im]},
                "file": name, "sha256": hex(&Sha256::digest(&bytes)),
                "black":pn.levels.black,"white":pn.levels.white,
                "gain_dn_per_e":pn.gain_dn_per_e,"read_noise_e":pn.read_noise_e,
                "photometric_gain":inputs.gains[i],
            }));
        }
    }
    write_new(
        &out.join("original-patch-diagnostics.json"),
        &serde_json::to_vec_pretty(&json!({
            "schema":"strehl.original-patch-diagnostics.v1",
            "source_sha256":hex(&Sha256::digest(include_bytes!("original-patch-diagnostics.rs"))),
            "scope":"Unresampled original u16 active-area same-color planes at saved pulls; separate rectangular original grids, not aligned images. Descriptive sampled spectra do not identify unaliased optical bandwidth. Never consumed by reconstruction, source selection, registration or admission.",
            "roi_sensor":[l.origin_sensor[0],l.origin_sensor[1],l.width,l.height],
            "records": records,
        }))?,
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    struct Sensor(Vec<u16>);
    impl QuadSource for Sensor {
        fn geometry(&self) -> PlaneGeometry {
            PlaneGeometry {
                width: 7,
                height: 6,
            }
        }
        fn quad_rows(&self, py: usize) -> (&[u16], &[u16]) {
            let start = py * 28;
            (&self.0[start..start + 14], &self.0[start + 14..start + 28])
        }
    }
    #[test]
    fn all_parities_preserve_original_codes_at_nonzero_sensor_origin() {
        let source = Sensor((0..168).map(|v| v as u16 + 512).collect());
        for parity in [[0, 0], [1, 0], [1, 1], [0, 1]] {
            let bytes = original_bytes(&source, [2, 1], 3, parity).unwrap();
            let actual: Vec<_> = bytes
                .chunks_exact(2)
                .map(|v| u16::from_le_bytes([v[0], v[1]]))
                .collect();
            let expected: Vec<_> = (1..4)
                .flat_map(|y| {
                    (2..5).map(move |x| (512 + (2 * y + parity[1]) * 14 + 2 * x + parity[0]) as u16)
                })
                .collect();
            assert_eq!(actual, expected);
        }
        assert!(original_bytes(&source, [5, 4], 3, [0, 0]).is_err());
        assert!(original_bytes(&source, [2, 1], 3, [2, 0]).is_err());
    }
}
