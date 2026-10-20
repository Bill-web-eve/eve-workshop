# EVE Műhely – teljes felhasználói kézikönyv

## A dokumentáció használata

A bal oldali menü alján található **Dokumentáció** a teljes kézikönyvet az alkalmazáson belül nyitja meg. A kézikönyv EVE-belépés és kiválasztott terv nélkül, internet nélkül is olvasható, ha a helyi app fut. A nyelve követi a Magyar / English választást, megjelenése a világos vagy sötét módot.

A **Tartalomjegyzékben** kattints a kívánt fejezetre. A **Keresés a kézikönyvben** a fejezetcímekben és a teljes szövegben keres; több szó együtt szűr, az ékezetek nem kötelezők. A **Keresés törlése** visszahoz minden fejezetet. A **Kézikönyv letöltése** az aktuális nyelvű teljes útmutatót Markdown-fájlként menti. A **Nyomtatás / PDF** a teljes kézikönyvet nyomtatja, a keresés miatt elrejtett fejezetekkel együtt; a böngésző nyomtatási ablakában PDF-be is mentheted.

## Felület nyelve / Interface language

A **Beállítások → Megjelenés és nyelv** oldalon válassz a **Magyar** és **English** gombokkal. A váltás azonnali, és az alkalmazásablak megjegyzi. A beírt mezők, szűrők és még nem mentett módosítások megmaradnak. A nevek és EVE-adatok változatlanok.


Az EVE Műhely helyben futó, magyar és angol nyelvű gyártástervező macOS-re és Windows 11 64 bitre. Excel és OpenAI API-előfizetés nem szükséges hozzá. A böngészős felület a saját gépeden futó alkalmazáshoz kapcsolódik.

## Saját Mac-ablak – tesztváltozat

Az új helyi Mac-tesztváltozat a saját alkalmazásablakában nyílik meg, címsor és böngészőlap nélkül. A meglévő karakterek, mentett tervek, készlet és beállítások ugyanabból a helyi profilból töltődnek be. Windowsos ablakos tesztkiadás még nincs; a korábbi Windows-kiadások böngészőben működnek.

A **Beállítások → Megjelenés és nyelv** tartalmazza a sötét módot és a Magyar / English választót. **⌘,** megnyitja ezt a részt, **⌘R** újratölti a felületet. A téma és a nyelv az appablakban külön tárolódik a korábbi böngészőtől, ezért első alkalommal válaszd ki őket. Az ablak helyzete és mérete megmarad.

Az ablak piros bezárógombja vagy a **⌘Q** a helyi Műhely-szolgáltatást is leállítja. Nem alkalmazott módosítás vagy futó EVE-frissítés esetén megerősítést kér. A mentett adatok megmaradnak. CSV-, ICS- és kézikönyv-exportnál a Mac fájlmentési ablaka nyílik meg. Az itemnevek és Multibuy-listák egyszerű szövegként kerülnek a vágólapra.

Az EVE-jóváhagyás a rendszer böngészőjében, a hivatalos EVE-oldalon történik. Sikeres belépés után a Műhely automatikusan átveszi az eredményt és visszatér a megfelelő beállításhoz. A böngésző belépési lapja ezután bezárható. A Client ID és a callback cím változatlan.

## Indítás

Az Asztalon nyisd meg az **EVE Műhely** parancsikont. Ez a helyi **~/Applications/EVE Muhely.app** alkalmazást indítja. A futáshoz szükséges programfájlok az alkalmazáson belül vannak, ezért az indítás nem függ a ProtonDrive mappa hozzáférésétől vagy szinkronizálásától. Az EVE mappában külön alkalmazáspéldány és **EVE Muhely.command** indító is található. A régebbi böngészős változat címe: http://127.0.0.1:8765.

Az indító már futó példány esetén ugyanazt az alkalmazást nyitja meg. A régebbi böngészős változatban a böngészőlap bezárása nem állítja le a műhelyt; erre a bal alsó sarokban lévő **Alkalmazás leállítása** gomb szolgál. A mentett adatok megmaradnak.

A csomagolt Mac- és Windows-kiadás tartalmazza a futtatókörnyezetet. Forrásból indításkor Python és a `cryptography` csomag szükséges; az indító ehhez saját környezetet hozhat létre, és első alkalommal interneten letöltheti a függőségeket. Külön szerver, Docker, Node.js vagy adatbázis-telepítés a normál használathoz nem kell.

## Tervezés EVE-belépés nélkül

1. Írd be a termék angol játékbeli nevét a **Termék** mezőbe, és válassz a találatok közül. A termékmező alatti gyorsválasztóban a saját mentett terveid látszanak.
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

A szűrősor alapértelmezetten csukva van. A táblázat fölötti **Szűrők megnyitása** gombbal nyithatod ki, a **Szűrők bezárása** gombbal csukhatod vissza. A becsukás nem törli a szűrést; a gomb jelzi az aktív szűrők számát. A **Karakter** oszlopban legördülő listából válassz; a holdtermelés és érctérfogat nézetek Hold oszlopában szintén listából választhatsz. A többi oszlopban szabad szöveget írhatsz. A szűrők együtt érvényesülnek, a számok ezreselválasztó nélkül is kereshetők. A **Rendezés és oszlopszűrők törlése** gomb visszaállítja az oszlopokat. A táblázat fölött látszik a megjelenített és az összes sor száma.

Az oszlopbeállítások nézetenként megmaradnak adatfrissítés és menüváltás közben; a böngészőlap újratöltése alaphelyzetbe állítja őket. A táblázat fölötti korábbi kereső az oszlopszűrőkkel együtt működik. A rendezés és szűrés a megjelenítést változtatja, a gyártási számítást és a foglalásokat nem.

## Sötét mód

A **Beállítások → Megjelenés és nyelv** oldalon a **Sötét mód** kapcsolóval válthatsz a világos és a sötét megjelenés között. Az alapbeállítás sötét. A választásodat az alkalmazásablak ezen a gépen megjegyzi, újratöltés és az alkalmazás újraindítása után is. A téma minden nézetre, a gyártási gráfra és a beviteli mezőkre is érvényes.

## Itemnév másolása

Kattints egy item nevére: a pontos angol név egyszerű szövegként a vágólapra kerül. Például a **Ferrofluid** nevére kattintva csak `Ferrofluid` másolódik, ID, darabszám és formázás nélkül. A sikeres másolást a **Másolva: Ferrofluid** üzenet jelzi. Beillesztés: ⌘V, Windowson Ctrl+V.

A funkció a gyártási tervben, az alapanyaghiányban és az összesített hiányban, a készletben, a blueprintoknál, a folyamatban lévő joboknál, a foglalásokban, a gráfon, valamint a PI- és skillnézetekben is működik. Billentyűzettel a névre lépve Enterrel is másolhatsz. A gráfelem kijelölése és a részleteket megnyitó termékgombok a másolással együtt továbbra is működnek.

## EVE-kapcsolat: egyszeri beállítás

