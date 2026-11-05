# Script Overlay

A companion for playing Japanese games to learn Japanese. It shows what the game is saying, in a web page and in a
small window over the game: the **Japanese** with furigana and a dictionary on hover, and the **English**.
For some games it also shows game info next to the text (party, battle, map, Pokédex, bag...).

The app does not translate anything. It finds the current line in a dialogue file of the game and shows the English
that goes with it. What is shown is specific to each game and can be adjusted (Settings on the text page).

Windows only. Free for personal use (see [LICENSE](LICENSE)).

## Download

Get **ScriptOverlay.zip** from the Releases (or from the Patreon post), unzip it anywhere and run `ScriptOverlay.exe`.
Everything is included (OCR program and Japanese model, dictionary, game files): no installation and no Internet needed.

## How to use

The home page opens in your browser. Pick a game and click **Start**. How the app knows which line is on screen
depends on the game, and the card of each game shows its type:

- **Emulator Script**: a script in the emulator sends the text. Click Start, then load the script in the emulator
  (mGBA: Tools > Scripting > File > Load script > `Script Viewer\script_viewer.lua`).
- **Game Hook**: the app reads the text straight from the game. Click Start and run the game.
- **OCR**: the app reads the dialogue box on screen. Click Start and draw a rectangle around the dialogue box once.

The game must run **windowed or borderless fullscreen**. The window over the game never takes the keyboard or the
gamepad from the game, and it is left out of screen captures. Drag it to move it, mouse wheel on a text to change
its size, right-click for its menu.

## Games

| Game | Type |
|---|---|
| Persona 5 Royal (PC) | Game Hook (with a day-by-day calendar and warnings at key choices) |
| Pokémon Crystal (Japanese, mGBA) | Emulator Script (with party, battle, map, Pokédex and bag) |
| Pokopia (Switch, Eden) | OCR |

No game or ROM is provided.

## Credits

- Persona 5 Royal hook and `libPCAtlus.js`: from the [Agent](https://github.com/0xDC00/agent) texthooker scripts, with [Frida](https://frida.re).
- Dictionary: [JMdict](https://www.edrdg.org/jmdict/j_jmdict.html) (EDRDG, CC BY-SA 4.0).
- Word splitting and readings: [SudachiPy](https://github.com/WorksApplications/SudachiPy) (Apache 2.0).
- OCR: [Tesseract](https://github.com/tesseract-ocr/tesseract) (Apache 2.0; the Windows build by [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki) is in `Tesseract\`, with its licence) and the tessdata_best Japanese model.
- Reading tables in the mGBA page: [SheetJS](https://sheetjs.com) (Apache 2.0).
- Map data of Pokémon Crystal made with the [pokecrystal](https://github.com/pret/pokecrystal) disassembly.

The game dialogue files are provided for educational purposes only. All game content belongs to its owners.

## For the author: build and release

```
pip install -r requirements.txt
python -m script_overlay          (run from the sources, with a console)
build.bat                         -> ScriptOverlay.exe (+ _internal\)
release.bat                       -> release\ScriptOverlay.zip (what is shared)
```

Not in git (see `.gitignore`): `data\` (settings, tables, .sop game files), `Tesseract\`, `build\`, `release\`,
`_sauvegardes\`, saved GameFAQs pages. Game files `.sop` are made with `python -m script_overlay.pack`.
