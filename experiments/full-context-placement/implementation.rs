// Default-off, stack-scoped local source placement. Geometry is runtime data;
// this module neither fits geometry nor changes the global alignment sidecar.
use super::*;
use anyhow::ensure;
use serde::Deserialize;
use strehl_core::optics::OpticalProfile;

pub(crate) const ENV: &str = "STREHL_LOCAL_PLACEMENT_FILE";

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Configuration {
    schema_version: u32,
    source_dir: PathBuf,
    expected_frame_count: usize,
    native_geometry: [usize; 2],
    support_native: [usize; 4],
    taper_native: usize,
    frames: Vec<Entry>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct Entry {
    file_name: String,
    transform_bits: [String; 4],
    delta_source_native: [f64; 2],
}

impl Entry {
    fn check_transform(&self, t: Similarity) -> Result<()> {
        let actual = [t.a.re, t.a.im, t.b.re, t.b.im].map(f64::to_bits);
        for (text, bits) in self.transform_bits.iter().zip(actual) {
            ensure!(u64::from_str_radix(text, 16)? == bits,
                "local placement: original transform differs for {}", self.file_name);
        }
        Ok(())
    }
}

impl Configuration {
    pub(crate) fn from_json(text: &str) -> Result<Self> {
        let mut cfg: Self = serde_json::from_str(text).context("local placement JSON")?;
        ensure!(cfg.schema_version == 1, "local placement: unsupported schema_version");
        ensure!(cfg.source_dir.is_absolute(), "local placement: source_dir must be absolute");
        cfg.source_dir = cfg.source_dir.canonicalize().context("local placement source_dir")?;
        ensure!(cfg.source_dir.is_dir(), "local placement: source_dir is not a directory");
        ensure!(cfg.expected_frame_count > 0 && !cfg.frames.is_empty()
            && cfg.frames.len() <= cfg.expected_frame_count,
            "local placement: invalid frame count");
        let [fw, fh] = cfg.native_geometry;
        let [x, y, w, h] = cfg.support_native;
        ensure!(fw >= 8 && fh >= 8 && fw % 2 == 0 && fh % 2 == 0
            && fw <= 65536 && fh <= 65536,
            "local placement: invalid native_geometry");
        ensure!(cfg.taper_native == 32 && w > 64 && h > 64
            && x.checked_add(w).is_some_and(|r| r <= fw)
            && y.checked_add(h).is_some_and(|r| r <= fh),
            "local placement: support must fit native geometry with a 32-pixel interior taper");
        for (i, entry) in cfg.frames.iter().enumerate() {
            let p = Path::new(&entry.file_name);
            ensure!(!entry.file_name.is_empty() && p.components().count() == 1
                && matches!(p.components().next(), Some(std::path::Component::Normal(_)))
                && !cfg.frames[..i].iter().any(|e| e.file_name.eq_ignore_ascii_case(&entry.file_name)),
                "local placement: invalid or duplicate file_name");
            ensure!(entry.delta_source_native.iter().all(|v| v.is_finite() && v.abs() <= 4.0),
                "local placement: source-native delta must be finite and within the measured 4-pixel bound");
            for text in &entry.transform_bits {
                ensure!(text.len() == 16 && text.bytes().all(|c| c.is_ascii_hexdigit()),
                    "local placement: transform_bits entries must be 16 hexadecimal digits");
                ensure!(f64::from_bits(u64::from_str_radix(text, 16)?).is_finite(),
                    "local placement: nonfinite transform");
            }
        }
        Ok(cfg)
    }

    fn check_scope(&self, path: &Path, geom: PlaneGeometry) -> Result<()> {
        ensure!(path.is_absolute(), "local placement: source path must be absolute");
        ensure!(path.parent().context("local placement: source has no parent")?.canonicalize()?
            == self.source_dir, "local placement: source directory differs");
        ensure!(geom.width.checked_mul(2) == Some(self.native_geometry[0])
            && geom.height.checked_mul(2) == Some(self.native_geometry[1]),
            "local placement: native geometry differs");
        Ok(())
    }

    fn entry(&self, path: &Path) -> Option<&Entry> {
        let name = path.file_name()?.to_str()?;
        self.frames.iter().find(|e| e.file_name.eq_ignore_ascii_case(name))
    }

    pub(crate) fn validate_stack(&self, paths: &[PathBuf], geom: PlaneGeometry,
        map: Option<&WarpMap>) -> Result<()> {
        ensure!(paths.len() == self.expected_frame_count, "local placement: stack length differs");
        let map = map.context("local placement requires an alignment map")?;
        ensure!(map.geometry() == geom && map.len() == paths.len()
            && map.resampler() == Resampler::CatmullRom,
            "local placement: map geometry, length or sampler differs");
        let mut found = 0;
        let mut seen = std::collections::HashSet::new();
        for (i, path) in paths.iter().enumerate() {
            self.check_scope(path, geom)?;
            ensure!(seen.insert(path.file_name().context("local placement: missing filename")?
                .to_string_lossy().to_ascii_lowercase()), "local placement: repeated source file");
            if let Some(entry) = self.entry(path) {
                let FrameWarp::Placed(t) = map.warp(i)? else {
                    bail!("local placement: configured frame {} is unplaced", path.display());
                };
                entry.check_transform(*t)?;
                found += 1;
            }
        }
        ensure!(found == self.frames.len(), "local placement: a configured file is absent or repeated");
        Ok(())
    }

    /// Product of two cubic smoothsteps. Coordinates name native reference CFA
    /// sites, not quad centres. The first/last supported sites have zero weight;
    /// sites at least 32 native pixels inside every edge have exactly one.
    pub(crate) fn weight_at(&self, x: f64, y: f64) -> f64 {
        let [ox, oy, w, h] = self.support_native;
        let ramp = |p: f64, origin: usize, size: usize| {
            let d = (p - origin as f64).min((origin + size - 1) as f64 - p);
            let q = (d / self.taper_native as f64).clamp(0.0, 1.0);
            q * q * (3.0 - 2.0 * q)
        };
        ramp(x, ox, w) * ramp(y, oy, h)
    }
}

fn configuration() -> Result<Option<&'static Configuration>> {
    static CONFIG: std::sync::OnceLock<std::result::Result<Option<Configuration>, String>> =
        std::sync::OnceLock::new();
    match CONFIG.get_or_init(|| (|| -> Result<Option<Configuration>> {
        let Some(path) = std::env::var_os(ENV) else { return Ok(None) };
        let path = PathBuf::from(path);
        ensure!(path.is_absolute(), "{ENV} must name an absolute JSON path");
        ensure!(direct_plane_mode()? != DirectPlaneMode::Off && fullres_gather_enabled(),
            "local placement requires enabled full-resolution direct planes");
        ensure!(!std::env::var(strehl_core::demosaic::DEMOSAIC_ENV)
            .is_ok_and(|v| v.eq_ignore_ascii_case("directional")),
            "local placement supports Malvar reconstruction only");
        ensure!(!std::env::var("STREHL_GATE_FLOOR").is_ok_and(|v| v.eq_ignore_ascii_case("debug")),
            "local placement cannot use the gate-floor debug identity-transform diagnostic");
        Ok(Some(Configuration::from_json(&std::fs::read_to_string(&path)
            .with_context(|| format!("reading {}", path.display()))?)?))
    })().map_err(|e| format!("{e:#}"))) {
        Ok(cfg) => Ok(cfg.as_ref()),
        Err(e) => bail!("{e}"),
    }
}

