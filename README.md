# DragonMax V12 Unified

DragonMax is a private-use Kodi/AuraMOD build project focused on a Netflix-style home screen, six themed realms, Dragon Portal administration, original artwork/audio, recovery tools, and Fire TV Stick 4K Max performance.

## Current stabilization line

This branch is the **V12 Unified 4.5.0 stabilization channel**. The build is generated from source by `build_v12.py`, validated in GitHub Actions, and then deployed to Render. Root-level historical release artifacts are not the production source of truth.

Production release host: `https://dragonmax-v12-release.onrender.com/`

## Release architecture

The generated `public/` directory is the only deployable release output. A successful build creates:

- `public/addons.xml` and `public/addons.xml.md5`
- `public/repository.dragonmax-4.5.0.zip`
- `public/plugin.program.dragonmaxwizard-4.5.0.zip`
- `public/build.json`
- `public/updates.json`, `public/themes.json`, and `public/realms.json`
- `public/builds/DragonMax_V12_Unified_Build_Content-4.5.0.zip`

The full payload is applied by DragonMax Wizard. It is not installed directly as a Kodi add-on ZIP.

## Dependency policy

AuraMOD is pinned to the validated Kodi 21/Omega source. Fire TV-sensitive AuraMOD dependencies are physically staged into the DragonMax payload so device installation does not depend on repository timing at the 57% dependency gate. The builder rejects corrupt packages, missing add-on manifests, unresolved critical dependencies, unsafe runtime data, development debris, and malformed release metadata.

## Release gates

1. GitHub Actions must build the exact release payload successfully.
2. Generated repository XML, checksums, manifests, installer ZIPs, and payload SHA-256 must validate.
3. No `.git`, `.github`, test, cache, database, package-cache, log, or temporary debris may enter the payload.
4. AuraMOD, Dragon Voice, and the Fire TV dependency flight pack must be present in the generated payload.
5. Render is advanced only after GitHub validation succeeds. The previous live Render deployment remains active until the replacement reaches `live`.
6. The live Render commit must match the GitHub-approved stabilization commit before Kodi testing begins.
7. A Fire TV/Kodi install is a final device-validation gate. A failed device install is not promoted as launch-ready.

## Legacy baseline

`DragonMax_V9_2_Build_Content-1.9.2.zip` remains in the repository only because the V12 builder intentionally uses it as the legacy content baseline. Old repository/wizard installers and stale release manifests are not part of the current release path.
