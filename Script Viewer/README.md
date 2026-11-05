# Script Viewer

While you play a Japanese game in **mGBA**, a web page shows the text of the dialogue box live
(kana as they are, or the kanji and the English if you give it a table of the game's dialogues),
with game info beside it: party, battle, map of the place, bag...

No OCR: a Lua script reads the console's memory (the tiles shown on screen) and sends it to the page.

## Supported games

| Game (Japanese version) | Text | Game info | Log |
|---|---|---|---|
| Pokémon Crystal / Gold / Silver | yes | party, battle, location (full map), bag | yes |

For any other game the page says "No reader for this game yet (TITLE, CODE)": a reader has to be written
(see below).

## Installation

1. Download this folder (*Code > Download ZIP* on GitHub) and unzip it anywhere.
2. mGBA 0.10 or newer.
3. Chrome or Edge for the page.

## Playing

1. Start the game in mGBA.
2. *Tools > Scripting… > File > Load script…* > `script_viewer.lua`
   (next times: *File > Recent scripts*).
3. The page `Script Viewer.html` opens by itself (unless it is already open). At the top: "mGBA: connected" and the recognised game.

### Dialogue table (optional)

Put the game's table (.sop, .xlsx, .csv, .tsv) in the game's folder, named like the folder or `table`
(e.g. `Games/Pokemon Crystal/Pokemon Crystal.sop`), or give its path in `config.lua` (`tableaux`).
The script sends it to the page, which reads it again if it changes.
A `.sop` game file made with `--sheets` (see Script Overlay's `pack.py`) works the same way.

Recommended format: one row per dialogue box, with these column titles on the first row.
The page recognises them by itself; other columns are ignored.

| Title | Content |
|---|---|
| `ID` | where the text is in the ROM (label, address or number) |
| `Jap` | the text as it shows in the game (often kana): this is what identifies the line |
| `Kanji` | the same text with kanji (optional) |
| `Eng` | the English translation (optional) |
| `Lieu`, `Perso`, `Note` | location, speaker, note (optional), shown small with the line |

With other titles, the page asks once which column holds what.
Without a table in the folder, the **Table…** button lets you pick one by hand.

Settings: kanji, kana or both, font, theme, sizes, history. Key **E**: show / hide the English.

### Game info (Pokémon Crystal)

Tabs to the right of the text:
- **Party**: level, HP, types, moves (type, power, PP), next moves, evolution
- **Battle**: opens by itself; the opposing Pokémon, its weaknesses, how effective your moves are against it;
  against a trainer, their name in Japanese and their whole team (with HP, fainted Pokémon greyed out)
- **Location**: name of the place, full map with your position, region map, wild Pokémon by time of day;
  on the map, the exits, items, hidden items and trainers (greyed out once picked up or beaten),
  with the list of what is left and the teams of the trainers not beaten yet
- **Pokédex**: the Japanese Pokédex text, category, height, weight and where to find it;
  shows the battle Pokémon (or your first Pokémon), a click on any name opens its page, or search by no. or name
- **Bag**: money, badges, Pokédex, items

## Personal settings and log

Copy `config.exemple.lua` to `config.lua` to change the port, say where your tables are, or turn on a game's **log**:
the order and moment of each line (`journal.tsv`) and a screenshot per screen of text, useful
to make subtitles or Anki cards. `config.lua` stays on your computer (it is not sent to GitHub).

## Contents

```
script_viewer.lua       the script to load in mGBA, the same for all games
Script Viewer.html      the page (opened by the script)
config.exemple.lua      template for personal settings (copy it to config.lua)
lib/                    SheetJS (reads .xlsx)
../Games/list.lua       which folder goes with which game (ROM title)
../Games/<game>/        everything about one game:
    reader.lua            reads the memory (box text, info)
    infos.js, maps/       fixed data for the info tabs (names, moves, maps)
    log.lua               log and screenshots (optional)
    <game>.sop / .xlsx    your table of the dialogues (optional, not shared)
    tools/                scripts that made infos.js and maps/
../Games/_common/       code shared between several games
```

## Adding a game

Create a folder `Games/<game>/` with a `reader.lua` that returns a table:
- `lire()`: the text of the dialogue box on screen (UTF-8 string, `\n` between lines), or `nil`;
- `balises` (optional): table tags to replace before comparing, e.g. `{ ["<NI>"] = "に" }`;
- `infos()` (optional): a table sent as is to the page (info tabs, with `infos.js`);
- `journal` (optional): a table with `image()`, `reset()`, `fin()`, `etat()`.

`reader.lua` receives the path of its folder (`local DOSSIER = ...`). Then add a line to `Games/list.lua`
with the ROM's title or code. You have to find the address of the tile grid, the position of the box and
the game's character table.

## Data

`Games/Pokemon Crystal/infos.js` and `maps/` are made from the
[pokecrystal](https://github.com/pret/pokecrystal) disassembly and the Japanese ROM
(for the Japanese names and the Pokédex texts), by the scripts in `tools/`
(`generer_pokemon_crystal.py`, then `generer_extras_crystal.py` for the Pokédex, trainers and map events). No need to run them to play.
No ROM is provided.

Included library: [SheetJS](https://sheetjs.com) (Apache 2.0).