Az EVE-kapcsolathoz Client ID és karakterenkénti bejelentkezés szükséges. A kiadásban a nyilvános Client ID már szerepelhet; ilyenkor rögtön hozzáadhatod a karaktereidet. Saját EVE Developer alkalmazáshoz az alábbi lépéseket kövesd. EVE-belépés nélkül kézi készlettel tervezhetsz.

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
7. Indíts **EVE-frissítést**. Ez a személyes asseteket, blueprinteket, ipari jobokat, valamint az engedélyezett skilladatokat, tanulási sort és PI-kolóniákat tölti le. A corporation készlethez külön corp-hozzáférést kell engedélyezni a Corporationok vagy az Adathozzáférések oldalon.
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

A **Folyamatban** menü figyelmeztet, ha van átvehető, elkészült job. Az oldalsávban számláló is jelzi. A jobot az EVE-ben kell átvenni, majd az app adatait frissíteni.

A **Folyamatban** mennyiség a gyártási és reakciós, `active`, `paused` vagy `ready` állapotú jobok **run × kimenet/run** értéke. A kutatás, másolás, invention, delivered, cancelled és reverted nem adódik hozzá. Az átvehető, még át nem vett job kimenetét továbbra is beszámítja.

Átvétel után frissíts. Az asset és job gyorsítótára eltérő időben frissülhet. Ha a program frissen átvett jobot lát egy korábbi assetpillanatkép mellett, az érintett tervvel megvárja a frissebb assetadatot. Addig ellenőrzött kézi készletértékkel folytathatod. A korábbi kézi felülírások EVE-frissítéskor is megmaradnak; a mező kiürítésével állhatsz vissza automatikus adatra.

Helyszűréshez a Struktúrák oldalon állomás- vagy struktúra-ID-ket adhatsz meg. Üres mező minden helyet beszámít. A konténerek tartalmát a felső helyszínhez rendeli, a joboknál a kimeneti helyet vizsgálja.

## Blueprintek és bónuszok

Automatikus módban az aktuális gyártási kör személyes vagy corporation blueprintjeiből olvassa az ME/TE-t és a BPC-k hátralévő runjait, **kézi készletmódban is**. A készletforrás csak az anyagok és jobkimenetek elszámolását kapcsolja. Külön oszlopban látható az összes szűrésbe tartozó **BPO- és BPC-darabszám**, a BPC-k összes runja, valamint az ME/TE-hez kiválasztott csoport **felhasználható runkerete**. A **Példányok megtekintése** gomb minden blueprint saját ME/TE-jét, hátralévő runját, helyét, karakterét, egyedi Item ID-ját és kiválasztási állapotát megmutatja. Kézi ME/TE-felülírás mellett is láthatók az eredeti EVE-példányok.

A BPO elsőbbséget kap; azon belül, illetve BPC-nél a legjobb ME, majd TE számít. Csak azonos ME/TE-jű BPC-k runjait vonja össze. BPC-példány határán új jobot kezd, így az anyagkerekítés is külön történik. Eltérő paraméterű vagy foglalt példányokra figyelmeztet. Konkrét blueprintet az egyedi Item ID-val lehet kiválasztani. Példa: két, egyenként ME 3 / TE 2 / 2 runos Salvation BPC esetén 2 BPC-t és 4 felhasználható runt mutat.

Hiányzó blueprintnél kézi, alapból ME 0 / TE 0 számítást készít, és ellenőrzési jelzést mutat. Kevés BPC-run esetén a teljes szükséglethez számol anyagot, de a runhiányt jelzi; ez nem jelenti azt, hogy minden job azonnal elindítható.

A **Run/job** szerkeszthető munkafeltételezés. Automatikus BPC-nél alapértéke legfeljebb 100 és a kiválasztott csoport leghosszabb másolatának hátralévő runja; BPO-nál vagy hiányzó blueprintnél legfeljebb 100, az SDE másolati runhatáráig. Ez nem azonos a karaktered és a játék által ténylegesen engedett jobmérettel. A kézzel mentett Run/job beállítás elsőbbséget kap. Állítsd a valóban használt jobméretre, mert az anyagkerekítés függ a felosztástól. Reakciónál az ME/TE mindig 0.

A gyártási és reakciós bónuszok a **Beállítások → Struktúrák és bónuszok** alatt szerkeszthetők. A kezdeti közös értékek:

| Tevékenység | Struktúra anyag | Rig anyag | Struktúra idő | Rig idő |
|---|---:|---:|---:|---:|
| Manufacturing | 1% | 4,2% | 30% | 42% |
| Reakció | 0% | 2,6% | 25% | 26,4% |

A bónuszok szorzódnak, és az adott tevékenység minden lépésére vonatkoznak. A kézi skill időszorzó alapból 1,00; csak kézi időbecsléshez használd. Kiválasztott, friss skilladatú karakter esetén az app az aktív skillekből számolja az időt, és nem alkalmazza újra a kézi szorzót.

## Vétel, mentés, adatok

- Bármely recepttel rendelkező köztes termék **Vételre** állítható a Blueprint oldalon. Ekkor annak saját alapanyagai eltűnnek, és maga a köztes termék kerül a beszerzési listára.
- Fuel block bemenetet alapból vásároltnak tekint, ahogy a korábbi táblázatok. Külön célterméknek kiválasztva gyártható, vagy a tervben Gyártásra állítható.
- A PI-termékek beszerzendő levelek. A PI-kolóniák külön menüben követhetők; invention és BPC-másolás külön jobjait nem tervezi. A karakterek közötti slotkiosztáshoz a külön Gyártásütemező használható. Az ISK-költségek és a jobdíjak külön becslésként jelennek meg. Az összes munkaóra a jobidők összege, nem a párhuzamos gyártás átfutási ideje.
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

Az alkalmazás frissítése előtt állítsd le a futó példányt. A külön tárolt saját adatokat ne töröld az alkalmazás mappájának cseréjekor. A vágólapra másolt listák és a CSV-exportok csak az adott pillanat számítását tartalmazzák; új gyártás vagy frissítés után készíts új exportot.

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

A termékmező alatti **Mentett tervek** sor szintén csak az aktuális gyártási kör mentéseit mutatja, névvel és célmennyiséggel. Kattintással ugyanaz a mentett terv nyílik meg, saját készletfoglalásának felhasználásával. A kiválasztott mentés kiemelést kap. Tervválasztáskor az aktuális oldalon maradsz: az ütemező, a gráf, az alapanyaghiány és a többi nézet az új tervvel frissül, nem vált vissza a Gyártási terv oldalra. Az ütemező beállításai megmaradnak; az előző terv ütemezését az új tervhez újra ki kell számolni. Nem alkalmazott módosításoknál a váltás előtt megerősítést kér. Új mentés vagy törlés után a sor frissül; a régi, előre beépített mintagombok eltűntek.

