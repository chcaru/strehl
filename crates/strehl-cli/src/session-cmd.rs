//! Opt-in multi-pass sessions. The ordinary stack command stays independent.
use std::fs::OpenOptions;
use std::io::Write;
use std::path::PathBuf;

use anyhow::{Context, Result, ensure};
use clap::{Args, Parser, Subcommand};
use serde::Serialize;

use crate::session_align::SessionAlignConfig;
use crate::session_cache::SourceCache;
use crate::session_input::{
    ResolvedSession, SessionMode, SessionSpec, SourceIdentity, SourceMetadata,
};

#[derive(Args, Debug, Clone)]
pub(crate) struct Resources {
    /// Total session working-memory reservation in GiB, separate from ordinary stacking.
    #[arg(long, default_value_t = 16.0)]
    pub memory_limit_gib: f64,
    /// Maximum CPU workers; arithmetic order remains independent of worker count.
    #[arg(long, default_value_t = 16)]
    pub threads: usize,
    /// Persistent original-CFA cache, outside all source directories.
    #[arg(long)]
    pub cache: Option<PathBuf>,
    #[arg(long, default_value = "catmull-rom")]
    pub resampler: String,
}
impl Resources {
    pub fn config(&self) -> Result<SessionAlignConfig> {
        ensure!(
            self.memory_limit_gib.is_finite() && (1.0..=4096.0).contains(&self.memory_limit_gib),
            "--memory-limit-gib must be finite in 1..4096"
        );
        let config = SessionAlignConfig {
            memory_limit_bytes: (self.memory_limit_gib * (1_u64 << 30) as f64) as usize,
            workers: self.threads,
            ..SessionAlignConfig::default()
        };
        config.validate()?;
        Ok(config)
    }
    pub fn cache_budget(&self) -> Result<usize> {
        Ok((self.config()?.memory_limit_bytes / 8).clamp(128 << 20, 2 << 30))
    }
}

#[derive(Args, Debug, Clone)]
pub(crate) struct StackArgs {
    pub manifest: PathBuf,
    /// Fresh output directory for the photograph, linear master and session report.
    #[arg(long)]
    pub out_dir: PathBuf,
    /// Reuse an exactly matching session alignment envelope.
    #[arg(long)]
    pub alignment: Option<PathBuf>,
    #[command(flatten)]
    pub resources: Resources,
    #[arg(long, default_value_t = 2.0)]
    pub pyramid_gate: f32,
    #[arg(long, default_value_t = 7)]
    pub pyramid_bands: usize,
    #[arg(long, default_value_t = 2.0)]
    pub pyramid_exponent: f32,
    #[arg(long, default_value_t = 1.4)]
    pub pyramid_sharpen: f32,
    #[arg(long, default_value_t = 0.0)]
    pub exposure: f32,
    /// Residual RMS threshold for proposed repeat groups; not a probability.
    #[arg(long, default_value_t = 4.0)]
    pub agreement_sigma: f32,
    #[arg(long)]
    pub binned: bool,
    /// Research control: use the session sampler even for a single pass.
    #[arg(long, hide = true)]
    pub native_single: bool,
    /// Research control: admit all sources separately without repeat grouping.
    #[arg(long, hide = true)]
    pub no_repeat_grouping: bool,
    /// Research control: render one pass using the complete session's joint geometry.
    #[arg(long, hide = true)]
    pub only_pass: Option<usize>,
}
impl StackArgs {
    pub fn merge_config(&self) -> Result<strehl_core::pyramid::MergeConfig> {
        ensure!(
            (1..=12).contains(&self.pyramid_bands),
            "--pyramid-bands must be 1..12"
        );
        ensure!(
            self.pyramid_gate.is_finite() && self.pyramid_gate >= 0.0,
            "invalid pyramid gate"
        );
        ensure!(
            self.pyramid_exponent.is_finite()
                && self.pyramid_exponent > 0.0
                && self.pyramid_exponent <= 8.0,
            "invalid pyramid exponent"
        );
        ensure!(
            self.pyramid_sharpen.is_finite() && self.pyramid_sharpen >= 1.0,
            "invalid pyramid sharpen"
        );
        ensure!(
            self.agreement_sigma.is_finite() && self.agreement_sigma > 0.0,
            "invalid agreement sigma"
        );
        ensure!(self.exposure.is_finite(), "invalid exposure");
        self.resources.config()?;
        Ok(strehl_core::pyramid::MergeConfig {
            bands: self.pyramid_bands,
            gate: self.pyramid_gate,
            exponent: self.pyramid_exponent,
            sharpen_per_octave: self.pyramid_sharpen,
            ..strehl_core::pyramid::MergeConfig::default()
        })
    }
}

