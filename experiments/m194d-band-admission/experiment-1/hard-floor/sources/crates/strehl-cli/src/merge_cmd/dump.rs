//! M111's merge-state dump: the two pass-state planes the election map does not
//! carry.
//!
//! `STREHL_DUMP_ELECTION` (`merge_cmd::write_election_map`) already writes pass
//! one's winner *index*. Two other planes decide whether a visible artefact is
//! an election artefact, and neither is observable from the outside:
//!
//! * **`best_focus`** — the winner's *regularised response value*. A region
//!   whose winner response sits at the pure-noise floor
//!   ([`strehl_core::merge::FOCUS_NOISE_SD`] is the SD of that floor) contains
//!   no focus signal, so its winner index is noise dressed up as a decision. A
//!   region whose winner response is far above the floor was elected on
//!   structure. **The index map alone cannot tell those apart**, and the whole
//!   waxy-blob question is which one the blobs are.
//! * **`n_eff`** — how many frames pass two actually averaged at each pixel.
//!   This is the direct observation of whether the fact-19 noise-gated mean is
//!   firing, per pixel, rather than the whole-image mean the log already
//!   prints. A whole-image mean cannot locate anything (fact 1141).
//!
//! # Why NPY and not TIFF
//!
//! `best_focus` is `f32` and its interesting range spans the pure-noise floor
//! (~0.43) to the p90 winner response (~23). Quantising that into a 16-bit
//! container to reuse the existing writer would mean choosing a scale, and a
//! chosen scale is exactly the kind of undocumented transform that makes a
//! diagnostic unfalsifiable later. NPY is 128 bytes of header plus the raw
//! little-endian buffer, it is self-describing in dtype *and* shape, and
//! `numpy.load` reads it with no options to get wrong.
//!
//! # Non-perturbation
//!
//! Every function here takes `&[T]` and writes a file. Nothing returns into the
//! merge. Rule 26 nevertheless demands the run, not the argument: see
//! `experiments/M111-waxy-blobs/` for the byte-identical on/off pair.

use std::io::Write;
use std::path::{Path, PathBuf};

use anyhow::{Context, Result};

/// Directory to write the merge-state dump into. Unset means write nothing.
const DUMP_ENV: &str = "STREHL_DUMP_MERGE_STATE";

/// The resolved dump directory. Unset, or set to whitespace, means no dump.
///
/// The caller prints the resolved path for the same reason
/// `super::election_map_path` prints its own: rule 47, an unprinted environment
/// variable is the input that makes a record unreproducible.
pub(crate) fn dump_dir() -> Option<PathBuf> {
    let raw = std::env::var(DUMP_ENV).ok()?;
    let trimmed = raw.trim();
    if trimmed.is_empty() {
        eprintln!("{DUMP_ENV} is set but empty; not writing a merge-state dump");
        return None;
    }
    Some(PathBuf::from(trimmed))
}

fn header(dtype: &str, width: usize, height: usize) -> Vec<u8> {
    // NPY v1.0: magic, version, u16 header length, then a padded ASCII dict
    // whose total length (magic..=dict) is a multiple of 64.
    let dict =
        format!("{{'descr': '{dtype}', 'fortran_order': False, 'shape': ({height}, {width}), }}");
    let prefix = 10; // 6 magic + 2 version + 2 length
    let unpadded = prefix + dict.len() + 1;
    let pad = (64 - (unpadded % 64)) % 64;
    let len = dict.len() + pad + 1;
    let mut out = Vec::with_capacity(prefix + len);
    out.extend_from_slice(b"\x93NUMPY\x01\x00");
    out.extend_from_slice(&(len as u16).to_le_bytes());
    out.extend_from_slice(dict.as_bytes());
    out.extend(std::iter::repeat_n(b' ', pad));
    out.push(b'\n');
    out
}

fn emit<W: Write>(w: &mut W, dtype: &str, width: usize, height: usize, body: &[u8]) -> Result<()> {
    w.write_all(&header(dtype, width, height))?;
    w.write_all(body)?;
    Ok(())
}

fn to_file(path: &Path, dtype: &str, width: usize, height: usize, body: &[u8]) -> Result<()> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)
            .with_context(|| format!("creating {}", parent.display()))?;
    }
    let mut f = std::io::BufWriter::new(
        std::fs::File::create(path).with_context(|| format!("creating {}", path.display()))?,
    );
    emit(&mut f, dtype, width, height, body)?;
    f.flush()?;
    Ok(())
}

/// Refuse a plane whose length does not match the geometry, **before** any
/// filesystem call.
///
/// This is separated out so it can be tested without a path. The first version
/// of the test asserted `!path.exists()` after a refusal, which reads as a
/// stronger guarantee but is not one: it makes the test depend on filesystem
/// residue, and M111's own planted-mutation control (NC6) left the file behind
/// and turned the *restored* tree red. A test that a sabotage can leave broken
/// is a test that cannot be trusted to have been green for the right reason.
fn check_len(len: usize, width: usize, height: usize, what: &str) -> Result<()> {
    anyhow::ensure!(
        len == width * height,
        "{what} plane is {len} long, expected {width}x{height}"
    );
    Ok(())
}

/// Write a `u16` plane as an `(h, w)` little-endian NPY file.
pub(crate) fn write_u16(path: &Path, width: usize, height: usize, data: &[u16]) -> Result<()> {
    check_len(data.len(), width, height, "u16")?;
    let mut body = Vec::with_capacity(data.len() * 2);
    for v in data {
        body.extend_from_slice(&v.to_le_bytes());
    }
    to_file(path, "<u2", width, height, &body)
}

/// Write an `f32` plane as an `(h, w)` little-endian NPY file.
pub(crate) fn write_f32(path: &Path, width: usize, height: usize, data: &[f32]) -> Result<()> {
    check_len(data.len(), width, height, "f32")?;
    let mut body = Vec::with_capacity(data.len() * 4);
    for v in data {
        body.extend_from_slice(&v.to_le_bytes());
    }
    to_file(path, "<f4", width, height, &body)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_npy_header_is_a_multiple_of_sixty_four_and_carries_the_shape() {
        let h = header("<f4", 7, 5);
        assert_eq!(h.len() % 64, 0, "numpy requires 64-byte alignment");
        let text = String::from_utf8(h[10..].to_vec()).unwrap();
        assert!(text.contains("'shape': (5, 7)"), "{text}");
        assert!(text.ends_with('\n'));
    }

    #[test]
    fn an_emitted_plane_is_a_header_plus_exactly_its_own_bytes() {
        let mut buf: Vec<u8> = Vec::new();
        let body: Vec<u8> = [1.0f32, 2.0, 3.0, 4.0, 5.0, 6.0]
            .iter()
            .flat_map(|v| v.to_le_bytes())
            .collect();
        emit(&mut buf, "<f4", 3, 2, &body).unwrap();
        assert_eq!(&buf[..6], b"\x93NUMPY");
        let hlen = u16::from_le_bytes([buf[8], buf[9]]) as usize;
        assert_eq!(buf.len(), 10 + hlen + 6 * 4);
        let first = f32::from_le_bytes(buf[10 + hlen..10 + hlen + 4].try_into().unwrap());
        assert_eq!(first, 1.0);
    }

    #[test]
    fn a_length_mismatch_is_refused_and_the_message_names_both_shapes() {
        let e = check_len(3, 4, 4, "u16").unwrap_err().to_string();
        assert!(e.contains("3 long"), "{e}");
        assert!(e.contains("4x4"), "{e}");
        assert!(check_len(16, 4, 4, "u16").is_ok());
    }
}