pub(crate) fn preflight(paths: &[PathBuf], geom: PlaneGeometry, map: Option<&WarpMap>) -> Result<()> {
    if let Some(cfg) = configuration()? { cfg.validate_stack(paths, geom, map)?; }
    Ok(())
}

pub(crate) fn enabled() -> Result<bool> { Ok(configuration()?.is_some()) }

struct Pick {
    slot: usize,
    index: usize,
    channel: usize,
    source: [f64; 2],
}

pub(crate) struct Prepared {
    patch: [usize; 4],
    picks: Vec<Pick>,
    plane_len: usize,
    plane_count: usize,
}

#[allow(clippy::too_many_arguments)]
pub(crate) fn prepare_with_config(frame: &strehl_raw::Frame, t: Similarity,
    geom: PlaneGeometry, crop: CropRect, offsets: &[(usize, usize)], mode: DirectPlaneMode,
    cfg: &Configuration, ca: Option<&OpticalProfile>) -> Result<Option<Prepared>> {
    cfg.check_scope(&frame.path, geom)?;
    ensure!(frame.active.width == 2 * geom.width && frame.active.height == 2 * geom.height,
        "local placement: decoded active geometry differs");
    ensure!(mode != DirectPlaneMode::Off && crop.width > 0 && crop.height > 0
        && crop.x.checked_add(crop.width).is_some_and(|x| x <= geom.width)
        && crop.y.checked_add(crop.height).is_some_and(|y| y <= geom.height)
        && !offsets.is_empty()
        && offsets.iter().enumerate().all(|(i, &(x, y))| x < 2 && y < 2
            && !offsets[..i].contains(&(x, y))), "local placement: invalid sink");
    let Some(entry) = cfg.entry(&frame.path) else { return Ok(None) };
    entry.check_transform(t)?;
    let delta = entry.delta_source_native;
    if delta == [0.0, 0.0] { return Ok(None) }
    let gain = wb_gains(&frame.wb_coeffs);
    ensure!(frame.levels.black.is_finite() && gain.iter().all(|v| v.is_finite() && *v > 0.0),
        "local placement: invalid black or WB");
    ensure!(frame.active.x.checked_add(frame.active.width).is_some_and(|x| x <= frame.stride)
        && frame.active.y.checked_add(frame.active.height).is_some_and(|y| y <= frame.buffer_height)
        && frame.stride.checked_mul(frame.buffer_height).is_some_and(|n| n <= frame.data.len()),
        "local placement: invalid decoded buffer");
    let [rx, ry, rw, rh] = cfg.support_native;
    let x0 = crop.x.max(rx / 2);
    let x1 = (crop.x + crop.width).min((rx + rw).div_ceil(2));
    let y0 = crop.y.max(ry / 2);
    let y1 = (crop.y + crop.height).min((ry + rh).div_ceil(2));
    let mut picks = Vec::new();
    let mut lo = [usize::MAX; 2];
    let mut hi = [0usize; 2];
    for (slot, &(dx, dy)) in offsets.iter().enumerate() {
        let channel = rggb_channel_index(dx, dy);
        for py in y0..y1 { for px in x0..x1 {
            let weight = cfg.weight_at((2 * px + dx) as f64, (2 * py + dy) as f64);
            if weight == 0.0 { continue }
            // Exact uniform-map arithmetic at weight one. Translation is in
            // source-native units and precedes the existing per-channel CA.
            let mut shifted = t;
            shifted.b.re += delta[0] * weight / 2.0;
            shifted.b.im += delta[1] * weight / 2.0;
            let pull = OpticalProfile::compose(ca, strehl_core::optics::cfa_site_channel(dx, dy), shifted);
            let (sx, sy) = pull.apply_at(px as f64 + dx as f64 * 0.5,
                py as f64 + dy as f64 * 0.5, geom.width as f64 * 0.5, geom.height as f64 * 0.5);
            let source = [2.0 * sx, 2.0 * sy];
            // Catmull floor-1..floor+2, each MHC site needs another two.
            for axis in 0..2 {
                let p = source[axis];
                ensure!(p.is_finite() && p.floor() >= 3.0
                    && p.floor() + 4.0 < cfg.native_geometry[axis] as f64,
                    "local placement: corrected source stencil leaves the active sensor");
                let floor = p.floor() as usize;
                lo[axis] = lo[axis].min(floor - 3);
                hi[axis] = hi[axis].max(floor + 5); // Exclusive CFA extent.
            }
            picks.push(Pick { slot, index: (py - crop.y) * crop.width + px - crop.x,
                channel, source });
        }}
    }
    if picks.is_empty() { return Ok(None) }
    // MHC sees the original RGGB phase, even for an odd decoded active origin.
    lo[0] &= !1;
    lo[1] &= !1;
    Ok(Some(Prepared { patch: [lo[0], lo[1], hi[0] - lo[0], hi[1] - lo[1]],
        picks, plane_len: crop.width * crop.height, plane_count: offsets.len() }))
}