/// Resolve a one-pass session into the unchanged ordinary command at process startup.
/// # Safety
/// Must run before any worker or GUI thread: it isolates legacy sidecar environment.
pub(crate) unsafe fn route_single_pass(
    command: crate::Command,
) -> Result<(crate::Command, Option<SinglePassCompletion>)> {
    let crate::Command::Session {
        action: Action::Stack(args),
    } = &command
    else {
        return Ok((command, None));
    };
    args.merge_config()?;
    let session = SessionSpec::load(&args.manifest)?.resolve(&args.manifest)?;
    if args.native_single
        || args.only_pass.is_some()
        || session.passes.len() != 1
        || session.passes[0].directories.len() != 1
        || !matches!(
            session.spec.mode,
            SessionMode::Combine | SessionMode::Repeat
        )
    {
        return Ok((command, None));
    }
    ensure!(
        args.alignment.is_none(),
        "a one-pass ordinary session does not consume a joint alignment envelope; omit --alignment"
    );
    let identities = session.hash_sources(true)?;
    let destination = reserve_output_directory(&session, &args.out_dir)?;
    write_json_new(&destination.join("session.json"), &session)?;
    write_json_new(&destination.join("source-identities.json"), &identities)?;
    eprintln!("session: one pass uses the unchanged ordinary stacking pipeline");
    eprintln!("session: session memory limit applies only to the multi-pass pipeline");
    // SAFETY: caller guarantees this is the startup-only argument-resolution phase.
    unsafe {
        std::env::set_var("STREHL_WARPMAP", destination.join("warpmap.txt"));
        std::env::set_var("STREHL_CACHE_DIR", destination.join("cache"));
        std::env::set_var("STREHL_PYRAMID_WORKERS", args.resources.threads.to_string());
        std::env::set_var("RAYON_NUM_THREADS", args.resources.threads.to_string());
    }
    let mut argv: Vec<std::ffi::OsString> = vec![
        "strehl".into(),
        "stack".into(),
        session.passes[0].directories[0].clone().into_os_string(),
        "--merge".into(),
        "pyramid".into(),
        "--srgb".into(),
        "--out".into(),
        destination.join("photograph.tiff").into_os_string(),
        "--linear-master".into(),
        destination.join("master.tiff").into_os_string(),
        "--pyramid-gate".into(),
        args.pyramid_gate.to_string().into(),
        "--pyramid-bands".into(),
        args.pyramid_bands.to_string().into(),
        "--pyramid-exponent".into(),
        args.pyramid_exponent.to_string().into(),
        "--pyramid-sharpen".into(),
        args.pyramid_sharpen.to_string().into(),
        "--exposure".into(),
        args.exposure.to_string().into(),
        "--resampler".into(),
        args.resources.resampler.clone().into(),
    ];
    if args.binned {
        argv.push("--binned".into());
    }
    Ok((
        crate::Cli::try_parse_from(argv)?.command,
        Some(SinglePassCompletion {
            session,
            identities,
            destination,
            threads: args.resources.threads,
            resampler: args.resources.resampler.clone(),
            started: std::time::Instant::now(),
        }),
    ))
}

/// Publication guard around the unchanged ordinary consumer. The source census
/// and every original hash must still match after that consumer has completed.
pub(crate) struct SinglePassCompletion {
    session: ResolvedSession,
    identities: Vec<SourceIdentity>,
    destination: PathBuf,
    threads: usize,
    resampler: String,
    started: std::time::Instant,
}
impl SinglePassCompletion {
    fn alignment_args(&self) -> Result<crate::align_cmd::AlignArgs> {
        let argv: Vec<std::ffi::OsString> = vec![
            "strehl".into(),
            "align".into(),
            self.session.passes[0].directories[0]
                .clone()
                .into_os_string(),
            "--out".into(),
            self.destination.join("warpmap.txt").into_os_string(),
            "--threads".into(),
            self.threads.to_string().into(),
            "--resampler".into(),
            self.resampler.clone().into(),
        ];
        match crate::Cli::try_parse_from(argv)?.command {
            crate::Command::Align(args) => Ok(args),
            _ => unreachable!("fixed ordinary alignment command"),
        }
    }
    /// Called after ordinary command environment configuration, before merging.
    /// Explicit STREHL_WARPMAP is a required-input contract, so create that map
    /// using the ordinary align command rather than pointing at a missing file.
    pub(crate) fn prepare_alignment(&self) -> Result<()> {
        crate::align_cmd::run(&self.alignment_args()?)
    }
    pub(crate) fn finish(self) -> Result<()> {
        let current = self
            .session
            .spec
            .resolve_from(&self.session.passes[0].directories[0])?;
        ensure!(
            current.frames == self.session.frames && current.hash_sources(true)? == self.identities,
            "session sources changed while ordinary stacking ran; result withheld from completed history"
        );
        for name in ["photograph.tiff", "master.tiff"] {
            ensure!(
                self.destination.join(name).metadata()?.len() > 0,
                "ordinary session did not complete {name}"
            );
        }
        write_json_new(
            &self.destination.join("completed.json"),
            &serde_json::json!({
                "schema":"strehl.session-completion.v1", "pipeline":"ordinary-single-pass",
                "elapsed_seconds":self.started.elapsed().as_secs_f64(),
                "outputs":1, "frames":self.session.len(), "passes":1,
                "primary_pass":self.session.primary_pass_index()
            }),
        )
    }
}

