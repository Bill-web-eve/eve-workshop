## Letöltés / Downloads

- **Mac Apple Silicon (M1 vagy újabb), macOS 11+:** `EVE_Muhely-0.11.0-macOS-AppleSilicon.dmg`
- **Windows 11 64-bit:** `EVE_Muhely-0.11.0-Windows11-x64.zip`

## Újdonságok

- Jita buy, sell és split (a kettő átlaga) árak: alapanyaghiány soronként és összesítve, gyártási anyagköltség, holdtermelés értéke.
- A gyártási terv teljes célmennyiségének Jita buy és sell eladási értéke.
- Manufacturinghoz és reakcióhoz külön kereshető gyártási rendszer. Nyilvános ESI system cost index és adjusted price, beállítható facility tax, SCC, Alpha-pótdíj és struktúra job-cost kedvezmény. Hátralévő jobok részletes díjbecslése és összesített anyag + job költség.
- Holdfúrók Fuel Block típusa választható, kézi egységár-felülírással és tagolt számokkal. Fuel Block és Magmatic Gas költségek holdanként és összesítve.
- A holdtermelés 30 napos bevétele, üzemanyag-, bérleti, egyéb és értékesítési költsége, valamint profitja. Athanor / Metenox / összes bontás.
- PI-előrejelzés a kolónia tényleges adatidejéből: kitermelőprogram vége, ciklusonként változó kitermelés, gyárak bemeneti fedezete, várható leállása és kibocsátása. A csak tárolt készletből számolt fedezet külön is látható.
- Javított angol figyelmeztetések. A holdtermelés és az érctérfogat táblázatainak holdoszlopában listás szűrő.

## What's new

- Cached Jita buy, sell and midpoint prices for missing materials, production inputs and moon output; per-row values and totals.
- Gross Jita buy and sell sales values for the plan's full target quantity.
- Separate searchable manufacturing and reaction systems, public ESI system cost indices and adjusted prices, configurable facility/SCC/Alpha fees and structure reductions. Remaining-job fee estimates and combined material + job costs.
- Selectable Fuel Block type, grouped manual unit-price override, Fuel Block and Magmatic Gas costs.
- Thirty-day moon revenue, fuel, rent, other costs, sales fees and profit, with Athanor/Metenox/combined views.
- PI forecasts anchored to the colony snapshot timestamp, including extractor expiry and varying yields, factory input coverage, expected stops and output. Stored-stock-only coverage remains separate.
- English UI corrections and dropdown moon filters.

## Telepítés és frissítés / Installation and updating

Macen másold az alkalmazást az Applications mappába; Windowson bontsd ki a teljes ZIP-et, majd indítsd az EVE_Muhely.exe fájlt. Frissítés előtt állítsd le a régi alkalmazást. A meglévő helyi profil megmarad. A kiadás tiszta: nincs benne karakter, mentett terv, hold, készlet vagy belépési token; csak a nyilvános EVE Client ID előre beállított. Böngészős cím: http://127.0.0.1:8765.

On Mac, copy the app to Applications. On Windows, extract the entire ZIP and start EVE_Muhely.exe. Stop the old app before replacing it. Existing local profiles are preserved. Packages contain no characters, saved plans, moons, inventory or login tokens; only the public EVE Client ID is preconfigured. Local browser address: http://127.0.0.1:8765.

Mac: ARM64 only; no Apple Developer ID signing or notarization. Windows: portable AMD64 package; binary architecture, DLL imports and archive integrity checked. Native Windows 11 execution has not been tested on this Mac; the included Ellenorzes.cmd runs an isolated recipient-side smoke test.

Az árak és a díjak becslések; hiányzó adat nem számít nullának. A gyártási költség a hátralévő munkára, az eladási érték a teljes céltételre vonatkozik. A PI-előrejelzés feltételes, új import nélkül számol, és nem módosítja az ESI-készletet.

Prices and fees are estimates; missing data is not treated as zero. Production costs cover remaining work, while sales values cover the full target quantity. PI projections assume no new imports and never change observed inventory.
