# DragonMax V12 Release Checklist

## Release rule

**280 MiB is an ideal packaging target, not a launch requirement.** DragonMax ships only when quality, stability, smooth operation, recovery safety, and visual consistency pass. Package size must never be increased with low-value filler just to hit a number.

## Critical launch gates

- [ ] Repository ZIP installs on a fresh Kodi 21 instance.
- [ ] DragonMax Repository opens without "Could not connect".
- [ ] DragonMax Wizard installs from the repository.
- [ ] `addons.xml` parses and `addons.xml.md5` matches.
- [ ] `build.json`, `updates.json`, `themes.json`, and `realms.json` parse.
- [ ] Build payload URL returns HTTP 200 anonymously.
- [ ] Build ZIP passes an integrity test with no corrupt member.
- [ ] Build ZIP contains `userdata/` and `addons/` after its top-level folder.
- [ ] AuraMOD exists in the payload under `addons/skin.auramod`.
- [ ] Dragon Voice service exists under `addons/service.dragonmax.voice` and its Python compiles.
- [ ] Wizard preflight catches low storage before downloading.
- [ ] Wizard refuses an unready payload.
- [ ] Wizard extracts to a temporary directory before applying files.
- [ ] Pre-install backup is created and rollback path is documented/tested.
- [ ] A failed install cannot leave Kodi in a partially applied state.

## Stability and smooth-use gates

- [ ] Kodi cold-start reaches the home screen without a crash or skin-reset loop.
- [ ] Home navigation remains responsive on Fire TV Stick 4K Max after widgets populate.
- [ ] No critical home row is permanently empty or broken.
- [ ] Dragon Portal opens, closes, and switches realms without restart loops.
- [ ] Maximum Speed profile remains usable on Fire TV Stick 4K Max.
- [ ] Balanced profile is the default and does not over-schedule widgets.
- [ ] Repeated navigation for at least 15 minutes shows no progressive slowdown or memory-related crash.
- [ ] Resume/playback return-to-home flow remains responsive.
- [ ] Install is repeated at least twice from clean Kodi profiles.
- [ ] Restart Kodi at least three times after install with consistent results.

## Dragon Voice + Dragon AI gates

- [ ] Dragon Voice service starts without blocking Kodi startup.
- [ ] Voice bridge health endpoint responds locally.
- [ ] Authenticated command requests succeed and unauthenticated requests are rejected.
- [ ] Commands for Home, Movies, TV Shows, and Dragon Portal execute correctly.
- [ ] All six realm-switch commands resolve correctly.
- [ ] Maximum Speed, Balanced, and Visual Quality voice commands change the stored DragonMax mode.
- [ ] System-health question returns a useful local response.
- [ ] Destructive commands require confirmation and are not directly executed by the voice service.
- [ ] Voice/AI outage does not break Kodi, Dragon Portal, playback, or remote-control operation.
- [ ] Companion speech-to-text input can send recognized text to the Kodi bridge.
- [ ] Manual text/remote fallback remains available for every critical action.
- [ ] Optional external AI cannot bypass the local command allow-list or safety checks.

## Visual and experience gates

- [ ] AuraMOD loads as the intended active skin without missing dependencies.
- [ ] Six realms have consistent artwork, labels, spacing, and navigation behavior.
- [ ] Hero art is legible at TV viewing distance and does not obscure titles or controls.
- [ ] Startup splash/audio works without delaying Kodi usability excessively.
- [ ] Fonts, icons, focus states, and selected-item visibility are consistent.
- [ ] No placeholder-looking artwork, broken paths, stretched images, or obvious filler assets remain in the launch build.
- [ ] Dragon Portal visually matches the home experience rather than feeling like a separate utility screen.
- [ ] Dragon Voice confirmations are brief and do not interrupt playback unnecessarily.

## Packaging target

- [ ] Package size is recorded for the release candidate.
- [ ] ~280 MiB is preferred when the content genuinely earns the space.
- [ ] Smaller is acceptable when it is complete and smoother.
- [ ] Larger is acceptable only when additional assets/features provide real value and do not hurt Fire TV performance or storage safety.
