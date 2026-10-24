EVE Workshop 1.4.1 – Windows intel overlay

## Downloads / Letöltések

- **Windows 11 x64:** `EVE_Muhely-1.4.1-Windows11-x64.zip` — extract the complete folder, then start `EVE_Muhely.exe`.
- **Mac Apple Silicon:** `EVE_Muhely-1.4.1-macOS-AppleSilicon.dmg` — drag the app into Applications. Intel Macs are not supported.
- SHA-256 checksums and Hungarian installation instructions are attached.

## What changed

- Windows now supports the transparent intel overlay in **Settings → Intel settings**.
- Borderless, topmost cards that do not take keyboard focus and let mouse clicks pass through in normal use.
- Per-monitor placement, a draggable positioning preview, configurable display duration from 1 to 3600 seconds, light/dark themes and Hungarian/English UI.
- Disabling intel notifications immediately clears the overlay. Reports expire from their original timestamps, so refreshes do not restart the countdown.
- The native Windows test checks actual drawing, window styles, focus, expiry, placement and shutdown cleanup.
- Use borderless windowed EVE on Windows. Exclusive full-screen games and Windows security screens may cover the overlay.

## Változások magyarul

- Az átlátszó inteljelző Windowson is használható a **Beállítások → Intelbeállítások** alatt.
- Keret nélküli, felül maradó jelzések; nem veszik el a billentyűzet fókuszát, normál módban átengedik a kattintásokat.
- Monitoronként menthető hely, húzható elhelyezési minta, 1–3600 másodperces megjelenítési idő, sötét/világos és magyar/angol felület.
- Az intelértesítések kikapcsolása az overlayt is azonnal elrejti. A lejárat az eredeti jelentés időpontjától számítódik.
- A Windowsos próba a valódi kirajzolást, ablakkezelést, fókuszt, lejáratot, pozíciómentést és bezárást is ellenőrzi.
- Windowson az EVE keret nélküli ablakos módját használd. Exkluzív teljes képernyős játék és a Windows biztonsági képernyői eltakarhatják az overlayt.

## Installation and existing data

Both packages open in their own application windows and include their Python runtime. Windows requires Microsoft WebView2 Runtime and .NET Framework, normally available on Windows 11. The Mac package supports Apple Silicon only and has no Developer ID signature or notarization.

Close the previous app before replacing its application folder. Personal profiles, characters, saved plans and encrypted credentials stay in the existing user data directory. Both packages ship without characters, plans or tokens; only the public EVE Client ID is preconfigured.
