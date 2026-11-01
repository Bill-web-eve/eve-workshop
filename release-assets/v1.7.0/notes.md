EVE Workshop 1.7.0 – Material readiness, training clones and reliable reservations

## Downloads / Letöltések

- **Mac Apple Silicon:** `EVE_Muhely-1.7.0-macOS-AppleSilicon.dmg` — drag the app into Applications. Intel Macs are not supported.
- **Windows 11 x64:** `EVE_Muhely-1.7.0-Windows11-x64.zip` — extract the complete folder and run `EVE_Muhely.exe`.
- SHA-256 checksums and installation instructions are attached.

## What changed

- **Material readiness:** production plans and the manufacturing/reaction scheduler distinguish inputs already in stock, supplied by actual running EVE jobs, and still missing. Quantities reserved by other plans are excluded. Expand the details for material quantities and locations. Timeline markers show the same status.
- **Blueprint destination:** input locations are compared with the BPO, BPC or reaction formula used. Materials at another station are marked for transfer. Missing or ambiguous locations remain unverified. The indicator does not add hauling time to schedules.
- **Reliable reservation views during ESI cache delays:** delivered components can disappear from running jobs before inventory reflects delivery. Previously confirmed allocations now remain visible as explicitly dated, read-only views; that mismatch no longer creates a new allocation of the same reaction inputs at another plan’s expense. New reservations and final schedules still require consistent data. Changed targets without a matching confirmed view use the separately marked uncertain preview.
- **Offline training clones:** after every connected character is confirmed offline, compare each currently training character’s active implants with their own jump clones using the current skill’s primary and secondary attributes. Better owned clones generate individual OS alerts. Missing online access is reported by character; authorized comparisons remain visible. The macOS native bridge now accepts the training-clone notification category. Clone read access must be authorized in Settings; automatic checks run at most every 15 minutes and respect ESI cache expiry.
- **Regional trading volume:** show the last seven published daily volumes and the weekly average over the 30 days ending on the latest published day. ESI history combines buy and sell trades across the region; it is not sell-order-only or station-specific history.
- **Location names:** shared, scope-aware name resolution across jobs, blueprints, contracts and inventory, without resetting table filters or draft fields. Inaccessible locations remain explicitly marked.
- **Temporary ESI failures:** keep the already-open last successful result only when the target and calculation inputs still match, disable saving/new scheduling, and retry after the background refresh finishes. Complete nested character/job error messages now translate into English.
- Updated Hungarian and English documentation. Both installers start without characters, plans, moons, inventory, credentials or reservation history; only the public EVE Client ID is preconfigured. Existing user profiles are preserved.

## Változások magyarul

- **Alapanyagállapot** a gyártási tervben és az ütemezőben: készlet, ténylegesen futó EVE-job és még hiányzó bemenet; részletes mennyiségek és állomásnevek, jelölések az idővonalon.
- A célhely a használt **BPO/BPC vagy reakcióformula helye**. Külön jelzi az átszállítandó anyagokat és a nem igazolható helyet. Az állomásjelzés nem ad szállítási időt az ütemtervhez.
- **Jobátvétel utáni készletkéséskor** az utolsó igazolt foglalási kiosztást tartja meg, időponttal és csak olvasható állapotban. Nem kér újra reakcióanyagokat másik terv rovására az ellentmondó pillanatképekből. Új foglalás és végleges ütemezés friss adatra vár.
- **Offline tanulóklón-figyelés:** minden karakter igazolt offline állapotánál a jelenlegi skillhez leggyorsabb saját klónt keresi. Karakterenkénti OS-riasztás, név szerint jelzett hiányzó online-jog, következő ellenőrzés és javított Mac-értesítés. Az új klónolvasási ESI-jogot engedélyezni kell; az automatikus lekérés legalább 15 perces időközű, az EVE gyorsítótára érvényesül.
- **Piaci forgalom:** az utolsó hét közzétett nap és a legutolsó publikált nappal záruló 30 nap heti átlaga. Regionális buy/sell összforgalom, nem külön sell orderes vagy állomásonkénti előzmény.
- Helynevek a jobokban, blueprinteknél, contractoknál és a készletben; átmeneti hibánál megmaradó korábbi terv, védett mentés és újrapróbálás; javított angol hibaüzenetek.
- Frissített kézikönyv. Személyes adatokat nem tartalmazó telepítők, kizárólag előre megadott nyilvános Client ID-val, a meglévő helyi adatok megőrzésével.

## Installation and validation

Both packages use their own application windows and bundled Python runtimes. Windows requires Microsoft WebView2 Runtime and .NET Framework, normally present on Windows 11. Mac supports Apple Silicon only; no Developer ID signature or notarization is included.

Close the previous app before replacing its application folder. Characters, encrypted credentials, saved plans, reservations, moons and settings remain in the separate user data directory. Installing an update does not reset that directory.

Validation: **711 Python tests and 245 interface tests passed**. The final frozen Apple Silicon package passed HTTPS verification, cold startup with an empty profile, material readiness, confirmed-plan cache, learning-clone endpoints, Boost/invention API checks and graceful shutdown. Windows ZIP contents, AMD64/AnyCPU binaries, DLL imports, application version and empty defaults were verified on the Mac build host. Publication is additionally gated by the real Windows runtime/WebView2 smoke test in GitHub Actions.

EVE Online and associated game data/trademarks belong to CCP Games. This independent fan application is not endorsed by CCP.