Az **Alapanyaghiány → Összes mentett terv** nézet a mentett célok anyaghiányait anyagonként egy sorban egyesíti. Az összesen beszerzendő mennyiség mellett tervenként is látszik a hiány. A közös készletet és a folyamatban lévő jobok kimenetét egyszer használja fel: az aktív foglalások a meglévő elsőbbségük szerint, utánuk a foglalás nélküli mentések létrehozási sorrendben kapnak készletet. A foglalás nélküli tervek is beleszámítanak, de az összesítés nem kapcsolja be a foglalásukat. A **Beszámított tervek** rész megmutatja a célokat és a sorrendet.

Az **Összesítés frissítése** újraszámol a legutóbbi helyi EVE-adatokkal; új assetekhez és jobokhoz előbb **EVE-frissítést** indíts. A közös lista másolható és CSV-be menthető. A **Kiválasztott terv** visszavált az egyedi hiányra. Az összesítés az elmentett mennyiségekkel dolgozik; a termékmezőben végzett, még nem mentett módosításokat nem tartalmazza. A kész komponensek és hajók alapanyagai itt sem kerülnek újra a hiányba.

## Átvett job és később frissülő készlet

Az EVE a jobok átvételét és a személyes készletet eltérő gyorsítótárral adhatja vissza. Ha egy szükséges anyagból már átvett job látszik, de a készletpillanatkép az átvétel előtti, a Műhely **Készletfrissítésre várunk** állapotot mutat. Kiírja az érintett karaktert, anyagot, a készlet időpontját, az átvételt és a CCP gyorsítótárának lejáratát. A lejáratig az ismételt EVE-frissítés ugyanazt az adatot adhatja.

A **Terv kiszámítása** gomb ilyen várakozásnál minden nézetben, az ütemezőben is látható hibaüzenetet ad. Az üzenet tartalmazza az érintett tervet és anyagokat, valamint a **legkorábbi frissítési próbálkozás** teljes dátumát, másodpercét és időzónáját a böngésző helyi idejében. A jelzett időpont után **EVE-frissítést** indíts; a Terv kiszámítása önmagában csak a helyi adatokból számol újra. Már lejárt gyorsítótárnál ezt külön jelzi. A felület nyelvváltásakor az üzenet és a dátum is nyelvet vált.

A mentett tervek és foglalások megmaradnak. Nyitott, előtérben lévő Műhely-ablaknál a jelzett lejárat után automatikus EVE-frissítés indul; újabb próbálkozás legfeljebb percenként történik, más frissítést és nem alkalmazott kézi módosítást nem szakít meg. A lejárat nem garantálja az új adatot: ha az EVE továbbra is régi pillanatképet ad, a program az új lejáratot mutatja és tovább vár. Bezárt alkalmazás mellett nincs ilyen ellenőrzés.

Az átvett kimenetet nem adja hozzá külön a régi készlethez, mert az új pillanatképnél dupla készletet eredményezhetne. A már készletből vagy aktív jobkimenetből teljesen fedezett tétel nem indít ilyen várakozást. A friss assetadat megérkezése után a számítás a tényleges készlettel automatikusan folytatódik. Emiatt nem szükséges feloldanod vagy törölnöd a mentett tervet.

## Nagy reakciómennyiség, BPC-hiány és karakteres gyártási idő

Reakciónál legfeljebb **100 000 000 db** célmennyiség adható meg; gyártásnál a határ továbbra is 1 000 000 db. A célmennyiség, a kézi készlet és a runmezők három számjegyenként szóközt kapnak. Gépelhetsz vagy beilleszthetsz szóköz nélkül is. A termék alatti **Mentett tervek** gyorsválasztó csak megnyitja a tervet, nem másol a vágólapra; a többi itemnév másolása változatlan.

Az **Alapanyaghiány** a még elvégzendő gyártás hiányzó BPC-runjait is tartalmazza. BPO esetén a runkeret korlátlan. BPC esetén a kiválasztott ME/TE-csoport felhasználható runjait vonjuk le. Például 5 szükséges run és egy 2 runos BPC mellett **3 run** hiányzik. A darabos becslés a mellette feltüntetett run/BPC feltételezéssel értendő; eltérő másolati runméretnél változik a darabszám. BPC másolással, inventionnel vagy beszerzéssel pótolható; ezek külön jobjait, idejét és anyagait ez a lista nem tervezi. A reakcióformula nem másolható: ebből hiány esetén 1 db beszerzést jelez. Az összesített hiány készlettulajdonosonként egyszer számolja a közösen használható formulát.

A meglévő készterméket, kész komponenst és aktív gyártási job kimenetét előbb levonjuk; ezekhez nem kérünk új BPC-t. A mentett terv a ténylegesen meglévő BPC-runokat is lefoglalja. A saját terv felhasználhatja saját foglalását, más terv csak a maradékot. Feloldás vagy törlés a BPC-runkeretet is felszabadítja. A **Lefoglalt tételek** részben a másolat Item ID-ja és a lefoglalt run is látszik. Személyes és corp másolatok nem keverednek. A felület és a beszerzési CSV külön jelzi a **db/run** egységet, így BPC-run nem értelmezhető nyersanyagdarabként. Az EVE Multibuy vágólaplistából a blueprintek kimaradnak.

A **Gyártó karakter** mező a tervvel együtt mentődik. Tervenként egy konkrét gyártó karaktert válassz: a terv minden gyártási és reakciós lépésének idejét az ő aktív skilljeivel számoljuk. Amíg nincs karakter kiválasztva, jelzett kézi becslés látszik; nem választunk helyetted automatikusan másik karaktert. Személyes gyártásnál a hozzáadott karakterek, corp gyártásnál az adott corporationhöz tartozó hozzáadott karakterek választhatók. Ez a választás az időbecslést befolyásolja; a készlet gyártási körét nem változtatja. A foglalás és a gyártási idő nem oszt ki karakteres jobslotokat, és nem ellenőrzi a karakter helyzetét vagy corp hangárjogosultságait.

Az idő az API-ban szereplő **aktív** skillszintekkel számol. Gyártásnál az **Industry** (4%/szint), az **Advanced Industry** (3%/szint) és a recepthez előírt, az SDE-ben időbónuszt adó speciális skillek külön szorzóként érvényesülnek. Reakciónál csak a **Reactions** (4%/szint) időbónusza számít. A blueprint TE és a struktúra időbónuszai továbbra is szorzódnak. Implantátumot ez a számítás nem tartalmaz. A **Gyártó / skillidő** oszlop megmutatja a karaktert; rámutatva látszanak a skillbónuszok és a hiányzó követelmények. A **Munkaóra** oszlop lépésenként mutatja az időt.

A skillekhez a **Skillek és tanulás** menüben engedélyezd és frissítsd a karakteradatokat. Ha nincs karakter kiválasztva vagy nincs róla megfelelő adat, az idő **jelzett kézi becslés**. Konkrétan kiválasztott, hiányos skillű karakter mellett figyelmeztetés jelzi, hogy a job még nem indítható. A külön **Kézi skill időszorzó** csak ilyen becslésnél vagy a kézi karakteropciónál érvényesül: az API-ból számolt skillbónuszt nem szorozzuk vele újra. A tanulási sor jövőbeli szintjeit nem feltételezzük aktívnak.

