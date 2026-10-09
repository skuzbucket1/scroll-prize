Since #1704 added `libs/volcomp` as a shared library, every binary installed by `build_from_src_debian.sh` (and by `cmake --install … --component vc_runtime` in general) fails to start on Linux:

```
$ vc_render_tifxyz --help
vc_render_tifxyz: error while loading shared libraries: libvolcomp.so: cannot open shared object file: No such file or directory
```

`ldd` shows the same unresolved library for `VC3D`, `vc_grow_seg_from_seed`, `flatboi` and the rest of the `vc_*` tools.

**Cause.** The install walker in `volume-cartographer/CMakeLists.txt` only visits `core`, `utils`, `libs/c3d` (plus `apps` and `libs/flatboi`). `libs/volcomp` has no install rule of its own, so `libvolcomp.so` is built but never installed, and the binaries' `RUNPATH` (`$ORIGIN/../lib`) cannot resolve it. `install_manifest_vc_runtime.txt` has 59 entries and no `libvolcomp.so`. The build script's final check only tests `-x`, so it reports success.

**Fix.** Add `libs/volcomp` to `_vc_install_dirs` so the existing walker installs it the same way as `libs/c3d`.

**Verified** on Ubuntu 24.04.5 (gcc 13.3, cmake 3.28.3, default `BUILD_SHARED_LIBS=ON`):
- after re-configure and `cmake --install build/from-source --component vc_runtime`: `lib/libvolcomp.so` is installed, the manifest lists it, `ldd` reports no unresolved libraries for any installed binary, and `vc_render_tifxyz --help` runs without `LD_LIBRARY_PATH`;
- real data: `vc_render_tifxyz --remote-url … -g 2 --scale 1 --num-slices 28` renders PHercParis4 segment 20231016151002 from the remote 2.4 µm volume (before the fix the tool cannot start at all).

Note: `volume-cartographer/Dockerfile` installs with the same component and the `ci-release-gcc` preset does not override `BUILD_SHARED_LIBS`, so the next image build would ship the same broken binaries; the currently published `:edge`/`:main` image (built 2026-05-13) predates #1704 and is unaffected.
