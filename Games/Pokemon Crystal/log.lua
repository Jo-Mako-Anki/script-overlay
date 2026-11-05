-- Pokémon Crystal (JP) : journal des répliques et captures d'écran, pour les sous-titres et le tableau Anki.
-- Chargé par lecteur.lua (même dossier) quand config.lua a une entrée journal["Pokemon Crystal"].
-- Dans le dossier choisi (config.lua) :
--   Pokemon Crystal.txt     les répliques du jeu (fabriqué à partir du tableau par export_script.py)
--   journal.tsv             l'ordre et le moment (numéro d'image) où chaque réplique apparaît
--   captures\<date>\<image>.png   une capture par écran de texte complet
-- Avec traitement = chemin d'un .bat : lancé à la fin de la partie si auto = true.
local cfg = ...
cfg = cfg or {}
local DOSSIER = (cfg.dossier or ""):gsub("[/\\]+$", "")
local TEXT_FILE = "Pokemon Crystal.txt"
local JOURNAL_FILE = "journal.tsv"
local GAME_FOLDER = cfg.dossier_jeu or ""
local AUTO_PROCESS = cfg.auto == true
local AFTER_SESSION = cfg.traitement or ""

local TILEMAP = 0xC4A0      -- wTilemap (20x18)
local PLAYER_NAME = 0xD48E
local RIVAL_NAME = 0xD49A
local PLAYER_GENDER = 0xD463 -- bit 0 : fille