## Windows 11 64 bites kiadás

A Windows ZIP-et az **Az összes kibontása** paranccsal csomagold ki, majd a kibontott **EVE Muhely** mappában az **EVE_Muhely.exe** fájlt indítsd. A teljes mappát tartsd együtt; a fájlt ne közvetlenül a ZIP-en belül indítsd. Python, Excel és Codex telepítése nem szükséges. A műhely a saját böngésződben nyílik meg: **http://127.0.0.1:8765**. Tartalék indító: **Inditas.cmd**.

A kiadásban nincs karakter, mentett terv, saját készlet vagy belépés. Csak a nyilvános Client ID van előre megadva; mindenki a saját EVE-karaktereit engedélyezi. A saját adatok Windows alatt a **%LOCALAPPDATA%\EVE Muhely** mappába kerülnek. A tokenek titkosítási kulcsát a Windows az adott felhasználói fiókhoz védi; másik gépen vagy Windows-fiókkal új EVE-belépés kell. Frissítés előtt a bal oldali **Alkalmazás leállítása** gombot használd, utána cseréld az alkalmazás mappáját. A külön tárolt saját adatok megmaradnak.

Az **Ellenorzes.cmd** külön ideiglenes tesztprofillal ellenőrzi a Windows-titkosítást, a helyi API-t, a tervmentést és az EVE HTTPS-kapcsolatot. Saját karaktert nem ad hozzá és saját tervet nem módosít. Az összeállítás ezen a Macen történt; natív Windows 11 futtatási próba itt nem volt elérhető. A Windows-csomag nincs kiadói tanúsítvánnyal aláírva. A vírusvédelmet és a SmartScreent nem kell kikapcsolni.


## Jita-árak és anyagköltség

A holdtermelés, a gyártási terv és az alapanyaghiány oldalán az **Árazás** mezőben választható a Jita sell, buy vagy split érték. A split a vételi és eladási ár átlaga. A választás minden költségnézetre érvényes és megmarad a böngészőben.

A gyártási anyagköltség a felhasználásra kerülő meglévő anyagok értékét is tartalmazza. A hiánylista összege csak a beszerzendő mennyiségeket mutatja. Az ár nélküli tételek kimaradnak a részösszegből, és külön figyelmeztetést kapsz. A BPC-runokhoz nem használunk BPO-árat. A gyártási díjakat, a system indexet és a facility tax értékét a külön job cost számítás tartalmazza.

Az árak Jita 4-4 nyilvános piaci ajánlataiból származnak, háttérben töltődnek be. A frissítés gomb az EVE ötperces gyorsítótárát betartja. A régi árak dátuma és az árazatlan tételek száma látható. A Production by moon és Ore volume and processing táblák holdszűrőiben a felsorolt holdakból választhatsz.

A **Holdak és kitermelés → Fogyasztás** oldalon a **Fuel Block típusa** legördülőben válassz a négy blokk közül. A választás minden holdfúró költségére érvényes. A **Kézi Fuel Block egységár (ISK)** mezővel felülírhatod a blokk piaci árát; üresen visszaáll a kiválasztott Jita-árazás. Az **Üzemanyagár alkalmazása** menti a beállításokat. A Magmatic Gas továbbra is a Jita buy/sell/split választással számít. A 30 napos összeg holdanként, struktúratípusonként és összesen is látható, és a megadott bekapcsolásokat is tartalmazza.

## Job cost és késztermék-eladási érték

A **Struktúrák és bónuszok** alatt válassz gyártási rendszert a kereső találatai közül, külön a manufacturing és a reakció mezőben. Az indexet az ESI tölti be. Add meg a **Facility tax** értékét; a struktúra job cost kedvezménye, SCC és az esetleges Alpha-pótdíj is ugyanitt állítható. A **Bónuszok mentése** után a terv anyagköltségénél látható a job cost, a teljes hátralévő gyártási költség és a részletes díjbontás. Az indexek és a díjalaphoz használt adjusted price háttérben frissül, a CCP gyorsítótárát betartva.

A terv késztermékének **Jita buy** és **Jita sell** eladási értéke egyszerre látható, a teljes célmennyiségre, bruttó összegként. A megadott termékre hiányzó Jita-ajánlat `–` értéket ad. A már meglévő késztermékek miatt a hátralévő gyártás költsége és a célmennyiség teljes eladási értéke eltérő mennyiségi alapot is jelenthet.

## A holdtermelés profitja

A **Termelés Jita-értéke** panel tartalmazza az üzemanyagot és Magmatic Gas-t, a megadott bérletet és egyéb költséget, az eladási díjakat, a teljes költséget és a **Profit / 30 nap** sort. Holdanként a **Szerkesztés** alatt add meg a havi bérletet és a további költségeket; ide írható például a külön Tatara üzemanyaga, a finomítás, bányászat és szállítás költsége. Ezek nem kerülnek automatikusan becslésre.

Az eladási adót és a broker fee-t a holdak **Számítási beállítások** lapján adhatod meg. Kezdetben mindkettő 0%. Buy áron történő eladásnál nincs új eladási megbízás broker fee-je; sell és split esetén a megadott broker fee is számít. A struktúraszűrő a költséget és a profitot is szűri. A kézi Fuel Block ár mező az ezreseket automatikusan tagolja, a tizedesrészt megtartja.

## Holdnyilvántartás és 30 napos termelés

Nyisd le a **Moon management / Holdak és kitermelés** menüt. A **Holdnyilvántartás** alatt új holdat vihetsz fel, a meglévőket szerkesztheted vagy törölheted.

1. A rendszermezőbe gépelj nevet, és válassz a szűkülő találati listából. Az app a rendszerhez tartozó constellationt és alapadatokat ESI-ből rendeli hozzá és gyorsítótárazza.
2. Válaszd ki a holdat és a fúrót: **Athanor** vagy **Metenox**. Holdanként legfeljebb négy különböző ércet választhatsz a listából; kevesebb érc is megadható. Minden érc mellé adj százalékos arányt.
3. A százalékok összegét ellenőrizd. A 100% fölötti összetétel hibás, nem kerül a termelésbe. A 100% alatti adat részleges: csak a megadott ércek mennyiségét számítja, a hiányzó részt nem osztja szét. Az app nem javítja ki automatikusan a kézzel beírt arányokat.
4. A működést, a bekapcsolások számát, az ércmező becsült élettartamát, a 30 napos bérletet és egyéb költségeket is megadhatod. A kikapcsolt hold termelése és folyamatos fogyasztása kimarad. Mentés után az összesítések frissülnek.

A **30 napos termelés** 720 órára becsül érctérfogatot és feldolgozott alapanyagokat. Holdanként és összesítve is megmutatja az eredményt; választhatsz összes, Athanor vagy Metenox bontást. A **Production by moon** és **Ore volume and processing** Hold oszlopa választható listával szűrhető. Az anyagtáblázat sorvégi értéke a kiválasztott Jita buy, sell vagy split árral számol.

