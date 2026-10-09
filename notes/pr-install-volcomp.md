# PR draft — VC3D: install `libvolcomp` with the `vc_runtime` component

Status: fix verified on the GPU box 2026-10-08 (branch `fix/install-volcomp`, uncommitted). Patch: `notes/fix-install-volcomp.patch`.
Ted authors and submits (CONTRIBUTING.md: human-run on real data, error screenshot + fix working, concise motivation).

## Suggested title
`VC3D: install libvolcomp with the vc_runtime component (fixes installed binaries failing to start since #1704)`

## Suggested body (edit freely)

Since #1704 added `libs/volcomp` as a shared library that `vc_core` (via `utils_volcomp_codec`) links, every executable produced by
`build_from_src_debian.sh` / `cmake --install … --component vc_runtime` fails to start:

```
$ vc_render_tifxyz --help
vc_render_tifxyz: error while loading shared libraries: libvolcomp.so: cannot open shared object file: No such file or directory
```

Cause: the install walker in `volume-cartographer/CMakeLists.txt` only visits `core utils libs/c3d (apps …) (libs/flatboi)`;
`libs/volcomp` has no `install()` rule of its own, so `libvolcomp.so` is built but never installed, and the binaries' `RUNPATH`
(`$ORIGIN/../lib`) cannot find it. `install_manifest_vc_runtime.txt` confirms it (59 entries, no `libvolcomp.so`).
The script's post-install check only tests `-x`, so it reports success. The `Dockerfile` uses the same component, so the next image build
would ship the same broken binaries (the published `:edge`/`:main` image, 2026-05-13, predates #1704).

Fix: add `libs/volcomp` to `_vc_install_dirs` so the existing walker installs it like `libs/c3d`.

Verified on Ubuntu 24.04.5 (gcc 13.3, cmake 3.28.3), real data: after re-configure + `cmake --install build --component vc_runtime`,
`libvolcomp.so` is installed, `ldd` shows no unresolved libraries for any installed binary, and `vc_render_tifxyz` renders
PHercParis4 segment 20231016151002 from the remote 2.4 µm volume (see attached render). `--help` output before/after attached.

## Evidence to attach (Ted)
1. Screenshot of the error: on the box, `git stash` (or `git checkout main`), re-run `cmake --install build/from-source --component vc_runtime`,
   `rm ~/.local/lib/libvolcomp.so`, then `~/.local/bin/vc_render_tifxyz --help` → screenshot the terminal. Then re-apply the fix and reinstall.
   (Or simply reproduce with the official script on a clean prefix.)
2. Screenshot/paste of `ldd ~/.local/bin/vc_render_tifxyz | grep -c "not found"` → 0 and `--help` working after the fix.
3. The crop render preview from `runs/20231016151002-2.4um-g2-28-crop1/` (real-data before/after: before = tool cannot start).

## Ready to click (staged 2026-10-08)
Fork `skuzbucket1/villa`, branch `fix/install-volcomp`, commit `382d6d0d8` (author Ted). Pre-filled form:
https://github.com/ScrollPrize/villa/compare/main...skuzbucket1:villa:fix/install-volcomp?expand=1 — paste `notes/pr-body.md` as the body if the prefill is lost.

## Mechanics (already done)
- On the Mac copy: `cd villa && git checkout -b fix/install-volcomp && git apply ../notes/fix-install-volcomp.patch && git commit -am "..."`
  then `gh pr create --repo ScrollPrize/villa --fill` (fork first if no push rights: `gh repo fork ScrollPrize/villa --remote`).
- Keep it to this one change; CONTRIBUTING caps PR size/time and closes "fishing expedition" PRs.
- Register on the Discord before submitting anything for a Progress Prize.
