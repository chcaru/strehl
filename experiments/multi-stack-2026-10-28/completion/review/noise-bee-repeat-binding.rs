//! Metadata-only original→workspace-copy membership; caller first hashes the
//! original receipt against the immutable protocol.input_receipts entry.
use std::collections::BTreeSet;

#[derive(Clone, Debug)]
pub struct Record {
    pub filename: String,
    pub bytes: u64,
    pub sha256: String,
}

pub fn bind32(originals: &[Record], copies: &[Record]) -> Result<[usize; 32], &'static str> {
    if originals.len() != 32 || copies.len() != 32 {
        return Err("exact32source census required");
    }
    let mut names = BTreeSet::new();
    let mut hashes = BTreeSet::new();
    for (ordinal, o) in originals.iter().enumerate() {
        if o.filename.to_ascii_uppercase() != format!("DSC{:05}.ARW", 328 + ordinal)
            || o.bytes == 0
            || o.sha256.len() != 64
            || !o
                .sha256
                .bytes()
                .all(|x| x.is_ascii_hexdigit() && !x.is_ascii_uppercase())
            || !names.insert(o.filename.to_ascii_uppercase())
            || !hashes.insert(&o.sha256)
        {
            return Err("invalid/duplicate frozen original identity");
        }
    }
    let mut result = [usize::MAX; 32];
    for (global, copy) in copies.iter().enumerate() {
        let ordinal = originals
            .iter()
            .position(|o| o.filename.eq_ignore_ascii_case(&copy.filename))
            .ok_or("copy filename outside frozen originals")?;
        let original = &originals[ordinal];
        if copy.bytes != original.bytes
            || copy.sha256 != original.sha256
            || result[ordinal] != usize::MAX
        {
            return Err("copy identity mismatch or duplicate");
        }
        result[ordinal] = global;
    }
    if result.contains(&usize::MAX) {
        return Err("unbound original");
    }
    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::*;
    fn originals() -> Vec<Record> {
        (0..32)
            .map(|i| Record {
                filename: format!("DSC{:05}.ARW", 328 + i),
                bytes: 1000 + i,
                sha256: format!("{i:064x}"),
            })
            .collect()
    }
    #[test]
    fn content_identity_survives_copy_order_and_new_mtime() {
        let o = originals();
        let mut c = o.clone();
        c.reverse();
        let map = bind32(&o, &c).unwrap();
        assert_eq!(map, std::array::from_fn(|i| 31 - i));
    }
    #[test]
    fn same_names_wrong_content_refused() {
        let o = originals();
        let mut c = o.clone();
        c[12].sha256 = format!("{:064x}", 999);
        assert!(bind32(&o, &c).is_err());
    }
    #[test]
    fn same_name_digest_wrong_size_refused() {
        let o = originals();
        let mut c = o.clone();
        c[3].bytes += 1;
        assert!(bind32(&o, &c).is_err());
    }
    #[test]
    fn duplicated_or_missing_acquisition_refused() {
        let o = originals();
        let mut c = o.clone();
        c[3] = c[4].clone();
        assert!(bind32(&o, &c).is_err());
        assert!(bind32(&o, &o[..31]).is_err());
    }
}
