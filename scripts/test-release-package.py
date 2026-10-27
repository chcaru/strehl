"""Adversarial packaging checks; no compiler, dependency source, or network access."""
import importlib.util
import json
from pathlib import Path
import struct
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

SPEC = importlib.util.spec_from_file_location("release_package", Path(__file__).with_name("release-package.py"))
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)


def pe_fixture(*, normal="KERNEL32.dll", delayed=None):
    data = bytearray(2048)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 0x3C, 0x80)
    data[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<HH", data, 0x84, 0x8664, 1)
    struct.pack_into("<H", data, 0x94, 240)
    optional = 0x98
    struct.pack_into("<H", data, optional, 0x20B)
    struct.pack_into("<Q", data, optional + 24, 0x140000000)
    struct.pack_into("<I", data, optional + 60, 512)
    struct.pack_into("<I", data, optional + 108, 16)
    struct.pack_into("<II", data, optional + 112 + 8, 0x1000, 40)
    section = optional + 240
    struct.pack_into("<IIII", data, section + 8, 1024, 0x1000, 1024, 512)
    struct.pack_into("<I", data, 512 + 12, 0x1080)
    data[640:640 + len(normal) + 1] = normal.encode() + b"\0"
    if delayed:
        struct.pack_into("<II", data, optional + 112 + 13 * 8, 0x1100, 64)
        struct.pack_into("<II", data, 768, 1, 0x1180)
        data[896:896 + len(delayed) + 1] = delayed.encode() + b"\0"
    return bytes(data)


class ReleasePackagingTests(unittest.TestCase):
    def test_application_source_keeps_declared_workspace_targets(self):
        # Exercise the real staging list: a forgotten external Cargo example
        # must fail here instead of producing an unrebuildable release kit.
        with tempfile.TemporaryDirectory() as temp:
            staged = Path(temp)
            copied = release.copy_application_source(staged)
            self.assertTrue(copied)
            workspace = release.tomllib.loads((staged / "Cargo.toml").read_text(encoding="utf-8"))
            targets = []
            for member in workspace["workspace"]["members"]:
                for directory in staged.glob(member):
                    manifest = release.tomllib.loads((directory / "Cargo.toml").read_text(encoding="utf-8"))
                    entries = [manifest["lib"]] if "lib" in manifest else []
                    for kind in ("bin", "example", "test", "bench"):
                        entries.extend(manifest.get(kind, []))
                    for entry in entries:
                        if "path" in entry:
                            target = (directory / entry["path"]).resolve()
                            self.assertTrue(target.is_relative_to(staged.resolve()), entry)
                            self.assertTrue(target.is_file(), f"Missing staged Cargo target: {target}")
                            targets.append(target)
            self.assertTrue(targets)

    def test_dependency_patent_grants_are_shipped_with_licenses(self):
        for name in ("LICENSE", "COPYING.md", "PATENTS", "Patent-Grant.txt"):
            self.assertTrue(release.license_name(name), name)
        for name in ("patented.rs", "licensee.rs", "decoder.rs"):
            self.assertFalse(release.license_name(name), name)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            dependency = root / "encoder"
            dependency.mkdir()
            (dependency / "LICENSE").write_text("BSD license", encoding="utf-8")
            (dependency / "PATENTS").write_text("patent grant", encoding="utf-8")
            metadata = {"packages": [{
                "name": name, "version": "1.0.0", "source": "registry+fixture",
                "manifest_path": str(dependency / "Cargo.toml"), "license": "BSD-2-Clause",
                "license_file": None,
            } for name in ("fixture-codec", "rawler")]}
            release.collect_notices(metadata, root / "notices", {"version": "0.0.0", "source_commit": "fixture"})
            self.assertEqual(
                (root / "notices/licenses/fixture-codec-1.0.0/PATENTS").read_text(),
                "patent grant",
            )

    def test_pe_audit_includes_delay_imports_and_rejects_missing_runtime(self):
        self.assertEqual(release.pe_imports(pe_fixture())[1], ["kernel32.dll"])
        with tempfile.TemporaryDirectory() as temp:
            binary = Path(temp) / "Strehl.exe"
            binary.write_bytes(pe_fixture(delayed="VCRUNTIME140.dll"))
            self.assertEqual(release.pe_imports(binary.read_bytes())[1],
                             ["kernel32.dll", "vcruntime140.dll"])
            with self.assertRaisesRegex(RuntimeError, "Non-system Windows DLL"):
                release.audit_windows(binary)
            binary.write_bytes(pe_fixture(delayed="d3d12.dll"))
            self.assertIn("d3d12.dll", release.audit_windows(binary)["imports"])

    def test_pe_audit_accepts_windows_combase_without_admitting_external_libraries(self):
        with tempfile.TemporaryDirectory() as temp:
            binary = Path(temp) / "Strehl.exe"
            for normal, delayed in (("ComBase.dll", None), ("KERNEL32.dll", "ComBase.dll")):
                with self.subTest(normal=normal, delayed=delayed):
                    binary.write_bytes(pe_fixture(normal=normal, delayed=delayed))
                    self.assertIn("combase.dll", release.audit_windows(binary)["imports"])
            for dependency in ("VCRUNTIME140.dll", "combase-helper.dll", "custom-codec.dll"):
                with self.subTest(dependency=dependency):
                    binary.write_bytes(pe_fixture(normal="ComBase.dll", delayed=dependency))
                    with self.assertRaisesRegex(RuntimeError, "Non-system Windows DLL imports"):
                        release.audit_windows(binary)

    def test_archive_paths_refuse_cross_platform_traversal_and_symlinks(self):
        for name in ("../escape", "/absolute", "C:/outside", "foo\\..\\escape"):
            with self.subTest(name=name), self.assertRaises(RuntimeError):
                release.safe_relative(name)
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / "bad.zip"
            with zipfile.ZipFile(archive, "w") as stream:
                entry = zipfile.ZipInfo("link")
                entry.external_attr = 0o120777 << 16
                stream.writestr(entry, "/outside")
            with self.assertRaisesRegex(RuntimeError, "Symlink"):
                release.unzip(archive, Path(temp) / "extract")
            self.assertFalse((Path(temp) / "extract/link").exists())

    def test_ldd_missing_library_fails_and_only_os_baseline_is_excluded(self):
        with self.assertRaisesRegex(RuntimeError, "Missing Linux"):
            release.parse_ldd("libvulkan.so.1 => not found\n")
        parsed = release.parse_ldd(
            "libX11.so.6 => /lib/x86_64-linux-gnu/libX11.so.6 (0x123)\n"
            "/lib64/ld-linux-x86-64.so.2 (0x456)\n")
        self.assertEqual(len(parsed), 2)
        for name in ("libc.so.6", "libm.so.6", "ld-linux-x86-64.so.2"):
            self.assertIsNotNone(release.LINUX_SYSTEM.match(name), name)
        for name in ("libX11.so.6", "libgcc_s.so.1", "libvulkan.so.1", "libcrypto.so.3"):
            self.assertIsNone(release.LINUX_SYSTEM.match(name), name)

    def test_notices_zip_roundtrip_and_existing_output_are_checked(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source"
            source.mkdir()
            (source / "NOTICE.md").write_text("notice")
            archive = root / "notices.zip"
            release.zip_tree(source, archive)
            release.unzip(archive, root / "unpacked")
            self.assertEqual((root / "unpacked/NOTICE.md").read_text(), "notice")
            with self.assertRaisesRegex(RuntimeError, "Refusing to replace"):
                release.new_output(root, archive.name)

    def test_linux_audit_checks_dlopen_transitive_dependencies(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            libraries = root / "lib"
            libraries.mkdir()
            (libraries / "libvulkan.so.1").touch()
            outputs = [
                "libc.so.6 => /lib/libc.so.6 (0x123)\n",
                "libdependency.so.1 => /usr/lib/libdependency.so.1 (0x456)\n",
            ]
            with patch.object(release, "run", side_effect=outputs) as mocked:
                with self.assertRaisesRegex(RuntimeError, "external app libraries"):
                    release.audit_linux_resolution(root / "Strehl", libraries)
                self.assertEqual(mocked.call_count, 2, "must inspect the dlopen library itself")

    def test_worker_smoke_rejects_wrong_source_or_unavailable_engine(self):
        context = {"version": "0.1.0-alpha.1", "source_commit": "a" * 40}
        with patch.object(release, "run", side_effect=["Usage: strehl stack", "strehl 0.1.0-alpha.1 deadbeef"]):
            with self.assertRaisesRegex(RuntimeError, "source commit"):
                release.smoke(["Strehl"], context)
        with patch.object(release, "run", return_value="desktop help only"):
            with self.assertRaisesRegex(RuntimeError, "processing worker"):
                release.smoke(["Strehl"], context)
        with patch.object(release, "run", side_effect=["Usage: strehl stack", "strehl 0.1.0-alpha.1 " + "a" * 12]):
            self.assertEqual(release.smoke(["Strehl"], context)["help"], "passed")

    def test_local_renderer_patch_keeps_upstream_notices_in_release_kit(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            renderer = root / "third-party" / "egui-wgpu"
            decoder = root / "registry" / "rawler"
            own = root / "crates" / "strehl-ui"
            for directory in (renderer, decoder, own):
                directory.mkdir(parents=True)
            (renderer / "LICENSE-MIT").write_text("upstream renderer notice")
            (decoder / "COPYING").write_text("decoder notice fixture")
            packages = [
                {"name": "egui-wgpu", "version": "0.33.3", "source": None,
                 "manifest_path": str(renderer / "Cargo.toml"), "license": "MIT OR Apache-2.0"},
                {"name": "rawler", "version": "0.7.2", "source": "registry+fixture",
                 "manifest_path": str(decoder / "Cargo.toml"), "license": "LGPL-2.1"},
                {"name": "strehl-ui", "version": "0.1.0", "source": None,
                 "manifest_path": str(own / "Cargo.toml"), "license": "MIT OR Apache-2.0"},
            ]
            context = {"version": "0.1.0", "source_commit": "a" * 40}
            notices = root / "notices"
            manifest = release.collect_notices({"packages": packages}, notices, context, root)
            indexed = {item["name"]: item for item in manifest}
            self.assertIn("egui-wgpu", indexed, "path patches remain third-party code")
            self.assertNotIn("strehl-ui", indexed, "do not duplicate our own licence")
            copied = notices / indexed["egui-wgpu"]["license_files"][0]
            self.assertEqual(copied.read_text(), "upstream renderer notice")
            self.assertEqual(indexed["egui-wgpu"]["source"], "local-patch:third-party/egui-wgpu")

    def test_source_kit_refuses_an_omitted_local_patch(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "experiments/native-gpu-gather").mkdir(parents=True)
            (root / "experiments/native-gpu-gather/Cargo.toml").write_text("[package]\nname='fixture'\n")
            (root / "Cargo.toml").write_text(
                "[patch.crates-io]\negui-wgpu={path='third-party/egui-wgpu'}\n")
            paths = "Cargo.toml\0experiments/native-gpu-gather/Cargo.toml\0"
            with patch.object(release, "ROOT", root), patch.object(release, "run", return_value=paths):
                with self.assertRaisesRegex(RuntimeError, "Patched dependency missing"):
                    release.copy_application_source(root / "kit")

    def test_source_staging_keeps_patch_sources_and_notices_in_distinct_directories(self):
        # Exercise real source staging, notice collection and both archives.
        # Only Cargo/git discovery is replaced with tiny owned fixtures.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repository, stage, output = (root / name for name in ("repository", "stage", "output"))
            stage.mkdir()
            output.mkdir()
            files = {
                "Cargo.toml": "[patch.crates-io]\negui-wgpu={path='third-party/egui-wgpu'}\n",
                "Cargo.lock": "[[package]]\nname='rawler'\nversion='0.0.1'\nsource='registry+fixture'\n",
                "third-party/egui-wgpu/Cargo.toml": "[package]\nname='egui-wgpu'\nversion='0.0.1'\n",
                "third-party/egui-wgpu/LICENSE-MIT": "renderer fixture notice\n",
                "experiments/native-gpu-gather/Cargo.toml": "[package]\nname='fixture'\n",
                **{name: "owned licence fixture\n" for name in
                   ("LICENSE-MIT", "LICENSE-APACHE", "LICENSE-LGPL-2.1")},
            }
            for relative, content in files.items():
                path = repository / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")

            def discovery(command, *, cwd=None, **kwargs):
                if command[:3] == ["git", "ls-files", "-z"]:
                    return "\0".join(files) + "\0"
                if command[:2] == ["cargo", "vendor"]:
                    decoder = cwd / "vendor/rawler-0.0.1"
                    decoder.mkdir(parents=True)
                    (decoder / "LICENSE").write_text("decoder fixture notice\n", encoding="utf-8")
                    return "# fixture vendor configuration\n"
                if command[:2] == ["cargo", "metadata"]:
                    return json.dumps({"packages": [
                        {"name": "rawler", "version": "0.0.1", "source": "registry+fixture",
                         "manifest_path": str(cwd / "vendor/rawler-0.0.1/Cargo.toml"), "license": "LGPL-2.1"},
                        {"name": "egui-wgpu", "version": "0.0.1", "source": None,
                         "manifest_path": str(cwd / "third-party/egui-wgpu/Cargo.toml"), "license": "MIT"},
                    ]})
                raise AssertionError(f"Unexpected discovery command: {command}")

            context = {"version": "0.0.1", "source_commit": "a" * 40}
            with patch.object(release, "ROOT", repository), patch.object(release, "run", side_effect=discovery):
                archives, counts = release.package_source(
                    SimpleNamespace(version="0.0.1", output=output), stage, context)
            source = stage / "Strehl-source"
            siblings = [path.name.casefold() for path in source.iterdir()]
            self.assertEqual(len(siblings), len(set(siblings)), "the kit must also extract on case-insensitive hosts")
            self.assertEqual((source / "third-party/egui-wgpu/Cargo.toml").read_text(),
                             files["third-party/egui-wgpu/Cargo.toml"])
            notices = source / "THIRD-PARTY-NOTICES"
            self.assertTrue((notices / "NOTICE.md").is_file())
            self.assertEqual((notices / "licenses/egui-wgpu-0.0.1/LICENSE-MIT").read_text(),
                             "renderer fixture notice\n")
            self.assertEqual(counts["dependency_count"], 2)
            with tarfile.open(archives[0]) as archive:
                self.assertEqual(archive.extractfile("Strehl-source/third-party/egui-wgpu/Cargo.toml").read(),
                                 (repository / "third-party/egui-wgpu/Cargo.toml").read_bytes())
                self.assertEqual(archive.extractfile("Strehl-source/THIRD-PARTY-NOTICES/NOTICE.md").read(),
                                 (notices / "NOTICE.md").read_bytes())
            with zipfile.ZipFile(archives[1]) as archive:
                self.assertEqual(archive.read("licenses/egui-wgpu-0.0.1/LICENSE-MIT"),
                                 (repository / "third-party/egui-wgpu/LICENSE-MIT").read_bytes())


if __name__ == "__main__":
    unittest.main()