local TILE = {[112]="「",[113]="」",[114]="『",[115]="』",[116]="・",[117]="⋯",[118]="ぁ",[119]="ぇ",[120]="ぉ",[127]=" ",[128]="ア",[129]="イ",[130]="ウ",[131]="エ",[132]="オ",[133]="カ",[134]="キ",[135]="ク",[136]="ケ",[137]="コ",[138]="サ",[139]="シ",[140]="ス",[141]="セ",[142]="ソ",[143]="タ",[144]="チ",[145]="ツ",[146]="テ",[147]="ト",[148]="ナ",[149]="ニ",[150]="ヌ",[151]="ネ",[152]="ノ",[153]="ハ",[154]="ヒ",[155]="フ",[156]="ホ",[157]="マ",[158]="ミ",[159]="ム",[160]="メ",[161]="モ",[162]="ヤ",[163]="ユ",[164]="ヨ",[165]="ラ",[166]="ル",[167]="レ",[168]="ロ",[169]="ワ",[170]="ヲ",[171]="ン",[172]="ッ",[173]="ャ",[174]="ュ",[175]="ョ",[176]="ィ",[177]="あ",[178]="い",[179]="う",[180]="え",[181]="お",[182]="か",[183]="き",[184]="く",[185]="け",[186]="こ",[187]="さ",[188]="し",[189]="す",[190]="せ",[191]="そ",[192]="た",[193]="ち",[194]="つ",[195]="て",[196]="と",[197]="な",[198]="に",[199]="ぬ",[200]="ね",[201]="の",[202]="は",[203]="ひ",[204]="ふ",[205]="へ",[206]="ほ",[207]="ま",[208]="み",[209]="む",[210]="め",[211]="も",[212]="や",[213]="ゆ",[214]="よ",[215]="ら",[216]="り",[217]="る",[218]="れ",[219]="ろ",[220]="わ",[221]="を",[222]="ん",[223]="っ",[224]="ゃ",[225]="ゅ",[226]="ょ",[227]="ー",[228]="ﾟ",[229]="ﾞ",[230]="？",[231]="！",[232]="。",[233]="ァ",[234]="ゥ",[235]="ェ",[236]="▷",[237]="▶",[238]="▼",[239]="♂",[240]="円",[242]="．",[243]="／",[244]="ォ",[245]="♀",[246]="０",[247]="１",[248]="２",[249]="３",[250]="４",[251]="５",[252]="６",[253]="７",[254]="８",[255]="９"}
local VOICED = {[130]="ヴ",[133]="ガ",[134]="ギ",[135]="グ",[136]="ゲ",[137]="ゴ",[138]="ザ",[139]="ジ",[140]="ズ",[141]="ゼ",[142]="ゾ",[143]="ダ",[144]="ヂ",[145]="ヅ",[146]="デ",[147]="ド",[153]="バ",[154]="ビ",[155]="ブ",[156]="ボ",[169]="ヷ",[170]="ヺ",[179]="ゔ",[182]="が",[183]="ぎ",[184]="ぐ",[185]="げ",[186]="ご",[187]="ざ",[188]="じ",[189]="ず",[190]="ぜ",[191]="ぞ",[192]="だ",[193]="ぢ",[194]="づ",[195]="で",[196]="ど",[202]="ば",[203]="び",[204]="ぶ",[205]="べ",[206]="ぼ"}
local SEMI = {[153]="パ",[154]="ピ",[155]="プ",[156]="ポ",[202]="ぱ",[203]="ぴ",[204]="ぷ",[205]="ぺ",[206]="ぽ"}
local CODE = {[5]="ガ",[6]="ギ",[7]="グ",[8]="ゲ",[9]="ゴ",[10]="ザ",[11]="ジ",[12]="ズ",[13]="ゼ",[14]="ゾ",[15]="ダ",[16]="ヂ",[17]="ヅ",[18]="デ",[19]="ド",[25]="バ",[26]="ビ",[27]="ブ",[28]="ボ",[38]="が",[39]="ぎ",[40]="ぐ",[41]="げ",[42]="ご",[43]="ざ",[44]="じ",[45]="ず",[46]="ぜ",[47]="ぞ",[48]="だ",[49]="ぢ",[50]="づ",[51]="で",[52]="ど",[58]="ば",[59]="び",[60]="ぶ",[61]="べ",[62]="ぼ",[64]="パ",[65]="ピ",[66]="プ",[67]="ポ",[68]="ぱ",[69]="ぴ",[70]="ぷ",[71]="ぺ",[72]="ぽ",[96]="′",[97]="″",[110]="ぃ",[111]="ぅ",[112]="「",[113]="」",[114]="『",[115]="』",[116]="・",[117]="⋯",[118]="ぁ",[119]="ぇ",[120]="ぉ",[121]="┌",[122]="─",[123]="┐",[124]="│",[125]="└",[126]="┘",[127]=" ",[128]="ア",[129]="イ",[130]="ウ",[131]="エ",[132]="オ",[133]="カ",[134]="キ",[135]="ク",[136]="ケ",[137]="コ",[138]="サ",[139]="シ",[140]="ス",[141]="セ",[142]="ソ",[143]="タ",[144]="チ",[145]="ツ",[146]="テ",[147]="ト",[148]="ナ",[149]="ニ",[150]="ヌ",[151]="ネ",[152]="ノ",[153]="ハ",[154]="ヒ",[155]="フ",[156]="ホ",[157]="マ",[158]="ミ",[159]="ム",[160]="メ",[161]="モ",[162]="ヤ",[163]="ユ",[164]="ヨ",[165]="ラ",[166]="ル",[167]="レ",[168]="ロ",[169]="ワ",[170]="ヲ",[171]="ン",[172]="ッ",[173]="ャ",[174]="ュ",[175]="ョ",[176]="ィ",[177]="あ",[178]="い",[179]="う",[180]="え",[181]="お",[182]="か",[183]="き",[184]="く",[185]="け",[186]="こ",[187]="さ",[188]="し",[189]="す",[190]="せ",[191]="そ",[192]="た",[193]="ち",[194]="つ",[195]="て",[196]="と",[197]="な",[198]="に",[199]="ぬ",[200]="ね",[201]="の",[202]="は",[203]="ひ",[204]="ふ",[205]="へ",[206]="ほ",[207]="ま",[208]="み",[209]="む",[210]="め",[211]="も",[212]="や",[213]="ゆ",[214]="よ",[215]="ら",[216]="り",[217]="る",[218]="れ",[219]="ろ",[220]="わ",[221]="を",[222]="ん",[223]="っ",[224]="ゃ",[225]="ゅ",[226]="ょ",[227]="ー",[228]="ﾟ",[229]="ﾞ",[230]="？",[231]="！",[232]="。",[233]="ァ",[234]="ゥ",[235]="ェ",[236]="▷",[237]="▶",[238]="▼",[239]="♂",[240]="円",[242]="．",[243]="／",[244]="ォ",[245]="♀",[246]="０",[247]="１",[248]="２",[249]="３",[250]="４",[251]="５",[252]="６",[253]="７",[254]="８",[255]="９"}

