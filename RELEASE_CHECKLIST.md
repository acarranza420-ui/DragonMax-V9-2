# DragonMax Release Checklist

- [ ] Repository ZIP installs on a fresh Kodi 21 instance.
- [ ] DragonMax Repository opens without "Could not connect".
- [ ] DragonMax Wizard installs from the repository.
- [ ] `addons.xml` parses and `addons.xml.md5` matches.
- [ ] `build.json`, `updates.json`, `themes.json`, and `realms.json` parse.
- [ ] Build payload URL returns HTTP 200.
- [ ] Build payload size is at least 60 MB.
- [ ] Build ZIP contains `userdata/` and `addons/` after its top-level folder.
- [ ] AuraMOD exists in the payload under `addons/skin.auramod`.
- [ ] Wizard preflight catches low storage before downloading.
- [ ] Wizard refuses unready or undersized payloads.
- [ ] Wizard extracts to a temporary directory before applying files.
- [ ] Pre-install backup is created.
- [ ] Startup video/audio playback succeeds after restart.
- [ ] Home screen loads with no empty critical menu rows.
- [ ] Maximum Speed profile remains usable on Fire TV Stick 4K Max.
- [ ] Install is repeated at least twice from clean Kodi profiles.
