# EVE Műhely – teljes felhasználói kézikönyv

A kitermelési naptár a „Moon extraction for …” EVE-esemény leírásából kiolvasott holdazonosító alapján párosít. Csak a nyilvántartásba már felvett Athanor-holdak szerepelnek; idegen holdat nem vesz fel automatikusan. Üzemanyag- és egyéb naptárriasztások nem számítanak kitermelésnek. A naptárbejegyzés időpontot adhat ércmennyiség nélkül is; ettől a mennyiség nem lesz nulla vagy automatikusan ismert. Az app UTC-t mutat, az ICS-előfizetés helyi időzónát használ.

A holdadat-frissítés külön összesíti a sikeres naptár-, értesítés- és corporationidőzítő-olvasókat. A még nem engedélyezett adatforrások és a korábban sem hozzáférhető corporationidőzítők 403-as szerepkörhiánya tájékoztatásként jelennek meg. A hálózati vagy belépési hiba, illetve egy korábban használt adatforrás hozzáférésének elvesztése továbbra is figyelmeztetés, a karakter és az adatforrás megnevezésével.

## Teljes személyes és corporation készlet

A Készlet menüben a terv készlete mellett az Összes személyes item és a Corporation teljes készlete nézet is elérhető. A személyes nézet minden hozzáadott karakter letöltött assetjeit mutatja, a terv karakter- és helyszűrőitől függetlenül. A corporation nézetben egy corporation választható; a készletek soha nem keverednek. A kibontott hajók, modulok és blueprintpéldányok is megjelennek. Ez böngészés: a gyártási szabályok, a foglalások és a kézi készletfelülírások nem változnak.

A kereső minden találatra keres, nem csak az aktuális oldalra. Karakterre legördülő listából lehet szűrni, az oszlopok rendezhetők és a többi oszlop szabad szöveggel szűrhető. Az oszlopszűrők alapból csukva vannak. Egy oldal 100 sort mutat; a CSV az összes szűrt találatot tartalmazza. Az item nevére kattintva csak a név kerül a vágólapra. A helyet az ESI helyazonosítója és tárolási jelzése mutatja; konténerben levő tárgynál a legfelső helyazonosító látszik.

A nézet a már letöltött adatokat használja; az EVE-frissítés tölti le az új asseteket. A hiányzó vagy régi karakteradatok külön jelzést kapnak. A Betöltött készlet újraolvasása csak a helyi adatokat olvassa újra. Tervezés vagy EVE-készletforrás bekapcsolása nem szükséges hozzá.

## Saját ablakos Windows-alkalmazás (1.2.0)

Bontsd ki a teljes Windows ZIP-et, és indítsd az **EVE_Muhely.exe** fájlt. A felület saját ablakban nyílik meg. Az EVE engedélykérése a rendszerböngészőt használja; jóváhagyás után térj vissza a Műhelybe. A sötét/világos téma és a nyelv a **Settings → Appearance and language** oldalon állítható. A vágólap, a mentési párbeszédablak, a nyomtatás és a külön intel-térkép/chatablak támogatott.

Microsoft Edge WebView2 Runtime és .NET Framework szükséges; ezek Windows 11-en rendszerint már megvannak. WebView2 hiányakor az indító a Microsoft hivatalos oldalát jelzi. Az app nem telepít rendszerkomponenseket automatikusan. A Windows rendszerértesítései külön engedélyezhetők; megjelenésüket a Windows értesítési és Ne zavarjanak beállításai is befolyásolják. Az átlátszó inteloverlay a Beállítások → Intelbeállítások alatt kapcsolható és helyezhető el.

Leállításkor az app figyelmeztet a nem mentett módosításokra és a futó lekérésekre. A helyi profil továbbra is a **%LOCALAPPDATA%\EVE Muhely** mappában van. A teljes ZIP cseréje előtt állítsd le a régi appot; a személyes adatok megmaradnak. Az **Ellenorzes_ablak.cmd** elkülönített, üres profilon vizsgálja a natív ablakot, az exportot és az intelablakokat. Opcionális böngészős tartalékindítás: az indító `--browser` kapcsolóval.

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

Az automatikus EVE-készletből csak a **becsomagolt** példányok használhatók fel, személyes és corporation-gyártásnál is. A kibontott hajók és modulok használatban lévőnek számítanak: nem fedezik a célt és nem szolgálnak gyártási bemenetként. A bennük vagy konténerekben lévő becsomagolt anyagok továbbra is számítanak. A BPO/BPC-tulajdont külön kezeljük. A kézi készletfelülírás szándékos kivétel. A **Terv kiszámítása** után a célmező alatt megjelenik a számítás eredménye; üres gyártási lista esetén jelzi, ha becsomagolt késztermék vagy folyamatban lévő job fedezi a célt.

## Bányászati napló – bányászati statisztikák

A bal oldali **Bányászati napló** menüpont a hozzáadott karakterek személyes bányászati naplóját összesíti. Ez a gyártási kör választásától független; ugyanazt a bányászatot nem számoljuk hozzá még egyszer corporation-megfigyelőkből.

Első használatkor a **Beállítások → Adathozzáférések** oldalon karakterenként kattints a **Bányászati napló engedélyezése** gombra. Az EVE Developer alkalmazásnak engedélyeznie kell az **esi-industry.read_character_mining.v1** scope-ot. A már hozzáadott karakterrel hagyd jóvá az engedélyt; a korábbi hozzáférések megmaradnak. Ezután a **Bányászati naplók frissítése** lekéri az összes karakter adatait. A közös EVE-adatellenőrzés is frissíti őket, ha legalább egy karakter hozzáférését már megadtad. A folyamatjelző a karaktert és az adatoldalt is mutatja.

- Válassz 7, 30, 90 napos, teljes helyi vagy egyéni időszakot. A kezdő és záró nap is beleszámít; a napló dátumai UTC szerint értendők.
- Szűrhetsz karakterre és ércre. A karakterenkénti és ércenkénti táblák a darabszámot, az m³-t és a finomított értéket mutatják, összesítő sorral.
- A **Napi bontás** a finomított értéket mutatja, a felső összesítésével azonos Jita-árazással, összesítő sorral. A finomítási adagok maradékát karakterenként és érctípusonként továbbvisszük az időszak következő napjára; a napi anyagkihozatalok összege megegyezik az időszaki kihozatallal. Az ISK-sorok külön kerekítése néhány fillér eltérést okozhat. A **Naplósorok** az időbeli és rendszer szerinti részleteket mutatja. A táblák rendezhetők, szűrősoruk alapból zárt. A részletes napló CSV-be menthető.
- Az értékelés a finomított anyagok kihozatalát árazza Jita buy, sell vagy split áron. A nyers ércek piaci értékét nem jelenítjük meg és nem kérjük le. A részletes napló CSV-exportja a mennyiségeket és térfogatokat tartalmazza. Az érték a jelenlegi árakon számolt becslés, nem a bányászat napjának eladási bevétele.
- A finomítás a holdaknál beállított nullsec Tatara, T2 rig, maximális skillek és implant kihozatalával számol. Az adott időszak érceit karakterenként és típusonként összevonja, csak egész finomítási adagokat dolgoz fel, a kimenetet lefelé kerekíti. A maradék ércet és a gázokat nem számolja finomított terméknek. Finomítási és piaci díjakat nem von le.

Az ESI jelenleg 30 nap bányászati adatát biztosítja, legfeljebb 10 perces gyorsítótárral. A már letöltött előzmény helyben megmarad. Az újabb érték ugyanannak a karakter–nap–rendszer–érc sornak a korábbi mennyiségét felülírja; nem adódik hozzá újra. A letöltés előtti, ESI-ben már nem látható múlt nem állítható vissza. A karakter törlése a saját helyi bányászati előzményeit is törli.

