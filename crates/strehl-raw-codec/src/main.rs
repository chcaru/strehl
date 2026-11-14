use anyhow::{Context, Result, ensure};
use clap::{Parser, Subcommand};
use std::{
    fs::File,
    io::Read,
    path::{Path, PathBuf},
};
use strehl_raw_codec::{MAX_RAW, archive};

#[derive(Parser)]
#[command(about = "Verify or restore exact original RAWs from Strehl lossless archives")]
struct Args {
    #[command(subcommand)]
    command: Command,
}
#[derive(Subcommand)]
enum Command {
    /// Verify every original byte without writing an ARW.
    Verify { input: PathBuf },
    /// Restore one archive or a stack folder. Existing files are never replaced.
    Restore {
        input: PathBuf,
        #[arg(long)]
        output_dir: Option<PathBuf>,
    },
    /// Archive an existing RAW without altering or deleting the source.
    Pack { input: PathBuf, output: PathBuf },
}

fn files(input: &Path) -> Result<Vec<PathBuf>> {
    if !input.is_dir() {
        ensure!(archive::is_archive(input), "Expected an .ARW.straw archive");
        return Ok(vec![input.into()]);
    }
    let mut paths = std::fs::read_dir(input)?
        .map(|e| e.map(|e| e.path()))
        .collect::<std::io::Result<Vec<_>>>()?;
    paths.retain(|p| p.is_file() && archive::is_archive(p));
    paths.sort();
    ensure!(!paths.is_empty(), "No RAW archives in {}", input.display());
    Ok(paths)
}
fn persist(temp: tempfile::NamedTempFile, output: &Path) -> Result<()> {
    temp.as_file().sync_all()?;
    temp.persist_noclobber(output)
        .map_err(|e| e.error)
        .context("Refusing to replace an existing file")?;
    #[cfg(unix)]
    File::open(output.parent().context("No parent folder")?)?.sync_all()?;
    Ok(())
}
fn main() -> Result<()> {
    match Args::parse().command {
        Command::Verify { input } => {
            for path in files(&input)? {
                let d = archive::verify(&path)?;
                println!(
                    "Verified {} bytes SHA-256 {}: {}",
                    d.bytes,
                    d.sha256,
                    path.display()
                );
            }
        }
        Command::Restore { input, output_dir } => {
            for path in files(&input)? {
                let directory = output_dir
                    .as_deref()
                    .unwrap_or_else(|| path.parent().unwrap_or(Path::new(".")));
                std::fs::create_dir_all(directory)?;
                let output = directory.join(path.file_stem().context("Missing original filename")?);
                ensure!(!output.exists(), "Already exists: {}", output.display());
                let mut temp = tempfile::NamedTempFile::new_in(directory)?;
                let d = archive::unpack(std::io::BufReader::new(File::open(&path)?), &mut temp)?;
                persist(temp, &output)?;
                println!(
                    "Restored {} bytes SHA-256 {}: {}",
                    d.bytes,
                    d.sha256,
                    output.display()
                );
            }
        }
        Command::Pack { input, output } => {
            let file = File::open(&input)?;
            ensure!(
                file.metadata()?.len() <= MAX_RAW,
                "RAW exceeds archive size limit"
            );
            ensure!(!output.exists(), "Already exists: {}", output.display());
            let directory = output
                .parent()
                .filter(|p| !p.as_os_str().is_empty())
                .unwrap_or(Path::new("."));
            std::fs::create_dir_all(directory)?;
            let mut bytes = Vec::new();
            file.take(MAX_RAW + 1).read_to_end(&mut bytes)?;
            let mut temp = tempfile::NamedTempFile::new_in(directory)?;
            archive::pack(bytes, &mut temp)?;
            archive::verify(temp.path())?;
            persist(temp, &output)?;
            println!("Archived: {}", output.display());
        }
    }
    Ok(())
}