Athanornál az app nullsec Tatarával, T2 moon-ore riggel és maximális finomítási skillekkel számol. Az implant a **Beállítások → Holdak számítási beállításai** alatt változtatható, alapból 4%; ugyanitt a bányászati visszanyerési arány is megadható. A kijelzett Tatara-kihozatal a feldolgozási szorzó. Metenoxnál saját kitermelési hatásfok és ciklusonkénti lefelé kerekítés érvényesül; csak a holdanyagokat adja hozzá, a normál ásványokat nem. Az ércreceptek és a gépi paraméterek a mellékelt katalógusból származnak.

A 30 napos adat becslés, nem a bányászott és elszállított tényleges készlet. Az ESI-ből érkező friss, azonosítható összetétel módosíthatja az Athanor számításban használt arányokat; az eredeti kézi értékek megmaradnak. Az adatok forrása mindenhol jelölt.

## Holdak fogyasztása

A **Fogyasztás** az Athanorok és Metenoxok 30 napos Fuel Block-igényét, a Metenox Magmatic Gas-fogyasztását és a megadott bekapcsolások egyszeri üzemanyagát mutatja. Holdanként, fúrótípusonként és együtt is láthatók a mennyiségek és ISK-értékek. A Fuel Block típusa választható, egységára kézzel felülírható; üres felülírásnál a Jita-árazás érvényesül. A külön Tatara és más szolgáltatások üzemanyaga nem része ennek a fúrófogyasztásnak; saját költségként adhatod meg.

## Kitermelési naptár és ESI-ércmennyiségek

A **Kitermelési naptár** az azonosított holdak kitermelési időpontjait mutatja. A naptár fölötti **Kitermelések és várható ércek** listából vagy egy naptáreseményből megnyithatók a részletek: hold, megérkezés, automatikus széttörés, összes és ércenkénti m³, forrás, frissesség és becsült eltűnés. Ha egy működő Athanorhoz nincs hozzáférhető kitermelés, figyelmeztetés jelenik meg; ez azt jelenti, hogy az appban nincs adat róla, nem bizonyítja, hogy a játékban sincs fúrás.

A **Beállítások → Adathozzáférések → Holdadatok hozzáférése** alatt engedélyezd a megfelelő karaktereket, majd frissíts holdadatot. Szükséges scope-ok: **esi-calendar.read_calendar_events.v1**, **esi-industry.read_corporation_mining.v1**, **esi-characters.read_notifications.v1**. Ezeket saját Client ID használatakor az EVE Developer alkalmazásban is engedélyezni kell. Az értesítésekhez olyan karaktert válassz, aki az EVE-ben megkapja a holdkitermelési értesítéseket. A corporation időzítőkhöz a fúró tulajdonos corporationjében megfelelő, Station Manager szerepkör kell. Más corporationtől bérelt fúró időzítője ettől még nem feltétlenül látszik.

A karakter **holdkitermelési értesítése** az ércadatok elsődleges forrása. Ha friss és azonosítható ércenkénti térfogatot tartalmaz, az app ebből számolja az arányokat, és **ESI-értesítés** forrást jelez. Egyértelmű naptárszöveg is lehet forrás. A corporation időzítő önmagában nem tartalmaz ércösszetételt: időtartamából becsült térfogat kézi arányokkal szerepel. Hiányos, régi vagy nem értelmezhető ércadat nem írja felül a kézi összetételt.

Az eltűnés becslés: a megfigyelt széttöréshez vagy a lehetséges széttörési időkhöz adja a holdnál megadott élettartamot. Ismeretlen széttörésnél tartomány vagy ismeretlen érték látható. Ez nem garantált ESI-lejárati adat. A naptár táblázatai UTC-t jelölnek; a helyi naptárfeliratkozás a naptáralkalmazás időzónáját használja.

## Bányászkristályok

A **Bányászkristályok** nézetben válassz holdat. Az app az adott kitermelés ércmennyiségeit használja, ha van hozzá használható adat; máskülönben a 30 napos holdbecslést. Az azonos kristályt használó érceket összevonja, majd a térfogatokból arányt készít. A kristályváltozat a holdszámítási beállításokban váltható. Metenoxhoz nem kell kristály.

Az arány minden tagja **1–9 közötti egész**, felfelé kerekített közelítés. A 75% és 25% megoszlás például **3 : 1**. A tábla megmutatja a kristály nevét, az érceket, térfogatukat és részesedésüket. Ez az összetételhez arányos készletjavaslat; nem veszi figyelembe a kopást, a lézerek számát vagy kihozatalát, és nem a teljes bányászathoz elfogyó darabszámot jelenti.

## Holdkitermelések a helyi naptárban

A **Moon management / Holdak és kitermelés** menü a bal oldali sávban lenyitható. Az almenükből közvetlenül megnyitható a holdnyilvántartás, a 30 napos termelés, a fogyasztás, a kitermelési naptár és a kristályterv.

A **Beállítások → Naptárszinkron → Helyi naptár szinkronizálása** részben engedélyezd a naptárszinkront, majd válaszd a **Feliratkozás a helyi naptárban** gombot. Macen a Naptár alkalmazásban a **Saját Mac / On My Mac** helyet és az óránkénti automatikus frissítést válaszd. Kézzel is feliratkozhatsz a kimásolható URL-re. A működés az Apple naptárfeliratkozási lehetőségét használja: https://support.apple.com/en-ie/102301

A naptár a működő Athanorok már betöltött kitermeléseit tartalmazza, a hold nevével és a kőzet megérkezési idejével; a leírásban az ismert ércmennyiségekkel és a becsült eltűnési adatokkal. A kliens helyi időzónában mutatja az időpontot. Az esemény egy időpontjelölő, nem bányászati időtartam. Az app és az EVE-frissítés továbbra is szükséges az új adatokhoz. A naptár lekérdezése nem indít külön ESI-frissítést.

A feliratkozás csak ezen a gépen működik, futó app mellett. Felhős naptárszolgáltatás és másik eszköz nem éri el a localhost címet. A naptár csak olvasható; nem módosítja az EVE-adatokat. Az **Új hivatkozás** érvényteleníti a régit, ezért új feliratkozás kell; a **Szinkronizálás letiltása** megszünteti a hozzáférést. A már letöltött eseményeket a naptáralkalmazásból külön kell eltávolítani.

Az **ICS letöltése** egy egyszer importálható fájlt ad. Ez nem frissül automatikusan; ismételt importáláskor a naptárkliens duplikálhat eseményeket. A feliratkozás ajánlott a folyamatos frissítéshez.

## Lekérések és folyamatjelző

Lekérés vagy számítás közben a felső sávban megjelenik az aktív műveletek száma, a jobb alsó sarokban pedig a részletes állapotpanel. Nézetváltás és görgetés közben is látható. A **Kis méret** gomb összecsukja; a felső állapotgombbal újra kinyitható.

