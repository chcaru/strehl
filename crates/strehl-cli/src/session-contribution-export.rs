//! Saved coefficient attribution, separately labelled from photograph pixels.
use super::*;
use std::fs::OpenOptions;
use std::io::{BufWriter, Read, Write};
use strehl_core::pyramid::session_fusion::{
    AttributionKind, BandAttribution, CoefficientAttribution,
};

pub(super) fn save(
    destination: &Path,
    bands: &[BandAttribution],
    domain: SamplingDomain,
) -> Result<Value> {
    let root = destination.join("contributions");
    std::fs::create_dir(&root)?;
    let mut reports = Vec::new();
    type Field = (&'static str, fn(&CoefficientAttribution) -> f32);
    let fields: [Field; 13] = [
        ("effective-sources", |v| v.effective_sources),
        ("contributing-sources", |v| v.contributing_sources as f32),
        ("primary-fraction", |v| v.primary_fraction),
        ("dominant-source-fraction", |v| v.dominant_source_fraction),
        ("effective-groups", |v| v.effective_groups),
        ("contributing-groups", |v| v.contributing_groups as f32),
        ("dominant-group-fraction", |v| v.dominant_group_fraction),
        ("accepted-repeat-fraction", |v| v.accepted_repeat_fraction),
        ("fixed-guide-fraction", |v| v.fixed_guide_fraction),
        ("luma-conditional-variance", |v| v.conditional_variance[0]),
        ("color-conditional-variance-bound", |v| {
            v.conditional_variance[1]
        }),
        ("dominant-source", |v| {
            if v.contributing_sources > 0 {
                v.dominant_source as f32
            } else {
                f32::NAN
            }
        }),
        ("dominant-group", |v| {
            if v.contributing_groups > 0 {
                v.dominant_group as f32
            } else {
                f32::NAN
            }
        }),
    ];
    for (k, band) in bands.iter().enumerate() {
        ensure!(
            band.width.checked_mul(band.height) == Some(band.coefficients.len()),
            "invalid contribution dimensions"
        );
        ensure!(
            band.coefficients
                .iter()
                .all(|v| v.dominant_source <= 16_777_216 && v.dominant_group <= 16_777_216),
            "source IDs exceed exact map encoding"
        );
        let dir = root.join(format!("band-{k:02}"));
        std::fs::create_dir(&dir)?;
        let mut files = Vec::new();
        for (name, field) in fields {
            let values: Vec<_> = band.coefficients.iter().map(field).collect();
            let path = dir.join(format!("{name}.tiff"));
            let mut writer = BufWriter::new(
                OpenOptions::new()
                    .write(true)
                    .create_new(true)
                    .open(&path)?,
            );
            tiff::encoder::TiffEncoder::new(&mut writer)?
                .write_image::<tiff::encoder::colortype::Gray32Float>(
                    band.width.try_into()?,
                    band.height.try_into()?,
                    &values,
                )?;
            writer.flush()?;
            writer.get_ref().sync_all()?;
            files.push(receipt(&path)?);
        }
        let values: Vec<u8> = band
            .coefficients
            .iter()
            .map(|v| match v.kind {
                AttributionKind::Uncovered => 0,
                AttributionKind::Weighted => 1,
                AttributionKind::PlainMean => 2,
                AttributionKind::SaturatedMean => 3,
                AttributionKind::SaturatedPrimary => 4,
            })
            .collect();
        let path = dir.join("kind.tiff");
        let mut writer = BufWriter::new(
            OpenOptions::new()
                .write(true)
                .create_new(true)
                .open(&path)?,
        );
        tiff::encoder::TiffEncoder::new(&mut writer)?
            .write_image::<tiff::encoder::colortype::Gray8>(
                band.width.try_into()?,
                band.height.try_into()?,
                &values,
            )?;
        writer.flush()?;
        writer.get_ref().sync_all()?;
        files.push(receipt(&path)?);
        reports.push(json!({"band":k,"dimensions":[band.width,band.height],"origin_quad":[domain.x,domain.y],"step_quad":1usize<<k,"files":files}));
    }
    let report = json!({"schema":"strehl.session-contributions.v1","domain_quad":[domain.x,domain.y,domain.width,domain.height],"bands":reports,"kind_codes":{"0":"uncovered","1":"focus weighted","2":"plain mean fallback","3":"saturated display mean","4":"saturated primary display"},"source_ids":"Global original indices in the parent source census; group IDs index proposed_groups in render-report.json.","scope":"Exact normalized source and group summaries for each band before pyramid collapse, demosaic and hull clamp. Conditional variance uses injected fixed-weight temporal models and excludes adaptive selection, shared guides and spatial/cross-band covariance. It is not final-pixel uncertainty.","missing":"NaN statistical fields and zero counts on uncovered/saturated display fallback; kind distinguishes missing evidence from zero variance."});
    write_json_new(&root.join("index.json"), &report)?;
    Ok(report)
}
fn receipt(path: &Path) -> Result<Value> {
    let mut reader = std::io::BufReader::new(std::fs::File::open(path)?);
    let mut hash = Sha256::new();
    let mut buffer = [0u8; 65536];
    loop {
        let n = reader.read(&mut buffer)?;
        if n == 0 {
            break;
        }
        hash.update(&buffer[..n]);
    }
    Ok(
        json!({"file":path.file_name().context("contribution filename missing")?.to_string_lossy(),"bytes":std::fs::metadata(path)?.len(),"sha256":crate::session_input::hex(&hash.finalize())}),
    )
}
