//! Immutable local storage for frozen learned treatments, outside pixel rendering.
//!
//! The caller selects an existing trusted directory; recipes supply only typed
//! content keys. Publication is synced and does not replace a competing file.
//! Missing/corrupt/wrong-source assets return errors, never a changed appearance.
//! Store-directory identity and link checks detect ordinary replacement, but
//! pathname operations are not a sandbox against a hostile process concurrently
//! changing ancestors between validation and publication. No garbage collection
//! occurs here: versions, Undo and recovery may still reference old assets.
use crate::learned_asset::{AssetDigest, AssetIdentities, FrozenLearnedAsset, MAX_ASSET_BYTES};
use crate::learned_scene_asset::FrozenSceneAsset;
use anyhow::{Context, Result, ensure};
use std::{
    fmt,
    fs::{self, File, Metadata},
    io::{Read, Write},
    path::{Path, PathBuf},
    str::FromStr,
    sync::{
        Arc,
        atomic::{AtomicBool, Ordering},
    },
};

const IO_CHUNK_BYTES: usize = 256 * 1024;

/// SHA-256 of the asset envelope before its trailing digest, not a filename.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub struct AssetKey(AssetDigest);

impl AssetKey {
    pub fn from_digest(digest: AssetDigest) -> Self {
        Self(digest)
    }
    pub fn digest(self) -> AssetDigest {
        self.0
    }
    fn filename(self) -> String {
        format!("{self}.strehl-profile")
    }
}

impl fmt::Display for AssetKey {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        for byte in self.0 {
            write!(f, "{byte:02x}")?;
        }
        Ok(())
    }
}

impl FromStr for AssetKey {
    type Err = anyhow::Error;
    fn from_str(value: &str) -> Result<Self> {
        ensure!(
            value.len() == 64
                && value
                    .bytes()
                    .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b)),
            "Asset key must be exactly 64 lowercase hexadecimal characters"
        );
        let nibble = |b: u8| {
            if b.is_ascii_digit() {
                b - b'0'
            } else {
                b - b'a' + 10
            }
        };
        let mut digest = [0; 32];
        for (destination, pair) in digest.iter_mut().zip(value.as_bytes().as_chunks::<2>().0) {
            *destination = nibble(pair[0]) * 16 + nibble(pair[1]);
        }
        Ok(Self(digest))
    }
}

/// Expected identities must come from the owning photo/recipe or analysis job,
/// not be copied from an untrusted file merely to make its comparison pass.
#[derive(Clone, Debug)]
pub struct ExpectedAsset {
    pub identities: AssetIdentities,
    pub full_size: [u32; 2],
}

impl ExpectedAsset {
    pub fn verify(&self, asset: &FrozenLearnedAsset) -> Result<()> {
        let actual = asset.descriptor();
        self.verify_fields(&actual.identities, actual.origin.full_size)
    }

    pub fn verify_scene(&self, asset: &FrozenSceneAsset) -> Result<()> {
        let actual = asset.descriptor();
        self.verify_fields(&actual.identities, actual.origin.full_size)
    }

    fn verify_fields(&self, actual: &AssetIdentities, full_size: [u32; 2]) -> Result<()> {
        ensure!(
            full_size == self.full_size,
            "Frozen asset photograph dimensions mismatch"
        );
        ensure!(
            actual.source_sha256 == self.identities.source_sha256,
            "Frozen asset source identity mismatch"
        );
        ensure!(
            actual.contract_id == self.identities.contract_id
                && actual.contract_sha256 == self.identities.contract_sha256,
            "Frozen asset contract mismatch"
        );
        ensure!(
            actual.model_sha256 == self.identities.model_sha256,
            "Frozen asset model identity mismatch"
        );
        ensure!(
            actual.input_sha256 == self.identities.input_sha256,
            "Frozen asset analysis input identity mismatch"
        );
        Ok(())
    }
}

#[derive(Clone)]
pub struct LearnedAssetStore {
    root: PathBuf,
    root_identity: (u64, u64),
    // Retaining the directory handle also prevents reuse of an unlinked inode
    // from making the identity check spuriously match a replacement directory.
    root_handle: Arc<File>,
}

