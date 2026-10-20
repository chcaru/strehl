//! Embed the application artwork and Windows product identity. Windows builds
//! fail explicitly if their resource compiler is missing or rejects either.
use std::{env, fs, path::PathBuf, process::Command};

fn main() {
    println!("cargo:rerun-if-changed=assets/strehl.ico");
    println!("cargo:rerun-if-changed=build.rs");
    for variable in [
        "STREHL_RC",
        "RC",
        "PATH",
        "WindowsSdkDir",
        "WindowsSDKVersion",
        "ProgramFiles(x86)",
        "ProgramFiles",
        "HOST",
        "TARGET",
    ] {
        println!("cargo:rerun-if-env-changed={variable}");
    }
    if env::var("CARGO_CFG_TARGET_OS").as_deref() != Ok("windows") {
        return;
    }
    let manifest =
        PathBuf::from(env::var_os("CARGO_MANIFEST_DIR").expect("Cargo manifest directory"));
    let out = PathBuf::from(env::var_os("OUT_DIR").expect("Cargo output directory"));
    let icon = manifest.join("assets/strehl.ico");
    assert!(
        icon.is_file(),
        "The checked-in Strehl Windows icon is missing: {}",
        icon.display()
    );
    let resource = out.join("strehl-icon.rc");
    let icon_path = icon
        .to_string_lossy()
        .replace('\\', "/")
        .replace('"', "\\\"");
    let version = env::var("CARGO_PKG_VERSION").expect("Cargo package version");
    let numeric_version = [
        env::var("CARGO_PKG_VERSION_MAJOR").unwrap(),
        env::var("CARGO_PKG_VERSION_MINOR").unwrap(),
        env::var("CARGO_PKG_VERSION_PATCH").unwrap(),
        "0".into(),
    ]
    .join(",");
    fs::write(
        &resource,
        format!(
            r#"#pragma code_page(65001)
1 ICON "{icon_path}"

LANGUAGE 9, 1
1 VERSIONINFO
 FILEVERSION {numeric_version}
 PRODUCTVERSION {numeric_version}
 FILEFLAGSMASK 0x3fL
 FILEFLAGS 0x0L
 FILEOS 0x40004L
 FILETYPE 0x1L
 FILESUBTYPE 0x0L
BEGIN
 BLOCK "StringFileInfo"
 BEGIN
  BLOCK "040904B0"
  BEGIN
   VALUE "FileDescription", "Strehl\0"
   VALUE "FileVersion", "{version}\0"
   VALUE "InternalName", "Strehl\0"
   VALUE "OriginalFilename", "Strehl.exe\0"
   VALUE "ProductName", "Strehl\0"
   VALUE "ProductVersion", "{version}\0"
  END
 END
 BLOCK "VarFileInfo"
 BEGIN
  VALUE "Translation", 0x0409, 1200
 END
END
"#
        ),
    )
    .expect("write Strehl Windows resource source");
    let msvc = env::var("CARGO_CFG_TARGET_ENV").as_deref() == Ok("msvc");
    let compiled = out.join(if msvc {
        "strehl-icon.res"
    } else {
        "strehl-icon.o"
    });
    let mut failures = Vec::new();
    for compiler in compilers(msvc) {
        // A successful compiler must produce this build's resource, rather
        // than accidentally accepting a previous attempt's file.
        if let Err(error) = fs::remove_file(&compiled) {
            assert_eq!(
                error.kind(),
                std::io::ErrorKind::NotFound,
                "remove stale icon resource: {error}"
            );
        }
        let mut command = Command::new(&compiler);
        if msvc {
            command
                .args(["/nologo", "/fo"])
                .arg(&compiled)
                .arg(&resource);
        } else {
            command
                .arg("--input")
                .arg(&resource)
                .arg("--output")
                .arg(&compiled)
                .args(["--output-format", "coff"]);
        }
        match command.output() {
            Ok(result)
                if result.status.success()
                    && fs::metadata(&compiled).is_ok_and(|metadata| metadata.len() > 0) =>
            {
                println!("cargo:rustc-link-arg-bin=strehl-ui={}", compiled.display());
                return;
            }
            Ok(result) => failures.push(format!(
                "{}: {}\n{}{}",
                compiler.display(),
                result.status,
                String::from_utf8_lossy(&result.stdout),
                String::from_utf8_lossy(&result.stderr),
            )),
            Err(error) => failures.push(format!("{}: {error}", compiler.display())),
        }
    }
    panic!(
        "Could not embed Strehl's Windows icon. Install the Windows SDK resource compiler \
         (rc.exe), or set STREHL_RC to its full path. GNU Windows targets require windres.\n{}",
        failures.join("\n")
    );
}

fn compilers(msvc: bool) -> Vec<PathBuf> {
    if let Some(path) = env::var_os("STREHL_RC").or_else(|| env::var_os("RC")) {
        return vec![path.into()];
    }
    if !msvc {
        let target = env::var("TARGET").unwrap_or_default();
        let prefix = match target.split('-').next().unwrap_or_default() {
            "x86_64" => "x86_64-w64-mingw32",
            "i686" => "i686-w64-mingw32",
            "aarch64" => "aarch64-w64-mingw32",
            _ => "",
        };
        return vec![format!("{prefix}-windres").into(), "windres".into()];
    }
    let mut found = vec![PathBuf::from("rc.exe"), PathBuf::from("llvm-rc")];
    let mut roots = Vec::new();
    if let Some(root) = env::var_os("WindowsSdkDir") {
        roots.push(PathBuf::from(root).join("bin"));
    }
    for variable in ["ProgramFiles(x86)", "ProgramFiles"] {
        if let Some(root) = env::var_os(variable) {
            roots.push(PathBuf::from(root).join("Windows Kits/10/bin"));
        }
    }
    let host = env::var("HOST").unwrap_or_default();
    let arch = if host.starts_with("aarch64") {
        "arm64"
    } else if host.starts_with("i686") {
        "x86"
    } else {
        "x64"
    };
    for root in roots {
        if let Some(version) = env::var_os("WindowsSDKVersion") {
            found.push(root.join(version).join(arch).join("rc.exe"));
        }
        let mut versions: Vec<_> = fs::read_dir(&root)
            .into_iter()
            .flatten()
            .flatten()
            .map(|entry| entry.path())
            .filter(|path| path.is_dir())
            .collect();
        versions.sort_by(|a, b| b.file_name().cmp(&a.file_name()));
        for version in versions {
            let candidate = version.join(arch).join("rc.exe");
            if candidate.is_file() {
                found.push(candidate);
            }
        }
        let unversioned = root.join(arch).join("rc.exe");
        if unversioned.is_file() {
            found.push(unversioned);
        }
    }
    found
}
