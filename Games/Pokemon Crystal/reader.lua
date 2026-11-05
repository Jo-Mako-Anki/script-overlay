-- Pocket Monsters Crystal (JP) : texte de la boîte (carte des tuiles wTilemap en 0xC4A0) et infos du jeu.
-- Adresses de la version japonaise, retrouvées en comparant le code de la ROM JP avec pokecrystal (US).
local DOSSIER = ...   -- ce dossier (Games\Pokemon Crystal)
local r = run_file(JEUX .. "/_common/pokemon_gb.lua", 0xC4A0)

local A = {
  party_count = 0xDC9D, party_mon1 = 0xDCA5, party_nicks = 0xDDE9,   -- 48 octets par Pokémon, surnoms de 6 octets
  map_group = 0xDC7B, map_number = 0xDC7C, y = 0xDC7D, x = 0xDC7E,
  money = 0xD841, johto_badges = 0xD84A, kanto_badges = 0xD84B,
  num_items = 0xD885, num_key_items = 0xD8AF, num_balls = 0xD8CA,
  battle_mode = 0xD25E, battle_type = 0xD261, enemy_mon = 0xD237, battle_mon = 0xC622, ot_party_count = 0xD2B1,
  ot_party_mon1 = 0xD2B9, other_trainer_class = 0xD260, other_trainer_id = 0xD262,
  event_flags = 0xDA65,   -- 256 octets : objets ramassés, dresseurs battus…
  time_of_day = 0xD29A, dex_caught = 0xDE2D, dex_seen = 0xDE4D,
}
local function rd(a) return emu:read8(a) end
local function rd16(a) return rd(a) * 256 + rd(a + 1) end
local function bytes(a, n) local t = {} for i = 0, n - 1 do t[#t + 1] = rd(a + i) end return t end
local function bits(a, n) local c = 0 for i = 0, n - 1 do local b = rd(a + i) while b > 0 do c = c + (b & 1); b = b >> 1 end end return c end

-- structure « battle_struct » : espèce, objet, 4 attaques, DV, 4 PP, bonheur, niveau, statut, -, PV, PV max, stats, types
local function battle_mon(a)
  return { sp = rd(a), moves = bytes(a + 2, 4), pp = bytes(a + 8, 4), lvl = rd(a + 13), status = rd(a + 14),
           hp = rd16(a + 16), maxhp = rd16(a + 18), types = bytes(a + 30, 2) }
end

-- écran affiché, reconnu à quelques tuiles de wTilemap (20×18) : menu des Pokémon, fiche d'un Pokémon, sac
local TM = 0xC4A0
local function tile(c, l) return rd(TM + l * 20 + c) end
local function screen()
  if tile(0, 0) == 0x28 and tile(1, 0) == 0x29 and tile(2, 0) == 0x2A and tile(0, 1) == 0x3C then return "sac" end
  for l = 1, 11, 2 do   -- une ligne par Pokémon : « :L » puis le « HP: » de la barre de PV
    if tile(8, l) == 0x6E and tile(11, l) == 0x60 and tile(12, l) == 0x61 then return "equipe" end
  end
  local fiche = true    -- fiche « つよさをみる » : trait vertical sur toute la colonne 7
  for l = 0, 17 do if tile(7, l) ~= 0x31 then fiche = false break end end
  if fiche then return "equipe" end
  return nil
end

local read_infos
-- la moitié haute de la WRAM (D000-DFFF) change de banque pendant les animations (combat, transitions) :
-- on ne lit les infos que quand la banque 1 est en place, sinon on renvoie les dernières lues
local last_infos = nil
function r.infos()
  local svbk = rd(0xFF70) & 7
  if svbk > 1 then return last_infos end
  last_infos = read_infos()
  return last_infos
end

read_infos = function()
  local party = {}
  local n = rd(A.party_count)
  if n > 6 then n = 0 end
  for i = 0, n - 1 do
    local a = A.party_mon1 + 48 * i
    party[#party + 1] = { sp = rd(a), item = rd(a + 1), moves = bytes(a + 2, 4), pp = bytes(a + 23, 4), lvl = rd(a + 31),
      status = rd(a + 32), hp = rd16(a + 34), maxhp = rd16(a + 36), nick = bytes(A.party_nicks + 6 * i, 6) }
  end
  local function pocket(a, pairs, max)
    local t, c = {}, rd(a)
    if c > max then c = 0 end
    for i = 0, c - 1 do
      if pairs then t[#t + 1] = { rd(a + 1 + 2 * i), rd(a + 2 + 2 * i) } else t[#t + 1] = { rd(a + 1 + i), 1 } end
    end
    return t
  end
  local mode = rd(A.battle_mode)
  local battle = nil
  if mode == 1 or mode == 2 then
    battle = { mode = mode, type = rd(A.battle_type), enemy = battle_mon(A.enemy_mon), mine = battle_mon(A.battle_mon),
               ot_count = mode == 2 and rd(A.ot_party_count) or 0 }
    if mode == 2 then
      -- dresseur adverse : classe, numéro et son équipe (espèce, niveau, PV)
      battle.trainer = { rd(A.other_trainer_class), rd(A.other_trainer_id) }
      local ot = {}
      for i = 0, math.min(battle.ot_count, 6) - 1 do
        local a = A.ot_party_mon1 + 48 * i
        ot[#ot + 1] = { sp = rd(a), lvl = rd(a + 31), hp = rd16(a + 34), maxhp = rd16(a + 36) }
      end
      battle.ot = ot
    end
  end
  -- drapeaux d'événements en hexadécimal (512 caractères)
  local f = {}
  for i = 0, 255 do f[#f + 1] = string.format("%02x", rd(A.event_flags + i)) end
  return {
    map = { rd(A.map_group), rd(A.map_number), rd(A.x), rd(A.y) },
    time = rd(A.time_of_day),
    money = rd(A.money) * 65536 + rd16(A.money + 1),
    badges = { bits(A.johto_badges, 1), bits(A.kanto_badges, 1) },
    dex = { bits(A.dex_caught, 32), bits(A.dex_seen, 32) },
    caught = bytes(A.dex_caught, 32),
    party = party,
    items = pocket(A.num_items, true, 20), key_items = pocket(A.num_key_items, false, 25), balls = pocket(A.num_balls, true, 12),
    battle = battle,
    flags = table.concat(f),
    screen = screen(),
  }
end

-- journal des répliques et captures (facultatif) : config.lua > journal["Pokemon Crystal"]
local jc = type(CONFIG) == "table" and type(CONFIG.journal) == "table" and CONFIG.journal["Pokemon Crystal"]
if type(jc) == "table" then r.journal = run_file(DOSSIER .. "/log.lua", jc) end

return r