Az EVE-adatellenőrzés az aktuális szakaszt, karaktert vagy corporationt, az ellenőrzött tételek számát, az adatfajtát és a lapozás állását mutatja. Külön jelzi az érvényes EVE-gyorsítótár használatát és a szerver válaszára várakozást. A Jita-árak és az ipari költségadatok saját haladási sort kapnak. A tervszámítások, keresések, mentések és más lekérések is megjelennek.

A haladási sáv ismert tétel- vagy oldalszámot követ; ismeretlen teljes mennyiségnél mozgó jelzés látszik. Az **eltelt idő** nem várható befejezési idő. Párhuzamos műveletek külön sorban szerepelnek. A háttérfrissítés elindításának visszaigazolása még nem jelenti a frissítés befejezését.

A végén **Elkészült**, **Figyelmeztetés** vagy **Sikertelen** állapot jelenik meg. Egyes karakterek vagy adatfajták hibája részleges eredményként látható. Ha maga az állapotlekérés nem érhető el, a panel ezt jelzi és újrapróbálja; nem állítja, hogy a folyamat elkészült. A feliratok a választott magyar/angol nyelvet követik.

## Értesítések és macOS-jelzések

A bal oldali **Értesítések** menü összegyűjti a nem tanuló és az 5 napon belül kiürülő sorú karaktereket, az átvehető jobokat, a leállt PI-termelést és a következő **3 napban** esedékes holdkitermeléseket. A jelzésből megnyitható a hozzá tartozó nézet. Az oldalsáv száma a megbízható aktuális jelzések számát mutatja; a kérdőjel ellenőrizendő adatot jelez.

A **Személyes** fülön a személyes jobok, a karakterek tanulása és PI-bolygói látszanak. A **Corp** fülön corporationenként szűrhetők a corp jobok és a hozzájuk rendelt holdak. A corp job nem szerepel másodszor a személyes listán. A tanulás és a PI karakteradat, ezért a Személyes fülön marad. A jogosultság nélküli, lejárt vagy hibás adat külön **Ellenőrizendő adatok** jelzés, és nem küld rendszerértesítést. Az Alpha-, MCT- vagy kézi tanulásihely-beállítás miatt kizárt karakterek nem kapnak indokolatlan „Nem tanul” jelzést.

Az EVE által átvehetőnek jelzett jobot és az időpont alapján várhatóan elkészült jobot külön megjelöljük. A PI-leállás dátumhoz kötött előrejelzése becslésként szerepel. Az értesítés nem vesz át jobot, nem indít termelést, és nem változtat a készleten.

A **Beállítások → Értesítések** alatt válaszd a **Rendszerértesítések engedélyezése** gombot, majd hagyd jóvá a macOS kérését. A **Tesztértesítés** gombbal ellenőrizheted a megjelenést. Itt kapcsolhatod a személyes/corp és típusonkénti jelzéseket, módosíthatod a holdelőrejelzést 1–30 napra, valamint engedélyezheted az EVE-adatok 4 percenkénti háttérellenőrzését. A CCP gyorsítótárát figyelembe vesszük. Az **EVE-adatok ellenőrzése** gomb kézzel is elindítja a frissítést.

A hold tulajdonosát az ESI corporation-időzítője azonosítja. Ismeretlen tulajdonosnál a hold a Személyes fülön marad, ezt felirat jelzi. A **Holdak értesítési tulajdonosa** táblázatban választhatsz automatikus, személyes vagy konkrét corporation-hozzárendelést. Ez csak az értesítési besorolást módosítja.

Ugyanazt az eseményt egy aktív időszakban egyszer küldjük; az újraindítás vagy ismételt frissítés nem ismétli meg. Több egyidejű jelzést tulajdonosonként és típusonként összevonunk. A rendszerértesítésre kattintva a megfelelő fül és típus nyílik meg. A macOS Fókusz módja és értesítési beállításai módosíthatják a megjelenést.

**Az alkalmazásnak futnia kell**, háttérben is működik. Bezárt alkalmazás mellett nincs új EVE-ellenőrzés és nincs új rendszerértesítés. A rendszerértesítések a helyi macOS-ablakos változatban érhetők el; a böngészős nézetben az értesítési lista használható.

## Közös beállítások

A bal oldali **Settings / Beállítások** menü lenyitható, és az alábbi részeket fogja össze:

- **Structures and bonuses / Struktúrák és bónuszok:** gyártás és reakció bónuszai, rendszer, adók, készletforrás, receptadatbázis.
- **EVE connection / EVE-kapcsolat:** Client ID, karakterek hozzáadása, kiválasztása és eltávolítása.
- **Data access / Adathozzáférések:** karakterenkénti skill-, PI-, corporation- és holdadatengedélyek, scope-ok, frissítési lehetőségek.
- **Moon calculation settings / Holdak számítási beállításai:** finomítás, implant, kristályváltozat, üzemanyagtípus, kézi üzemanyagár és gazdasági paraméterek.
- **Calendar sync / Naptárszinkron:** helyi naptárfeliratkozás és ICS-letöltés. A meglévő feliratkozások változatlanul működnek.
- **Accounts and training / Accountok és tanulás:** accountcsoportok, Omega- és MCT-lejáratok, tanulási helyek.
- **Notifications / Értesítések:** rendszerengedély, jelzéstípusok, háttérfrissítés, holdelőrejelzés és holdak értesítési tulajdonosa.

A műveleti nézeteken a hozzáférési és beállítási panelek helyett rövid hivatkozások mutatnak az új helyre. Az EVE-engedélyezés után a megfelelő Beállítások lap nyílik meg. A még nem mentett értékekre lapváltáskor figyelmeztetünk.

A Mining crystals / Bányászkristályok nézet nem mutat Tatara-kihozatalt. A kristályarány minden tagja 1–9 közötti egész szám. Az azonos kristályt igénylő érceket előbb összevonjuk. A legkisebb pontos arányt megtartjuk, ha minden tagja legfeljebb 9 (75:25 → 3:1). Egyébként a legnagyobb tagot 9-re skálázzuk, minden tagot felfelé kerekítünk, majd a közös osztóval egyszerűsítünk (99,99:0,01 → 9:1; 37,3:62,7 → 2:3). Ez közelítő készletarány, nem kopásból számolt tényleges fogyasztás; egyetlen szükséges kristálytípus sem tűnik el nullára kerekítés miatt.

## EVE Multibuy lista

A Material shortfall / Alapanyaghiány oldalon a kiválasztott és az összesített lista másolása EVE Multibuy formátumot használ: soronként az angol itemnév, tabulátor és tagolatlan egész mennyiség. Nincs fejléc vagy mértékegység. A BPO-k, BPC-k, hiányzó BPC-runok és reakcióformulák kimaradnak a vágólapról; a felületen továbbra is külön követhetők. Az azonos anyagok mennyisége összeadódik.

## Accountok, Omega és MCT

