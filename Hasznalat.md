# EVE Műhely – használati útmutató

## Felület nyelve / Interface language

Az oldalsávban a sötét mód kapcsolója alatt válassz a **Magyar** és **English** gombokkal. A váltás azonnali, és a böngésző megjegyzi. A beírt mezők, szűrők és még nem mentett módosítások megmaradnak. A nevek és EVE-adatok változatlanok.

Use **Magyar / English** in the sidebar, below the dark-mode switch. Your browser remembers the language. Switching keeps your current view, inputs and filters. Character, corporation, saved-plan and EVE item names remain unchanged.


Helyben futó, magyar nyelvű gyártástervező macOS-re. Excel és OpenAI API-előfizetés nem szükséges hozzá. A böngészős felület kizárólag a saját gépeden futó alkalmazáshoz kapcsolódik.

## Indítás

Az Asztalon nyisd meg az **EVE Műhely** parancsikont. Ez a helyi **~/Applications/EVE Muhely.app** alkalmazást indítja. A futáshoz szükséges programfájlok az alkalmazáson belül vannak, ezért az indítás nem függ a ProtonDrive mappa hozzáférésétől vagy szinkronizálásától. Az EVE mappában külön alkalmazáspéldány és **EVE Muhely.command** indító is található. A megnyíló cím: http://127.0.0.1:8765.

Az indító már futó példány esetén ugyanazt az alkalmazást nyitja meg. A böngészőlap bezárása nem állítja le a műhelyt; erre a bal alsó sarokban lévő **Alkalmazás leállítása** gomb szolgál. A mentett adatok megmaradnak.

