# DragonMax GitHub Upload Rules

1. Keep repository/wizard/manifests in the repository root.
2. Put full build payloads only in `/builds/`.
3. For V11, upload exactly:
   `builds/DragonMax_V11_Build_Content-3.0.0.zip`
4. Confirm the GitHub Pages URL downloads that ZIP.
5. Confirm its size is at least 60 MB.
6. Run the repository validation workflow.
7. Only after validation passes, change `ready` in `build.json` from `false` to `true`.
8. Test from a fresh Kodi 21 installation before treating the release as stable.

Do not expose a build payload as the file users should install from Kodi's **Install from zip file** screen.