A **Settings → Accounts and training / Beállítások → Accountok és tanulás** alatt adj meg egy saját accountnevet, az Omega állapotát és lejáratát, illetve a két MCT-hely lejáratát. Az ESI nem szolgáltat accountazonosítót, Omega- vagy MCT-lejáratot, ezért ezek kézi adatok. Nem kérünk fióknevet, jelszót vagy előfizetéshez hozzáférést. CCP-tájékoztató: https://developers.eveonline.com/blog/caution-accountstatus-xml-aspx-deprecated-and-unreliable

Accountonként legfeljebb három hozzáadott karakter csoportosítható. A tanulási hely lehet automatikus, alaphely, MCT 1, MCT 2 vagy kézzel kizárt. A lejárt MCT-helyre rendelt, a más karakterek által elfoglalt hely miatt nem tanítható, illetve a kézzel kizárt karakter nem kap „nem tanul” riasztást. Az ismeretlen jogosultságot nem tekintjük automatikusan tiltottnak. Alpha státusz önmagában nem tiltja a tanulást; a legalább 5 millió betöltött SP-t is vizsgáljuk.

A Skillek és tanulás nézetben az összes megadott lejárat megtekinthető, a lejárt és 5 napon belül lejáró időpontok külön jelzést kapnak. A konkrét tanulási hely lejárata az aktív sor folytonosságának becslését is korlátozza. Az adatok frissítése nem hosszabbítja meg a kézzel beírt előfizetési dátumokat; megújításkor ezeket is módosítani kell. MCT-információ: https://support.eveonline.com/hc/en-us/articles/203411052-Multiple-Character-Training

## Gyártásütemező

A **Production scheduler / Gyártásütemező** a felül kiválasztott termékhez, célmennyiséghez és személyes vagy corp gyártási körhöz készít kézzel indítható jobtervet. Válaszd ki a bevonható karaktereket, majd nyomd meg a Calculate schedule / Ütemterv kiszámítása gombot.

- A gyártási slotkeret: 1 + aktív Mass Production + aktív Advanced Mass Production. A reakcióké külön: 1 + Mass Reactions + Advanced Mass Reactions. A tudományos jobok nem foglalnak gyártási slotot, de a bennük használt blueprintet igen. Az app a karakterek személyes és az összes betöltött corporation jobját együtt, Job ID alapján egyszer számolja. Az elavult/hibás skilladatot, valamint a hiányzó vagy egy napnál régebbi jobadatot frissíteni kell.
- Csak a recept közvetlen aktív skillkövetelményeit teljesítő karakter kap munkát. A gyártási időben az ő skilljei, a blueprint TE-je és az aktuális struktúrabónuszok szerepelnek. A tanulásfigyelésből kizárt karakter industry slotjai továbbra is használhatók. Slotmechanika: https://support.eveonline.com/hc/en-us/articles/203210272-Activities-and-Job-Types
- A **Use only owned BPOs/BPCs / Csak a meglévő BPO/BPC készlettel** módban tényleges, a kiválasztott ME/TE-vel egyező assetpéldányok kellenek. A kézi runkeret nem helyettesít fizikai blueprintet. A más tervek által lefoglalt BPC-runokat és a futó jobokba kötött runokat levonjuk. Ugyanazt a példányt nem használjuk két egyidejű jobhoz. A BPC-k eltérő ME/TE-csoportjait nem vonjuk össze; a Blueprint oldalon választható másik csoport.
- Ha a meglévő készletre korlátozás ki van kapcsolva, a gyorsabb párhuzamos munkához további BPC-ket vagy reakcióformulákat is tervezhet. A szükséges példányszámot, runokat és feltételezett run/BPC értéket külön táblázat mutatja. A beszerzés vagy másolás/invention ideje az általad megadott új-blueprint-érkezés; ezeket a külön kutatási jobokat nem indítjuk vagy ütemezzük.
- A személyes blueprinteket alapból csak a tulajdonos karakter használja. A karakterek közötti átadás külön engedélyezhető, és az érintett jobok megjelölést kapnak. Corp terv kizárólag az adott corporation készletével, blueprintjeivel és tagkaraktereivel számol; a szükséges corp indítási és hangárjogosultságokat biztosítottnak tekinti.
- Meglévő készlet azonnal, folyamatban készülő termék csak a hozzá tartozó job befejezésekor használható. A kézi folyamatban mennyiség érkezési dátum nélkül megakasztja az érintett sort; ilyenkor az ütemterv részleges. Vásárolandó anyagok és új blueprintek a megadott anyagérkezéskor érkeznek, üres mező esetén a kezdésre.
- Az anyagok felhasználása egyszer történik meg, a gyártási függőségek figyelembevételével. Több jobfelosztást hasonlítunk össze, és a rövidebb teljes megoldást választjuk. Ez heurisztikus becslés, nem garantált matematikai optimum. A jobok azonnali átvételét, azonnali árumozgatást és aktuális slotadatokat feltételez. A megadott Omega-idő után új jobot csak frissített aktív skillekkel/megújított dátummal tervez.
- Az új jobfelosztás anyagkerekítése különbséget okozhat az eredeti tervhez képest: az ütemező saját, újraszámolt anyaghiányát is megmutatja, Multibuy-másolással. A mentett terv foglalását nem módosítja. Az ütemterv CSV-be menthető; egyszerre legfeljebb 10 000 job tervezhető. A felület 100 jobot mutat oldalanként.

Az ütemező nem indít vagy módosít EVE-jobot, és a készletet sem írja át. Ha új jobot indítasz vagy átveszel az EVE-ben, frissítsd az EVE-adatokat, majd készíts új ütemtervet.

### Reakciók, gyártás és anyagfüggőségek

Az ütemező külön **Reaction schedule / Reakciók ütemterve** és **Manufacturing schedule / Gyártás ütemterve** táblázatot mutat. A reakció és a gyártás ugyanannál a karakternél is párhuzamosan futhat, ha az anyagok és a megfelelő blueprintek rendelkezésre állnak. A külön slotkeretek nem foglalják egymást.

A **Schedule graph and timeline / Ütemezési gráf és idővonal** közös időtengelyen, karakterenként és tevékenységenként külön sávokon mutatja a jobokat. Kattints egy sávra vagy a táblázat Job-számára: az alatta megjelenő lista megmutatja minden bemenet mennyiségét, forrását és érkezését. A forrás vagy felhasználó Job-számával másik oldalra is át lehet ugrani. A gráf és a két táblázat külön lapozható, 100 jobos oldalakon.

Egy bemenet csak egyszer költhető el, a következő job pedig csak az összes szükséges mennyiség megérkezése után indul. Készlet, beszerzés, meglévő folyamatban lévő munka és az újonnan ütemezett jobok kimenete külön forrásként látszik. Az anyag rendelkezésre állása után még a slotra vagy a blueprintre is várhat a job.