fn check_cancelled(cancelled: &AtomicBool) -> Result<()> {
    ensure!(
        !cancelled.load(Ordering::Relaxed),
        "Frozen asset operation cancelled"
    );
    Ok(())
}

fn is_link(metadata: &Metadata) -> bool {
    if metadata.file_type().is_symlink() {
        return true;
    }
    #[cfg(windows)]
    {
        use std::os::windows::fs::MetadataExt;
        use windows_sys::Win32::Storage::FileSystem::FILE_ATTRIBUTE_REPARSE_POINT;
        if metadata.file_attributes() & FILE_ATTRIBUTE_REPARSE_POINT != 0 {
            return true;
        }
    }
    false
}

fn regular_file(metadata: &Metadata) -> Result<()> {
    ensure!(
        metadata.is_file() && !is_link(metadata),
        "Frozen asset must be a regular file, not a link or reparse point"
    );
    ensure!(
        metadata.len() <= MAX_ASSET_BYTES as u64,
        "Frozen asset exceeds file size limit"
    );
    Ok(())
}

#[cfg(unix)]
fn file_identity(file: &File) -> Result<(u64, u64)> {
    use std::os::unix::fs::MetadataExt;
    let metadata = file.metadata()?;
    Ok((metadata.dev(), metadata.ino()))
}

#[cfg(windows)]
fn file_identity(file: &File) -> Result<(u64, u64)> {
    use std::os::windows::io::AsRawHandle;
    use windows_sys::Win32::Storage::FileSystem::{
        BY_HANDLE_FILE_INFORMATION, GetFileInformationByHandle,
    };
    let mut info: BY_HANDLE_FILE_INFORMATION = unsafe { std::mem::zeroed() };
    // SAFETY: the File owns a valid handle throughout the call; info is a
    // correctly sized writable structure, initialized before any field is read.
    ensure!(
        unsafe { GetFileInformationByHandle(file.as_raw_handle() as _, &mut info) } != 0,
        "Reading store directory identity: {}",
        std::io::Error::last_os_error()
    );
    Ok((
        u64::from(info.dwVolumeSerialNumber),
        (u64::from(info.nFileIndexHigh) << 32) | u64::from(info.nFileIndexLow),
    ))
}

#[cfg(not(any(unix, windows)))]
fn file_identity(_file: &File) -> Result<(u64, u64)> {
    anyhow::bail!("Frozen asset storage requires a supported native filesystem");
}

fn open_directory(path: &Path) -> Result<File> {
    let metadata = fs::symlink_metadata(path)?;
    ensure!(
        metadata.is_dir() && !is_link(&metadata),
        "Frozen asset store must be a directory, not a link or reparse point"
    );
    let mut options = fs::OpenOptions::new();
    options.read(true);
    #[cfg(windows)]
    {
        use std::os::windows::fs::OpenOptionsExt;
        use windows_sys::Win32::Storage::FileSystem::{
            FILE_FLAG_BACKUP_SEMANTICS, FILE_FLAG_OPEN_REPARSE_POINT,
        };
        options.custom_flags(FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT);
    }
    let file = options.open(path)?;
    let metadata = file.metadata()?;
    ensure!(
        metadata.is_dir() && !is_link(&metadata),
        "Store directory changed to a link or non-directory"
    );
    Ok(file)
}

impl LearnedAssetStore {
    /// Open an existing trusted directory. Directory selection/creation belongs
    /// to the photo/project owner; this function never creates arbitrary paths.
    pub fn open(root: &Path) -> Result<Self> {
        ensure!(
            root.is_absolute(),
            "Frozen asset store requires an absolute directory"
        );
        let original = open_directory(root)?;
        let root_identity = file_identity(&original)?;
        let root = fs::canonicalize(root)?;
        let canonical = open_directory(&root)?;
        ensure!(
            file_identity(&canonical)? == root_identity,
            "Store directory changed while opening"
        );
        Ok(Self {
            root,
            root_identity,
            root_handle: Arc::new(original),
        })
    }

