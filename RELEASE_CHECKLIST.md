# DragonMax V12 Release Checklist

## Release rule

DragonMax V12 4.9.0 ships only when source, generated artifacts, Render deployment, and Fire TV/Kodi device validation all pass. Package size is secondary to stability and clean launch behavior.

## Automated launch gates

- [ ] GitHub Actions passes for the exact stabilization commit.
- [ ] `addons.xml` parses and `addons.xml.md5` matches.
- [ ] `build.json`, `updates.json`, `themes.json`, and `realms.json` parse.
- [ ] Repository, wizard, and build versions all equal 4.9.0.
- [ ] Payload ZIP passes integrity and SHA-256 verification.
- [ ] Payload contains AuraMOD and Dragon Voice.
- [ ] Payload contains the Fire TV dependency flight pack, including skin helper service/widgets, TMDb Helper, metadata utilities, Image Resource Select, studio resources, and required repositories.
- [ ] No `.git`, `.github`, IDE, test, docs, cache, package-cache, database, log, temp, or compiled-Python debris exists in the payload.
- [ ] Protected Kodi runtime paths are absent.
- [ ] Installer ZIPs are valid and protocol 4+ is enforced.
- [ ] Installer ZIPs contain exactly one correctly named add-on root and a root `addon.xml`.
- [ ] The byte-identical recovered V9.2 reference and all six curated realm wallpapers match the artwork manifest.
- [ ] No procedural placeholder or dead artwork directories exist in the payload.
- [ ] Skin activation is gated on a real Kodi process restart.
- [ ] CI leaves `ready=false` until real-device validation.

## Deployment gates

- [ ] Previous Render release remains live while the replacement builds.
- [ ] Render deploys the exact GitHub-approved stabilization commit.
- [ ] Render deployment reaches `live` with no build error.
- [ ] Production `build.json`, repository XML, installer ZIPs, and payload are reachable anonymously.
- [ ] Production payload checksum and size match the generated release metadata.

## Fire TV/Kodi launch gates

- [ ] Repository ZIP installs on fresh Kodi 21.
- [ ] DragonMax Repository opens without connection errors.
- [ ] DragonMax Wizard installs and launches.
- [ ] Install passes the former 57% AuraMOD dependency stage without unresolved dependencies.
- [ ] Failed preflight leaves Kodi unchanged and rollback remains available.
- [ ] Successful install reaches 100% and Kodi restarts cleanly.
- [ ] AuraMOD loads without a missing-dependency or skin-reset loop.
- [ ] Home navigation remains responsive after widgets populate.
- [ ] Dragon Portal, realm switching, playback return-to-home, and Dragon Voice start without crash loops.
- [ ] Repeat install succeeds from a clean Kodi profile.

## Launch decision

A build is called **ready to launch** only when GitHub validation is green, the same commit is live on Render, production artifacts verify, and the Fire TV/Kodi validation install succeeds.
