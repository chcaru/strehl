//! Stream a strictly validated independent-view bundle without copying any RAW.
use super::*;
use std::io::Write;

fn copy_checked(
    source: &Path,
    destination: &Path,
    digest: &str,
    cancelled: &AtomicBool,
    observer: &mut impl FnMut(u64),
) -> Result<()> {
    let mut input = std::fs::File::open(source)?;
    let size = input.metadata()?.len();
    ensure!(size <= FILE_LIMIT, "Bundle artifact exceeds file budget");
    let mut output = std::fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(destination)?;
    let mut hash = Sha256::new();
    let mut buffer = [0u8; 65536];
    let mut copied = 0u64;
    loop {
        ensure!(
            !cancelled.load(Ordering::Relaxed),
            "View bundle export cancelled; incomplete destination has no completion receipt"
        );
        let n = input.read(&mut buffer)?;
        if n == 0 {
            break;
        }
        copied = copied
            .checked_add(n as u64)
            .context("Bundle size overflow")?;
        ensure!(copied <= size, "Bundle source grew during export");
        output.write_all(&buffer[..n])?;
        hash.update(&buffer[..n]);
        observer(n as u64);
    }
    let actual: String = hash.finalize().iter().map(|v| format!("{v:02x}")).collect();
    ensure!(
        copied == size && actual.eq_ignore_ascii_case(digest),
        "Bundle source changed during copy"
    );
    output.sync_all()?;
    Ok(())
}

pub(crate) fn export(
    source: &Path,
    destination: &Path,
    cancelled: &AtomicBool,
) -> Result<std::path::PathBuf> {
    export_observed(source, destination, cancelled, &mut |_| {})
}

fn export_observed(
    source: &Path,
    destination: &Path,
    cancelled: &AtomicBool,
    observer: &mut impl FnMut(u64),
) -> Result<std::path::PathBuf> {
    ensure!(
        !cancelled.load(Ordering::Relaxed),
        "View bundle export cancelled"
    );
    let source = source.canonicalize()?;
    let parent = destination
        .parent()
        .context("Choose a destination parent")?
        .canonicalize()?;
    let leaf = destination
        .file_name()
        .and_then(|s| s.to_str())
        .context("Choose a new bundle folder name")?;
    crate::agent_interface::safe_file_name(leaf).map_err(anyhow::Error::msg)?;
    crate::jobs::validate_export_destination(Some(&source), &parent)?;
    let destination = parent.join(leaf);
    ensure!(
        !destination.try_exists()?,
        "View bundle destination already exists; choose a fresh folder"
    );
    // Parsing and full scalar/TIFF validation precede writes. No original RAW is opened.
    let run = load(&source, cancelled)?;
    let draft = run
        .settings
        .session
        .as_ref()
        .context("View session missing")?;
    ensure!(
        draft.manifest.mode == SessionMode::IndependentViews,
        "Open an independent-view bundle first"
    );
    for pass in &draft.manifest.passes {
        for directory in &pass.directories {
            crate::jobs::validate_export_destination(Some(directory), &parent)?;
            crate::jobs::validate_output_parent(directory, &destination)?;
        }
    }
    let evidence = run.imported.context("View provenance missing")?;
    ensure!(evidence.renderer_bound, "Bundle is not renderer bound");
    for name in evidence.files.keys() {
        ensure!(
            matches!(
                Path::new(name).extension().and_then(|v| v.to_str()),
                Some("json" | "tiff")
            ),
            "Bundle contains an unsupported artifact; original captures are never copied"
        );
    }
    ensure!(
        !cancelled.load(Ordering::Relaxed),
        "View bundle export cancelled"
    );
    std::fs::create_dir(&destination)?;
    let destination = destination.canonicalize()?;
    let mut copied = evidence.clone();
    let completion = copied
        .files
        .remove("completed.json")
        .context("Bundle completion missing")?;
    for (name, digest) in &copied.files {
        let target = destination.join(name);
        let target_parent = target.parent().context("Bundle artifact parent missing")?;
        std::fs::create_dir_all(target_parent)?;
        ensure!(
            target_parent.canonicalize()?.starts_with(&destination),
            "Bundle copy escapes destination"
        );
        copy_checked(&source.join(name), &target, digest, cancelled, observer)?;
    }
    // Exact hashes make the relocated semantic evidence identical to the parsed source.
    // Verify every copied artifact, then recheck source identity before final publication.
    verify(&destination, &copied, cancelled)?;
    verify(&source, &evidence, cancelled)?;
    let pending = destination.join("bundle-completion.partial.json");
    copy_checked(
        &source.join("completed.json"),
        &pending,
        &completion,
        cancelled,
        observer,
    )?;
    ensure!(
        !cancelled.load(Ordering::Relaxed),
        "View bundle export cancelled before publication"
    );
    crate::jobs::publish_no_replace(&pending, &destination.join("completed.json"))?;
    Ok(destination)
}

#[cfg(test)]
#[path = "session-bundle-export-tests.rs"]
mod tests;
