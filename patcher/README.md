# Native patch guards (source only)

`merge_apk.py` is the existing split merger/native patch source with fail-closed
site validation. This directory intentionally excludes APKs, DEX, keystores,
signing tools, private configuration and local experimental artifacts.

Run the synthetic regression without an APK or extra dependencies:

```bash
python3 -m unittest discover -s patcher -p 'test_native_patch_guards.py'
```

`requirements-test.txt` pins optional dependencies for the separately maintained
experimental ARM64 tests; installing them alone does not supply the original APK.
Passing synthetic guards does not certify the patches on an Android device.
