//! Content-addressed cache of measured sampler/pyramid noise transfer.
//! Stores only small numeric operator reports, never image planes.
use super::*;
use crate::session_sampling::WarpBandTransfer;
use serde::{Deserialize, Serialize};
use std::io::{Read, Write};
use std::sync::atomic::{AtomicU64, Ordering};

const SCHEMA: &str = "strehl.session-transfer.v1";
static NEXT_TEMP: AtomicU64 = AtomicU64::new(0);

#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Payload {
    cfa: [Vec<u32>; 4],
    luma: Vec<u32>,
    color: Vec<u32>,
    samples: Vec<usize>,
    realizations: usize,
    seed: u64,
}
impl Payload {
    fn from_transfer(t: &WarpBandTransfer) -> Self {
        Self {
            cfa: std::array::from_fn(|i| t.cfa_beta[i].iter().map(|v| v.to_bits()).collect()),
            luma: t.luma_beta.iter().map(|v| v.to_bits()).collect(),
            color: t.max_color_beta.iter().map(|v| v.to_bits()).collect(),
            samples: t.samples_per_band.clone(),
            realizations: t.realizations,
            seed: t.seed,
        }
    }
    fn transfer(self, domain: SamplingDomain, config: ProbeConfig) -> Result<WarpBandTransfer> {
        let n = strehl_core::pyramid::level_sizes(domain.width, domain.height, config.bands).len();
        ensure!(
            self.realizations == config.realizations
                && self.seed == config.seed
                && self.samples.len() == n
                && self
                    .samples
                    .iter()
                    .all(|&v| v >= config.min_samples_per_band),
            "noise transfer cache probe support differs"
        );
        for values in self.cfa.iter().chain([&self.luma, &self.color]) {
            ensure!(
                values.len() == n
                    && values.iter().all(|&v| {
                        let v = f32::from_bits(v);
                        v.is_finite() && v > 0.0
                    }),
                "noise transfer cache contains invalid coefficients"
            );
        }
        let cfa_beta = self
            .cfa
            .map(|v| v.into_iter().map(f32::from_bits).collect::<Vec<_>>());
        let max_color_beta: Vec<_> = self.color.into_iter().map(f32::from_bits).collect();
        ensure!(
            (0..n).all(
                |k| cfa_beta.iter().map(|v| v[k]).fold(0.0, f32::max).to_bits()
                    == max_color_beta[k].to_bits()
            ),
            "noise transfer color bound differs"
        );
        Ok(WarpBandTransfer {
            cfa_beta,
            max_color_beta,
            luma_beta: self.luma.into_iter().map(f32::from_bits).collect(),
            samples_per_band: self.samples,
            realizations: self.realizations,
            seed: self.seed,
        })
    }
}
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Envelope {
    schema: String,
    key: String,
    checksum: String,
    payload: Payload,
}
fn digest(bytes: &[u8]) -> String {
    crate::session_input::hex(&Sha256::digest(bytes))
}
fn key(
    domain: SamplingDomain,
    placement: strehl_core::align::Similarity,
    profile: Option<&OpticalProfile>,
    resampler: Resampler,
    config: ProbeConfig,
) -> Result<String> {
    domain.validate()?;
    ensure!(
        resampler != Resampler::ClampedCatmullRom
            && (1..=128).contains(&config.realizations)
            && config.min_samples_per_band > 0,
        "invalid or nonlinear noise transfer probe"
    );
    let mut hash = Sha256::new();
    hash.update(serde_json::to_vec(&(
        SCHEMA,
        std::env::consts::ARCH,
        std::env::consts::OS,
        [
            domain.full.width,
            domain.full.height,
            domain.x,
            domain.y,
            domain.width,
            domain.height,
        ],
        [
            placement.a.re.to_bits(),
            placement.a.im.to_bits(),
            placement.b.re.to_bits(),
            placement.b.im.to_bits(),
        ],
        format!("{profile:?}"),
        format!("{resampler:?}"),
        config.bands,
        config.realizations,
        config.seed,
        config.min_samples_per_band,
    ))?);
    for bytes in [
        include_bytes!("session-transfer-cache.rs").as_slice(),
        include_bytes!("session-sampling.rs").as_slice(),
        include_bytes!("../../strehl-core/src/align.rs").as_slice(),
        include_bytes!("../../strehl-core/src/plane.rs").as_slice(),
        include_bytes!("../../strehl-core/src/pyramid.rs").as_slice(),
        include_bytes!("../../strehl-core/src/optics.rs").as_slice(),
        include_bytes!("../../../Cargo.lock").as_slice(),
    ] {
        hash.update((bytes.len() as u64).to_le_bytes());
        hash.update(bytes);
    }
    Ok(crate::session_input::hex(&hash.finalize()))
}
fn read(
    path: &Path,
    expected: &str,
    domain: SamplingDomain,
    config: ProbeConfig,
) -> Result<WarpBandTransfer> {
    let file = std::fs::File::open(path)?;
    ensure!(
        file.metadata()?.len() <= 1 << 20,
        "noise transfer cache is oversized"
    );
    let mut bytes = Vec::new();
    file.take((1 << 20) + 1).read_to_end(&mut bytes)?;
    ensure!(
        bytes.len() <= 1 << 20,
        "noise transfer cache grew during read"
    );
    let saved: Envelope = serde_json::from_slice(&bytes)?;
    ensure!(
        saved.schema == SCHEMA
            && saved.key == expected
            && saved.checksum == digest(&serde_json::to_vec(&saved.payload)?),
        "noise transfer cache binding/checksum differs"
    );
    saved.payload.transfer(domain, config)
}

