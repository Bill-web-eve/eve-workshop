EVE Workshop 1.5.0 – Contracts and notifications

## Downloads / Letöltések

- **Windows 11 x64:** `EVE_Muhely-1.5.0-Windows11-x64.zip` — extract the complete folder, then start `EVE_Muhely.exe`.
- **Mac Apple Silicon:** `EVE_Muhely-1.5.0-macOS-AppleSilicon.dmg` — drag the app into Applications. Intel Macs are not supported.
- SHA-256 checksums and installation instructions are attached.

## What changed

- Separate personal and corporation **Contracts** tabs, owner/date filters, sortable tables, contract items and persistent local status history.
- One-time notifications for newly observed open contracts directly assigned to your characters/corporations and acceptance of contracts you issued. The first import establishes a baseline without historical notification spam. ESI returns the past 30 days and in-progress contracts; downloaded history remains locally available.
- Grant the two new contract scopes through **Settings → Data access → Authorize contracts**. Custom Developer applications must enable `esi-contracts.read_character_contracts.v1` and `esi-contracts.read_corporation_contracts.v1`. Disabled corporation monitoring prevents corporation contract requests. Automatic checks respect the 15-minute interval and ESI caching.
- Optional per-character active-clone implant value alerts on undocking, with configurable thresholds. Authorize implant access and enable each desired character in **Settings → Notifications**. Only confirmed dock-to-space changes trigger alerts; stale or failed data does not invent an undock.
- Mac intel overlay remains above the EVE window when the game is clicked, until its configured expiry. Improved Hungarian/English UI and native Mac menu/error translations.
- Closing the main window quits the complete application. Improved Windows shutdown verification. Inventory status dropdowns, resolved location names, compact quantity columns and 25/50/100-row table paging.

## Változások magyarul

- Külön személyes és corp **Szerződések** nézet, tulajdonos- és dátumszűrőkkel, tétellistával és megőrzött helyi állapotelőzményekkel.
- Egyszeri értesítés új, közvetlenül karakternek/corporationnek címzett nyitott szerződésről és saját kiadott szerződés elfogadásáról. Az első import nem küld régi értesítéseket. Az ESI 30 napos és folyamatban lévő listájából beolvasott adatok később is megmaradnak.
- A két új szerződésjogosultság a **Beállítások → Adathozzáférések → Szerződések engedélyezése** alatt adható meg. Saját Developer alkalmazásnál a fenti két scope-ot is engedélyezni kell. Kikapcsolt corporationfigyelésnél nincs corp-szerződéslekérés. Automatikus ellenőrzés legfeljebb 15 percenként, az ESI gyorsítótárának betartásával.
- Opcionális, karakterenként kapcsolható implantérték-figyelés kidokkoláskor, állítható értékhatárral, külön ESI-engedéllyel. Csak megerősített állomás–űr váltásra jelez; hibás vagy korábbi adatból nem következtet kidokkolásra.
- A Mac intel overlay az EVE-re kattintáskor is megmarad a beállított lejáratig. Javított magyar–angol felület és Mac-menü- és hibaüzenetek.
- A főablak bezárása a teljes alkalmazást leállítja. Javított Windowsos leállásellenőrzés, készletállapot-választó, helynevek, kompakt mennyiségoszlop és 25/50/100 soros táblázatok.

## Installation and existing data

Both packages open in their own application windows and include their Python runtime. Windows requires Microsoft WebView2 Runtime and .NET Framework, normally available on Windows 11. The Mac package supports Apple Silicon only and has no Developer ID signature or notarization.

Close the previous app before replacing its application folder. Existing profiles, characters, saved plans and encrypted credentials stay in the user data directory. Both packages ship without characters, plans or tokens; only the public EVE Client ID is preconfigured.
