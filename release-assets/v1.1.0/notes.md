## Downloads / Letöltés

- **Mac Apple Silicon (M1 or later), macOS 11+:** `EVE_Muhely-1.1.0-macOS-AppleSilicon.dmg` — native app window, self-contained runtime.
- **Windows 11 64-bit:** `EVE_Muhely-1.1.0-Windows11-x64.zip` — portable app, browser interface.

## What's new since 1.0.0

- Native macOS Cocoa/WKWebView app with bundled backend, independent intel map/chat windows, OS notifications and configurable frameless intel overlay. Settings now contain appearance and language controls.
- Local EVE intel chat-log monitoring: region map, jump-range warnings, clear reports, verified character zKillboard links and ship icons. Map report cards expire after three minutes; overlay duration and display position are configurable.
- Personal and corporation notification center for training, completed jobs, idle PI and upcoming moon extractions. Visible progress for EVE requests and background operations.
- Personal mining ledger: character, ore, day and record breakdowns, archived history, volume and refined Jita buy/sell/split valuation. Daily refining totals reconcile with the selected period. Raw-ore valuations and residue calculations are excluded.
- **Authorize all access** requests every supported ESI scope for one character in a single EVE approval. Existing individual authorization options remain available.
- Production uses packaged assets only, excluding assembled items in use. Clear plan-calculation feedback and inventory-cache retry deadlines, running jobs on the schedule timeline, saved-plan switching that keeps the current view, and more compact layouts.

## Újdonságok az 1.0.0 óta

- Saját ablakos, önálló Mac-app beépített futtatókörnyezettel, külön intel-térkép- és chatablakokkal, OS-értesítésekkel és állítható inteloverlayjel. A nyelv és a megjelenés a Settings alatt állítható.
- Helyi EVE intelchat-logok követése, teljes régiós térkép, ugrástávolság szerinti jelzések, clear-kezelés, pilóták zKillboard-linkje és hajóikonok. A térképes jelentéskártyák három perc után eltűnnek.
- Személyes és corporation értesítési központ: tanulás, kész jobok, PI és közelgő holdkitermelések. Folyamatjelző az adatlekéréseknél.
- Bányászati napló karakterenként, ércenként és naponta, megőrzött előzményekkel, térfogattal és finomított Jita-értékkel. Egyeztetett napi és időszaki finomítási összegek; nyersérc-árazás és residue nélkül.
- Karakterenként egyetlen **Authorize all access** jóváhagyással megadható minden támogatott ESI-hozzáférés.
- Csak repackagelt assetek számítanak gyártáshoz. Javított terv-visszajelzések és készletfrissítési határidők, aktív jobok az idővonalon, nézetet megőrző tervváltás és kompaktabb elrendezés.

## Installation and updating / Telepítés és frissítés

Stop the previous app before replacing it. Mac: copy EVE Muhely.app from the DMG to Applications; the interface opens in its own window. Windows: extract the whole ZIP and start EVE_Muhely.exe; the interface opens at http://127.0.0.1:8765 in your browser. No separate Python, Excel or Codex installation is required. EVE authorization opens the system browser.

Frissítés előtt állítsd le a korábbi appot. Macen másold a DMG alkalmazását az Applications mappába; Windowson bontsd ki a teljes ZIP-et, és indítsd az EVE_Muhely.exe fájlt. A saját helyi adatok megmaradnak.

Both packages are clean: no characters, saved plans, moons, inventory, account data, chat logs or login tokens. Only the public EVE Client ID is preconfigured. Authorize your own characters under Settings → Data access. Every requested scope must also be enabled in the Developer application; corporation endpoints still require the appropriate in-game roles.

A csomagok nem tartalmaznak személyes adatokat, karaktereket, terveket, holdakat, készletet vagy belépési tokent; csak a nyilvános Client ID van előre beállítva. A meglévő profilokat nem törlik.

Mac: arm64 only; ad-hoc signing, no Apple Developer ID or notarization. Windows: portable AMD64, no publisher signing. Shared Python/UI tests, clean-package audits, checksums, Mac frozen-backend HTTPS/startup/shutdown and native UI integration tests passed. Windows executable architecture, DLL dependencies and ZIP integrity checked; native Windows 11 runtime execution was not tested on this Mac. The included Ellenorzes.cmd performs an isolated recipient-side smoke test.

Native macOS notifications and overlay are Mac features; this Windows release retains the browser interface.
