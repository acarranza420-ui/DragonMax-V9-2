# DragonMax V12 Binary Publishing Rules

DragonMax V12 Unified currently uses release line **4.5.0**.

## Required generated artifacts

The deployable files are generated into `public/` by `build_v12.py`:

- `repository.dragonmax-4.5.0.zip`
- `plugin.program.dragonmaxwizard-4.5.0.zip`
- `builds/DragonMax_V12_Unified_Build_Content-4.5.0.zip`
- `addons.xml` and `addons.xml.md5`
- `build.json`, `updates.json`, `themes.json`, and `realms.json`

## Hosting rules

1. Render is the production release host for the stabilization channel.
2. Full payloads must remain anonymously downloadable by Kodi without browser login, cookies, or confirmation pages.
3. The GitHub repository is source and CI, not the authoritative live payload host.
4. Every generated payload must pass ZIP integrity, SHA-256, manifest, version, dependency, and debris checks before deployment.
5. AuraMOD and the Fire TV dependency flight pack must already exist inside the generated payload before Render deployment.
6. The previous live Render deployment remains active while a replacement builds, preventing release downtime.
7. Render may advance only after GitHub validation passes for the exact stabilization commit.
8. The live Render commit must match that approved commit before Kodi/Fire TV validation begins.
9. A real Fire TV/Kodi install remains the final device-validation gate before the build is treated as launch-ready.

Never call a build launch-ready merely because an artifact exists or Render responds. GitHub validation, exact-commit deployment, live artifact verification, and device validation are separate gates.
