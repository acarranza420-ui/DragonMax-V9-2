# DragonMax V12 Unified

DragonMax is a private-use Kodi/AuraMOD build project focused on a Netflix-style home screen, six themed realms, Dragon Portal administration, original artwork/audio, recovery tools, and Fire TV Stick 4K Max performance.

## Current repository status

This branch is the **V12 Unified 4.0.0 stabilization channel**. Repository, wizard, build manifests, and UI metadata use the 4.0.0 release line. The V12 build remains gated until the three 4.0.0 binary artifacts are published to stable, anonymously downloadable URLs and validation passes.

## Kodi source

`https://acarranza420-ui.github.io/DragonMax-V9-2/`

Install only the repository ZIP from Kodi's **Install from zip file** screen. The build payload is not a Kodi add-on ZIP and is applied by DragonMax Wizard.

## Release architecture

- `addons.xml` + `addons.xml.md5` — repository index
- `repository.dragonmax-4.0.0.zip` — Kodi repository installer
- `plugin.program.dragonmaxwizard-4.0.0.zip` — manifest-driven build installer
- `build.json` — V12 build release manifest
- `updates.json` — repository/wizard release metadata
- `themes.json` / `realms.json` — DragonMax realm metadata
- `builds/DragonMax_V12_Unified_Build_Content-4.0.0.zip` — canonical V12 payload path when hosted through GitHub Pages

## V12 merge policy

V9.2 is the legacy baseline. V11 is overlaid afterward and wins every duplicate path. Useful V9.2-only files are retained. The resulting unified release is DragonMax V12 / 4.0.0.

## Stability rules

1. Repository, wizard, manifests, and UI version numbers stay synchronized at 4.0.0.
2. Build payloads are never installed directly from Kodi.
3. The wizard checks free space, manifest readiness, payload size, ZIP integrity, and required `userdata/` + `addons/` folders before applying files.
4. A pre-install backup is made before userdata is applied.
5. V12 remains `ready=false` until its binary artifacts are hosted and validated.
6. Live release requires a fresh Kodi 21 install trial and a repeat install on the Fire TV Stick 4K Max target.
