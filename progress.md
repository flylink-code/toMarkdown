# Progress Log

## 2026-07-14

- Confirmed v0.6.1 was published with MSI assets after the WiX retries.
- Started v0.6.2 migration from WiX/MSI to NSIS.
- Added an NSIS Unicode installer with selectable directory, Start Menu shortcut, desktop shortcut, uninstaller, registry uninstall metadata, and application icon.
- Switched the release workflow to install NSIS and publish `*-windows-x64-setup.exe` alongside the portable ZIP.
- Updated version metadata and README references to `0.6.2` and NSIS.
- PyInstaller build completed successfully for the NSIS input tree.
- The first local NSIS static-check command was malformed by PowerShell variable expansion; no source files were affected.
- NSIS script, workflow, README, and local `build.bat` checks passed; NSIS compiler is unavailable on this machine, so only GitHub Actions can compile the installer here.
- Full local test suite passed: `34 passed`.
- Committed the NSIS migration as `5f1254a` and pushed `main`.
- Created and pushed tag `v0.6.2`; waiting for the NSIS release workflow.
- Run #15 installed NSIS but failed because `makensis` was not on `PATH`; the installer script was not reached.
- Updated the workflow to resolve the compiler from `PATH` or `Program Files (x86)\NSIS`.
- Run #16 found `installer\toMarkdown.ico` relative to the wrong NSIS working directory; changed the script to use `${__FILEDIR__}`-based absolute paths.
- Run #17 showed NSIS resolves relative paths from the script directory after already applying `${__FILEDIR__}`; removed the duplicated directory and use script-relative paths directly.
- Run #18 reached script parsing and reported `SetShellVarContext` outside a Section/Function; moved it into installer and uninstaller initialization callbacks.
- Run #19 succeeded; NSIS generated the installer and GitHub uploaded both release assets.
