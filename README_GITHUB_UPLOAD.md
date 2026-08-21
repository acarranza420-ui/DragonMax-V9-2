# DragonMax V12 Binary Publishing Rules

DragonMax V12 Unified uses release line **4.0.0**.

## Required binary artifacts

- `repository.dragonmax-4.0.0.zip`
- `plugin.program.dragonmaxwizard-4.0.0.zip`
- `DragonMax_V12_Unified_Build_Content-4.0.0.zip`

## Hosting rules

1. Repository/wizard/manifests remain in the repository release architecture.
2. Full build payloads must use a stable anonymous direct-download URL accessible by Kodi without browser login, cookies, or confirmation pages.
3. If GitHub Pages hosts the payload, use `/builds/DragonMax_V12_Unified_Build_Content-4.0.0.zip`.
4. If external storage hosts the payload, update only the V12 manifest URL; do not expose the payload as a Kodi add-on.
5. Verify HTTP success, ZIP integrity, and payload size before enabling the release.
6. Confirm the V12 payload contains `userdata/` and `addons/`, including `addons/skin.auramod`.
7. Run repository validation.
8. Only after validation passes change `ready` in `build.json` from `false` to `true`.
9. Test from a fresh Kodi 21 installation before treating V12 as stable.

Never mark a build ready merely because a filename exists. The URL must return the actual ZIP bytes anonymously and the payload must pass validation.
