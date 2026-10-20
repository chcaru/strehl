"""Adversarial packaging checks; no compiler, dependency source, or network access."""
import importlib.util
from pathlib import Path
import struct
import tempfile
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


if __name__ == "__main__":
    unittest.main()