A **Production material cost** összesítésében a célmennyiség teljes eladási értéke mellett külön **Sell price per unit · Jita sell** sor mutatja a késztermék darabonkénti Jita sell árát. Ez nem változik az anyagár módjával vagy a célmennyiséggel.

### Folyamatban lévő jobok az idővonalon

Az idővonal a betöltött EVE-adatokban **active** állapotú, még futó gyártási és reakciós jobokat is mutatja, ha a kiválasztott terv valamely termékét állítják elő, és a kiválasztott karakterekhez, készlettulajdonoshoz és helyszűréshez tartoznak. A zöld, szaggatott keret, az **EVE** felirat és a **Folyamatban az EVE-ben** jelölés különbözteti meg őket az újonnan tervezett munkáktól. Saját EVE-sávban jelennek meg; nem adódnak hozzá ismét a tervezett runokhoz, a beszerzéshez vagy a CSV új jobjaihoz.

Kijelölve látható az eredeti EVE Job ID, a karakter, a kezdés és befejezés, a run és kimenet, a dátumokból becsült előrehaladás, valamint a jobpillanatkép ideje. A korábbi EVE-adat szürke jelölést kap. Ha közben letelik a befejezési idő, **Várhatóan elkészült** jelzésre vált; a tényleges állapothoz EVE-frissítés és új ütemezés szükséges. Egy tervezett jobot az app nem jelöl futónak csak azért, mert elérkezett a számolt kezdése. Szüneteltetett, átvehető és átvett job nem jelenik meg futóként.

Az ütemezőben a tervválasztó és az ütemezési beállítások széles ablakban két kompakt, egymás melletti blokkban jelennek meg, kisebb ablakban egymás alá kerülnek. Az **Ütemezési tudnivalók** lenyitható súgó tartalmazza a minimum jobhossz és az anyagérkezés magyarázatát.

### Az idővonalon látható napok

A **Schedule graph and timeline / Ütemezési gráf és idővonal** panel **Látható napok** mezőjében 1–3650 közötti egész számot adhatsz meg. Alapból legfeljebb **7 nap** látszik egyszerre. A böngésző megjegyzi a napok számát. Üres mező vagy a **Teljes időtáv** gomb az egész ütemtervet mutatja.

Az **Előző időszak / Következő időszak** gombok a kiválasztott számú, 24 órás napokból álló időablakok között lépnek. Az utolsó időszak rövidebb lehet, ha a terv előbb véget ér. A dátumtartomány és az időszakszámláló jelzi, hol jársz. Az ablakon átnyúló job minden érintett időszakban látszik, csak a sáv látható része rajzolódik ki; a részletek és a felugró szöveg a teljes jobidőt mutatják.

A karakterszűrő ugyanarra az időablakra vonatkozik. A 100 jobos lapozás az adott időszakban és a kiválasztott karakterhez látható munkákat lapozza; nem az időszakot váltja. Másik időszakban lévő jobra kattintva az idővonal automatikusan odaugrik. Új ütemezés a terv első időszakán kezdődik. A napok száma nem módosítja a gyártási időket, a minimum jobhosszt, az anyagfüggőségeket, a táblázatokat vagy a CSV-exportot.

A **Schedule graph and timeline** karakterválasztó listájával az összes karakter vagy egyetlen karakter munkái jeleníthetők meg. A szűrés az idővonalra vonatkozik; az ütemezést és a táblázatokat nem módosítja. A lapozás a kiválasztott karakter és időszak jobjaihoz igazodik; az időtengely a karakterek között azonos marad. Másik karakter jobjára ugorva a szűrő automatikusan követi a kiválasztást.

Az ütemező összevonja az azonos karakteren, sloton és ugyanazzal a formulával közvetlenül egymás után futó reakciókat, ha minden bemenet már az első induláskor elérhető, és az összevonás miatt egyetlen felhasználó job sem indulna később. Kikapcsolt minimum jobhossznál megtartja a beállított run/job korlátot; a maximális jobidőt mindig betartja. Az összevont job tényleges anyagigényét újrakerekíti, az anyaghiányt és a jobfüggőségeket is ehhez igazítja. A korai részeredményért vagy későbbi anyagérkezés miatt szükséges rövid jobok megmaradnak.


### Minimum jobhossz

A **Minimum job duration (hours) / Minimum jobhossz (óra)** alapértéke 12 óra, és a böngésző megjegyzi a beállítást. A minimum a gyártásra és a reakciókra is vonatkozik, a karakter skilljeivel, TE-vel és struktúrabónuszokkal számolt tényleges futásidő alapján. Szükség esetén növeli a szokásos Run/job felosztást, és kiegyenlíti a jobméreteket a rövid maradékok elkerülésére. A 0 érték kikapcsolja a minimumot.

Két job közé nem kerül kötelező várakozás: amint az anyagok, a slot és a blueprint elérhetők, a következő indulhat. A hiányzó mennyiségen felül nem gyártunk csak a minimum eléréséért. A BPC-runok, a recept runkorlátja és a maximális jobidő továbbra is korlátoz; az elkerülhetetlenül rövidebb jobok külön jelölést kapnak.


## Gyakori helyzetek és hibaelhárítás

- **Üres gyártási lista:** nézd meg a késztermék-összesítést: a készlet vagy a folyamatban lévő jobok teljesen fedezhetik a célt. Ellenőrizd a kiválasztott gyártási kört, a saját és más tervek foglalását, illetve a kézi felülírásokat. További új késztermék gyártásához a megtartandó meglévő darabokat a Másra foglalva mezővel tedd félre.
- **Kész komponens alapanyaga újra hiányzik:** ellenőrizd a készletforrást, a karakter- és helyszűrést, a corp/személyes kört, a más tervhez foglalást és az asset időpontját. A terv a ténylegesen felhasználható komponenst vonja le, a más célhoz félretettet nem.
- **Ismételt frissítés után is régi adatok:** a CCP gyorsítótárának lejáratáig azonos pillanatkép érkezhet. Átvett jobnál várd meg a kijelzett új készletet, vagy használj ellenőrzött kézi felülírást. A foglalást nem szükséges törölni.
- **invalid_scope vagy nincs jogosultság:** a kért scope legyen engedélyezve az EVE Developer alkalmazásban is, majd a megfelelő karaktert az Adathozzáférések alatt engedélyezd újra. Corporationadatokhoz a játékbeli szerepkör is kell. Jelszót és Client Secretet ne írj a Műhelybe.
- **Nem készül teljes ütemterv:** nézd meg a Nem ütemezhető tételek és a Karakterek ipari kapacitása táblát. Ellenőrizd az aktív skilleket, a friss jobadatot, a fizikai blueprinteket, az Omega dátumát és az anyagok érkezését. A részleges ütemterv nem jelenti azt, hogy a teljes cél fedezett.
- **Felületi frissítés:** helyi programfrissítés után töltsd újra a lapot (Mac: ⌘R, Windows: Ctrl+R), majd számold újra a tervet vagy ütemezést. Az app leállításához az oldalsáv alján lévő gombot használd; a böngészőlap bezárása nem elegendő.
