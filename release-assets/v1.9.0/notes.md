EVE Workshop 1.9.0 – Signed updates from the application

## Downloads / Letöltések

- **Mac Apple Silicon:** `EVE_Muhely-1.9.0-macOS-AppleSilicon.dmg` — drag the app into Applications. Intel Macs are not supported.
- **Windows 11 x64:** `EVE_Muhely-1.9.0-Windows11-x64.zip` — extract the complete folder and run `EVE_Muhely.exe`.
- SHA-256 checksums and installation instructions are attached.

**Install 1.9.0 manually once when upgrading from 1.8.0 or earlier. Those versions do not contain an updater. Future stable releases can then be installed from Settings → Updates.**

## What changed

- **Settings → Updates:** automatic stable-version checks at most once every 24 hours, optional scheduling, a manual check button and a compact new-version banner. Startup waits for the authenticated local app state before requesting a check. Detached intel windows do not create duplicate checks. No EVE login, GitHub account or personal token is required.
- **Download and restart:** one explicit click downloads the platform-specific archive, displays progress, verifies its size, SHA-256 and Ed25519 signature, and prepares installation. Merely finding an update never installs it. Pending edits and active EVE data refreshes block installation until finished.
- **Safe application replacement:** a detached copy of the runtime waits for the main app and local service to exit, backs up SQLite, stages the new application, retains the previous copy and restarts. Failed directory swaps restore the original app. Restart is verified against the expected new version on the loopback health endpoint. A startup failure retains both copies and the database backup; a potentially migrated database is not automatically rolled back.
- **Local data stays separate:** characters, encrypted credentials, plans, reservations, moons and settings remain in the existing user-data directory. The updater never replaces that directory. Windows backup connections are explicitly closed so cleanup/replacement is compatible with Windows file locking.
- **Authenticated release assets:** the public verification key is embedded in both apps. Only signed metadata for the expected repository, stable tag, filenames and platforms is accepted. Invalid signatures, altered files, unsafe archive paths, external symlinks and older-than-cached metadata are rejected. The private signing key stays on the maintainer's machine and is not published.
- Updated Hungarian and English manuals, packaging instructions and automated Windows updater checks. Existing eve-preview, intel, production planning and all other 1.8.0 features remain available.

## Változások magyarul

- **Beállítások → Frissítések:** napi automatikus és kézi verzióellenőrzés, kikapcsolható ütemezés, új kiadást jelző kompakt sáv. Az indulás megvárja a helyi kapcsolat felépülését; a külön intelablakok nem indítanak újabb keresést.
- **Letöltés és újraindítás:** egy gombbal induló letöltés, látható folyamatállapot, fájlméret-, SHA-256- és Ed25519-aláírás-ellenőrzés. A puszta keresés nem telepít. Előbb menteni/alkalmazni kell a módosításokat, és be kell fejezni a folyamatban lévő EVE-adatfrissítést.
- **Külön frissítőfolyamat:** teljes leállás megvárása, adatbázismentés, az app mappájának egyben cseréje, korábbi példány megtartása, újraindítás és az új verzió ellenőrzése. Sikertelen fájlcserekor visszaáll az eredeti app; sikertelen indításkor a másolatok és az adatmentés megmaradnak.
- A karakterek, belépések, tervek, holdak és beállítások külön felhasználói mappája változatlanul megmarad. Javított Windowsos adatbázislezárás.
- Saját, ingyenes frissítési aláírás. A nyilvános ellenőrzőkulcs az app része; a privát kulcs helyben marad. Frissített két nyelvű kézikönyv.

**Az 1.9.0-t egyszer kézzel kell telepíteni az 1.8.0 vagy korábbi verzióról. Utána a következő stabil kiadások már az alkalmazásból telepíthetők.**

## Installation and validation

Close the old app before replacing its application folder. Existing profiles are preserved. Both installers start without characters, plans, inventory, credentials or personal data; only the public EVE Client ID and public update-verification key are preconfigured.

The free Ed25519 update signature authenticates the update archive. It is separate from an Apple Developer ID or Windows publisher certificate. Mac remains Apple Silicon only, ad-hoc signed without Developer ID/notarization; Windows remains an unsigned portable x64 application requiring Microsoft WebView2 and .NET Framework. No Gatekeeper, SmartScreen or privacy protection is disabled. macOS can still request eve-preview permissions again after an unsigned app update.

The Mac `-update.zip` and `update.json` assets are for the app updater, not additional installers. Use the DMG or standard Windows ZIP for manual installation. Updates need sufficient free disk space and a writable installation parent folder. Developer/source or read-only copies require manual installation.

Validation: **815 Python application tests and 288 interface tests passed**. The finished Apple Silicon package passed HTTPS certificate verification, empty-profile startup, updater API and preference checks, production planning, plan saving, graceful shutdown, safe update-archive extraction and technical signature verification. Windows archives are checked for integrity, exact source parity, public-only defaults, AMD64/AnyCPU binaries and DLL imports. The signed update descriptor verifies against the embedded key and both archives' actual hashes.

The Windows update implementation passed [run 43191611684](https://github.com/Bill-web-eve/eve-workshop/actions/runs/43191611684) before release preparation: copied embedded runtimes, real process exit waits, whole-directory replacement, synthetic launcher restart/health handshake, preserved profile and credentials, database backup and cleanup. This uses an isolated test application and ephemeral test key, not a user's installed app or the maintainer's private signing key. Publication reruns the application and native Windows checks for the release commit and publishes only after both pass.

EVE Online and associated game data/trademarks belong to CCP Games. This independent fan application is not endorsed by CCP.
