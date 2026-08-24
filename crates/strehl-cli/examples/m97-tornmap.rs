//! M97 — does `WarpMap::load` reject a **torn** sidecar, or silently render a
//! partial registration?
//!
//! M97 measured a real half-written read of `bee-3-cpl/warpmap.txt` while a
//! sibling process rewrote it in place. That is not theoretical: with several
//! agents live in one working tree, a merge can read a sidecar that another
//! process is still writing. The consequence depends entirely on what `load`
//! does with a short file:
//!
//! * if it **rejects** the file, `load_or_solve` falls through to `re-solving`
//!   and the render is correct but slow — an availability bug;
//! * if it **accepts** the file, the merge registers some frames and silently
//!   leaves the rest wherever the truncation left them — a correctness bug that
//!   produces a plausible-looking, wrong photograph and no diagnostic.
//!
//! So this reads a real sidecar, truncates copies of it at a ladder of byte
//! fractions, and reports what `load` does with each. Everything is written to
//! the system temp directory; **no capture directory is touched**.
//!
//! Controls, so that a clean result cannot be a disconnected probe:
//!
//! * **C-full** — an untruncated byte-for-byte copy must load `Ok`, and report
//!   the same frame count as the original. If the copy itself fails, the
//!   harness is broken and every `Err` below is meaningless.
//! * **C-empty** — a zero-byte file must fail. If it does not, `load` is not
//!   reading the file at all.
//! * **frame-count check** — for any truncation that loads `Ok`, the reported
//!   `len()` is printed next to the original's. An `Ok` with a *short* length
//!   is the dangerous case and is called out explicitly, because
//!   `load_or_solve` only catches that through a separate `map.len() ==
//!   paths.len()` test, which a caller could forget.
//!
//! ```text
//! cargo run --release -p strehl-cli --example m97-tornmap -- <SIDECAR.txt>
//! ```

use std::path::{Path, PathBuf};

use anyhow::{Context, Result};
use strehl_core::warpmap::WarpMap;

fn write_prefix(src: &[u8], n: usize, tag: &str) -> Result<PathBuf> {
    let p = std::env::temp_dir().join(format!("m97-tornmap-{tag}.txt"));
    std::fs::write(&p, &src[..n.min(src.len())])?;
    Ok(p)
}

fn report(label: &str, path: &Path, want_len: usize) -> bool {
    let bytes = std::fs::metadata(path).map(|m| m.len()).unwrap_or(0);
    match WarpMap::load(path) {
        Ok(m) => {
            let n = m.len();
            let flag = if n == want_len {
                "OK, full length"
            } else {
                "*** ACCEPTED A SHORT MAP ***"
            };
            println!(
                "  {label:<14} {bytes:>8} bytes  -> Ok, {n} frames (want {want_len})  {flag}"
            );
            n != want_len
        }
        Err(e) => {
            let msg = e.to_string();
            let msg = msg.lines().next().unwrap_or("").trim();
            println!("  {label:<14} {bytes:>8} bytes  -> Err: {msg}");
            false
        }
    }
}

fn main() -> Result<()> {
    let arg = std::env::args().nth(1).context(
        "usage: m97-tornmap <SIDECAR.txt>   (a warp-map sidecar to truncate copies of)",
    )?;
    let src_path = PathBuf::from(&arg);
    let src = std::fs::read(&src_path).with_context(|| format!("reading {arg}"))?;

    let original = WarpMap::load(&src_path)
        .with_context(|| format!("{arg} does not load as a WarpMap; pick a valid sidecar"))?;
    let want = original.len();
    println!(
        "source        : {} ({} bytes, {} frames, {} placed, {} refused)",
        src_path.display(),
        src.len(),
        want,
        original.placed_count(),
        original.refused_count()
    );

    println!("\ncontrols");
    let full = write_prefix(&src, src.len(), "full")?;
    let full_bad = report("C-full copy", &full, want);
    let empty = write_prefix(&src, 0, "empty")?;
    let empty_ok = WarpMap::load(&empty).is_ok();
    println!(
        "  C-empty        must fail -> {}",
        if empty_ok {
            "*** LOADED AN EMPTY FILE ***"
        } else {
            "Err, as required"
        }
    );

    println!("\ntruncations");
    let mut accepted_short = false;
    for pct in [10usize, 25, 50, 75, 90, 95, 99] {
        let n = src.len() * pct / 100;
        let p = write_prefix(&src, n, &format!("{pct:02}pct"))?;
        accepted_short |= report(&format!("{pct}% of bytes"), &p, want);
        let _ = std::fs::remove_file(&p);
    }
    // A tear is far more likely to land mid-line than on a line boundary, but
    // both are possible, so exercise a whole-line prefix too.
    let text = String::from_utf8_lossy(&src);
    let lines: Vec<&str> = text.lines().collect();
    if lines.len() > 4 {
        let keep = lines.len() / 2;
        let body = lines[..keep].join("\n") + "\n";
        let p = write_prefix(body.as_bytes(), body.len(), "halflines")?;
        accepted_short |= report("half the lines", &p, want);
        let _ = std::fs::remove_file(&p);
    }

    let _ = std::fs::remove_file(&full);
    let _ = std::fs::remove_file(&empty);

    println!("\nverdict");
    if full_bad {
        println!("  HARNESS BROKEN: the untruncated copy did not reproduce the original.");
    } else if accepted_short {
        println!(
            "  CORRECTNESS RISK: `WarpMap::load` accepted at least one torn file and\n  \
             returned a SHORT map. A caller that does not separately compare `len()`\n  \
             against the frame count will register some frames and silently leave the\n  \
             rest unregistered."
        );
    } else {
        println!(
            "  SAFE: every torn file was rejected. A torn sidecar costs a re-solve,\n  \
             not a wrong photograph."
        );
    }
    Ok(())
}