    pub fn root(&self) -> &Path {
        &self.root
    }

    /// For revealing an asset to the user; no caller-controlled path component
    /// can enter this name. Actual reads/writes revalidate the directory.
    pub fn path(&self, key: AssetKey) -> PathBuf {
        self.root.join(key.filename())
    }

    fn validate_root(&self) -> Result<()> {
        let current = open_directory(&self.root).context("Frozen asset store is unavailable")?;
        ensure!(
            file_identity(&current)? == self.root_identity
                && fs::canonicalize(&self.root)? == self.root,
            "Frozen asset store directory was replaced"
        );
        Ok(())
    }

    fn sync_directory(&self) -> Result<()> {
        #[cfg(unix)]
        self.root_handle
            .sync_all()
            .context("Syncing frozen asset directory")?;
        // Windows publication uses MOVEFILE_WRITE_THROUGH in publish.rs.
        #[cfg(not(unix))]
        let _ = &self.root_handle;
        Ok(())
    }

    pub fn load(
        &self,
        key: AssetKey,
        expected: &ExpectedAsset,
        cancelled: &AtomicBool,
    ) -> Result<Arc<FrozenLearnedAsset>> {
        let bytes = self.read_bytes(key, cancelled)?;
        let asset = FrozenLearnedAsset::decode(&bytes)
            .with_context(|| format!("Invalid frozen asset {key}"))?;
        ensure!(
            asset.digest() == key.digest(),
            "Frozen asset content does not match its key"
        );
        expected.verify(&asset)?;
        check_cancelled(cancelled)?;
        Ok(Arc::new(asset))
    }

    /// Read only the distinct scene codec. Legacy content is never interpreted
    /// as a scene treatment, even if supplied under the same typed content key.
    pub fn load_scene(
        &self,
        key: AssetKey,
        expected: &ExpectedAsset,
        cancelled: &AtomicBool,
    ) -> Result<Arc<FrozenSceneAsset>> {
        let bytes = self.read_bytes(key, cancelled)?;
        let asset = FrozenSceneAsset::decode(&bytes)
            .with_context(|| format!("Invalid frozen scene asset {key}"))?;
        ensure!(
            asset.digest() == key.digest(),
            "Frozen scene content does not match its key"
        );
        expected.verify_scene(&asset)?;
        check_cancelled(cancelled)?;
        Ok(Arc::new(asset))
    }

    fn read_bytes(&self, key: AssetKey, cancelled: &AtomicBool) -> Result<Vec<u8>> {
        check_cancelled(cancelled)?;
        self.validate_root()?;
        let path = self.path(key);
        let named = fs::symlink_metadata(&path)
            .with_context(|| format!("Frozen asset {key} is missing or unavailable"))?;
        regular_file(&named)?;
        let mut file = File::open(&path)?;
        let before = file.metadata()?;
        regular_file(&before)?;
        ensure!(
            named.len() == before.len() && named.modified()? == before.modified()?,
            "Frozen asset changed while opening"
        );
        let identity = file_identity(&file)?;
        let mut bytes = Vec::with_capacity(before.len() as usize);
        let mut chunk = vec![0u8; IO_CHUNK_BYTES];
        loop {
            check_cancelled(cancelled)?;
            let read = file.read(&mut chunk)?;
            if read == 0 {
                break;
            }
            ensure!(
                bytes.len() + read <= MAX_ASSET_BYTES,
                "Frozen asset grew beyond file size limit"
            );
            bytes.extend_from_slice(&chunk[..read]);
        }
        let after = file.metadata()?;
        ensure!(
            before.len() == after.len()
                && before.modified()? == after.modified()?
                && bytes.len() as u64 == before.len(),
            "Frozen asset changed while reading"
        );
        regular_file(&fs::symlink_metadata(&path)?)?;
        ensure!(
            fs::canonicalize(&path)? == path && file_identity(&File::open(&path)?)? == identity,
            "Frozen asset entry was replaced while reading"
        );
        self.validate_root()?;
        check_cancelled(cancelled)?;
        Ok(bytes)
    }