pub(crate) fn prepare(frame: &strehl_raw::Frame, t: Similarity, geom: PlaneGeometry,
    resampler: Resampler, crop: CropRect, offsets: &[(usize, usize)], mode: DirectPlaneMode)
    -> Result<Option<Prepared>> {
    let Some(cfg) = configuration()? else { return Ok(None) };
    ensure!(resampler == Resampler::CatmullRom, "local placement requires Catmull-Rom");
    if cfg.entry(&frame.path).is_none() {
        cfg.check_scope(&frame.path, geom)?;
        return Ok(None);
    }
    let ident = strehl_raw::identity(&frame.path);
    let ca = strehl_core::optics::profile_for_capture_env(ident.model.as_deref(), ident.lens_type3)?;
    prepare_with_config(frame, t, geom, crop, offsets, mode, cfg, ca)
}

impl Prepared {
    /// Reconstruct one unaligned source patch. Commit corrected samples only
    /// after every one has been computed and checked; never blend images.
    pub(crate) fn apply(&self, frame: &strehl_raw::Frame, planes: &mut [Vec<f32>],
        mode: DirectPlaneMode) -> Result<usize> {
        ensure!(mode != DirectPlaneMode::Off && planes.len() == self.plane_count
            && planes.iter().all(|p| p.len() == self.plane_len), "local placement: output shape differs");
        let [ox, oy, w, h] = self.patch;
        let black = frame.levels.black;
        let gain = wb_gains(&frame.wb_coeffs);
        let mut mosaic = vec![0f32; w * h];
        for y in 0..h { for x in 0..w {
            mosaic[y * w + x] = (frame.sample(ox + x, oy + y) as f32 - black)
                * gain[rggb_channel_index(x, y)];
        }}
        let m = strehl_core::demosaic::Mosaic { data: &mosaic, width: w, height: h };
        let mut channels: [Vec<f32>; 3] = std::array::from_fn(|_| vec![0.0; w * h]);
        let mut row = vec![0f32; w * 3];
        for y in 0..h {
            strehl_core::demosaic::demosaic_malvar_row(&m, y, &mut row);
            for x in 0..w { for c in 0..3 { channels[c][y * w + x] = row[3 * x + c]; }}
        }
        drop(mosaic);
        let geometry = PlaneGeometry { width: w, height: h };
        let refs = channels.iter().map(|c| PlaneRef::from_geometry(c, geometry).unwrap()).collect::<Vec<_>>();
        let mut values = Vec::with_capacity(self.picks.len());
        for pick in &self.picks {
            let value = strehl_core::align::sample_catmull_rom(refs[pick.channel],
                pick.source[0] - ox as f64, pick.source[1] - oy as f64);
            ensure!(value.is_finite(), "local placement: nonfinite reconstructed source");
            values.push(consumed_fullres_value(value, true, 1.0 / gain[pick.channel], black, mode));
        }
        for (pick, value) in self.picks.iter().zip(values) { planes[pick.slot][pick.index] = value; }
        Ok(self.picks.len())
    }
}

// The independent verifier owns both acceptance choices and assertions.
#[cfg(all(test, feature = "native-gpu-gather"))]
mod independent_controls {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/full-context-placement/independent-controls.rs"));
}