pub(crate) fn reserve_output_directory(
    session: &ResolvedSession,
    path: &std::path::Path,
) -> Result<PathBuf> {
    let path = session.ensure_fresh_output(path)?;
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    std::fs::create_dir(&path)
        .with_context(|| format!("creating fresh output directory {}", path.display()))?;
    Ok(path)
}

pub(crate) fn write_json_new(path: &std::path::Path, value: &impl Serialize) -> Result<()> {
    let mut file = OpenOptions::new().write(true).create_new(true).open(path)?;
    serde_json::to_writer_pretty(&mut file, value)?;
    file.write_all(b"\n")?;
    file.sync_all()?;
    Ok(())
}

#[derive(Subcommand)]
pub(crate) enum Action {
    /// Fit all passes together using direct native measurements and separate focus tracks.
    Align {
        manifest: PathBuf,
        #[arg(long)]
        out: PathBuf,
        #[command(flatten)]
        resources: Resources,
    },
    /// Stack an explicit multi-pass session; ordinary single-pass sessions keep the legacy pipeline.
    Stack(StackArgs),
    /// Inspect explicit passes, ordered folder segments, and capture metadata.
    Inspect {
        /// Versioned JSON manifest; relative source folders resolve beside it.
        manifest: PathBuf,
        /// Save the report to a new file. Otherwise print JSON.
        #[arg(long)]
        out: Option<PathBuf>,
        /// Read every RAW byte and reject duplicate content across the session.
        #[arg(long)]
        hash_sources: bool,
    },
}

#[derive(Serialize)]
struct Inspection {
    schema: &'static str,
    session: ResolvedSession,
    metadata: Vec<SourceMetadata>,
    source_identities: Option<Vec<SourceIdentity>>,
    limitations: Vec<&'static str>,
}

