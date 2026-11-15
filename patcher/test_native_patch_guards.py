"""Synthetic native fixtures only: never build, sign or publish an APK."""
import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location('guarded_merge_apk',
                                            Path(__file__).with_name('merge_apk.py'))
patcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(patcher)


class NativePatchGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        size = max(offset + len(old) for offset, old, _, _ in patcher.LIBIL2CPP_PATCHES)
        original = bytearray(size)
        for offset, old, new, _ in patcher.LIBIL2CPP_PATCHES:
            assert len(old) == len(new)
            original[offset:offset + len(old)] = old
        cls.original = bytes(original)

    def test_all_sites_patched_without_changing_length_or_other_bytes(self):
        actual, count = patcher.patch_libil2cpp_so(self.original)
        expected = bytearray(self.original)
        for offset, _, new, _ in patcher.LIBIL2CPP_PATCHES:
            expected[offset:offset + len(new)] = new
        self.assertEqual(actual, bytes(expected))
        self.assertEqual(count, len(patcher.LIBIL2CPP_PATCHES))
        self.assertEqual(len(actual), len(self.original))

    def test_retry_is_idempotent(self):
        first, _ = patcher.patch_libil2cpp_so(self.original)
        second, count = patcher.patch_libil2cpp_so(first)
        self.assertEqual(first, second)
        self.assertEqual(0, count)

    def test_unknown_last_site_rejects_without_modifying_input(self):
        original = bytearray(self.original)
        offset = patcher.LIBIL2CPP_PATCHES[-1][0]
        original[offset] ^= 0xff
        before = bytes(original)
        with self.assertRaisesRegex(ValueError, 'Unsupported native bytes'):
            patcher.patch_libil2cpp_so(original)
        self.assertEqual(before, bytes(original))

    def test_truncated_or_unrelated_native_rejected(self):
        for data in (b'', b'not a native build', self.original[:-1]):
            with self.subTest(size=len(data)), self.assertRaisesRegex(ValueError, 'site missing'):
                patcher.patch_libil2cpp_so(data)

    def test_mixed_known_sites_finish_remaining_patches(self):
        mixed = bytearray(self.original)
        offset, _, replacement, _ = patcher.LIBIL2CPP_PATCHES[0]
        mixed[offset:offset + len(replacement)] = replacement
        actual, count = patcher.patch_libil2cpp_so(mixed)
        expected, _ = patcher.patch_libil2cpp_so(self.original)
        self.assertEqual(expected, actual)
        self.assertEqual(len(patcher.LIBIL2CPP_PATCHES) - 1, count)


if __name__ == '__main__':
    unittest.main()
