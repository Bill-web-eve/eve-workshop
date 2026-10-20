# Intel: kutatás és működési döntések

Ellenőrizve: 2026. október 20. Ez a dokumentum a forrásokban ténylegesen megfigyelhető funkciókat különválasztja a saját alkalmazásunkhoz választott megoldástól. Külső alkalmazás forráskódját nem vettük át.

## Meglévő megoldások

- [RIFT hivatalos oldal](https://riftforeve.online/): helyi ESI-adatkezelés, intelcsatornák értelmezése, jelenlegi és történeti térkép, saját karakterek helye, beállítható helyzetfüggő és rendszerértesítések. A RIFT összetett beszélgetési kontextust is értelmez; a mi első változatunk ennél egyszerűbb, önálló üzenetekre épül.
- [IntelWalker készítőjének EVE-fórumbejegyzése](https://forums.eveonline.com/t/intelwalker-intel-chat-log-monitor/319071): helyi Chatlogs olvasás, előre feldolgozott jump-adatok, játékkliens-integráció nélkül. A bejegyzés 2021-es; nem igazolja a mai kompatibilitást. A megadott [intelwalker.com](https://www.intelwalker.com/) oldalból nem volt olvasható részletes jelenlegi dokumentáció.
- [Vintel saját tároló és leírás](https://github.com/Xanthos-Code/vintel): idővel változó jelölések, clear állapot, az eredeti bejelentések visszanézése és távolsághoz kötött riasztás. Ezek megerősítik a bejelentés korának és forrásának jelentőségét.
- [EVE Console saját leírás](https://docs.eveconsole.com/logs-and-map-data/): kiválasztott chatlogokból rendszer-, pilóta- és hajófelismerés, `clr` kezelés. A chat szövege továbbra sem biztos telemetria.
- [EVE Empire](https://eve-empire.org/): a megadott webhely az ellenőrzéskor a kutatáshoz használt böngészőeszközzel nem volt elérhető. Funkcióit és állítólagos előnyeit ezért nem tekintjük ellenőrzöttnek.
- [CCP Static Data dokumentáció](https://developers.eveonline.com/docs/services/static-data/): hivatalos rendszer- és kapuadatok, JSONL formátum, build-szám és gyorsítótárazás. A csomag nyilvános topológiát tartalmaz; nincs szükség online útvonalkérésre minden üzenetnél.

## A saját apphoz választott gyakorlat

Ezek a fenti megoldásokból és a helyi logok formátumából levont tervezési következtetések, nem egy külső termék kötelező specifikációja.

1. **Helyben maradó adat:** csak kiválasztott csatornák és saját Local-helyzet olvasása, az eredeti fájlok módosítása nélkül. A teljes chatszöveg nem kerül feltöltésre. A felismert karakterneveket a CCP nyilvános ESI névfeloldása ellenőrizheti; a hajóikon a CCP képszolgáltatásából jön, zKillboard csak kattintáskor nyílik. Nincs rejtett játékautomatizálás.
2. **Növekményes olvasás:** UTF-16, több karakter azonos bejelentéseinek összevonása, tartós kurzor, új fájl és forgatás, félkész sor visszatartása. Régi logok visszajátszásából nincs új riasztás.
3. **Ellenőrizhető értelmezés:** bejelentő és jelentett pilóta külön; szabad szöveges név bizonytalanként jelölve. Többértelmű helyből nincs közelségi riasztás. Az eredeti sor és idő látható.
4. **Clear:** `clr` = `clear`; kérdés és tagadás nem clear. Régi vagy clearrel feloldott bejelentésből nincs aktív riasztás.
5. **Valódi kaputávolság:** teljes, gyorsítótárazott kapugráfon legrövidebb út; a térkép kivágása nem változtatja meg a távolságot. Ugróhidat és wormhole-t csak külön, későbbi hiteles adatforrással lenne érdemes hozzáadni.
6. **Helyzet eredete:** friss ESI + online adat, explicit kézi referencia vagy külön engedélyezett, friss Local-alternatíva. Az utolsó ismert hely nem állítható be észrevétlenül élő pozíciónak.
7. **Értesítési zaj csökkentése:** közelben lévő, friss, új események; saját karakterek kihagyása; azonos esemény tartós kézbesítési visszaigazolása, beállítható szünet, clear utáni új esemény kezelése.
8. **Egyértelmű működés:** futó app szükséges, figyelési állapot és utolsó ellenőrzés látható; hibás fájl vagy hiányzó helyzet külön jelzés. Az intel segédeszköz, az elhallgatása nem bizonyítja a környék biztonságát.

## Az első változat határai

Nincs több üzenetre kiterjedő beszélgetésértelmezés, standings szerinti minősítés, killboard, automatikus játékművelet, Ansiblex vagy wormhole útvonal. Egy pilótanév szövegbeli felismerése heurisztikus. A legrövidebb kapuút nem biztonsági útvonalajánlás. A teljes használati útmutató az app Dokumentáció menüjében magyarul és angolul is szerepel.

## Régiótérkép és ablakok

A térkép most a teljes kiválasztott régiót rajzolja. A saját karaktertől mért kaputávolságot halo és kapuszínezés jelzi. A bejelentés melletti kártyák azonosított pilótákhoz pontos zKillboard-linket és felismert hajókhoz típusalapú ikont adnak. A Mac-app külön térkép- és összevont chatablakot kezel, közös helyi profillal, külön nézeti állapottal és egyetlen OS-értesítési kezelővel.

[CCP Image Server dokumentáció](https://developers.eveonline.com/docs/services/image-server/) · [ESI API Explorer](https://developers.eveonline.com/api-explorer)
