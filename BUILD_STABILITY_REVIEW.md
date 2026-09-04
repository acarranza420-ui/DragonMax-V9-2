# DragonMax 4.9 Build Stability Review

## Reference packages inspected

The supplied repository installers were treated as untrusted data and inspected without executing code.

| Package | SHA-256 | Contents | Useful pattern | Deliberately not copied |
|---|---|---|---|---|
| `repository.redwizard-1.2.2(1).zip` | `967f93b8c678f5356799a63f32b41eb67b8ef810c6ba3cf48e89e778afd8c103` | Repository XML, changelog, icon, fanart, license | Explicit Kodi-version repository ranges; standard one-root ZIP layout | Third-party repository aggregation, foreign endpoints/branding/assets/license |
| `repository.redwizard-1.2.2(2).zip` | `967f93b8c678f5356799a63f32b41eb67b8ef810c6ba3cf48e89e778afd8c103` | Byte-for-byte identical to the first Red Wizard ZIP | No additional distinct behavior | Same exclusions as the first copy |
| `Diggz_Repo(1).zip` | `db198f85c361f02a07f389520328d9b5e9ce9fa75675f084f2ea3fac9735d98a` | Repository XML and icon | Non-overlapping Omega/Piers compatibility ranges; standard one-root ZIP layout | Mutable branch endpoints, `<hashes>false</hashes>`, foreign endpoint/branding/icon |

These files are repository locators, not build wizards. They contain no installer, extraction, backup, rollback, dependency, or recovery implementation to reuse.

## DragonMax build outline

1. Pin the build runtime to Python 3.12 and invoke the same `build_release.py` path locally, in CI, and on Render.
2. Recover the approved V9.2 baseline and remove inherited runtime state and development debris.
3. Stage the pinned AuraMOD 2.0.4 source, DragonMax add-ons, and the complete Kodi 21 dependency closure.
4. Validate add-on identities, minimum dependency versions, Python syntax, protected paths, real artwork, native home navigation, and startup recovery hooks.
5. Create a complete per-file install manifest and a deterministically ordered/timestamped payload ZIP.
6. Generate separate DragonMax repository and wizard ZIPs, then validate both root layouts and every ZIP member.
7. Publish exact compressed size, expanded size, member count, and SHA-256 in `build.json`.
8. Keep `ready=false` until CI, Render commit parity, production artifact verification, and a physical Kodi 21 / Fire TV install all pass.

## Stability changes applied

- Restricted the repository to Kodi `21.0.0` through `21.89.0`, excluding the Kodi 22/Piers pre-release range.
- Kept one HTTPS DragonMax origin instead of aggregating unrelated repositories.
- Replaced a mutable Image Resource Select branch download with Kodi Omega's versioned `3.0.2` package.
- Added download, expanded-size, member-count, duplicate-path, traversal-path, symbolic-link, exact-manifest, and free-space guards.
- Made bootstrap repository writes part of the install transaction.
- Backed up every overwritten target and the pending activation marker; rollback now restores all originals and removes all newly created targets.
- Preserved only valid AuraMOD 2.0.4+ installations; corrupt or older copies are repaired from the payload.
- Required Kodi to report Dragon Voice and Dragon Portal as enabled instead of trusting a successful-looking command response.
- Deferred skin activation through a restart-required marker and removed pre-transaction cache deletion.
- Validated both generated installer ZIPs rather than only the last loop item.
- Added generated-wizard runtime regression coverage for the transaction and trust boundaries.

## Remaining release gate

The software build and simulated install gates do not replace the physical device test. DragonMax must remain a launch candidate until a clean Kodi 21 installation and repeat installation succeed on the target Fire TV Stick 4K Max.
