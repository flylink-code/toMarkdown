# v0.6.2 Release Plan

## Goal

Publish v0.6.2 with an NSIS installer without changing the existing v0.6.0 or v0.6.1 releases.

## Phases

- [complete] Check the v0.6.1 MSI release and confirm the NSIS migration scope.
- [complete] Implement and statically validate the NSIS installer and v0.6.2 workflow.
- [complete] Commit and push v0.6.2, then push tag `v0.6.2`.
- [complete] Monitor GitHub Actions and verify the v0.6.2 release assets.

## Constraints

- Do not rewrite or delete the existing `v0.6.0` tag or release.
- Do not commit generated build output or local assistant settings.
- Preserve unrelated user changes.

## Errors Encountered

| Error | Attempt | Resolution |
|---|---:|---|
| `pytest -q` could not import `tomarkdown` | 1 | Use `python -m pytest` so the active interpreter includes the project root. |
| Version check read `pyproject.toml` with GBK | 1 | Read the TOML file explicitly as UTF-8. |
| `python -m pytest -q` lacks `markdown_it` | 2 | Record as a local dependency gap; CI installs `requirements.txt` before tests/build. |
| `light.exe` reported `LGHT0311` for Chinese shortcut descriptions | 1 | Previous v0.6.1 MSI issue; replaced WiX with NSIS for v0.6.2. |
| NSIS compiler unavailable locally | 1 | Validate the script statically; GitHub Actions installs NSIS on `windows-latest`. |
| PowerShell expanded `$SMPROGRAMS` during a Python static-check command | 1 | Re-run the check with a single-quoted PowerShell argument and no shell interpolation. |
| GitHub Actions could not resolve `makensis` after Chocolatey install | 1 | Resolve `makensis.exe` from `PATH` or the standard NSIS installation directory. |
| NSIS could not open `installer\\toMarkdown.ico` | 2 | NSIS resolves paths relative to the script directory; use `toMarkdown.ico` and `..\\dist` directly. |
| NSIS rejected `SetShellVarContext` outside a Section or Function | 3 | Move installer and uninstaller shell-context setup into `.onInit` callbacks. |