pub(crate) fn run(action: Action) -> Result<()> {
    match action {
        Action::Stack(args) => crate::merge_cmd::session_consumer::run(&args),
        Action::Align {
            manifest,
            out,
            resources,
        } => {
            let session = SessionSpec::load(&manifest)?.resolve(&manifest)?;
            let out = session.ensure_fresh_output(&out)?;
            let config = resources.config()?;
            let resampler = crate::align_cmd::parse_resampler(&resources.resampler)?;
            let identities = session.hash_sources(true)?;
            let cache_path = resources
                .cache
                .clone()
                .unwrap_or_else(|| out.with_extension("source-cache"));
            let mut cache = SourceCache::new(&cache_path, &session, resources.cache_budget()?)?;
            let pool = rayon::ThreadPoolBuilder::new()
                .num_threads(resources.threads)
                .build()?;
            let alignment = pool.install(|| {
                crate::session_align::align_session(
                    &session,
                    &identities,
                    &mut cache,
                    &config,
                    resampler,
                )
            })?;
            alignment.save(&out, &session)?;
            eprintln!(
                "session alignment: {} frames, {} measured edges, {} anchor cycles",
                alignment.report.frames,
                alignment.report.measured_edges,
                alignment.report.anchor_component_cycle_rank
            );
            Ok(())
        }
        Action::Inspect {
            manifest,
            out,
            hash_sources,
        } => {
            let spec = SessionSpec::load(&manifest)?;
            let session = spec.resolve(&manifest)?;
            let out = out
                .as_deref()
                .map(|path| session.ensure_output_outside_sources(path))
                .transpose()?;
            if let Some(path) = &out {
                ensure!(
                    std::fs::symlink_metadata(path).is_err(),
                    "report already exists: {}",
                    path.display()
                );
            }
            let metadata = session.read_metadata()?;
            let source_identities = hash_sources
                .then(|| session.hash_sources(true))
                .transpose()?;
            let mut limitations = vec![
                "Folder segments are explicit capture order, not proof of equal focus.",
                "Metadata and repeated image agreement do not establish subject rigidity or equal illumination.",
                "A camera model match does not establish a physical-body identity when serial metadata is absent.",
            ];
            if !hash_sources {
                limitations.push(
                    "Full RAW content independence has not been checked; use --hash-sources.",
                );
            }
            let report = Inspection {
                schema: "strehl.session-inspection.v1",
                session,
                metadata,
                source_identities,
                limitations,
            };
            let mut bytes = serde_json::to_vec_pretty(&report)?;
            bytes.push(b'\n');
            if let Some(path) = out {
                if let Some(parent) = path.parent() {
                    std::fs::create_dir_all(parent)?;
                }
                // A fresh destination also refuses a hardlink alias to a RAW file.
                let mut file = OpenOptions::new()
                    .write(true)
                    .create_new(true)
                    .open(&path)
                    .with_context(|| format!("creating session report {}", path.display()))?;
                file.write_all(&bytes)?;
                file.sync_all()?;
            } else {
                std::io::stdout().lock().write_all(&bytes)?;
            }
            Ok(())
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use clap::Parser;

    #[test]
    fn session_single_pass_publication_checks_census_hashes_and_completion() {
        use std::sync::atomic::{AtomicU64, Ordering};
        static NEXT: AtomicU64 = AtomicU64::new(0);
        let root = std::env::var_os("STREHL_TEST_TMP")
            .map(PathBuf::from)
            .unwrap_or_else(std::env::temp_dir)
            .join(format!(
                "strehl-single-publish-{}-{}",
                std::process::id(),
                NEXT.fetch_add(1, Ordering::Relaxed)
            ));
        let source = root.join("source");
        std::fs::create_dir_all(&source).unwrap();
        std::fs::write(source.join("a.ARW"), b"first-original").unwrap();
        let spec = SessionSpec {
            passes: vec![crate::session_input::PassSpec {
                name: "A".into(),
                directories: vec![source.clone()],
            }],
            ..SessionSpec::default()
        };
        let session = spec.resolve_from(&root).unwrap();
        let identities = session.hash_sources(true).unwrap();
        for (name, mutate) in [("good", 0), ("added", 1), ("changed", 2)] {
            let destination = root.join(name);
            std::fs::create_dir(&destination).unwrap();
            std::fs::write(destination.join("photograph.tiff"), b"completed-photo").unwrap();
            std::fs::write(destination.join("master.tiff"), b"completed-master").unwrap();
            if mutate == 1 {
                std::fs::write(source.join("b.ARW"), b"second-original").unwrap();
            }
            if mutate == 2 {
                std::fs::write(source.join("a.ARW"), b"other-original").unwrap();
            }
            let completion = SinglePassCompletion {
                session: session.clone(),
                identities: identities.clone(),
                destination: destination.clone(),
                threads: 16,
                resampler: "catmull-rom".into(),
                started: std::time::Instant::now(),
            };
            let alignment = completion.alignment_args().unwrap();
            assert_eq!(alignment.dir, session.passes[0].directories[0]);
            assert_eq!(alignment.out, Some(destination.join("warpmap.txt")));
            assert_eq!(alignment.threads, 16);
            assert_eq!(alignment.resampler, "catmull-rom");
            assert!(alignment.reference.is_none());
            let result = completion.finish();
            assert_eq!(result.is_ok(), mutate == 0);
            assert_eq!(destination.join("completed.json").exists(), mutate == 0);
            if mutate == 1 {
                std::fs::remove_file(source.join("b.ARW")).unwrap();
            }
        }
        std::fs::remove_dir_all(root).unwrap();
    }
    #[test]
    fn session_cli_inspection_is_opt_in_and_rejects_missing_manifest() {
        let cli = crate::Cli::try_parse_from([
            "strehl",
            "session",
            "inspect",
            "session.json",
            "--hash-sources",
        ])
        .unwrap();
        assert!(matches!(
            cli.command,
            crate::Command::Session {
                action: Action::Inspect {
                    hash_sources: true,
                    ..
                }
            }
        ));
        let ordinary = crate::Cli::try_parse_from(["strehl", "stack", "capture"]).unwrap();
        assert!(matches!(ordinary.command, crate::Command::Stack { .. }));
        assert!(crate::Cli::try_parse_from(["strehl", "session", "inspect"]).is_err());
    }
}
