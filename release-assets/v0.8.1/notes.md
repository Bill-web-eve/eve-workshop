## Letölthető alkalmazások

- **Mac Apple Silicon: 0.8.0** — `EVE_Muhely-0.8.0-macOS-AppleSilicon.dmg`
- **Windows 11 x64: 0.8.1** — `EVE_Muhely-0.8.1-Windows11-x64.zip`

A két csomag verziója eltér: a 0.8.1-es módosítások a Windows-futtatást érintik. A kiadás a korábban elkészült csomagokat teszi letölthetővé, új fordítás nélkül.

Nem tartalmaznak karaktert, mentett tervet, készletet, belépési tokent vagy Client Secretet. A nyilvános EVE Client ID előre be van állítva. Excel, Codex és külön Python telepítése nem szükséges.

### Telepítés

**Mac:** nyisd meg a DMG-t, és másold az alkalmazást az Alkalmazások mappába. Csak Apple Silicon gépekhez készült.

**Windows:** bontsd ki a teljes ZIP-et, és indítsd az `EVE_Muhely.exe` fájlt a kibontott mappából. A mappa teljes tartalmát tartsd együtt.

Mindkét alkalmazás a saját böngésződben nyílik meg: http://127.0.0.1:8765. A részletes telepítési útmutatók külön is letölthetők a mellékletek között.

### Ellenőrzés és ismert korlátok

A csomagok aláírás és kiadói hitelesítés nélkül készültek. Az operációs rendszer figyelmeztetést jeleníthet meg az első indításkor.

**A Windows 11 alatti tényleges futtatási próba még nem történt meg.** A fejlesztői gépen a Windows tesztkörnyezet nem volt hozzáférhető. A Windows-csomagban található `Ellenorzes.cmd` külön, ideiglenes profillal ellenőrzi a működést, és nem módosítja a személyes adatokat.

Mindkét csomaghoz SHA-256 ellenőrzőösszeg tartozik. A közzététel a helyi fájlok és a feltöltött mellékletek ellenőrzőösszegét is ellenőrzi.