    /// The returned key is safe to reference only after this succeeds. A late
    /// cancellation can leave a complete unreferenced asset; it never replaces
    /// another object. A crash may leave an ignored temporary file, never a
    /// partially published final name. Existing valid content is idempotent.
    pub fn save(
        &self,
        asset: &FrozenLearnedAsset,
        expected: &ExpectedAsset,
        cancelled: &AtomicBool,
    ) -> Result<AssetKey> {
        self.save_before_publish(asset, expected, cancelled, || Ok(()))
    }

    fn save_before_publish(
        &self,
        asset: &FrozenLearnedAsset,
        expected: &ExpectedAsset,
        cancelled: &AtomicBool,
        hook: impl FnOnce() -> Result<()>,
    ) -> Result<AssetKey> {
        check_cancelled(cancelled)?;
        self.validate_root()?;
        expected.verify(asset)?;
        let key = AssetKey::from_digest(asset.digest());
        self.publish_checked(
            key,
            cancelled,
            || asset.encode(),
            || self.load(key, expected, cancelled).map(|_| ()),
            hook,
        )
    }

    /// Same immutable publication behavior as `save`, for the separately
    /// versioned SDR scene format. A key is usable only after success.
    pub fn save_scene(
        &self,
        asset: &FrozenSceneAsset,
        expected: &ExpectedAsset,
        cancelled: &AtomicBool,
    ) -> Result<AssetKey> {
        self.save_scene_before_publish(asset, expected, cancelled, || Ok(()))
    }

    fn save_scene_before_publish(
        &self,
        asset: &FrozenSceneAsset,
        expected: &ExpectedAsset,
        cancelled: &AtomicBool,
        hook: impl FnOnce() -> Result<()>,
    ) -> Result<AssetKey> {
        check_cancelled(cancelled)?;
        self.validate_root()?;
        expected.verify_scene(asset)?;
        let key = AssetKey::from_digest(asset.digest());
        self.publish_checked(
            key,
            cancelled,
            || asset.encode(),
            || self.load_scene(key, expected, cancelled).map(|_| ()),
            hook,
        )
    }

    // Both codecs retain identical file/link/race/cancellation behavior. Encoding
    // is lazy so idempotent publication does not rebuild an existing payload.
    fn publish_checked(
        &self,
        key: AssetKey,
        cancelled: &AtomicBool,
        encode: impl FnOnce() -> Result<Vec<u8>>,
        verify_existing: impl Fn() -> Result<()>,
        hook: impl FnOnce() -> Result<()>,
    ) -> Result<AssetKey> {
        let path = self.path(key);
        match fs::symlink_metadata(&path) {
            Ok(_) => {
                verify_existing()?;
                self.sync_directory()?;
                return Ok(key);
            }
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => {}
            Err(error) => return Err(error.into()),
        }
        let bytes = encode()?;
        ensure!(
            bytes.len() <= MAX_ASSET_BYTES,
            "Frozen asset exceeds file size limit"
        );
        check_cancelled(cancelled)?;
        let publication = crate::publish::new_file_checked(
            &path,
            |file| {
                for chunk in bytes.chunks(IO_CHUNK_BYTES) {
                    check_cancelled(cancelled)?;
                    file.write_all(chunk)?;
                }
                Ok(())
            },
            || {
                hook()?;
                check_cancelled(cancelled)?;
                self.validate_root()
            },
        );
        if let Err(publication_error) = publication {
            // A simultaneous publisher may have won with exactly this content.
            // Corruption or a different object never becomes successful reuse.
            if verify_existing().is_err() {
                return Err(publication_error).context("Publishing frozen asset");
            }
        }
        self.validate_root()?;
        self.sync_directory()?;
        verify_existing()?;
        Ok(key)
    }
}

#[cfg(test)]
#[path = "learned-store-tests.rs"]
mod tests;

#[cfg(test)]
#[path = "learned-scene-store-tests.rs"]
mod scene_tests;