---------------------------------------------------------------- helpers
local function chars(s)
  local t = {}
  for _, c in utf8.codes(s) do t[#t + 1] = utf8.char(c) end
  return t
end

-- sur l'écran, リ/り, ヘ/へ… sont la même tuile
local NORM = { ["リ"] = "り", ["ヘ"] = "へ", ["ベ"] = "べ", ["ペ"] = "ぺ" }
local DROP = { [" "] = true, ["　"] = true, ["…"] = true, ["⋯"] = true, ["・"] = true, ["\n"] = true, ["/"] = true }

local function normalize(s)
  s = s:gsub("<[^>]*>", "")
  local out = {}
  for _, c in ipairs(chars(s)) do
    if not DROP[c] then out[#out + 1] = NORM[c] or c end
  end
  return out
end

local function bigrams(cs)
  local set, n = {}, 0
  for i = 1, #cs - 1 do
    local b = cs[i] .. cs[i + 1]
    if not set[b] then set[b] = true; n = n + 1 end
  end
  if #cs == 1 then set[cs[1]] = true; n = 1 end
  return set, n
end

local function json_str(s)
  s = s or ""
  s = s:gsub('[%c"\\]', function(c)
    if c == '"' then return '\\"' elseif c == "\\" then return "\\\\" end
    return string.format("\\u%04x", c:byte())
  end)
  return '"' .. s .. '"'
end

local function trim(x) return ((x or ""):gsub("^%s+", ""):gsub("%s+$", "")) end
local function oneline(x) return (x:gsub("[\t\r\n]", " ")) end

---------------------------------------------------------------- dossiers
local function ensure_dir(d)
  pcall(function()
    if package.config:sub(1, 1) == "\\" then os.execute('mkdir "' .. d:gsub("/", "\\") .. '" 2>nul')
    else os.execute('mkdir -p "' .. d .. '"') end
  end)
end

---------------------------------------------------------------- texts
local rows = {}          -- {uid, id, box, jp, en, flat}
local index = {}         -- bigram -> list of row ids
local rowsize = {}
local source_info, source_error = "", ""

local function add_row(r)
  rows[#rows + 1] = r
  local cs = normalize(r.jp)
  r.flat = table.concat(cs)
  local set, nb = bigrams(cs)
  rowsize[#rows] = nb
  for b in pairs(set) do
    local l = index[b]; if not l then l = {}; index[b] = l end
    l[#l + 1] = #rows
  end
end

-- UTF-16LE (Excel "Texte Unicode") -> UTF-8
local function utf16le_to_utf8(s)
  local out, i, n = {}, 1, #s
  while i + 1 <= n do
    local c = s:byte(i) | (s:byte(i + 1) << 8); i = i + 2
    if c >= 0xD800 and c <= 0xDBFF and i + 1 <= n then
      local c2 = s:byte(i) | (s:byte(i + 1) << 8)
      if c2 >= 0xDC00 and c2 <= 0xDFFF then c = 0x10000 + ((c - 0xD800) << 10) + (c2 - 0xDC00); i = i + 2 end
    end
    out[#out + 1] = utf8.char(c)
    if #out >= 4096 then out = { table.concat(out) } end
  end
  return table.concat(out)
end

local function load_texts()
  for k in pairs(rows) do rows[k] = nil end
  for k in pairs(index) do index[k] = nil end
  for k in pairs(rowsize) do rowsize[k] = nil end
  local path = DOSSIER .. "/" .. TEXT_FILE
  local f = io.open(path, "rb")
  if not f then
    source_error = "Textes introuvables : " .. path
    console:error("Journal Crystal : " .. source_error)
    return
  end
  local raw = f:read("a"); f:close()
  if raw:sub(1, 2) == "\255\254" then raw = utf16le_to_utf8(raw:sub(3))
  elseif raw:sub(1, 3) == "\239\187\191" then raw = raw:sub(4) end
  local col, first = {}, true
  for line in raw:gmatch("[^\r\n]+") do
    local f2 = {}
    for x in (line .. "\t"):gmatch("([^\t]*)\t") do f2[#f2 + 1] = x end
    if first then
      for c, h in ipairs(f2) do col[trim(h):lower()] = c end
      first = false
    else
      local jp = (f2[col["jap"] or 4] or ""):gsub("\\n", "\n")
      if trim(jp) ~= "" then
        add_row({ uid = f2[col["uid"] or 1] or "", id = f2[col["id"] or 2] or "", box = f2[col["boîte"] or 3] or "",
                  jp = jp, kj = (col["kanji"] and f2[col["kanji"]] or ""):gsub("\\n", "\n"),
                  en = f2[col["eng"] or (col["kanji"] and 6 or 5)] or "" })
      end
    end
  end
  source_info, source_error = path, ""
  console:log(string.format("Journal Crystal : %d répliques lues dans %s", #rows, path))
end

---------------------------------------------------------------- reading the screen
local function read_name(addr)
  local s = {}
  for i = 0, 10 do
    local b = emu:read8(addr + i)
    if b == 0x50 then break end
    s[#s + 1] = CODE[b] or ""
  end
  return table.concat(s)
end

local function tile_at(x, y) return emu:read8(TILEMAP + y * 20 + x) end

local function read_box()
  -- boîte de dialogue standard : lignes 12 à 17, coins 0x79 / 0x7E ; texte en 14 et 16, (han)dakuten au-dessus
  if tile_at(0, 12) ~= 0x79 or tile_at(19, 17) ~= 0x7E then return nil end
  local lines = {}
  for _, y in ipairs({ 14, 16 }) do
    local s = {}
    for x = 1, 18 do
      local t, mark = tile_at(x, y), tile_at(x, y - 1)
      local c = TILE[t]
      if c then
        if mark == 0xE5 and VOICED[t] then c = VOICED[t]
        elseif mark == 0xE4 and SEMI[t] then c = SEMI[t] end
        s[#s + 1] = c
      end
    end
    lines[#lines + 1] = (table.concat(s):gsub("^%s+", ""):gsub("%s+$", ""))
  end
  return lines[1] .. (lines[2] ~= "" and (" / " .. lines[2]) or "")
end

---------------------------------------------------------------- matching
local state = { idx = 0, screen = "", history = {} }

local function match(screen)
  local cs = normalize(screen)
  if #cs < 3 then return nil end
  local set, n = bigrams(cs)
  local score = {}
  for b in pairs(set) do
    local l = index[b]
    if l then for _, r in ipairs(l) do score[r] = (score[r] or 0) + 1 end end
  end
  -- le texte à l'écran est un morceau continu de la bonne réplique : gros bonus s'il y est tel quel
  local pieces = {}
  for part in screen:gmatch("[^/]+") do
    local p = table.concat(normalize(part))
    if p ~= "" then pieces[#pieces + 1] = p end
  end
  local screenflat = table.concat(cs)
  local best, bestv = nil, -1
  for r, v in pairs(score) do
    local s = v / n - 0.0005 * (rowsize[r] or 0)
    local flat = rows[r].flat
    if flat and #pieces > 0 then
      local all = true
      for _, p in ipairs(pieces) do if not flat:find(p, 1, true) then all = false; break end end
      if all then s = s + 0.25 end
      -- toute la réplique est à l'écran après un préfixe (nom de dresseur…)
      if not all and #flat >= 12 and screenflat:find(flat, 1, true) then
        s = math.max(s, 0.6) + 0.25
        if screenflat:sub(-#flat) == flat then s = s + 0.1 end
      end
    end
    if r == state.idx or r == state.idx + 1 then s = s + 0.05 end   -- les répliques se suivent dans le tableau
    if s > bestv or (s == bestv and math.abs(r - state.idx) < math.abs(best - state.idx)) then
      best, bestv = r, s
    end
  end
  if best and #cs < 6 and (rowsize[best] or 0) > n + 1 then return nil end  -- trop court pour être sûr
  if best and bestv >= 0.6 then return best end
  return nil
end

-- vrai si le texte à l'écran peut encore être le début de plusieurs répliques
local function unsure(probe)
  local p = table.concat(normalize(probe))
  if p == "" then return false end
  local hits = 0
  for _, row in ipairs(rows) do
    if row.flat:find(p, 1, true) then
      hits = hits + 1
      if hits >= 2 then return true end
    end
  end
  return false
end

---------------------------------------------------------------- journal
local frame = 0
local SHOT_DIR = nil     -- dossier des captures de la session
local buffer = nil
local seen, seen_n = {}, 0
local cur = nil          -- réplique à l'écran : {r, s, shots}
local box_open = nil     -- image d'ouverture de la boîte

local function now()
  local ok, f = pcall(function() return emu:currentFrame() end)
  if ok and type(f) == "number" then return f end
  return frame
end

local journal_path = nil
local function jwrite(...)
  if not journal_path then
    ensure_dir(DOSSIER)
    journal_path = DOSSIER .. "/" .. JOURNAL_FILE
    local f = io.open(journal_path, "r")
    if f then f:close() else
      f = io.open(journal_path, "w")
      if f then f:write("Type\tUID\tID\tBoîte\tDébut\tFin\tÉcrans\tTexte\n"); f:close() end
    end
  end
  local f = io.open(journal_path, "a")
  if not f then return end
  f:write(table.concat({ ... }, "\t"), "\n")
  f:close()
end

local function close_cur(t)
  if not cur then return end
  local r = rows[cur.r]
  jwrite("R", r.uid, r.id, r.box, cur.s, math.max(t, cur.s + 1), table.concat(cur.shots, ","), oneline(r.jp))
  cur = nil
end

local function commit(r, t, st)
  if not rows[r] then return end
  if not cur or cur.r ~= r then
    st = st or t
    if cur and st <= cur.s then st = t end      -- changement de réplique au milieu d'une boîte
    close_cur(st)
    cur = { r = r, s = st, shots = {} }
  end
  if r ~= state.idx then
    if state.idx > 0 then
      table.insert(state.history, 1, state.idx)
      if #state.history > 4 then table.remove(state.history) end
    end
    state.idx = r
    if not seen[r] then seen[r] = true; seen_n = seen_n + 1 end
    if buffer then buffer:clear(); buffer:print(rows[r].jp .. "\n\n" .. rows[r].en) end
  end
end

-- texte qui reste à l'écran sans être dans le tableau : gardé quand même (journal)
local unknown, unknown_n = {}, 0
local function unknown_row(text)
  if unknown[text] then return unknown[text] end
  unknown_n = unknown_n + 1
  rows[#rows + 1] = { uid = "X" .. unknown_n, id = "(inconnu)", box = "", jp = text:gsub(" / ", "\n"), en = "",
                      flat = table.concat(normalize(text)) }
  unknown[text] = #rows
  return #rows
end

---------------------------------------------------------------- each frame
local SETTLE = 30        -- images sans changement avant de valider une réplique douteuse (0,5 s)
local SHOT_WAIT = 12     -- images sans changement avant de noter l'écran comme complet (0,2 s)
local pending, unknown_pending = nil, nil
local prev_screen, box_start = nil, nil
local scr_key, scr_f, scr_shot = nil, 0, false

local function on_frame()
  frame = frame + 1
  if frame % 3 ~= 0 then return end
  local screen = read_box()
  local t = now()
  -- boîte ouverte / fermée (sert à caler la vidéo)
  if screen and not box_open then box_open = t
  elseif not screen and box_open then jwrite("B", "", "", "", box_open, t, "", ""); box_open = nil end
  -- écran complet (le texte ne s'écrit plus) : on note l'image pour la capture
  local skey = screen and (screen:gsub("▼", "")) or nil
  if skey ~= scr_key then scr_key = skey; scr_f = frame; scr_shot = false end
  if cur and not pending and not scr_shot and skey and skey ~= "" and frame - scr_f >= SHOT_WAIT then
    scr_shot = true
    if #cur.shots < 20 then
      cur.shots[#cur.shots + 1] = t
      -- capture à la résolution du jeu, nommée par son image (colonne Écrans du journal)
      if SHOT_DIR then pcall(function() emu:screenshot(SHOT_DIR .. "/" .. t .. ".png") end) end
    end
  end
  if unknown_pending and screen == prev_screen and frame - unknown_pending.f >= SETTLE then
    local u = unknown_pending; unknown_pending = nil
    commit(unknown_row(u.text), u.t, u.st)
    return
  end
  if pending and screen == prev_screen and frame - pending.f >= SETTLE then
    local p = pending; pending = nil
    commit(p.r, p.t, p.st)
    return
  end
  if not screen then                       -- plus de boîte : la réplique se termine
    if pending and frame - pending.f >= 12 then commit(pending.r, pending.t, pending.st) end
    pending = nil; unknown_pending = nil
    close_cur(t); prev_screen, box_start = nil, nil
    return
  end
  if screen == prev_screen then return end
  if pending and screen == "" and frame - pending.f >= 12 then commit(pending.r, pending.t, pending.st) end
  pending = nil; unknown_pending = nil
  local was_empty = (prev_screen == nil or prev_screen == "")
  prev_screen = screen
  if screen == "" then box_start = nil; return end   -- boîte vidée (paragraphe suivant)
  if was_empty then box_start = t end
  state.screen = screen
  local probe = screen
  for _, nm in ipairs({ read_name(PLAYER_NAME), read_name(RIVAL_NAME) }) do
    if #nm >= 3 then probe = probe:gsub(nm:gsub("%p", "%%%0"), "") end
  end
  local r = match(probe)
  if not r then
    local text = screen:gsub("▼", ""):gsub("%s+$", "")
    if #normalize(text) >= 2 then unknown_pending = { text = text, f = frame, t = t, st = box_start } end
    return
  end
  local flatp = table.concat(normalize(probe))
  if unsure(probe) or not (rows[r].flat or ""):find(flatp, 1, true) then
    pending = { r = r, f = frame, t = t, st = box_start }; return
  end
  commit(r, t, box_start)
end

---------------------------------------------------------------- démarrage
local windows = package.config:sub(1, 1) == "\\"
local function new_session()
  local t0 = os.time()
  SHOT_DIR = DOSSIER .. "/captures/" .. os.date("%Y%m%d_%H%M%S", t0)
  ensure_dir(SHOT_DIR)
  pcall(jwrite, "SESSION", "", "", "", now(), "", "", os.date("%Y-%m-%d %H:%M:%S", t0))
end

local J = {}
local done = false
if DOSSIER == "" then
  source_error = "config.lua : dossier du journal vide"
else
  local ok, err = pcall(load_texts)
  if not ok then source_error = tostring(err); console:error("Journal Crystal : " .. source_error) end
  pcall(function() buffer = console:createBuffer("Crystal") end)
  new_session()
  console:log("Journal Crystal : " .. DOSSIER)
end

function J.image()
  if DOSSIER ~= "" and not done then on_frame() end
end
function J.reset()
  if DOSSIER == "" or done then return end
  close_cur(now()); new_session()
end
-- fin de partie : on ferme la réplique en cours et on lance le traitement (une seule fois)
function J.fin()
  if done or DOSSIER == "" then return end
  done = true
  pcall(close_cur, now())
  if box_open then pcall(jwrite, "B", "", "", "", box_open, now(), "", ""); box_open = nil end
  if AUTO_PROCESS and windows and seen_n > 0 and AFTER_SESSION ~= "" then
    local f = io.open(AFTER_SESSION, "r")
    if f then
      f:close()
      -- le .bat est lancé par cmd /c, qui enlève le premier et le dernier guillemet : on entoure d'une paire en plus
      pcall(os.execute, string.format('start "Traitement Pokemon Crystal" cmd /c ""%s" "%s" "%s""', AFTER_SESSION,
        GAME_FOLDER, (DOSSIER:gsub("/", "\\"))))
    end
  end
end
-- pour la page : où en est le journal
function J.etat()
  return { dossier = DOSSIER, vues = seen_n, repliques = #rows, erreur = source_error }
end
J.match, J.read_box, J.state, J.rows, J.close_cur = match, read_box, state, rows, close_cur   -- pour les tests
return J