Hiányzó engedély, sikertelen frissítés, ismeretlen térfogat vagy hiányzó ár esetén a felület jelzi a hiányt; egy részösszeg nem jelenti az összes karakter teljes termelését. Az **Adatforrás és lefedettség** mutatja az utolsó sikeres lekérést és a gyorsítótár lejáratát. A bányászati napló nem készlet: a kibányászott ércet azóta eladhattad vagy felhasználhattad.

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
- **Szürke:** nincs engedély, nincs betöltött adat, a frissítés hibás, vagy a legutóbbi ellenőrzés több mint 20 perce volt. Ilyenkor nem állítja biztosan, hogy a karakter nem tanul; a régi adatokat jelölve őrzi meg.

A korábbi belépések a gyártási adatokhoz továbbra is használhatók, de a skillekhez egyszeri bővítés kell. Az [EVE Developer oldalon](https://developers.eveonline.com/applications) a **meglévő alkalmazást** szerkeszd, és a korábbi három mellett engedélyezd az `esi-skills.read_skills.v1` és az `esi-skills.read_skillqueue.v1` jogosultságot. A Client ID és a callback maradjon ugyanaz. Ezután a Műhely skillnézetében karakterenként kattints a **Skillek engedélyezése** gombra, és az EVE belépőoldalán ugyanazt a karaktert válaszd. Jelszót és Client Secretet a Műhely nem kér. Másik karakter kiválasztásakor a meglévő belépést nem írja felül.

A **Skilladatok frissítése** csak a skilladatokat frissíti; a felső **EVE-frissítés** az ipari adatok után ezeket is ellenőrzi. Sikertelen skilllekérés nem teszi érvénytelenné a gyártási készletet. A nyitott skillnézet percenként újraszámolja a helyi állapotot, de automatikus ESI-lekérés legfeljebb 15 percenként indul. A kézi frissítés gomb ezt az alkalmazásoldali korlátot megkerüli, a CCP gyorsítótárát továbbra is betartva. Bezárt vagy leállított alkalmazás mellett nincs figyelés vagy értesítés.

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

A kitermelő és a gyártó bolygók figyelése külön történik:

- **Kitermelő bolygó:** kizárólag az ESI-ben közölt programkezdést, programvéget és hátralévő időt figyeljük. A helyi gyárak készlethiánya nem rövidíti le a kitermelőprogramot. A program újraindítása az új ESI-kezdés és -lejárat alapján jelenik meg. A visszaszámlálás a frissítések között is halad; az új HTTP-lekérés nem tolja ki a végét.
- **Gyártó bolygó:** csak a saját bolygón letöltött készlet, a gyárak saját bemeneti pufferei és az ezekből a helyi gyárakban készülő köztes termékek finanszírozzák a becslést. Más bolygó készletét, későbbi importot vagy várható kitermelést nem adunk hozzá. Egy raktár közös készletét egyszer használjuk fel, a beállított útvonalak figyelembevételével.

A gyártó bolygóknál az ellátás a következő ciklusra és választható **1 / 6 / 24 / 72 órára** ellenőrizhető. Az **Ellátási hiányok CSV** a kiválasztott időtáv fedezeti hiányait menti. Az **Időalapú termelési becslés** a készlet adatidejétől számolja az eltelt gyártást, a várható leállást és az elkészülő termékeket. A már elindított ciklus bemeneteit nem vonja le újra. Az eredeti készlettáblázat pillanatkép, a becslés ettől elkülönítve jelenik meg. A program nem módosítja a mentett ESI-adatokat; régi cikluskezdet, bizonytalan sorrend vagy kimeneti korlát esetén külön jelzést ad.

**EVE-korlát:** a kolónia állapotát az EVE csak a bolygó játékbeli megnyitásakor számolja újra. Ezért a kolóniaállapot és az API-lekérés időpontja is látszik. A 30 percnél régebbi gyári pillanatkép szürke, az ellátási számok dátumhoz kötött becslések. Nyisd meg a bolygót a játékban, majd frissíts a Műhelyben; a CCP körülbelül tízperces gyorsítótára késleltetheti az új adatot. A nyitott, előtérben lévő PI-nézet percenként ellenőrzi az állapotot, de automatikus ESI-lekérés legfeljebb 15 percenként indul. A kézi frissítés gombbal korábban is ellenőrizhetsz, a CCP gyorsítótárát betartva. Bezárt alkalmazás mellett nincs figyelés vagy külső értesítés.

A PI-ellenőrzések közös raktárakat, útvonalakat, gyári puffereket, lejárt programokat, régi adatokat, hibás API-válaszokat, jogosultságokat és több karaktert fednek le. A felületet elkülönített mintakolóniákkal is ellenőriztük. Hivatalos háttér: [CCP PI útmutató](https://developers.eveonline.com/docs/guides/pi/).

## Mentett tervek gyorsválasztója és közös beszerzés

A **Mentett tervek** oldalon külön **Személyes** és corporationönként külön **Corp** kategóriát választhatsz. Csak a kiválasztott kategóriába mentett tervek látszanak. A kategória és a felső **Gyártási kör** ugyanazt a kiválasztást mutatja: a **Terv mentése és foglalás** gomb mindig ebbe a körbe ment. Meglévő terv frissítése megtartja a kategóriáját; másik körben külön új tervet menthetsz. A foglalások személyes és corp készlet között továbbra sem keverednek.

A termékmező alatti **Mentett tervek** sor szintén csak az aktuális gyártási kör mentéseit mutatja, névvel és célmennyiséggel. Kattintással ugyanaz a mentett terv nyílik meg, saját készletfoglalásának felhasználásával. A kiválasztott mentés kiemelést kap. Tervválasztáskor az aktuális oldalon maradsz: az ütemező, a gráf, az alapanyaghiány és a többi nézet az új tervvel frissül, nem vált vissza a Gyártási terv oldalra. Az ütemező beállításai megmaradnak; az előző terv ütemezését az új tervhez újra ki kell számolni. Nem alkalmazott módosításoknál a váltás előtt megerősítést kér. Új mentés vagy törlés után a sor frissül; a régi, előre beépített mintagombok eltűntek.

Az **Alapanyaghiány → Összes mentett terv** nézet a mentett célok anyaghiányait anyagonként egy sorban egyesíti. Az összesen beszerzendő mennyiség mellett tervenként is látszik a hiány. A közös készletet és a folyamatban lévő jobok kimenetét egyszer használja fel: az aktív foglalások a meglévő elsőbbségük szerint, utánuk a foglalás nélküli mentések létrehozási sorrendben kapnak készletet. A foglalás nélküli tervek is beleszámítanak, de az összesítés nem kapcsolja be a foglalásukat. A **Beszámított tervek** rész megmutatja a célokat és a sorrendet.

Az **Összesítés frissítése** újraszámol a legutóbbi helyi EVE-adatokkal; új assetekhez és jobokhoz előbb **EVE-frissítést** indíts. A közös lista másolható és CSV-be menthető. A **Kiválasztott terv** visszavált az egyedi hiányra. Az összesítés az elmentett mennyiségekkel dolgozik; a termékmezőben végzett, még nem mentett módosításokat nem tartalmazza. A kész komponensek és hajók alapanyagai itt sem kerülnek újra a hiányba.

## Átvett job és később frissülő készlet

Az EVE a jobok átvételét és a személyes készletet eltérő gyorsítótárral adhatja vissza. Ha egy szükséges anyagból már átvett job látszik, de a készletpillanatkép az átvétel előtti, a Műhely **Készletfrissítésre várunk** állapotot mutat. Kiírja az érintett karaktert, anyagot, a készlet időpontját, az átvételt és a CCP gyorsítótárának lejáratát. A lejáratig az ismételt EVE-frissítés ugyanazt az adatot adhatja.

A **Terv kiszámítása** gomb ilyen várakozásnál minden nézetben, az ütemezőben is látható hibaüzenetet ad. Az üzenet tartalmazza az érintett tervet és anyagokat, valamint a **legkorábbi frissítési próbálkozás** teljes dátumát, másodpercét és időzónáját a böngésző helyi idejében. A jelzett időpont után **EVE-frissítést** indíts; a Terv kiszámítása önmagában csak a helyi adatokból számol újra. Már lejárt gyorsítótárnál ezt külön jelzi. A felület nyelvváltásakor az üzenet és a dátum is nyelvet vált.

A mentett tervek és foglalások megmaradnak. Nyitott, előtérben lévő Műhely-ablaknál a jelzett lejárat után automatikus EVE-frissítés indul; újabb automatikus ESI-próbálkozás legfeljebb 15 percenként történik, más frissítést és nem alkalmazott kézi módosítást nem szakít meg. A lejárat nem garantálja az új adatot: ha az EVE továbbra is régi pillanatképet ad, a program az új lejáratot mutatja és tovább vár. Bezárt alkalmazás mellett nincs ilyen ellenőrzés.

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


## Marketek, gyártási költség és értékesítés

Az árazásnál **Jita buy/sell/split** és **Helyi buy/sell/split** választható. A split a legjobb vételi és eladási ár átlaga. Jita alatt kizárólag Jita 4-4 értendő; a helyi ár a kiválasztott konkrét állomásról vagy struktúrából származik. Hiányzó helyi árat nem helyettesítünk Jitával. A piaci mennyiségi mélységet nem becsüljük.

A **Beállítások → Marketek és értékesítés** alatt gépelj rendszernevet, válassz találatot, állíts be olvasó karaktert, majd keress marketnévre vagy adj meg Structure ID-t. Válaszd ki a megfelelő állomást és mentsd el. Saját helyi példánk: **C-N4OD – C-N4OD - Fountain of Life**. Privát struktúrához dokkolási hozzáférés és ESI market/search/structure engedély szükséges; ezt a **Market-hozzáférés engedélyezése** gombbal kérheted. A felsorolt új scope-okat az EVE Developer alkalmazásban is engedélyezni kell. A korábbi jogosultságok megmaradnak.

A **Gyártási költség és várható bevétel** kompakt panel a hátralévő munkák előtt jelenik meg. Az anyagok/blueprintek árazása és az eladási árforrás külön állítható. Válassz eladó karaktert, majd frissítsd az adatait. Ezek a beállítások mentett tervenként megmaradnak; egy új terv mentése átviszi a piszkozat költségbeállításait is.

A bekerülésben szerepel a hátralévő gyártáshoz felhasznált készlet és köztes WIP piaci értéke, a beszerzendő alapanyag, a hiányzó blueprint, a munkaköltség és a beállított szállítás és az egyéb költség. A tervben gyártott köztes termék alapanyagait egyszer számoljuk. A **További költségek és részletek** alatt találod a kézi költségeket és az anyag/job részletezést. Hiányzó BPC-runhoz nem használunk BPO-piaci árat: add meg a tényleges beszerzési vagy másolási költséget. A nem ismert anyagár és munkaköltség továbbra is megakadályozza a teljes költség számítását.

**Szállítás:** a Settings → Marketek és értékesítés alatt négy külön ISK/m³ díj állítható: Jita import/export és helyi market import/export. Az import az anyagárforrás marketét használja a még beszerzendő anyagok csomagolt térfogatához. Az export az eladási árforrás marketét használja az újonnan gyártandó céltermék csomagolt térfogatához, a runkerekítés többletével együtt. A meglévő készletet, blueprinteket és már elindított céltermékjobokat nem szállítjuk újra. Az import és az export külön sorban látszik, és mindkettő része a teljes bekerülésnek és profitnak; az egyéb egyszeri költség külön mezőben marad. Alapérték: 0. A korábbi egyetlen szállítási díjat mindkét market importdíjaként megőrizzük, az export kezdetben 0.

A meg nem adott BPC-költség 0 ISK, ezt a teljes bekerülés mellett jelezzük. A meglévő BPC használatánál is megadható a tervre jutó költség; kifejezett 0 esetén nincs hiányjelzés. A kizárólag BPO-val fedezett gyártás blueprintköltsége 0, jelzés nélkül. A hiányzó reakcióformula piaci költsége továbbra is számít.

A bevétel a hátralévő jobok **új céltermékkimenetével** számol, a runkerekítés többletével együtt. A már meglévő kész célterméket és az elindított céltermékjobokat nem értékesíti újra a profitban. Látható az egységár, bruttó eladási érték, eladási adó, közvetítői díj, nettó bevétel, teljes gyártási bekerülés és nettó profit. Az alapanyaghiány oldalon csak a még beszerzendő mennyiségek értéke számít; az egyesített lista a készletet egyszer használja fel.

Eladási adó = 7,5% × (1 − 0,11 × aktív Accounting-szint). Az NPC közvetítői díj a Broker Relations skillt és az állomástulajdonos corporation/faction felé érvényes, módosítatlan standingeket használja. Struktúránál ez az NPC-kedvezmény nem érvényes: add meg az EVE-ben rád érvényes **teljes közvetítői díjat SCC-vel együtt**. Ezt az ESI nem közli. Azonnali eladásnál nincs új megbízási közvetítői díj; eladási megbízásnál van, legalább 100 ISK. Kézzel megadott 0%-os struktúradíjjal ideiglenesen közvetítői díj nélküli becslés készül; az eladási adó megmarad. Alapból buy árhoz azonnali eladás, sell/split árhoz megbízás tartozik; az eladási mód külön felülírható.

A market- és standingadatok gyorsítótárazva tárolódnak. Automatikusan legalább 15 perc telik el új lekérések között; a kézi frissítés is betartja az ESI gyorsítótárát. A korábbi és hiányzó adatokat jelöljük. A split tájékoztató középár. Újraárazást, későbbi árváltozást és be nem írt költséget nem becsülünk.

## Munkaköltség és gyártási hely

A **Beállítások → Struktúrák és bónuszok** alatt külön rendszer választható gyártás és reakció számára. Az ESI rendszerindexe és korrigált ár adatai adják a díjalapot; a létesítményi adó, a struktúra kedvezménye, SCC és Alpha-pótdíj itt állítható. A kompakt összesítő a munkaköltséget a többi bekerülési költséghez adja. Hiányzó index vagy korrigált ár esetén a teljes költség és profit ismeretlen.

## A holdtermelés profitja

A **Termelés Jita-értéke** panel tartalmazza az üzemanyagot és Magmatic Gas-t, a megadott bérletet és egyéb költséget, az eladási díjakat, a teljes költséget és a **Profit / 30 nap** sort. Holdanként a **Szerkesztés** alatt add meg a havi bérletet és a további költségeket; ide írható például a külön Tatara üzemanyaga, a finomítás, bányászat és szállítás költsége. Ezek nem kerülnek automatikusan becslésre.

Az eladási adót és a közvetítői díjat a holdak **Számítási beállítások** lapján adhatod meg. Kezdetben mindkettő 0%. Buy áron történő eladásnál nincs új eladási megbízás közvetítői díja; sell és split esetén a megadott közvetítői díj is számít. A struktúraszűrő a költséget és a profitot is szűri. A kézi Fuel Block ár mező az ezreseket automatikusan tagolja, a tizedesrészt megtartja.

## Holdnyilvántartás és 30 napos termelés

Nyisd le a **Moon management / Holdak és kitermelés** menüt. A **Holdnyilvántartás** alatt új holdat vihetsz fel, a meglévőket szerkesztheted vagy törölheted.

**Tömeges export/import:** az **Összes hold exportja** a teljes nyilvántartást JSON-fájlba menti, a felvitt ércekkel, arányokkal, struktúrával, költségekkel és megjegyzésekkel, a nézetszűrőtől függetlenül. Karakteradatot és EVE-belépést nem exportál. A **Tömeges import / scan** alatt töltsd be a fájlt, vagy illeszd be a játék scantáblázatát; több hold is szerepelhet benne. Az EVE Quantity 0–1 közötti arány, amelyet százalékká alakítunk. A MoonID, SolarSystemID, PlanetID és Ore TypeID értékeit ellenőrizzük; az ID-khez nem illő neveket jelezzük.

Válaszd ki az új scanholdak struktúráját és közös kezdő bérleti díját. Kérj **Import előnézete** ellenőrzést, majd a külön importgombbal ments. Alapból a már felvitt holdak kimaradnak. **Frissítés** esetén a scan csak az összetételt cseréli, a meglévő struktúra és költségek megmaradnak; JSON-import a fájl holdbeállításait alkalmazza. A kihagyott holdakat soha nem törli. Az import egy műveletben legfeljebb 1000 holdat és 1 MB szöveget fogad. Hibás sor vagy az előnézet óta megváltozott nyilvántartás esetén egyetlen holdat sem módosít.

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

A **Beállítások → Értesítések** alatt válaszd a **Rendszerértesítések engedélyezése** gombot, majd hagyd jóvá a macOS kérését. A **Tesztértesítés** gombbal ellenőrizheted a megjelenést. Itt kapcsolhatod a személyes/corp és típusonkénti jelzéseket, módosíthatod a holdelőrejelzést 1–30 napra, valamint engedélyezheted az EVE-adatok 15 percenkénti háttérellenőrzését. A CCP gyorsítótárát figyelembe vesszük. Az **EVE-adatok ellenőrzése** gomb kézzel is elindítja a frissítést.

A hold tulajdonosát az ESI corporation-időzítője azonosítja. Ismeretlen tulajdonosnál a hold a Személyes fülön marad, ezt felirat jelzi. A **Holdak értesítési tulajdonosa** táblázatban választhatsz automatikus, személyes vagy konkrét corporation-hozzárendelést. Ez csak az értesítési besorolást módosítja.

Ugyanazt az eseményt egy aktív időszakban egyszer küldjük; az újraindítás vagy ismételt frissítés nem ismétli meg. Több egyidejű jelzést tulajdonosonként és típusonként összevonunk. A rendszerértesítésre kattintva a megfelelő fül és típus nyílik meg. A macOS Fókusz módja és értesítési beállításai módosíthatják a megjelenést.

**Az alkalmazásnak futnia kell**, háttérben is működik. Bezárt alkalmazás mellett nincs új EVE-ellenőrzés és nincs új rendszerértesítés. A rendszerértesítések a helyi macOS-ablakos változatban érhetők el; a böngészős nézetben az értesítési lista használható.

## Közös beállítások

A bal oldali **Settings / Beállítások** menü lenyitható, és az alábbi részeket fogja össze:

- **Structures and bonuses / Struktúrák és bónuszok:** gyártás és reakció bónuszai, rendszer, adók, készletforrás, receptadatbázis.
- **EVE connection / EVE-kapcsolat:** Client ID, karakterek hozzáadása, kiválasztása és eltávolítása.
A **Minden hozzáférés engedélyezése** gomb egy karakterhez egyetlen EVE-belépéssel kéri az alkalmazás összes támogatott engedélyét: személyes készlet, blueprintek és jobok, skillek és tanulási sor, PI, corporationadatok, holdnaptár és értesítések, intelhelyzet és mining ledger. Az EVE-oldalon ugyanazt a karaktert válaszd. Saját Client ID esetén minden kért scope legyen engedélyezve a Developer alkalmazásban is; corporationadatokhoz a játékbeli szerepkörök továbbra is szükségesek. Jóváhagyás után frissítsd az EVE-adatokat. A külön engedélyező gombok továbbra is használhatók.

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

## Inteltérkép és helyi chatlogfigyelés

Az **Inteltérkép** a bal oldali menüben érhető el, gyártási terv kiválasztása nélkül. A megadott EVE Chatlogs mappát másodpercenként ellenőrzi, az új sorokat a háttérben olvassa; a natív Mac-ablak háttérbe téve is képes rendszerértesítést küldeni. Bezárt app mellett nincs figyelés. Az EVE kliensben a chatnaplózásnak bekapcsolva kell lennie, és csatlakoznod kell a figyelt csatornához. Ez bejelentett intel, nem a játék teljes, biztos helyzetképe.

1. Nyisd meg a **Beállítások → Intelbeállítások** oldalt.
2. Válaszd ki a **Chatlogmappát**. Macen a **Mappa kiválasztása** natív mappaválasztót nyit. A **Csatornák keresése** a fájlnevekben talált csatornákat kínálja fel; kattintással hozzáadhatók. A **Figyelt csatornák** mezőben soronként egy pontos csatornanevet adj meg.
3. Kapcsold be a figyelést. Állítsd be a riasztás távolságát (0–30 csillagkapu-jump), az intel érvényességét (1–120 perc) és az azonos rendszerhez tartozó értesítések közti szünetet (0–600 másodperc). A 0 jump csak azonos rendszert jelent.
4. Jelöld ki a figyelt saját karaktereket. Az **Intelhelyzet engedélyezése** gomb a karakter meglévő EVE-jogosultságai mellé kéri az `esi-location.read_location.v1` és `esi-location.read_online.v1` scope-okat. Ezeket a Client ID EVE Developer alkalmazásában is engedélyezni kell. Az EVE-belépést és az új jogosultságokat te hagyod jóvá.
5. Alternatíva a **Kézi referenciarendszer**: gépelésre szűkülő listából válassz. Ez rögzített referencia, nem követi a karakter mozgását. Törlésével visszatér az automatikus helyzet.
6. Mentsd az intelbeállításokat. Az OS-értesítéshez a **Beállítások → Értesítések** alatt a személyes és a **Közeli intel** jelzéseket, valamint a rendszerértesítést is engedélyezd; macOS-hozzájárulás szükséges. Az intelhez külön hang kapcsolható.

A friss ESI-adatból online állapot és rendszer is kell a közelségi riasztáshoz. Hibás, lejárt vagy offline ESI-adat nem számít megbízható élő pozíciónak. A saját karakter Local-naplójának rendszerváltása utolsó ismert helyet ad. A **Friss Local-napló helyzetével is riasszon** kapcsoló külön engedélyezi ezt a kevésbé biztos alternatívát, és csak legfeljebb 5 perces Local-adat használható; ez nem bizonyítja az online állapotot. A helyzet forrása és ideje mindig látható.

## Intelüzenetek értelmezése és clear

A rendszer teljes rendszerneveket és egyértelmű, legalább három karakteres, számot vagy kötőjelet tartalmazó nagybetűs rövidítéseket ismer fel. A rövidítések régiója szűkíthető. A több rendszerre egyszerre utaló bizonytalan üzenetet jelöli, és nem riaszt belőle; egyértelmű nyíllal megadott útvonálnál a célrendszert használja.

- `J5A-IX Pilot Name` egy rendszerhez rendelt bejelentés. A bejelentő neve külön oszlopban marad; nem kerül automatikusan a jelentett pilóták közé.
- A karakter showinfo-hivatkozásából származó név azonosítóval rendelkezik. Szabad szövegből felismert nevet külön jelöl az app; elírás, szokatlan hajórövidítés vagy beszélgetés téves felismerést okozhat. Az eredeti üzenetet mindig ellenőrizheted. A felismert karakternevek pontos azonosítóját a nyilvános ESI névfeloldás ellenőrzi; a teljes üzenetszöveg nem kerül elküldésre.
- `J5A-IX clr` és `J5A-IX clear` egyaránt tisztára jelöli a rendszert, és megszünteti az ott korábban bejelentett aktív intel közelségi jelzését.
- `J5A-IX clr?` vagy `clear?` kérdés; nem törli a korábbi bejelentést. A „not clear” sem clear.
- A lejárt bejelentésből nincs közelségi riasztás. Egy pilóta újabb, egyértelmű rendszerbejelentése felváltja a korábbit.

A program a különböző saját karakterek logjaiban szereplő azonos csatornaüzenetet egyszer dolgozza fel. Induláskor vagy új csatorna kiválasztásakor a régi bejegyzések előzményként jelennek meg; nem indítanak visszamenőleges riasztást. A beolvasási pozíció és az értesítés kézbesítése helyben megmarad újraindítás után. Clear után egy újabb bejelentés új esemény lehet, az értesítési szünet figyelembevételével.

## Az inteltérkép használata

A **Karakter** mező választja ki a követett saját karaktert. A térkép alapértelmezetten a kiválasztott karakter helyének teljes régióját mutatja. A **Régió** listából másik teljes régió választható; a **Karakter követése** visszatér a saját karakter régiójához. Az 5 jumpos, illetve az Intelbeállításokban megadott más távolságon belüli rendszereket és kapukat kék kiemelés jelöli. Ez kapugráf szerinti távolság, nem geometriai kör. A rendszerek elhelyezése az olvashatósághoz igazított sematikus régiórajz; a kapukapcsolatok a CCP adatait követik. A távolság mindig a kiválasztott saját karakter helyétől számolódik, akkor is, ha egy másik rendszerre kattintasz. Korábbi Local-helyzetnél a körzet szaggatott és figyelmeztetés jelzi, hogy nincs megbízható élő pozíció. Mozgasd húzással a térképet, nagyíts a görgővel vagy a +/− gombokkal; a **Teljes nézet** visszaállítja a kezdeti keretezést.

Piros jelölés: aktív bejelentés, zöld: clear, arany: bekapcsolt előzménynézetben lejárt intel. Kék gyűrű: saját karakter beolvasott vagy rögzített helye, a forrásjelzés figyelembevételével. A rendszer melletti nevek a jelentett pilóták. Kattintás vagy billentyűzetes Enter kijelöli a rendszert, alatta az eredeti bejelentések olvashatók. Az **Intelüzenetek** tábla az utolsó 24 órából legfeljebb 500 bejegyzést mutat, a közös rendezési és szűrési lehetőségekkel.

A távolság a nyilvános CCP SDE teljes csillagkapu-hálózatának legrövidebb útja; Ansiblex, wormhole és cyno nem része. A kiválasztott régió összes rendszerét megjeleníti, az útvonal- és közelségszámítás a teljes hálózatot használja. A nyilvános rendszer- és kapuadat a receptadatbázis frissítésével frissülhet. A chatlog szövege és az intelbeállítások a saját helyi adatprofilban maradnak, a csomagba nem kerülnek. Az app az eredeti naplókat nem módosítja. A naplóforgatást, új fájlokat, UTF-16 kódolást és félkész sorokat kezeli.

## Intelaktivitás-kártyák és zKillboard

A bejelentett aktivitás mellett kis kártya mutatja a jelentett pilótákat, hajókat és a bejelentés korát. A nagyobb kártyák belseje görgethető. A hajó neve mellett a CCP hivatalos képszolgáltatásából származó ikon látható. Ha csak általános „shuttle” vagy ismeretlen hajónév szerepel, az app nem talál ki hajótípus-azonosítót; ilyenkor nincs konkrét típusikon.

Az ismert karakterazonosítóval rendelkező pilótanév kattintható: az alapértelmezett böngészőben a `https://zkillboard.com/character/<azonosító>/` oldal nyílik meg. Steve Hluskan mintája: `https://zkillboard.com/character/359618261/`. A szabad szövegből felismert név továbbra is következtetés, akkor is, ha az ESI ilyen nevű karaktert igazolt. A még fel nem oldott nevet **Azonosító még nem ismert** jelzés kíséri; ehhez nem készül kitalált link.

A háttérben csak a felismert karakternevek mennek a CCP nyilvános ESI névfeloldásához, bejelentkezési token nélkül. A teljes chatüzenet nem. A név–azonosító találatok helyben, 30 napra gyorsítótárazódnak, a nem talált nevek egy óráig nem kérődnek újra. Hálózati hiba nem állítja le a chatlogfigyelést vagy a térképet. A **Pilótaazonosítók frissítése** gomb elindítja a szükséges ellenőrzéseket, a gyorsítótár figyelembevételével. A zKillboard csak kattintáskor nyílik meg; az app nem tölt le killboard-adatokat.

Több pilóta és több hajó közös bejelentésénél az app nem állít biztos pilóta–hajó párosítást. A kártyán ez **Több pilóta · közös hajójelentés** jelzést kap. A hajófelismerés a nyilvános EVE-adatokban szereplő nevekre és néhány szokásos rövidítésre épül. Az eredeti üzenet ellenőrizhető.

## Külön térkép- és intelchat-ablak

A térképes kártyákból a jelentések az üzenet időpontjától számított 3 perc után eltűnnek; üres kártya nem marad. Az eredeti üzenet a chatben és az előzményekben továbbra is olvasható, a beállított aktivitási és riasztási élettartam nem változik.

Az **Inteltérkép** tetején a **Térkép külön ablakban** gomb önálló, átméretezhető Mac-ablakot nyit a régiótérképpel, a kártyákkal és a körzetjelöléssel. A **Intelchat külön ablakban** egy másik ablakban, játékon belüli chathez hasonló sorokban mutatja az összes kiválasztott intelcsatornát együtt. Minden sorban látszik az időpont, a csatorna, a bejelentő és az üzenet; az időpontok az alkalmazás helyi idejét követik. Az ismert pilótanevek itt is zKillboard-linkek, a rendszernévre kattintás a külön térképablakra visz.

A külön térképablak csak a rendszertérképet, annak nagyítási vezérlőit és jelmagyarázatát mutatja. A karaktert, a régiót és az intelbeállításokat a fő alkalmazás Inteltérkép oldalán válaszd ki; a Térkép külön ablakban gomb a már megnyitott ablakra is alkalmazza a választást.

A Mac az önálló ablakokat az Ablak menüben és a Dock appikonjára jobb kattintva is felsorolja. Az ablakok külön kis méretre tehetők és visszahozhatók; nem egyesülnek automatikusan lapokká.

A chat **csak olvasható**: nem küld üzenetet a játékba. Az **Automatikus görgetés** kapcsolóval a legújabb sor követése leállítható. Felfelé görgetve az app megőrzi az olvasási helyet; az alsó szélre visszatérve a követés folytatódik. A bejegyzéseket időrendben, legrégebbitől a legújabbig mutatja, legfeljebb az utolsó 24 óra 500 sorával. A változatlan sorok nem épülnek újra minden ellenőrzésnél.

Egy térkép- és egy chatablak lehet nyitva; az ismételt megnyitás a meglévőt hozza elő. A mellékablak bezárása nem állítja le az appot és a másik ablakot. A főablak bezárása vagy az alkalmazás kiléptetése minden ablakot és a helyi figyelést leállítja. A nyelv és a sötét/világos téma közös az ablakokban. Az OS-értesítéseket továbbra is a főablak kezeli, így a több ablak nem küld ismételt értesítést.

## Átlátszó inteljelző

Beállítások → Intelbeállítások → **Átlátszó inteljelző**: külön, keret nélküli Mac- vagy Windows-ablak. A beállított riasztási jumptávolságon belüli, friss és egyértelmű jelentéseket mutatja, megbízható karakterhelyzet alapján. Nem igényel OS-értesítési engedélyt, és nem ad külön értesítési hangot. Clear vagy a pilóta új helyszíne megszünteti a korábbi aktív jelentést.

Alapértelmezett megjelenítés: **60 másodperc**, 1–3600 között egész másodpercre állítható. Az üzenet időpontjától számolunk: a frissítés vagy újranyitás nem indítja újra a visszaszámlálást. Az előzmények a chatben megmaradnak. Egyszerre legfeljebb öt friss jelentés látszik: rendszer, jump, jelentett pilóták, ismert hajók és a saját referenciakarakter.

Üresen teljesen eltűnik. Normál módban nincs címsora, nem veszi el a billentyűzet fókuszát, és a kattintásokat átengedi az alatta lévő alkalmazásnak. A normál és teljes képernyős alkalmazások fölött lebeg; a macOS rendszer- és biztonsági felületei elsőbbséget élvezhetnek. Windowson a normál és a keret nélküli teljes képernyős ablakok felett jelenik meg. Exkluzív teljes képernyős játék és a Windows biztonsági képernyői eltakarhatják; EVE-hez a keret nélküli ablakos módot használd.

Válaszd ki a monitort, az X/Y pozíciót és a szélességet, majd mentsd. Az X/Y az adott monitor bal felső sarkától mért képernyőpont. Monitoronként megmarad a hely. Az **Inteljelző mozgatása** gomb egy húzható mintát mutat akkor is, ha nincs jelentés. Húzd a kívánt monitorra, majd kattints a mintán a **Kész** gombra. Az **Elhelyezés kész · pozíció beolvasása** lezárja a mozgatást és visszaolvassa a beállítási mezőkbe a helyet. Ha a mentett monitor nincs csatlakoztatva, elérhető monitorra helyezi az ablakot, annak határain belül. A pozíció ezen a gépen tárolódik. Az app bezárásával az inteljelző is leáll.

## Corporationfigyelés és frissítési időköz

A **Corporationok → Figyelés** kapcsoló corporationönként ki- és bekapcsolható. Kikapcsolva nem indul hozzá corp-készlet-, blueprint-, job- vagy corp holdidőzítő-lekérés, kézi frissítéskor sem. A korábbi helyi pillanatképek és tervek megmaradnak, de az app nem küld ebből a corporationből régi jobértesítéseket. A tagkarakterek személyes készlete, PI-je, tanulása, naptára és értesítése ettől független.

Az automatikus ESI-lekérések adatforrásonként legalább **15 perc** távolságra történnek. A korlát több ablak és újraindítás mellett is megmarad, sikertelen próbálkozás után is. A helyi táblázatok, visszaszámlálások és chatlogok gyakrabban frissülhetnek hálózati ESI-lekérés nélkül. A frissítés gomb kézi ellenőrzést indít; a CCP saját gyorsítótára ekkor is érvényes.

Az **Inteltérkép → Intelértesítések: be-/kikapcsolva** gomb az intel rendszerértesítéseit és a képernyőn felugró átlátszó inteljelzőt együtt kapcsolja. Kikapcsoláskor a már látható jelzés is eltűnik. A többi értesítés beállítása, a térkép és a chatfigyelés megmarad. Rendszerértesítéshez az általános alkalmazás- és OS-engedély is szükséges. Az intel ESI-helyzete is a 15 perces automatikus korlátot követi; régi ESI-helyzet nem igazol élő közelséget. A helyi Local-napló továbbra is folyamatosan frissülhet.

A **Folyamatban / In progress** oldal a kiválasztott személyes vagy corp gyártási kör ipari jobjait mutatja. Ezen az oldalon nincs termék-, célmennyiség- vagy mentettterv-választó blokk; a gyártási kör és a karakter külön, kompakt választóban állítható. Személyes módban a **Minden karakter** az összes hozzáadott karakter személyes jobjait összesíti, a tervező karakter- és helyszűrőjétől függetlenül.

## Flottatevékenység: killmailek és megfigyelt útvonal

A **Flottatevékenység** menü az alkalmazásba felvett karakterek zKillboardon nyilvánosan megjelent killjeit és veszteségeit gyűjti. A **Killmailek frissítése** az összes kijelölt követett karaktert vagy a fenti karakterválasztóval megadott karaktert kéri le. Első alkalommal az utolsó 30 napot keresi, karakterenként legfeljebb 5 oldallal / 1000 killmaillel. A korábbi letöltések megmaradnak. A nézetben 7, 30 vagy 90 nap választható. Egy közös killmail az összesített listában egyszer szerepel, mellette minden érintett saját karakterrel. A killmail linkje a zKillboardra mutat. Az oszlopok rendezhetők és szűrhetők.

A **Flottamenetek** karakterenként csoportosítja az eseményeket: alapértelmezésként 45 percnél hosszabb kill nélküli szünet új menetet jelent. Ez becslés, mert sem a killmail, sem a pozíció nem bizonyítja a flottatagságot. Az ESI-minták kizárólag a killmailekkel már azonosított menethez egészítenek ki rendszereket; önmagában az utazás nem hoz létre harci riportot.

A **Megnyitás** megmutatja az érintett rendszerek látogatási sorrendjét, az ESI-minták és killmailek számát, valamint a rendszerhez tartozó időablakokat. Minden kill helyszíne legalább 15 percet kap az első kill előtt és az utolsó után; a ráhagyás növelhető. A szomszédos, friss helyminták a köztes rendszerekben a lehetséges érkezést és távozást határolják. Hosszabb mintahiánynál ismét bizonytalan, ráhagyásos ablak marad. Egy későbbi visszatérés külön látogatás; csak az egymást fedő, azonos rendszerű ablakokat vonjuk össze. Nem adunk hozzá feltételezett köztes kapuútvonalat, mert jump bridge, cyno vagy féregjárat is használható.

A **Kapcsolódó killmailek betöltése** a rendszerablakok nyilvános eseményeit is összegyűjti, így egy battle reporthoz hasonló helyi eseménylista készül. Az ismert saját kill és veszteség elkülönül a környező eseményektől. Más harcok is beleeshetnek az ablakba; a kezdő csapatbeosztás a harci kapcsolatokból becsült, kézzel javítható. Egy riport legfeljebb 20 lekérést végez, rendszerenként és UTC-hónaponként legfeljebb 5 oldallal. Elért korlát vagy forráshiba esetén részlegesnek jelöli az eredményt. Új esemény vagy módosított időablak esetén újratöltést jelez. Az **Időablakok CSV** a rendszerneveket és UTC-határokat exportálja. A képernyőn helyi idő látszik; az időpont fölé vitt egér UTC-t mutat.

A **Követés és csoportosítás beállításai** alatt kiválaszthatók a követett karakterek, külön ki-/bekapcsolható az élő zKillboard-követés és a helykövetés, állítható a lekérési időköz (30–900 másodperc, alapból 60), a menetek elválasztása (15–180 perc) és a kill előtti/utáni ráhagyás (15–60 perc). A helyadat külön engedélye: `esi-location.read_location.v1`; ezt az **Adathozzáférések** intel- vagy összes hozzáférésének engedélyezése tartalmazza. Ehhez a funkcióhoz nem kell új killmail-hozzáférés. A zKillboard lekérése nem használja és nem kapja meg az EVE-tokeneket.

Az ESI nem ad múltbeli útvonalat: az app a futása közben kapott helymintákat menti el. Az ESI-helyzet utolsó ismert hely, nem igazolja, hogy a karakter online van, és a minták közti tényleges út ismeretlen. A helyadat az egyetlen, a korábbi 15 perces automatikus korlátnál sűrűbben lekért ESI-adat. Az ESI gyorsítótárát így is betartjuk. Az új killmaileket az R2Z2 élő adatfolyam folyamatosan hozza be. Emellett a publikus történetet az app óránként ellenőrzi, és a zKillboard minden azonos listalekérdezését egy óráig helyben tárolja; a kézi frissítés ezt nem kerüli meg. A zKillboardról hiányzó vagy későn publikált kill nem pótolható biztosan.

Az **Adatforrás és lefedettség** karakterenként mutatja a kill- és helyadat ellenőrzési idejét, az új killlekérés lehetőségét és az esetleges hozzáférési hibát. Lekéréskor az állapotjelző mutatja a karaktert/rendszert és az oldal előrehaladását. Az adatbázis az alkalmazás helyi profiljában marad; új telepítőbe nem kerülnek ezek az előzmények.

### Flottamenet ISK-összegzése és killmailikonok

Egy flottamenet megnyitásakor három összegző kártya látszik: **a session teljes veszteségértéke**, **a karakter részvételével elért killek értéke** és **a karakter saját vesztesége**. A részvételnél a karaktert támadóként tartalmazó killmailek teljes értéke számít, killmailenként egyszer; nem osztjuk a támadók vagy a kiosztott sebzés szerint. A kártyák a darabszámot is mutatják, a részvételi kártya pedig az összes ismert veszteségértékből való százalékos arányt.

A nagy összeg a zKillboard `totalValue` becslése, a kihullott loot értékével együtt. Alatta a **Ténylegesen megsemmisült** sor külön a `destroyedValue` összege, a kihullott loot nélkül. A hiányzó érték nem számít nullának. Ha az ár vagy a kapcsolódó riport hiányzik, részleges, illetve a rendszerablak változott, a kijelzés részösszeget jelez. A teljesebb összeghez használd a **Kapcsolódó killmailek betöltése** gombot. A session egészének összege a megadott rendszerablakok minden betöltött eseményét tartalmazza, így környező idegen harcot is tartalmazhat.

A **Killmail** oszlopban a szöveges hivatkozás helyén a megsemmisült hajó ikonja látható, a session részleteinél és az összesített killmaillistában is. Az ikonra kattintva az adott killmail nyílik meg a zKillboardon. Fölé vitt egérrel a hajó neve és a killmail azonosítója is olvasható; a hajó szöveges neve továbbra is másolható.

### Szemben álló felek: battle report és kézi besorolás

A megnyitott session **Szemben álló felek** részében egymás mellett látszik a 2–4 résztvevő oldal. Mindegyiknél külön szerepel a teljes veszteségérték, a loot nélküli megsemmisült érték, az egyedi pilóták száma, a veszteségek száma és a részvétellel elért killek száma. A **Veszteségek** lenyitásával hajótípusonként összesített lista látszik: a sor elején hajóikon, utána típusnév, elvesztett darabszám és összesített ISK-érték. Az egyedi killmailek lent, a session eseménylistájában érhetők el. Az összegek a sessionben betöltött rendszerablakokra vonatkoznak, és hiányos riportnál részösszegként jelennek meg.

Az automatikus kezdőbeosztás a killmaileken szereplő alliance-t használja. Alliance nélkül a játékoscorporation, NPC corporationben lévő pilótánál az egyedi karakter a csoport. A közös célpontra lövők együttműködési kapcsolatot kapnak; az egymásra lövők szembenállási kapcsolatot. Az app a közösen támadó csoportokat csak akkor vonja össze, ha köztük nem lát közvetlen egymás elleni támadást, majd legfeljebb négy oldalt alakít ki. A saját karakterrel összefüggő harctól elkülönülő, nem azonosítható vagy négy oldalba egyértelműen be nem osztható szereplők **Besorolatlan** állapotban maradnak. Ez becslés, nem biztos flottatagság: közös célpont nem mindig jelent szövetséget, egy félreklikkelés pedig egymásra lövést is okozhat.

A **Felek száma** választóban az **Automatikus** mellett 2, 3 vagy 4 oldal állítható be. Minden alliance-csoport saját oldalválasztót kap; ezzel vagy az egész csoport másik oldalkártyára húzásával áthelyezhető. Egy áthelyezés csak azt a csoportot mozgatja, a többit megtartja. A kézi döntés automatikusan az adott sessionhöz mentődik, és új betöltésnél is megmarad. Ha a beállított oldalszám csökkentése megszünteti egy kézi csoport oldalát, az a csoport besorolatlan lesz. Az **Automatikus besorolás visszaállítása** az adott session kézi beosztását törli, és újra a becslést mutatja. Más session beosztását ez nem érinti.

A veszteség mindig az áldozat oldalán számít, killmailenként egyszer. A killek száma több támadó oldalnál is megjelenhet, ha ugyanarra az áldozatra több fél lőtt; ezeket a számokat nem szabad összeadni. Az app külön jelzi, ha azonos oldalra sorolt csoportok között is lát lövést. A **Harci kapcsolatok és a számítás értelmezése** alatt az oldal–oldal támadási mátrix ellenőrizhető. A kil­lmailekről hiányzó logisztikások és más flottatagok nem kerülnek be automatikusan.

A neveket nyilvános ESI-névlekérdezésből, helyi gyorsítótárral egészítjük ki a kapcsolódó riport betöltésekor. A hovatartozást a korabeli killmail azonosítója adja, nem a karakter jelenlegi corporationje. Névlekérési hiba esetén az alliance/corporation azonosítója látszik, a beosztás és az összegek akkor is működnek.

### Élő zKillboard-adatfolyam

Az **Élő zKillboard-követés** alapból bekapcsolt. Futó appnál az R2Z2 nyilvános adatfolyamot követi, a kijelölt karakterek új killjeit és veszteségeit, valamint a flottamenetek rendszer- és időablakaiba eső további killmaileket menti a történetbe. A session ISK-összesítése és az oldalak hajótípusonkénti veszteséglistája automatikusan frissül; a nézet legfeljebb körülbelül 10 másodpercenként olvassa a helyi állapotot. A zKillboardra érkezés és közzététel idejét az app nem tudja gyorsítani.

A felső állapotjelző mutatja a kapcsolódást, az események feldolgozását, az aktív kapcsolatot vagy a hiba utáni újrapróbálás idejét. A beérkezett események és a releváns frissítések száma az app aktuális futására vonatkozik. Az adatfolyam nem tartja folyamatosan foglaltnak az általános adatellenőrzést.

Az app elmenti a következő sorszámot, újraindítás után onnan folytatja. Egy átmeneti helyi puffer az utoljára beérkezett legfeljebb 10 000 eseményt legfeljebb 6 óráig őrzi, hogy a később beérkező saját killhez a korábbi környező veszteségeket is társíthassa. Az érdektelen események nem kerülnek a tartós harci történetbe. A hosszabb kiesés miatt elveszett élő lefedettséget jelzi; korábbi csatákhoz használd a **Kapcsolódó killmailek betöltése** gombot. Az élő figyelés nem igazol teljes csatalefedettséget.

Egyetlen soros adatfolyam-kapcsolat működik, legfeljebb 5 lekéréssel másodpercenként. Ha nincs új esemény, legalább 6 másodpercet vár; hibánál egyre hosszabb idő után próbál újra, és betartja a szerver várakozási utasítását. Az ESI-adatok megszokott frissítési rendje változatlan. A már ismert alliance/corporation nevek helyi gyorsítótárból jönnek; az új csoportok neveinek kiegészítését legfeljebb 15 percenként ellenőrzi.

### Régiós killintel az élő adatfolyamból

Az **Inteltérkép** a chatjelentések mellett az élő R2Z2-adatfolyam új killjeit is mutatja. A térképen megnyitott régió rendszerei külön **☠ kill** jelölést és darabszámot kapnak. Egy rendszer egy közös kis kártyán összesíti a frissen beérkezett killeket és az elvesztett hajótípusokat. A kártya a beérkezéstől számított 3 perc után eltűnik; a jelölés az **Intel érvényessége** beállítás időtartamáig marad meg. Az időpont a killmail tényleges eseményideje, nem a letöltés ideje.

A **Killek a régióban** táblázat a rendszerenként összevont csomagokat mutatja, hajóikonokkal, darabszámmal és összesített értékkel. Az egyedi killmailek a hajóikonokra kattintva nyílnak meg a zKillboardon. A külön térképablak továbbra is csak a térképet és annak vezérlőit mutatja; az összevont chatbe nem keverednek a nyilvános killadatok.

Az azonos rendszerben 10 másodpercen belül beérkező killmailek közös értesítési csomagot alkotnak, ha az eseményidejük legfeljebb 2 percet fed le. A csomag lezárásáig az app vár az értesítéssel. Más rendszerek és egymástól távoli események külön csomagba kerülnek. A killmail újrafeldolgozása frissítheti az adatot, de nem növeli a darabszámot és nem küldi el újra ugyanazt a jelzést. A rendszerértesítés és az átlátszó inteljelző a rendszert, darabszámot és hajótípusokat mutatja, **ISK-érték nélkül**.

A **Beállítások → Intelbeállítások → zKillboard-killek az intelben** kapcsoló külön vezérli ezt a forrást. A **Killértesítések régiója** alapból a figyelt karakterek utolsó ismert régióit használja; választható egy konkrét régió is. Ez független a térkép böngészésre használt régióválasztójától és a chatben rövidített rendszernevek értelmezési régiójától. Killértesítés a teljes figyelt régióra érkezik, a chatből érkező közelségi riasztások továbbra is a jumplimitet követik. Ha nincs ismert karakterhelyzet, válassz konkrét killrégiót vagy állíts be helyadatot.

A forráshoz futnia kell az appnak és a **Fleet activity → Live zKillboard tracking** funkciónak. Chatlog-olvasás vagy további ESI-engedély nem szükséges a killadatokhoz. Az **Intelértesítések** kapcsoló kikapcsolása az OS-értesítést és a képernyőn felugró jelzést is tiltja; a térképen a killek továbbra is látszanak. Az OS-értesítéshez az app fő értesítési engedélye is kell. Több megnyitott térkép-/chatablak nem küldi ki többször a jelzéseket.

A kill megtörtént veszteség, nem igazolt jelenlegi ellenséges jelenlét. A chatből érkező **clear/clr** nem törli a killjelölést. A későn publikált kill tényleges időpontját figyelembe vesszük: az érvényességi ablaknál régebbi esemény nem vált ki friss riasztást. Az app legfeljebb 24 óra / 20 000 tömörített helyi killintelrekordot tart meg. A zKillboardon nem közzétett események itt sem látszanak.

## Lapméret, készlethelyek és ablakbezárás

A táblázatok **Sor oldalanként** mezőjével 25, 50 vagy 100 sor választható. A beállítás megmarad, és a többi táblázatra is érvényes. A rendezés és szűrés az összes betöltött soron működik, nem csak az aktuális oldalon. A lapozás nem dobja el a sorokban megadott, még nem alkalmazott értékeket.

A teljes személyes és corporation készlet **Állapot** szűrője a készletben ténylegesen előforduló állapotokat kínálja fel. A **Hely / tárolási hely** oszlop a rendszer, állomás vagy struktúra nevét mutatja; az azonosító a cella súgójában és CSV-exportban megmarad. A névfeloldás háttérben történik, az ismert nevek gyorsítótárazódnak. Privát struktúrához struktúraolvasási ESI-jog és az adott karakter dokkolási hozzáférése szükséges. Ha a név nem hozzáférhető, az ID megmarad és az app jelzi az engedélyigényt.

A **főablak bezárógombja**, a rendszer Quit parancsa és az **Alkalmazás leállítása** ugyanahhoz a teljes leállításhoz vezet. Leáll a helyi szolgáltatás és az intel-/flottafigyelés, felszabadul a helyi port, bezárulnak a külön intelablakok és az overlay. Indulás közbeni bezárás sem hagy háttérszolgáltatást futni. A külön térkép- vagy chatablak önálló bezárása továbbra is csak azt az ablakot zárja. A saját mentett adatok megmaradnak.

## Implantfigyelés kidokkoláskor

A **Beállítások → Értesítések → Implantfigyelés kidokkoláskor** résznél karakterenként kapcsolható be a figyelés, és ISK-ban megadható az értékhatár. Az alapérték 1 milliárd ISK; a karakterfigyelés kezdetben ki van kapcsolva. Az összérték az aktív klón implantjainak Jita sell árán alapul. A rendszerértesítések, a Személyes jelzések és az Implantfigyelés jelzéstípus is legyen bekapcsolva.

Az **Implantfigyelés engedélyezése** gombbal add meg az `esi-location.read_location.v1` és `esi-clones.read_implants.v1` engedélyeket. Saját Client ID esetén az implantengedélyt az EVE Developer alkalmazásban is hozzá kell adni. A Minden hozzáférés gomb ezt is kéri.

A figyelés futó app mellett, a többi EVE-frissítéstől függetlenül működik. A helyzetet 5 másodpercenként figyeli; az implantadatok az ESI legalább 120 másodperces gyorsítótárát követik. A Jita-árak a meglévő 15 perces automatikus árfrissítési korlátot használják. Friss klónváltás után átmenetileg még korábbi implantlista érkezhet. A rendszer nem tudja megakadályozni a kidokkolást.

Csak a megfigyelt dokkolt → űrben átmenetre küld értesítést, kidokkolásonként egyszer. Induláskor már űrben lévő karakterre vagy hosszú adathiány után nem küld utólagos riasztást. Hibás helyzetadatból nem következtet kidokkolásra. Hiányos árak mellett csak akkor jelez, ha az ismert részösszeg önmagában is meghaladja a határt; ilyenkor **Legalább** jelölést használ. Az értesítés az Értesítések személyes lapján is megjelenik, 5 percig.

A Mac intel overlay kattintás nélkül, fókuszváltáskor is az ablakok előtt marad. Az EVE kliensre kattintás nem rövidíti le a jelzés beállított élettartamát; a lejárt vagy kikapcsolt jelzés nem jelenik meg újra.
