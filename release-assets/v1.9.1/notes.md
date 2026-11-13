EVE Workshop 1.9.1 – Preview layout fix and 100px minimum

## Downloads / Letöltések

- **Mac Apple Silicon:** `EVE_Muhely-1.9.1-macOS-AppleSilicon.dmg`
- **Windows 11 x64:** `EVE_Muhely-1.9.1-Windows11-x64.zip`
- Installation instructions, SHA-256 checksums and signed updater assets are attached.

**Already using 1.9.0? Open Settings → Updates → Check for updates, then Download and restart.** Users of 1.8.0 or earlier must install the full package manually once. Existing profiles are preserved.

## What changed

- **Windows eve-preview no longer jumps back after dragging.** Saving a width, label or order used to replace the window-settings objects while native mouse callbacks still referenced the old objects. A drag then changed the wrong copy, and refresh restored the previous position. Validated settings now update the existing live objects, preserving callback targets and atomic validation.
- **Minimum thumbnail width is 100 pixels on Mac and Windows.** The shared input, native validation and resizing accept 100–900 px. Windows also enforces the 100px minimum during native resizing. Existing layouts remain valid.
- Added regression checks for dragging after a size/order save at 100px and 160px, refresh, Finish layout and persisted geometry. Updated both user manuals.

## Változások magyarul

- **Javított Windows-preview pozíciómentés:** a szélesség, címke vagy sorrend mentése után az elmozgatott előnézet nem ugrik vissza a következő frissítéskor vagy az elrendezés befejezésekor.
- **100 pixeles minimumszélesség** mindkét platformon, a beviteli mezőben és a natív méretezésnél is. Az állítható tartomány 100–900 px; a meglévő elrendezések megmaradnak.
- Célzott próbák a 100/160 pixeles mozgatásra és a mentett pozíció visszatöltésére; frissített magyar–angol kézikönyv.

**Az 1.9.0-ból az appon belül frissíthető:** Beállítások → Frissítések → Frissítések keresése, majd Letöltés és újraindítás. Az 1.8.0 vagy korábbi verziókról kézi telepítés szükséges. A karakterek, tervek és beállítások megmaradnak.

## Installation and validation

For manual installation, close the old app before replacing its application folder. On Mac, use the DMG and move the app to Applications. On Windows, extract the complete ZIP and run EVE_Muhely.exe. The Mac `-update.zip` and signed `update.json` are used by the updater, not additional manual installers.

Both packages have separate user-data directories and start without personal characters, plans, inventory or credentials. Only the public EVE Client ID and public update-verification key are preconfigured. The Ed25519 updater key remains the same as 1.9.0, so existing clients can authenticate this update. The private key is never included in source, installers or release assets.

Mac supports Apple Silicon only, without Developer ID/notarization; Windows supports x64 with Microsoft WebView2 and .NET Framework. The archive authentication signature is separate from OS publisher certificates. macOS may ask for preview permissions again after this native update. No OS protection is disabled.

Validation: **817 Python application tests and 289 interface tests passed**. The finished Mac package passed empty-profile startup, updater APIs, planning, save and shutdown checks, HTTPS verification, safe update-ZIP extraction and technical signature validation. Both update archives match the signed descriptor; Windows ZIP contents match the reviewed source and exclude private data. The 1.9.0 verifier recognizes 1.9.1 as a valid newer version.

The preview fix passed the [native Windows check for 69d850c](https://github.com/Bill-web-eve/eve-workshop/actions/runs/43455415851), using real WinForms/DWM test windows and the mouse-handler path with deterministic drag completion. Position survives a saved width change, refresh, Finish layout and reloading at 100 and 160px. Mac's native minimum-width test also passed. These isolated tests do not move real EVE client windows. Publication reruns full application and Windows native checks for this release commit before publishing.

EVE Online and associated game data/trademarks belong to CCP Games. This independent fan application is not endorsed by CCP.
