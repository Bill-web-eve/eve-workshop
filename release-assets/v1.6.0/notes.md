EVE Workshop 1.6.0 – Connected W, Boost counter and invention

## Downloads / Letöltések

- **Mac Apple Silicon:** `EVE_Muhely-1.6.0-macOS-AppleSilicon.dmg` — drag the app into Applications. Intel Macs are not supported.
- **Windows 11 x64:** `EVE_Muhely-1.6.0-Windows11-x64.zip` — extract the complete folder and run `EVE_Muhely.exe`.
- SHA-256 checksums and installation instructions are attached.

## What changed

- New connected **W** identity throughout the sidebar, favicon, macOS app/Dock icon and Windows executable/window icon. Existing navy, amber and pale-cyan colours are retained.
- **Boost counter:** choose a local chat channel with Boost in its name, then start counting new declarations. Nine in-game charge icons show green count badges. A character's latest declared set replaces their previous set; repeated declarations, duplicate logs, missing summaries and copied numerical reports are ignored. Copy all nine charge names, counts (including zero) and the declaring character names.
- **T2 ship invention costing:** select an inventor, use active skills for expected success chance, and include datacores, decryptors, T1 copying and invention job fees. Compare all decryptors by the full manufacturing chain, including ME/TE and BPC run limits; an expensive decryptor can win through material savings. Expected successes are mathematical estimates, not guaranteed in-game outcomes.
- Every **Compare** checks required market quotes, industry indices/adjusted prices and inventor skills. Missing/expired data is loaded and calculations update automatically while respecting valid ESI cache entries. New invention profiles default to the selected production character; a saved separate inventor stays selected.
- Dedicated **Reservations** menu with per-plan on/off controls and priority ordering inside the same inventory owner. Delivered-job cache waits allow provisional plan previews, while final reservation changes still require fresh inventory.
- Acknowledge notifications, sidebar Intel On/Off control, separate import/export hauling switches, compact saved-plan dropdown and accurate high-precision broker fee calculations.
- Updated Hungarian and English documentation; existing local profiles are preserved.

## Változások magyarul

- Új **W-formájú arculat** az oldalsávon, a böngészőikonon, a Mac alkalmazás/Dock ikonján és a Windows indító/ablak ikonján.
- **Boost számláló:** Boost nevű helyi chatcsatorna kiválasztása után csak az indítástól érkező bejelentések számítanak. Kilenc játékbeli ikon, zöld számbuborék, karakterenként utolsó összeállítás, ismétlések és összesítések kizárása. A másolt listán minden típus, szám és karakternevek szerepelnek, a hiányzó típusoknál 0-val.
- **T2 hajók invention-költsége:** inventáló karakter aktív skillekkel, datacore/decryptor, T1 másolás és invention jobdíjak, várható sikeresség. A decryptorokat az ME/TE, a runhatár és a teljes gyártási lánc alapján hasonlítja össze. A várható sikeresség becslés, nem garantált játékbeli eredmény.
- Minden **Compare** ellenőrzi a szükséges árakat, ipari indexeket/korrigált árakat és az inventor skilljeit; a hiányzó vagy lejárt adatokat lekéri és újraszámol. Az ESI érvényes gyorsítótára továbbra is érvényesül.
- Külön **Foglalások** menü, tervenkénti be-/kikapcsolás és tulajdonosi körön belüli sorrend. Jobátvétel utáni készletfrissítésre várva előzetes tervek készülhetnek; a végleges foglalás friss készlethez kötött.
- Tudomásul vehető értesítések, Intel On/Off kapcsoló, külön import/export szállítási kapcsolók, kompakt tervválasztó és javított brokerfee-számítás.
- Frissített magyar–angol kézikönyv és a meglévő helyi profil megőrzése.

## Installation, validation and existing data

Both packages have their own application windows and bundled Python runtimes. Windows requires Microsoft WebView2 Runtime and .NET Framework, normally present on Windows 11. Mac supports Apple Silicon only; no Developer ID or notarization is included.

Close the previous app before replacing its application folder. Characters, encrypted credentials, saved plans, reservations, moons and settings remain in the separate user data directory. Both packages are distributed without personal data; only the public EVE Client ID is preconfigured.

Local validation: 661 Python application tests and 211 interface tests passed. The frozen Apple Silicon runtime passed cold startup with an empty profile, Boost/invention API checks, HTTPS verification and graceful shutdown. Windows ZIP structure, AMD64/AnyCPU binaries, DLL imports, version, icons and empty defaults were checked on the Mac build host. Publication additionally requires the Windows-hosted runtime/WebView2 smoke test in GitHub Actions.

The new icon was produced with the built-in image-generation tool from the user-approved W concept; the retained prompt is in the source tree. EVE Online and associated game data/trademarks belong to CCP Games. This independent fan application is not endorsed by CCP.
