//! Stamp the source commit into the binary at build time.
//!
//! # Why this exists
//!
//! `strehl --version` printed `strehl 0.0.0` and nothing else. Every audit in
//! this project pins a binary and then reasons about which source produced it,
//! and that fact lived nowhere in the artifact -- so it was reconstructed from
//! filesystem timestamps and recollection. An hour was lost to a "regression"
//! that was really a pin predating the feature by 57 minutes.
//!
//! **A binary that cannot name its own provenance cannot be audited.** Every
//! claim about what a pinned artifact does is a claim about which source built
//! it.
//!
//! # What "dirty" means here, precisely
//!
//! Dirtiness is computed over `crates/` only -- the paths that actually compile
//! into this binary -- and not over the whole worktree. A modified design note
//! or experiment script cannot change the artifact, so counting it would make
//! the flag fire constantly and mean nothing. Changes under `crates/` can and
//! do change the artifact, so those are reported.
//!
//! `-dirty` therefore means: **the code this binary was built from is not the
//! code at that commit.** A measurement taken against a `-dirty` binary is not
//! reproducible from the hash alone, and should say so.
//!
//! # Failure is reported, never faked
//!
//! If git is unavailable or this is not a repository, the stamp reads `unknown`
//! rather than an empty string or a plausible-looking placeholder. An audit that
//! reads `unknown` knows it has no provenance; one that reads a wrong hash does
//! not, and would be worse off than with no stamp at all.

use std::path::{Path, PathBuf};
use std::process::Command;

fn git(dir: &Path, args: &[&str]) -> Option<String> {
    let out = Command::new("git").current_dir(dir).args(args).output().ok()?;
    if !out.status.success() {
        return None;
    }
    Some(String::from_utf8(out.stdout).ok()?.trim().to_string())
}

/// The directory git keeps its state in.
///
/// This crate lives in a SUBMODULE, where `.git` is a FILE containing
/// `gitdir: <path>` rather than a directory. Resolving it is what lets the
/// rerun triggers below actually fire; watching a `.git/HEAD` that does not
/// exist would silently never re-stamp, and a stale stamp is the exact defect
/// this file exists to remove.
fn git_dir(dir: &Path) -> Option<PathBuf> {
    let raw = git(dir, &["rev-parse", "--absolute-git-dir"])?;
    let p = PathBuf::from(raw);
    p.is_dir().then_some(p)
}

/// `-dirty`, `` (clean), or `-dirty?` when the question could not be answered.
///
/// # The bug this function is written around
///
/// The first version of this ran `git status --porcelain -- crates` from
/// `CARGO_MANIFEST_DIR`. **Git pathspecs are relative to the working
/// directory**, and that directory is `crates/strehl-cli`, so the pathspec
/// meant `crates/strehl-cli/crates` -- which does not exist. It matched
/// nothing, the output was empty, and empty was read as CLEAN. The stamp
/// certified a clean build over seven modified files on its very first run.
///
/// An empty result meant "looked in the wrong place" and was reported as
/// "nothing was wrong". Those must never be the same glyph, so the scope is now
/// resolved against the repository root AND confirmed non-empty before its
/// emptiness is allowed to mean anything.
fn dirty_suffix(manifest: &Path) -> &'static str {
    let Some(top) = git(manifest, &["rev-parse", "--show-toplevel"]).map(PathBuf::from) else {
        return "-dirty?";
    };
    // Does the scope select any tracked file at all? If not, a clean `status`
    // is not evidence of cleanliness -- it is evidence of an empty scope, which
    // is the defect above.
    match git(&top, &["ls-files", "--", "crates"]) {
        Some(files) if !files.trim().is_empty() => {}
        _ => return "-dirty?",
    }
    // `--porcelain` prints one line per changed path and nothing when clean, so
    // emptiness is the test -- now that emptiness has been shown to be
    // meaningful. Scoped to `crates/`; see the module comment for why the whole
    // worktree is the wrong scope.
    match git(&top, &["status", "--porcelain", "--", "crates"]) {
        Some(s) if s.trim().is_empty() => "",
        Some(_) => "-dirty",
        None => "-dirty?",
    }
}

fn main() {
    let manifest = PathBuf::from(std::env::var("CARGO_MANIFEST_DIR").unwrap());

    // An explicit stamp always wins, so a build outside a checkout (a release
    // tarball, a container) can still name its source.
    println!("cargo:rerun-if-env-changed=STREHL_BUILD_ID");
    if let Ok(forced) = std::env::var("STREHL_BUILD_ID") {
        if !forced.trim().is_empty() {
            println!("cargo:rustc-env=STREHL_BUILD_ID={}", forced.trim());
            return;
        }
    }

    let stamp = match git(&manifest, &["rev-parse", "--short=12", "HEAD"]) {
        Some(hash) if !hash.is_empty() => format!("{hash}{}", dirty_suffix(&manifest)),
        _ => "unknown".to_string(),
    };

    if let Some(g) = git_dir(&manifest) {
        // Re-stamp when the commit moves or the index changes. Without these a
        // build that touches no source file keeps the previous hash.
        for f in ["HEAD", "index"] {
            let p = g.join(f);
            if p.exists() {
                println!("cargo:rerun-if-changed={}", p.display());
            }
        }
    }

    println!("cargo:rustc-env=STREHL_BUILD_ID={stamp}");
}
