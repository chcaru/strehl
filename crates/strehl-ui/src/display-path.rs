//! Paths as people read them. Windows canonical paths carry the `\\?\`
//! verbatim prefix (`\\?\UNC\` for shares); it is needed by some file APIs
//! but means nothing on screen or when pasted into Explorer.
use std::path::Path;

pub(crate) fn display_path(path: &Path) -> String {
    let text = path.display().to_string();
    if let Some(share) = text.strip_prefix(r"\\?\UNC\") {
        format!(r"\\{share}")
    } else if let Some(local) = text.strip_prefix(r"\\?\") {
        local.to_owned()
    } else {
        text
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn verbatim_prefixes_are_removed_and_other_paths_are_unchanged() {
        for (raw, shown) in [
            (r"\\?\D:\StrehlCaptures\weevil", r"D:\StrehlCaptures\weevil"),
            (r"\\?\UNC\nas\photos\run", r"\\nas\photos\run"),
            (r"D:\StrehlCaptures", r"D:\StrehlCaptures"),
            (r"\\nas\photos", r"\\nas\photos"),
            ("relative/run", "relative/run"),
        ] {
            assert_eq!(display_path(Path::new(raw)), shown, "{raw}");
        }
    }
}