Ezen a Macen a meglévő Python-környezet elegendő, külön telepítés most nem szükséges. Másik gépen Python 3.9 vagy újabb kell; célszerű a [python.org hivatalos macOS-telepítőjét](https://www.python.org/downloads/macos/) használni. A belépéshez szükséges `cryptography` csomagot az indító szükség esetén saját környezetbe telepíti a PyPI-ról. Ez az első alkalommal internetet igényel. Külön szerver, Docker, Node.js vagy adatbázis-telepítés nem kell.

## Tervezés EVE-belépés nélkül

1. Írd be a termék angol játékbeli nevét a **Termék** mezőbe, és válassz a találatok közül. A Salvation és Redeemer gyorsgombbal is elérhető.
2. Add meg a célmennyiséget **darabban**, majd kattints a **Terv kiszámítása** gombra.
3. A **Blueprint** oldalon állítsd a paraméterforrást Kézire, és add meg az ME-t, TE-t, a jobonkénti runszámot, illetve ha ismert, az összes rendelkezésre álló BPC-runt. Alkalmazd a módosításokat.
4. A **Készlet** oldalon megadhatod a meglévő darabszámokat és a már folyamatban lévő jobok várható kimenetét. A folyamatban mező **darabszám**, nem run.
5. A **Gyártási terv** csak a hátralévő tételeket mutatja, a receptfüggőségek sorrendjében. Az alacsonyabb szintű reakciókkal és komponensekkel kezdj. Külön szerepel a szükséges run, a gyártás kimenete és a jobfelosztás.
6. Az **Alapanyaghiány** csak a hátralévő gyártáshoz hiányzó alapanyagokat mutatja. A már kész vagy folyamatban lévő komponens alapanyagait nem kéri újra.

A kézi módosítások az **alkalmazás** gomb megnyomásakor mentődnek. A kézi készlet és folyamatban mező üresen automatikus EVE-adatot, kézi készletmódban nullát jelent. A beírt **0 valódi felülírás**. A **Másra foglalva** az elérhető készletet csökkenti.

## Corporation készletek és corp gyártás

A **Corporationok** menüpontban kérheted le a hozzáadott karakterek corporationjeit. A **Corp-adatok felderítése és frissítése** gomb felderíti a tagságukat, majd corporationönként egyszer tölti le a teljes készletet, blueprintlistát és ipari joblistát. Több hozzáadott tag nem többszörözi meg ugyanazt a corp készletet. A személyes karakter-/helyszűrő nem korlátozza ezt a lekérést.

Egyszeri engedélyezés:

1. Az EVE Developer oldalon a meglévő alkalmazáshoz add hozzá a következő három scope-ot: `esi-assets.read_corporation_assets.v1`, `esi-corporations.read_blueprints.v1`, `esi-industry.read_corporation_jobs.v1`.
2. A **Corporationok** oldalon a megfelelő karakter mellett kattints a **Corp-hozzáférés engedélyezése** gombra. Az EVE oldalán ugyanazzal a karakterrel engedélyezd az olvasást. A korábbi személyes, skill- és PI-jogosultságok megmaradnak.
3. A készlet és blueprintek olvasásához **Director**, a corp jobokhoz **Factory Manager** szerepkör kell. Egy megfelelő tagkarakter elég corporationönként. A hiányzó corp-hozzáférés nem akadályozza a személyes tervezést.

A termék fölötti **Gyártási kör** mezőben válassz **Személyes gyártás** vagy **Corp gyártás · [corporation neve]** között. Corp módban kizárólag az adott corporation készlete, folyamatban lévő jobjainak kimenete és blueprintjei számítanak. A személyes készlet és a többi corporation készlete kimarad. A kézi készlet- és blueprintbeállítások, valamint a helyszűrés corporationönként is külön mentődnek. A struktúrabónuszok továbbra is közös beállítások.

A mentett terv megjegyzi a gyártási körét; újranyitva ehhez tér vissza. A meglévő tervek személyesek maradtak. Másik készlettulajdonoshoz új tervet kell kezdeni. A foglalások csak ugyanannak a tulajdonosnak a többi tervét csökkentik. Az **Összes mentett terv** anyaghiánya külön készletből számolja ki az egyes tulajdonosok hiányát, majd csak a beszerzendő mennyiségeket összesíti.

A corp módban megnyomott **EVE-frissítés** a corporation adatokat frissíti. Személyes módban a korábban sikeresen bekapcsolt corp-adatok is frissülnek az EVE-frissítés részeként. Hibánál nincs személyes készletre visszaesés: a corporationhez tartozó számítás megáll, a korábbi adatok megmaradnak. Az átvett jobok és a még korábbi assetpillanatkép közötti várakozás corp módban is érvényes.

## Táblázatok rendezése és szűrése

Minden táblázat fejlécére kattintva rendezhetsz: az első kattintás növekvő, a második csökkenő, a harmadik az eredeti sorrendet állítja vissza. A számok mennyiség szerint, az időpontok időrendben rendeződnek. A Gyártási terv eredeti sorrendje a gyártási függőségeket követi.

A szűrősor alapértelmezetten csukva van. A táblázat fölötti **Szűrők megnyitása** gombbal nyithatod ki, a **Szűrők bezárása** gombbal csukhatod vissza. A becsukás nem törli a szűrést; a gomb jelzi az aktív szűrők számát. A **Karakter** oszlopban legördülő listából válassz; minden más oszlopban szabad szöveget írhatsz. A szűrők együtt érvényesülnek, a számok ezreselválasztó nélkül is kereshetők. A **Rendezés és oszlopszűrők törlése** gomb visszaállítja az oszlopokat. A táblázat fölött látszik a megjelenített és az összes sor száma.

Az oszlopbeállítások nézetenként megmaradnak adatfrissítés és menüváltás közben; a böngészőlap újratöltése alaphelyzetbe állítja őket. A táblázat fölötti korábbi kereső az oszlopszűrőkkel együtt működik. A rendezés és szűrés a megjelenítést változtatja, a gyártási számítást és a foglalásokat nem.

## Sötét mód

A menüben a **Sötét mód** kapcsolóval válthatsz a világos és a sötét megjelenés között. Az alapbeállítás sötét. A választásodat a böngésző ezen a gépen megjegyzi, újratöltés és az alkalmazás újraindítása után is. A téma minden nézetre, a gyártási gráfra és a beviteli mezőkre is érvényes.

## Itemnév másolása

Kattints egy item nevére: a pontos angol név egyszerű szövegként a vágólapra kerül. Például a **Ferrofluid** nevére kattintva csak `Ferrofluid` másolódik, ID, darabszám és formázás nélkül. A sikeres másolást a **Másolva: Ferrofluid** üzenet jelzi. Beillesztés: ⌘V, Windowson Ctrl+V.

A funkció a gyártási tervben, az alapanyaghiányban és az összesített hiányban, a készletben, a blueprintoknál, a folyamatban lévő joboknál, a foglalásokban, a gráfon, valamint a PI- és skillnézetekben is működik. Billentyűzettel a névre lépve Enterrel is másolhatsz. A gráfelem kijelölése és a részleteket megnyitó termékgombok a másolással együtt továbbra is működnek.

## EVE-kapcsolat: egyszeri beállítás

Az EVE-kapcsolathoz saját Client ID és karakterenkénti bejelentkezés szükséges. Ezek beállításáig kézi készlettel használható a műhely.

1. Nyisd meg az [EVE Developer alkalmazásoldalát](https://developers.eveonline.com/applications), jelentkezz be, és hozz létre egy saját alkalmazást.
2. Az alkalmazás lehet például **EVE Muhely**. Az ESI-adatokat használó, helyi/native/PKCE alkalmazástípust válaszd, ha a portál típust kér. A portál további kötelező név- és leírásmezőit töltsd ki.
3. A **Callback URL pontosan**:

   `http://127.0.0.1:8765/callback`

4. A kért olvasási jogosultságok:

   - `esi-assets.read_assets.v1`
   - `esi-characters.read_blueprints.v1`
   - `esi-industry.read_character_jobs.v1`
   - `esi-skills.read_skills.v1`
   - `esi-skills.read_skillqueue.v1`
   - `esi-planets.manage_planets.v1` (a PI-adatok lekéréséhez használt CCP-jogosultság)

5. Mentsd az alkalmazást. A kapott nyilvános **Client ID**-t másold a műhely **EVE-kapcsolat** oldalára, és mentsd. Client Secretet nem használunk, azt ne másold be.
6. A **Bejelentkezés EVE Online-nal** gombbal add hozzá egyenként a karaktereidet. A jelszavadat kizárólag a CCP hivatalos bejelentkezőoldalán add meg.
7. Indíts **EVE-frissítést**. Ez a személyes asseteket, blueprinteket, ipari jobokat, valamint az engedélyezett skilladatokat, tanulási sort és PI-kolóniákat tölti le. Corporation hangárt nem kér le.
8. Az első sikeres frissítés automatikusan bekapcsolja a **Személyes EVE-készlet** forrást, ha korábban nem választottál külön készletmódot. Így a terv rögtön levonja az asseteket és jobkimeneteket. Később a **Struktúrák és bónuszok** oldalon bármikor válthatsz; a külön kiválasztott kézi módot a frissítés megőrzi. Az EVE-kapcsolat oldalon kiválaszthatod a beszámított karaktereket.

A Mac a Kulcskarikához hozzáférést kérhet a titkosított belépés mentésekor. A hozzáférést az EVE fiókod oldalán később visszavonhatod.

## Skillek és tanulás

A bal oldali **Skillek és tanulás** menü **minden hozzáadott karaktert** mutat, függetlenül a gyártáshoz kiválasztott karakterektől és helyszínektől. A karakter neve vagy a **Részletek** gomb alatt két lap van: a teljes **Tanulási sor**, valamint a szűrhető **Összes skill**, tanult/aktív szinttel és skillpontokkal. Az aktuális tanulás, a következő tételek, a befejezési időpontok és a sor hossza külön látszik.

- **Piros:** a karakter most nem tanul, a sor üres vagy szünetel.
- **Sárga:** a folyamatos tanulás legkésőbb 5 × 24 órán belül megszakad. A sor közbeni rést is figyelembe veszi, nem csak a legutolsó befejezést.
- **Zöld:** jelenleg tanul, és a betöltött sor több mint 5 napig folyamatosan kitart.
- **Szürke:** nincs engedély, nincs betöltött adat, a frissítés hibás, vagy a legutóbbi ellenőrzés több mint 5 perce volt. Ilyenkor nem állítja biztosan, hogy a karakter nem tanul; a régi adatokat jelölve őrzi meg.

A korábbi belépések a gyártási adatokhoz továbbra is használhatók, de a skillekhez egyszeri bővítés kell. Az [EVE Developer oldalon](https://developers.eveonline.com/applications) a **meglévő alkalmazást** szerkeszd, és a korábbi három mellett engedélyezd az `esi-skills.read_skills.v1` és az `esi-skills.read_skillqueue.v1` jogosultságot. A Client ID és a callback maradjon ugyanaz. Ezután a Műhely skillnézetében karakterenként kattints a **Skillek engedélyezése** gombra, és az EVE belépőoldalán ugyanazt a karaktert válaszd. Jelszót és Client Secretet a Műhely nem kér. Másik karakter kiválasztásakor a meglévő belépést nem írja felül.

A **Skilladatok frissítése** csak a skilladatokat frissíti; a felső **EVE-frissítés** az ipari adatok után ezeket is ellenőrzi. Sikertelen skilllekérés nem teszi érvénytelenné a gyártási készletet. Nyitott, előtérben lévő skillnézetnél percenként frissülnek az engedélyezett karakterek adatai, a CCP gyorsítótárazását figyelembe véve. Bezárt vagy leállított alkalmazás mellett nincs figyelés vagy értesítés.

Az EVE néha még a sorban jelzi az időközben befejezett szintet, amíg a karakter újra be nem lép a játékba. Ezeket a befejezéseket a tanult szinthez és az ismert SP-hez hozzáadjuk. Az aktív szintet külön, az EVE skilladata szerint mutatjuk, mert az előfizetés vagy Expert System miatt eltérhet. A **Befejezett sorok megjelenítése** kapcsolóval a sorban maradt korábbi befejezések is láthatók.

## Frissítés és folyamatban lévő gyártás

Az **EVE-frissítés** újra lekéri a szerver által már frissíthető adatokat, majd újraszámolja a tervet. A CCP gyorsítótárazása miatt a többszöri kattintás nem feltétlenül hoz frissebb készletet. Az asset-, blueprint- és jobpillanatkép idejét karakterenként láthatod az EVE-kapcsolat oldalon. A lejárt pillanatképből végzett számítást figyelmeztetés jelzi; sikertelen karakterfrissítéskor az EVE-mód új tervét a program megállítja, a régi adatokat megőrzi.

A **Folyamatban** mennyiség a gyártási és reakciós, `active`, `paused` vagy `ready` állapotú jobok **run × kimenet/run** értéke. A kutatás, másolás, invention, delivered, cancelled és reverted nem adódik hozzá. Az átvehető, még át nem vett job kimenetét továbbra is beszámítja.

Átvétel után frissíts. Az asset és job gyorsítótára eltérő időben frissülhet. Ha a program frissen átvett jobot lát egy korábbi assetpillanatkép mellett, az érintett tervvel megvárja a frissebb assetadatot. Addig ellenőrzött kézi készletértékkel folytathatod. A korábbi kézi felülírások EVE-frissítéskor is megmaradnak; a mező kiürítésével állhatsz vissza automatikus adatra.

Helyszűréshez a Struktúrák oldalon állomás- vagy struktúra-ID-ket adhatsz meg. Üres mező minden helyet beszámít. A konténerek tartalmát a felső helyszínhez rendeli, a joboknál a kimeneti helyet vizsgálja.

## Blueprintek és bónuszok

Automatikus módban a személyes blueprintekből olvassa az ME/TE-t és a BPC-k hátralévő runjait, **kézi készletmódban is**. A készletforrás csak az anyagok és jobkimenetek elszámolását kapcsolja. Külön oszlopban látható az összes szűrésbe tartozó **BPO- és BPC-darabszám**, a BPC-k összes runja, valamint az ME/TE-hez kiválasztott csoport **felhasználható runkerete**. A **Példányok megtekintése** gomb minden blueprint saját ME/TE-jét, hátralévő runját, helyét, karakterét, egyedi Item ID-ját és kiválasztási állapotát megmutatja. Kézi ME/TE-felülírás mellett is láthatók az eredeti EVE-példányok.

A BPO elsőbbséget kap; azon belül, illetve BPC-nél a legjobb ME, majd TE számít. Csak azonos ME/TE-jű BPC-k runjait vonja össze. BPC-példány határán új jobot kezd, így az anyagkerekítés is külön történik. Eltérő paraméterű vagy foglalt példányokra figyelmeztet. Konkrét blueprintet az egyedi Item ID-val lehet kiválasztani. Példa: két, egyenként ME 3 / TE 2 / 2 runos Salvation BPC esetén 2 BPC-t és 4 felhasználható runt mutat.

Hiányzó blueprintnél kézi, alapból ME 0 / TE 0 számítást készít, és ellenőrzési jelzést mutat. Kevés BPC-run esetén a teljes szükséglethez számol anyagot, de a runhiányt jelzi; ez nem jelenti azt, hogy minden job azonnal elindítható.

A **Run/job** szerkeszthető munkafeltételezés. Automatikus BPC-nél alapértéke legfeljebb 100 és a kiválasztott csoport leghosszabb másolatának hátralévő runja; BPO-nál vagy hiányzó blueprintnél legfeljebb 100, az SDE másolati runhatáráig. Ez nem azonos a karaktered és a játék által ténylegesen engedett jobmérettel. A kézzel mentett Run/job beállítás elsőbbséget kap. Állítsd a valóban használt jobméretre, mert az anyagkerekítés függ a felosztástól. Reakciónál az ME/TE mindig 0.

A kapott képek szerinti közös alapértékek:

| Tevékenység | Struktúra anyag | Rig anyag | Struktúra idő | Rig idő |
|---|---:|---:|---:|---:|
| Manufacturing | 1% | 4,2% | 30% | 42% |
| Reakció | 0% | 2,6% | 25% | 26,4% |

A bónuszok szorzódnak. A skill időszorzó alapból 1,00; állítsd át, ha a saját skilljeid gyorsítását is figyelembe akarod venni. A megadott rigbónuszok a kérésed szerint minden megfelelő gyártási, illetve reakciós lépésre érvényesek.

## Vétel, mentés, adatok

- Bármely recepttel rendelkező köztes termék **Vételre** állítható a Blueprintok oldalon. Ekkor annak saját alapanyagai eltűnnek, és maga a köztes termék kerül a beszerzési listára.
- Fuel block bemenetet alapból vásároltnak tekint, ahogy a korábbi táblázatok. Külön célterméknek kiválasztva gyártható, vagy a tervben Gyártásra állítható.
- A PI-termékek beszerzendő levelek. A PI-kolóniák külön menüben követhetők; invention, BPC-másolás és slotok naptári ütemezése nem része a tervezőnek. Az ISK-költségek és a jobdíjak külön becslésként jelennek meg. Az összes munkaóra a jobidők összege, nem a párhuzamos gyártás átfutási ideje.
- A **Terv mentése és foglalás** a célterméket és darabszámot tárolja, valamint aktív készletfoglalást indít. A készlet és a blueprintparaméterek közösek. A foglalások kezelését az alábbi rész írja le.
- A gyártási és beszerzési lista CSV-be menthető; a beszerzési lista vágólapra is másolható.
- A **Receptadatok frissítése** a CCP hivatalos SDE-jét tölti le. A mellékelt adatbázis: **3607705**, 2026. október 12.; **4172 választható, publikált gyártható termék**. Frissítés nélkül az előre csomagolt receptek internet nélkül is használhatók.

## Mentett tervek és foglalások

A célmennyiségből a már meglévő késztermékeket is levonja. Ha például van 3 Redeemered, és **további 3-at** szeretnél gyártani, a Készlet oldalon a Redeemer sorának **Másra foglalva (kézi)** mezőjébe írj 3-at. A meglévő hajókat így minden terv félreteszi, az újonnan elkészülő példányok viszont csökkentik a hátralévő mennyiséget. Ez valódi készlet mellett működik; ne állítsd a kézi készletet 0-ra, mert az frissítés után is elrejtené az új hajókat. A gyártási oldalon külön összesítés mutatja a késztermékből és jobkimenetből fedezett mennyiséget.

## Gyártási gráf

A kiválasztott vagy megnyitott mentett tervhez a bal oldali **Gyártási gráf** menü mutatja az összefüggéseket. A nyilak balról jobbra, a bemenettől a belőle készülő termék felé haladnak. Alapból csak a még gyártandó reakciók és komponensek látszanak, ugyanazokkal a mennyiségekkel és runokkal, mint a táblázatos listában. A csomópontok a kerekített gyártandó darabszámot, a hiányt, valamint a szabad készletet és jobkimenetet is jelzik. A foglalásokat már levontuk.

- A **Beszerzendő anyagok** kapcsoló a tényleges alapanyaghiányokat, a **Fedezett elemek** kapcsoló a készletből vagy folyamatban lévő jobokkal fedezett komponenseket is megjeleníti. A már kész komponenshez nem építi vissza a szükségtelen alapanyagágat.
- Egy tétel mindig egyszer szerepel, több felhasználási hely esetén több nyíllal. A kártyán a teljes terv összesített mennyisége látszik, a nyíl fölé vitt egérrel pedig az adott gyártás bemeneti mennyisége olvasható.
- Kattints egy csomópontra: kiemeli a hozzá tartozó gyártási ágat, alul pedig megmutatja a mennyiségeket, jobfelosztást, bemeneteket és felhasználási helyeket. A csomópontok billentyűzettel is kijelölhetők.
- A **+ / −**, **100%** és **Teljes gráf** gombokkal nagyíthatsz. A rajz görgethető és az üres rész húzásával mozgatható. Az **Ugrás egy tételhez** listából kiválasztott elemre középre igazít és ránagyít. A **Táblázatos lista** visszavisz az eredeti gyártási nézetre.
- A **Nagy nézet** kitölti az alkalmazásablakot. A **Normál nézet** gomb vagy az Esc visszavált. A **Részletek** gomb a kiválasztott tétel adatlapjához visz.

## A foglalások használata

1. Számítsd ki a kívánt terméket és mennyiséget. A **Terv mentése és foglalás** gomb elmenti a célt, és lefoglalja a hozzá felhasznált készletet, valamint a folyamatban lévő jobokból felhasznált kimenetet.
2. Egy másik termék kiválasztásakor új tervvel számol. A mentett tervek foglalásait ebből már levonja, így a hozzájuk rendelt anyagok hiányként jelennek meg. Ugyanahhoz a termékhez külön gyártási cél az **Új terv ezzel a céllal** gombbal indítható.
3. A saját mentett tervet a **Mentett tervek → Terv megnyitása** gombbal nyisd meg. Ekkor a neki lefoglalt mennyiségek felhasználhatók. A fejléc egyértelműen mutatja, hogy mentett tervet vagy új célt nézel; az oldal újratöltése is megőrzi ezt.
4. A mennyiség módosítása előnézet. A **Terv és foglalás frissítése** gomb ugyanazt a mentést frissíti, új példány létrehozása nélkül. A korábban aktívvá tett tervek elsőbbséget kapnak; egy ilyen terv mennyiségének növelése csökkentheti a későbbi tervekhez jutó készletet.
5. A **Lefoglalt tételek** listában termékenként külön látszik a készletből és a folyamatban lévő jobokból foglalt darabszám. A **Készlet** oldalon a **Más tervek foglalása** és **Saját terv foglalása** oszlopok teszik követhetővé a levonást.
6. **Foglalás feloldása** után az anyagok azonnal más célhoz használhatók; a terv megmarad. Törléskor a foglalás is megszűnik. A **Foglalás bekapcsolása** újra aktiválja a tervet, az akkor már aktív tervek mögötti elsőbbséggel. A korábbi programváltozatban mentett tervek megmaradnak, és ezzel a gombbal aktiválhatók.

A foglalás minden számításkor az aktuális közös készletforrás, karakter- és helyszűrés, ME/TE és jobméret alapján újraszámolódik. Csak a rendelkezésre álló mennyiséget foglalja: a még hiányzó anyag beszerzési vagy gyártási igény marad. Ha elkészül egy komponens, a terv azt a komponenst foglalja, és a hozzá korábban szükséges alapanyagokat felszabadítja. A kész célterméket is védi, amíg fel nem oldod a tervet; lezárt gyártásnál ezért oldd fel a foglalást.

A foglalás a Műhely terveire vonatkozik, a játékbeli tárgyakat nem mozgatja. A BPC-runokat a 0.8.0-s verziótól példányonként lefoglalja; BPO-t és karakteres jobslotot nem foglal. A blueprintpéldányok állapotát a Blueprint oldalon ellenőrizheted. A kézi **Másra foglalva** ezen felüli, külön készletlevonás. Sikertelen EVE-frissítésnél a program nem kezeli üresként az ismeretlen készletet: előbb az adatokat kell frissíteni, vagy a készletforrást tudatosan kézire állítani.

## Fájlok, mentés és ellenőrzés

A kész indítók és ez az útmutató az EVE mappa gyökerében vannak. A forrás, receptadatbázis és tesztek: **workdir/eve_muhely**. A helyi alkalmazáspéldány és az Asztali parancsikon ezek áthelyezésétől függetlenül használható. Új programváltozat telepítésekor a helyi alkalmazáspéldányt is frissíteni kell.

A személyes készlet, beállítások, mentett tervek és titkosított belépések helye ezen a Macen:

`~/Library/Application Support/EVE Muhely/`

Ezeket nem mentjük a ProtonDrive-ba. A `muhely.sqlite3` tartalmazza a beállításokat és készletpillanatképeket; biztonsági másolatot leállított alkalmazás mellett készíts. A `characters.enc` titkosított tokenfájl kulcsa a Mac Kulcskarikájában van, ezért egyszerű fájlmásolással másik gépen nem áll helyre a belépés: ott add hozzá újra a karaktereket. Indítási hiba esetén a `server.log` és `launcher.log` segít; a program nem naplózza a hozzáférési tokeneket.

A **0.6.2-s változat 115 Python- és 7 gráfellenőrzést** tartalmaz, köztük a Salvation és Redeemer korábban ellenőrzött számításaival **2367 számérték összehasonlítását**, a készlet- és jobelszámolást, BPC-felosztást, SSO-t, helyi adatvédelmet és a több terv közötti foglalást. Ellenőrzött a saját foglalás felhasználása, feloldás/törlés, párhuzamos mentés, újraindítás, régi mentések megőrzése, valamint a kész komponensek alapanyagainak felszabadítása. A gráftesztek a közös anyagokat, a fedezett ágak levágását, a beszerzést, a kijelölést és az elrendezést ellenőrzik. A skilltesztek az ötnapos határt, üres/szünetelő sort, megszakadást, elavult adatokat, befejezéseket, új engedélyeket és a régi ipari tokenek megőrzését is ellenőrzik. A Salvation, Redeemer és Purifier gráfját, valamint a skillnézetet mintakarakterekkel böngészőben is kipróbáltuk. A valódi skilladatokhoz karakterenként külön EVE-engedélyezés szükséges.

Hivatalos háttér: [EVE SSO](https://developers.eveonline.com/docs/services/sso/), [ESI lekérdezések](https://developers.eveonline.com/docs/services/esi/best-practices/), [SDE](https://developers.eveonline.com/docs/services/static-data/).

## Bolygók és PI

A **Bolygók és PI** menü minden hozzáadott karakter kolóniáit mutatja, a gyártási karakter- és helyszűréstől függetlenül. A bolygó neve, tulajdonosa, típusa, CC-szintje és épületei mellett külön látszanak a kitermelők programjai, a gyári receptek, a raktárak és a bemeneti készletek. A **Részletek** gomb megnyitja a kolóniát; a gyártott termék nevére kattintva az egyes gyárak bemenete és puffere is látható.

Első használatkor a meglévő [EVE Developer alkalmazásodhoz](https://developers.eveonline.com/applications) add hozzá az **esi-planets.manage_planets.v1** jogosultságot. A neve ellenére a Műhely csak olvassa a PI-adatokat. A Client ID és callback változatlan. Ezután karakterenként **PI engedélyezése**, belépés ugyanazzal a karakterrel, majd **PI-adatok frissítése**. A meglévő gyártási és skillengedélyeket megőrzi. Hiányzó jogosultság vagy sikertelen lekérés szürke, ismeretlen állapotot ad; nem állítja, hogy a bolygó üres vagy leállt.

- **Piros:** a betöltött adatok szerint nincs aktív termelési jel, és például lejárt a kitermelőprogram, nincs bemenet vagy termékkimeneti útvonal.
- **Sárga:** részleges probléma, kifogyó készlet, utánpótlásfüggő gyár, hamarosan lejáró program, tele raktár vagy nem igazolható gyári futás.
- **Zöld:** a pillanatképben aktív program vagy időbélyeggel jelzett gyári ciklus látszik, és nincs észlelt probléma.
- **Szürke:** hiányzó, régi vagy nem ellenőrizhető adat.

Az ellátás a következő ciklusra és választható **1 / 6 / 24 / 72 órára** ellenőrizhető. A már tárolt készletből számított időtartam külön látható. Egy raktár közös készletét egyszer használja fel, figyelembe veszi a termékútvonalakat, a fizikai kapcsolatokat és az egyes gyárak saját bemeneti puffereit. A jövőbeli kitermelést és köztes termelést nem számolja meglévő készletnek: az ilyen ellátás utánpótlásfüggésként szerepel. Ha van anyag a bolygón, mégis hiányt jelez, ellenőrizd az útvonalakat. Az **Ellátási hiányok CSV** az adott bolygó kiválasztott időtávjához tartozó fedezeti hiányokat menti. Más bolygó készletét, későbbi importot és a linkek sávszélességét nem szimulálja.

Az új **Időalapú termelési becslés** a kolónia időpontjától számolja az eltelt gyártást, a várható leállást és az elkészülő termékeket. A köztes gyári kimenetek a beállított útvonalakon továbbjuthatnak. A kitermelők változó hozamát a CCP dokumentált képletével becsüli a program végéig, ezután csak a megmaradt anyagokból folyhat a gyártás. Külön **Csak tárolt készletből** oszlop mutatja a jövőbeli kitermelés nélküli fedezetet. A kitermelőknél a program teljes időtartama, végdátuma és hátralévő ciklusai is láthatók. A becslés nem változtatja meg a mentett ESI-pillanatképet, és az új API-lekérés nem indítja újra a fedezeti időt. Régi vagy hiányzó cikluskezdet, közös készlet miatti bizonytalan sorrend és kimeneti korlát esetén külön jelzés jelenik meg.

**EVE-korlát:** a kolónia állapotát az EVE csak a bolygó játékbeli megnyitásakor számolja újra. Ezért a kolóniaállapot és az API-lekérés időpontja is látszik. A 30 percnél régebbi gyári pillanatkép szürke, az ellátási számok dátumhoz kötött becslések. Nyisd meg a bolygót a játékban, majd frissíts a Műhelyben; a CCP körülbelül tízperces gyorsítótára késleltetheti az új adatot. A nyitott, előtérben lévő PI-nézet percenként ellenőrzi az állapotot, és a gyorsítótár lejártakor kér új adatot. Bezárt alkalmazás mellett nincs figyelés vagy külső értesítés.

A PI-ellenőrzések közös raktárakat, útvonalakat, gyári puffereket, lejárt programokat, régi adatokat, hibás API-válaszokat, jogosultságokat és több karaktert fednek le. A felületet elkülönített mintakolóniákkal is ellenőriztük. Hivatalos háttér: [CCP PI útmutató](https://developers.eveonline.com/docs/guides/pi/).

## Mentett tervek gyorsválasztója és közös beszerzés

A **Mentett tervek** oldalon külön **Személyes** és corporationönként külön **Corp** kategóriát választhatsz. Csak a kiválasztott kategóriába mentett tervek látszanak. A kategória és a felső **Gyártási kör** ugyanazt a kiválasztást mutatja: a **Terv mentése és foglalás** gomb mindig ebbe a körbe ment. Meglévő terv frissítése megtartja a kategóriáját; másik körben külön új tervet menthetsz. A foglalások személyes és corp készlet között továbbra sem keverednek.

A termékmező alatti **Mentett tervek** sor szintén csak az aktuális gyártási kör mentéseit mutatja, névvel és célmennyiséggel. Kattintással ugyanaz a mentett terv nyílik meg, saját készletfoglalásának felhasználásával. A kiválasztott mentés kiemelést kap. Új mentés vagy törlés után a sor frissül; a régi, előre beépített mintagombok eltűntek.

Az **Alapanyaghiány → Összes mentett terv** nézet a mentett célok anyaghiányait anyagonként egy sorban egyesíti. Az összesen beszerzendő mennyiség mellett tervenként is látszik a hiány. A közös készletet és a folyamatban lévő jobok kimenetét egyszer használja fel: az aktív foglalások a meglévő elsőbbségük szerint, utánuk a foglalás nélküli mentések létrehozási sorrendben kapnak készletet. A foglalás nélküli tervek is beleszámítanak, de az összesítés nem kapcsolja be a foglalásukat. A **Beszámított tervek** rész megmutatja a célokat és a sorrendet.

Az **Összesítés frissítése** újraszámol a legutóbbi helyi EVE-adatokkal; új assetekhez és jobokhoz előbb **EVE-frissítést** indíts. A közös lista másolható és CSV-be menthető. A **Kiválasztott terv** visszavált az egyedi hiányra. Az összesítés az elmentett mennyiségekkel dolgozik; a termékmezőben végzett, még nem mentett módosításokat nem tartalmazza. A kész komponensek és hajók alapanyagai itt sem kerülnek újra a hiányba.

## Átvett job és később frissülő készlet

Az EVE a jobok átvételét és a személyes készletet eltérő gyorsítótárral adhatja vissza. Ha egy szükséges anyagból már átvett job látszik, de a készletpillanatkép az átvétel előtti, a Műhely **Készletfrissítésre várunk** állapotot mutat. Kiírja az érintett karaktert, anyagot, a készlet időpontját, az átvételt és a CCP gyorsítótárának lejáratát. A lejáratig az ismételt EVE-frissítés ugyanazt az adatot adhatja.

A mentett tervek és foglalások megmaradnak. Nyitott, előtérben lévő Műhely-ablaknál a jelzett lejárat után automatikus EVE-frissítés indul; újabb próbálkozás legfeljebb percenként történik, más frissítést és nem alkalmazott kézi módosítást nem szakít meg. A lejárat nem garantálja az új adatot: ha az EVE továbbra is régi pillanatképet ad, a program az új lejáratot mutatja és tovább vár. Bezárt alkalmazás mellett nincs ilyen ellenőrzés.

Az átvett kimenetet nem adja hozzá külön a régi készlethez, mert az új pillanatképnél dupla készletet eredményezhetne. A már készletből vagy aktív jobkimenetből teljesen fedezett tétel nem indít ilyen várakozást. A friss assetadat megérkezése után a számítás a tényleges készlettel automatikusan folytatódik. Emiatt nem szükséges feloldanod vagy törölnöd a mentett tervet.

## Nagy reakciómennyiség, BPC-hiány és karakteres gyártási idő

Reakciónál legfeljebb **100 000 000 db** célmennyiség adható meg; gyártásnál a határ továbbra is 1 000 000 db. A célmennyiség, a kézi készlet és a runmezők három számjegyenként szóközt kapnak. Gépelhetsz vagy beilleszthetsz szóköz nélkül is. A termék alatti **Mentett tervek** gyorsválasztó csak megnyitja a tervet, nem másol a vágólapra; a többi itemnév másolása változatlan.

Az **Alapanyaghiány** a még elvégzendő gyártás hiányzó BPC-runjait is tartalmazza. BPO esetén a runkeret korlátlan. BPC esetén a kiválasztott ME/TE-csoport felhasználható runjait vonjuk le. Például 5 szükséges run és egy 2 runos BPC mellett **3 run** hiányzik. A darabos becslés a mellette feltüntetett run/BPC feltételezéssel értendő; eltérő másolati runméretnél változik a darabszám. BPC másolással, inventionnel vagy beszerzéssel pótolható; ezek külön jobjait, idejét és anyagait ez a lista nem tervezi. A reakcióformula nem másolható: ebből hiány esetén 1 db beszerzést jelez. Az összesített hiány készlettulajdonosonként egyszer számolja a közösen használható formulát.

A meglévő készterméket, kész komponenst és aktív gyártási job kimenetét előbb levonjuk; ezekhez nem kérünk új BPC-t. A mentett terv a ténylegesen meglévő BPC-runokat is lefoglalja. A saját terv felhasználhatja saját foglalását, más terv csak a maradékot. Feloldás vagy törlés a BPC-runkeretet is felszabadítja. A **Lefoglalt tételek** részben a másolat Item ID-ja és a lefoglalt run is látszik. Személyes és corp másolatok nem keverednek. A beszerzési CSV és a másolt lista külön jelzi a **db/run** egységet, így BPC-run nem értelmezhető nyersanyagdarabként.

A **Gyártó karakter** mező a tervvel együtt mentődik. Tervenként egy konkrét gyártó karaktert válassz: a terv minden gyártási és reakciós lépésének idejét az ő aktív skilljeivel számoljuk. Amíg nincs karakter kiválasztva, jelzett kézi becslés látszik; nem választunk helyetted automatikusan másik karaktert. Személyes gyártásnál a hozzáadott karakterek, corp gyártásnál az adott corporationhöz tartozó hozzáadott karakterek választhatók. Ez a választás az időbecslést befolyásolja; a készlet gyártási körét nem változtatja. A foglalás és a gyártási idő nem oszt ki karakteres jobslotokat, és nem ellenőrzi a karakter helyzetét vagy corp hangárjogosultságait.

Az idő az API-ban szereplő **aktív** skillszintekkel számol. Gyártásnál az **Industry** (4%/szint), az **Advanced Industry** (3%/szint) és a recepthez előírt, az SDE-ben időbónuszt adó speciális skillek külön szorzóként érvényesülnek. Reakciónál csak a **Reactions** (4%/szint) időbónusza számít. A blueprint TE és a struktúra időbónuszai továbbra is szorzódnak. Implantátumot ez a számítás nem tartalmaz. A **Gyártó / skillidő** oszlop megmutatja a karaktert; rámutatva látszanak a skillbónuszok és a hiányzó követelmények. A **Munkaóra** oszlop lépésenként mutatja az időt.

A skillekhez a **Skillek és tanulás** menüben engedélyezd és frissítsd a karakteradatokat. Ha nincs karakter kiválasztva vagy nincs róla megfelelő adat, az idő **jelzett kézi becslés**. Konkrétan kiválasztott, hiányos skillű karakter mellett figyelmeztetés jelzi, hogy a job még nem indítható. A külön **Kézi skill időszorzó** csak ilyen becslésnél vagy a kézi karakteropciónál érvényesül: az API-ból számolt skillbónuszt nem szorozzuk vele újra. A tanulási sor jövőbeli szintjeit nem feltételezzük aktívnak.

## Windows 11 64 bites kiadás

A Windows ZIP-et az **Az összes kibontása** paranccsal csomagold ki, majd a kibontott **EVE Muhely** mappában az **EVE_Muhely.exe** fájlt indítsd. A teljes mappát tartsd együtt; a fájlt ne közvetlenül a ZIP-en belül indítsd. Python, Excel és Codex telepítése nem szükséges. A műhely a saját böngésződben nyílik meg: **http://127.0.0.1:8765**. Tartalék indító: **Inditas.cmd**.

A kiadásban nincs karakter, mentett terv, saját készlet vagy belépés. Csak a nyilvános Client ID van előre megadva; mindenki a saját EVE-karaktereit engedélyezi. A saját adatok Windows alatt a **%LOCALAPPDATA%\EVE Muhely** mappába kerülnek. A tokenek titkosítási kulcsát a Windows az adott felhasználói fiókhoz védi; másik gépen vagy Windows-fiókkal új EVE-belépés kell. Frissítés előtt a bal oldali **Alkalmazás leállítása** gombot használd, utána cseréld az alkalmazás mappáját. A külön tárolt saját adatok megmaradnak.

Az **Ellenorzes.cmd** külön ideiglenes tesztprofillal ellenőrzi a Windows-titkosítást, a helyi API-t, a tervmentést és az EVE HTTPS-kapcsolatot. Saját karaktert nem ad hozzá és saját tervet nem módosít. Az összeállítás ezen a Macen történt; natív Windows 11 futtatási próba itt nem volt elérhető. A Windows-csomag nincs kiadói tanúsítvánnyal aláírva. A vírusvédelmet és a SmartScreent nem kell kikapcsolni.


### Jita-árak és anyagköltség (helyi tesztváltozat)

A holdtermelés, a gyártási terv és az alapanyaghiány oldalán az **Árazás** mezőben választható a Jita sell, buy vagy split érték. A split a vételi és eladási ár átlaga. A választás minden költségnézetre érvényes és megmarad a böngészőben.

A gyártási anyagköltség a felhasználásra kerülő meglévő anyagok értékét is tartalmazza. A hiánylista összege csak a beszerzendő mennyiségeket mutatja. Az ár nélküli tételek kimaradnak a részösszegből, és külön figyelmeztetést kapsz. A BPC-runokhoz nem használunk BPO-árat. A gyártási díjakat, a system indexet és a facility tax értékét a külön job cost számítás tartalmazza.

Az árak Jita 4-4 nyilvános piaci ajánlataiból származnak, háttérben töltődnek be. A frissítés gomb az EVE ötperces gyorsítótárát betartja. A régi árak dátuma és az árazatlan tételek száma látható. A Production by moon és Ore volume and processing táblák holdszűrőiben a felsorolt holdakból választhatsz.

A **Holdak és kitermelés → Fogyasztás** oldalon a **Fuel Block típusa** legördülőben válassz a négy blokk közül. A választás minden holdfúró költségére érvényes. A **Kézi Fuel Block egységár (ISK)** mezővel felülírhatod a blokk piaci árát; üresen visszaáll a kiválasztott Jita-árazás. Az **Üzemanyagár alkalmazása** menti a beállításokat. A Magmatic Gas továbbra is a Jita buy/sell/split választással számít. A 30 napos összeg holdanként, struktúratípusonként és összesen is látható, és a megadott bekapcsolásokat is tartalmazza.

### Job cost és késztermék-eladási érték

A **Struktúrák és bónuszok** alatt válassz gyártási rendszert a kereső találatai közül, külön a manufacturing és a reakció mezőben. Az indexet az ESI tölti be. Add meg a **Facility tax** értékét; a struktúra job cost kedvezménye, SCC és az esetleges Alpha-pótdíj is ugyanitt állítható. A **Bónuszok mentése** után a terv anyagköltségénél látható a job cost, a teljes hátralévő gyártási költség és a részletes díjbontás. Az indexek és a díjalaphoz használt adjusted price háttérben frissül, a CCP gyorsítótárát betartva.

A terv késztermékének **Jita buy** és **Jita sell** eladási értéke egyszerre látható, a teljes célmennyiségre, bruttó összegként. A megadott termékre hiányzó Jita-ajánlat `–` értéket ad. A már meglévő késztermékek miatt a hátralévő gyártás költsége és a célmennyiség teljes eladási értéke eltérő mennyiségi alapot is jelenthet.

### A holdtermelés profitja

A **Termelés Jita-értéke** panel tartalmazza az üzemanyagot és Magmatic Gas-t, a megadott bérletet és egyéb költséget, az eladási díjakat, a teljes költséget és a **Profit / 30 nap** sort. Holdanként a **Szerkesztés** alatt add meg a havi bérletet és a további költségeket; ide írható például a külön Tatara üzemanyaga, a finomítás, bányászat és szállítás költsége. Ezek nem kerülnek automatikusan becslésre.

Az eladási adót és a broker fee-t a holdak **Számítási beállítások** lapján adhatod meg. Kezdetben mindkettő 0%. Buy áron történő eladásnál nincs új eladási megbízás broker fee-je; sell és split esetén a megadott broker fee is számít. A struktúraszűrő a költséget és a profitot is szűri. A kézi Fuel Block ár mező az ezreseket automatikusan tagolja, a tizedesrészt megtartja.
