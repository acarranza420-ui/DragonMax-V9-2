# DragonMax

DragonMax is a private-use Kodi/AuraMOD build project focused on a Netflix-style home screen, six themed realms, Dragon Portal administration, original artwork/audio, recovery tools, and Fire TV Stick 4K Max performance.

## Current repository status

This repository is now a **stabilization/staging channel**. Repository and wizard metadata are version synchronized at **1.9.3**. The V11 build entry remains gated until the release payload is uploaded to the exact `/builds/` path and passes validation.

## Kodi source

`https://acarranza420-ui.github.io/DragonMax-V9-2/`

Install only the repository ZIP from Kodi's **Install from zip file** screen. The build payload is not a Kodi add-on ZIP and must be applied by DragonMax Wizard.

## Release architecture

- `addons.xml` + `addons.xml.md5` — repository index
- `repository.dragonmax-*.zip` — Kodi repository installer
- `plugin.program.dragonmaxwizard-*.zip` — manifest-driven build installer
- `build.json` — build release manifest
- `updates.json` — repository/wizard release metadata
- `themes.json` / `realms.json` — DragonMax realm metadata
- `builds/` — build payloads only

## Stability rules

1. Repository, wizard, manifests, and UI version numbers must stay synchronized.
2. Build payloads are staged under `/builds/`, never installed directly from Kodi.
3. The wizard checks free space, manifest readiness, payload size, ZIP integrity, and required `userdata/` + `addons/` folders before applying files.
4. A pre-install backup is made before userdata is applied.
5. V11 remains `ready=false` until its binary payload has been uploaded and validated.