/// The caller supplies an already verified source-cache root outside all inputs.
pub(super) fn measure(
    root: &Path,
    domain: SamplingDomain,
    placement: strehl_core::align::Similarity,
    profile: Option<&OpticalProfile>,
    resampler: Resampler,
    config: ProbeConfig,
) -> Result<(WarpBandTransfer, bool)> {
    let key = key(domain, placement, profile, resampler, config)?;
    let path = root.join(format!("transfer-{key}.json"));
    if std::fs::symlink_metadata(&path).is_ok() {
        match read(&path, &key, domain, config) {
            Ok(value) => return Ok((value, true)),
            Err(error) => {
                eprintln!("session transfer: rejected derived cache ({error}); measuring again");
                std::fs::remove_file(&path)?;
            }
        }
    }
    let value = measure_band_transfer(domain, placement, profile, resampler, config)?;
    let payload = Payload::from_transfer(&value);
    let envelope = Envelope {
        schema: SCHEMA.into(),
        key: key.clone(),
        checksum: digest(&serde_json::to_vec(&payload)?),
        payload,
    };
    let temporary = root.join(format!(
        ".transfer-{}-{}.tmp",
        std::process::id(),
        NEXT_TEMP.fetch_add(1, Ordering::Relaxed)
    ));
    let publish = (|| -> Result<()> {
        let mut file = std::fs::OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(&temporary)?;
        serde_json::to_writer(&mut file, &envelope)?;
        file.write_all(b"\n")?;
        file.sync_all()?;
        drop(file);
        // Hard-link publication is atomic and refuses an existing destination
        // on every supported OS. It cannot overwrite a concurrent writer.
        match std::fs::hard_link(&temporary, &path) {
            Ok(()) => Ok(()),
            Err(error) => read(&path, &key, domain, config)
                .map(|_| ())
                .with_context(|| format!("publishing transfer cache: {error}")),
        }
    })();
    if temporary.exists() {
        std::fs::remove_file(&temporary)?;
    }
    publish?;
    Ok((value, false))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;
    use strehl_core::{align::Similarity, plane::PlaneGeometry};
    #[test]
    fn session_transfer_cache_exact_bits_hit_corruption_and_changed_operator() {
        let root = std::env::var_os("STREHL_TEST_TMP")
            .map(PathBuf::from)
            .unwrap_or_else(std::env::temp_dir)
            .join(format!(
                "strehl-transfer-{}-{}",
                std::process::id(),
                NEXT_TEMP.fetch_add(1, Ordering::Relaxed)
            ));
        std::fs::create_dir_all(&root).unwrap();
        let domain = SamplingDomain::full(PlaneGeometry {
            width: 96,
            height: 80,
        });
        let config = ProbeConfig {
            bands: 2,
            realizations: 2,
            min_samples_per_band: 16,
            ..ProbeConfig::default()
        };
        let placement = Similarity::IDENTITY;
        let (a, hit) =
            measure(&root, domain, placement, None, Resampler::Bilinear, config).unwrap();
        assert!(!hit);
        let (b, hit) =
            measure(&root, domain, placement, None, Resampler::Bilinear, config).unwrap();
        assert!(hit);
        assert_eq!(
            serde_json::to_vec(&Payload::from_transfer(&a)).unwrap(),
            serde_json::to_vec(&Payload::from_transfer(&b)).unwrap()
        );
        let k = key(domain, placement, None, Resampler::Bilinear, config).unwrap();
        let path = root.join(format!("transfer-{k}.json"));
        let mut env: Envelope = serde_json::from_slice(&std::fs::read(&path).unwrap()).unwrap();
        env.payload.luma[0] ^= 1; // plausible positive float, wrong payload checksum
        std::fs::write(&path, serde_json::to_vec(&env).unwrap()).unwrap();
        let (c, hit) =
            measure(&root, domain, placement, None, Resampler::Bilinear, config).unwrap();
        assert!(!hit);
        assert_eq!(a.luma_beta, c.luma_beta);
        assert_ne!(
            k,
            key(domain, placement, None, Resampler::Nearest, config).unwrap()
        );
        assert_ne!(
            k,
            key(
                domain,
                placement,
                None,
                Resampler::Bilinear,
                ProbeConfig {
                    seed: config.seed ^ 1,
                    ..config
                }
            )
            .unwrap()
        );
        assert!(
            measure(
                &root,
                domain,
                placement,
                None,
                Resampler::ClampedCatmullRom,
                config
            )
            .is_err()
        );
        std::fs::remove_dir_all(root).unwrap();
    }
}
