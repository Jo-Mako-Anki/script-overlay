-- Script Viewer : envoie le texte affiché à l'écran (et les infos du jeu) à la page « Script Viewer.html ».
-- mGBA 0.10+ : Outils > Scripting > Fichier > Charger le script > script_viewer.lua
-- Le script reconnaît le jeu (titre de la ROM, voir Games\list.lua) et charge Games\<jeu>\reader.lua.
-- La page s'ouvre toute seule ; elle lit http://127.0.0.1:8890/state, et /tableau pour le tableau des dialogues du jeu.
-- Réglages personnels (port, journal, tableaux…) : config.lua, à créer en copiant config.exemple.lua.

---------------------------------------------------------------- dossiers
local function script_dir()
  local ok0, d0 = pcall(function() return script and script.dir end)
  if ok0 and type(d0) == "string" and d0 ~= "" then return d0 end
  local ok, info = pcall(function() return debug.getinfo(1, "S") end)
  if ok and type(info) == "table" then
    for _, src in ipairs({ info.source or "", info.short_src or "" }) do
      src = src:gsub("^[@=]", "")
      local d = src:match("^(.*)[/\\][^/\\]*$")
      if d and d ~= "" and src:lower():match("%.lua$") then return d end
    end
  end
  return "."
end
local DIR = script_dir()

-- comme dofile, en passant des arguments au fichier chargé
function run_file(path, ...)
  local f = io.open(path, "rb")
  if not f then error("file not found: " .. path) end
  local src = f:read("a"); f:close()
  local chunk, err = load(src, "@" .. path)
  if not chunk then error(err) end
  return chunk(...)
end
JEUX = DIR .. "/../Games"  -- dossier Games commun à Script Overlay (un sous-dossier par jeu)

-- réglages personnels : config.lua (facultatif)
CONFIG = {}
do
  local f = io.open(DIR .. "/config.lua", "rb")
  if f then
    f:close()
    local okc, c = pcall(run_file, DIR .. "/config.lua")
    if okc and type(c) == "table" then CONFIG = c
    else console:error("Script Viewer : config.lua illisible : " .. tostring(c)) end
  end
end
local PORT = tonumber(CONFIG.port) or 8890
local OPEN_PAGE = CONFIG.ouvrir_page ~= false   -- false : ne pas ouvrir la page au chargement du script

---------------------------------------------------------------- état envoyé à la page
local state = { title = "", code = "", reader = "", screen = "", seq = 0, frame = 0, error = "" }
local reader = nil
local frame, last = 0, nil   -- compteur d'images, dernier texte envoyé

local function json_str(s)
  s = tostring(s or "")
  s = s:gsub('[%c"\\]', function(c)
    if c == '"' then return '\\"' elseif c == "\\" then return "\\\\" elseif c == "\n" then return "\\n"
    elseif c == "\t" then return "\\t" else return string.format("\\u%04x", c:byte()) end
  end)
  return '"' .. s .. '"'
end
-- balises du tableau propres au jeu (ex. <NI> = に), données par le lecteur : la page les remplace avant de comparer
local function tags_json()
  local t = {}
  if reader and type(reader.balises) == "table" then
    for k, v in pairs(reader.balises) do t[#t + 1] = json_str(k) .. ":" .. json_str(v) end
  end
  table.sort(t)
  return "{" .. table.concat(t, ",") .. "}"
end
-- tables Lua -> JSON (pour les infos du jeu : équipe, carte…)
local function to_json(v)
  local t = type(v)
  if t == "number" then return (v == math.floor(v)) and string.format("%d", v) or tostring(v)
  elseif t == "string" then return json_str(v)
  elseif t == "boolean" then return tostring(v)
  elseif t == "table" then
    local out = {}
    if #v > 0 or next(v) == nil then
      for _, x in ipairs(v) do out[#out + 1] = to_json(x) end
      return "[" .. table.concat(out, ",") .. "]"
    end
    for k, x in pairs(v) do out[#out + 1] = json_str(k) .. ":" .. to_json(x) end
    return "{" .. table.concat(out, ",") .. "}"
  end
  return "null"
end
local function infos_json()
  if not reader or type(reader.infos) ~= "function" then return "null" end
  local ok, t = pcall(reader.infos)
  if not ok then return to_json({ erreur = tostring(t) }) end
  return to_json(t)
end
-- journal du jeu (si le lecteur en a un et que config.lua l'active)
local function journal() return reader and type(reader.journal) == "table" and reader.journal or nil end
local function journal_json()
  local j = journal()
  if not j or type(j.etat) ~= "function" then return "null" end
  local ok, t = pcall(j.etat)
  return ok and to_json(t) or to_json({ erreur = tostring(t) })
end
-- tableau des dialogues du jeu : config.lua > tableaux["<jeu>"], sinon Games\<jeu>\<jeu>.xlsx ou Games\<jeu>\tableau.xlsx
-- (ou .sop = fichier de jeu de Script Overlay, en premier ; ou .xlsm, .csv, .tsv, .txt)
local tableau = nil   -- {chemin, nom, taille}
local function file_size(path)
  local f = io.open(path, "rb")
  if not f then return nil end
  local n = f:seek("end"); f:close()
  return n
end
local function find_table(dossier)
  local cands = {}
  if type(CONFIG.tableaux) == "table" and type(CONFIG.tableaux[dossier]) == "string" then cands[1] = CONFIG.tableaux[dossier] end
  for _, nom in ipairs({ dossier, "tableau" }) do
    for _, ext in ipairs({ "sop", "xlsx", "xlsm", "csv", "tsv", "txt" }) do cands[#cands + 1] = JEUX .. "/" .. dossier .. "/" .. nom .. "." .. ext end
  end
  for _, c in ipairs(cands) do
    local n = file_size(c)
    if n then return { chemin = c, nom = c:match("([^/\\]+)$"), taille = n } end
  end
  return nil
end
local function state_json()
  return string.format('{"title":%s,"code":%s,"reader":%s,"screen":%s,"seq":%d,"frame":%d,"error":%s,"tags":%s,"infos":%s,"journal":%s,"tableau":%s}',
    json_str(state.title), json_str(state.code), json_str(state.reader), json_str(state.screen), state.seq, state.frame,
    json_str(state.error), tags_json(), infos_json(), journal_json(),
    tableau and to_json({ nom = tableau.nom, taille = tableau.taille }) or "null")
end

---------------------------------------------------------------- lecteur du jeu en cours
local function trim(x) return ((x or ""):gsub("^%s+", ""):gsub("%s+$", "")) end

local function end_journal()
  local j = journal()
  if j and j.fin then
    local ok, e = pcall(j.fin)
    if not ok then console:error("Journal : " .. tostring(e)) end
  end
end

local function load_reader()
  end_journal()
  reader, last, tableau = nil, nil, nil
  state.reader, state.error, state.screen = "", "", ""
  local okt, title = pcall(function() return emu:getGameTitle() end)
  local okc, code = pcall(function() return emu:getGameCode() end)
  state.title = okt and trim(title) or ""
  state.code = okc and trim(code) or ""
  if state.title == "" and state.code == "" then state.error = "No game loaded"; return end
  console:log("Script Viewer: game \"" .. state.title .. "\" (code " .. state.code .. ")")
  local okl, list = pcall(run_file, JEUX .. "/list.lua")
  if not okl or type(list) ~= "table" then
    state.error = "Games\\list.lua not found or unreadable: " .. tostring(list)
    console:error("Script Viewer : " .. state.error); return
  end
  local T, C = state.title:upper(), state.code:upper()
  for _, e in ipairs(list) do
    local hit = false
    for _, t in ipairs(e.titres or {}) do if t:upper() == T then hit = true end end
    for _, c in ipairs(e.codes or {}) do if C:find(c:upper(), 1, true) then hit = true end end
    if hit then
      local d = JEUX .. "/" .. e.dossier
      local okr, r = pcall(run_file, d .. "/reader.lua", d)
      if okr and type(r) == "table" and type(r.lire) == "function" then
        reader = r; state.reader = e.dossier
        console:log("Script Viewer: game recognised, folder Games\\" .. e.dossier)
        tableau = find_table(e.dossier)
        if tableau then console:log("Script Viewer: table " .. tableau.chemin) end
      else
        state.error = "Games\\" .. e.dossier .. "\\reader.lua : " .. tostring(r)
        console:error("Script Viewer : " .. state.error)
      end
      return
    end
  end
  state.error = "No reader for this game yet (" .. state.title .. ", " .. state.code .. ")"
  console:warn("Script Viewer: " .. state.error .. " ; ask Claude to write one.")
end

local function on_frame()
  frame = frame + 1
  if tableau and frame % 120 == 0 then tableau.taille = file_size(tableau.chemin) or tableau.taille end   -- tableau mis à jour ?
  local j = journal()
  if j and j.image then
    local ok, e = pcall(j.image)
    if not ok and not SV_JERR then SV_JERR = true; console:error("Journal : " .. tostring(e)) end
  end
  if not reader or frame % 3 ~= 0 then return end
  local ok, text = pcall(reader.lire)
  if not ok then
    if state.error == "" then state.error = "Read error: " .. tostring(text); console:error("Script Viewer : " .. state.error) end
    return
  end
  text = text and trim(text) or ""
  if text ~= last then
    last = text
    state.screen = text
    state.seq = state.seq + 1
    local okf, f = pcall(function() return emu:currentFrame() end)
    state.frame = okf and f or frame
  end
end

---------------------------------------------------------------- petit serveur HTTP
local server, clients, next_id = nil, {}, 1
local last_poll = 0   -- dernière fois que la page a demandé /state (la page demande toutes les 0,25 s quand elle est ouverte)

-- envoi en plusieurs fois, sans bloquer le jeu : la suite part aux images suivantes
local function close(id)
  local c = clients[id]; clients[id] = nil
  if c then c.sock:close() end
end
local function pump(id)
  local c = clients[id]; if not c or not c.out then return end
  for _ = 1, 64 do
    if c.pos > #c.out then close(id); return end
    local lastb, err = c.sock:send(c.out, c.pos, math.min(c.pos + 16383, #c.out))
    if lastb then c.pos = lastb + 1
    elseif err == socket.ERRORS.AGAIN then return
    else
      if not SV_SENDERR then SV_SENDERR = true; console:warn("Script Viewer: send interrupted (" .. tostring(err) .. ")") end
      close(id); return
    end
  end
end
local function reply(id, ctype, body)
  local c = clients[id]; if not c then return end
  c.out = "HTTP/1.1 200 OK\r\nContent-Type: " .. ctype .. "\r\nCache-Control: no-store\r\n" ..
    "Access-Control-Allow-Origin: *\r\nAccess-Control-Allow-Private-Network: true\r\nConnection: close\r\nContent-Length: " ..
    #body .. "\r\n\r\n" .. body
  c.pos = 1
  pump(id)
end
local function on_data(id)
  local c = clients[id]; if not c or c.out then return end
  while true do
    local p, err = c.sock:receive(2048)
    if p then c.buf = c.buf .. p
    else
      if err ~= socket.ERRORS.AGAIN then close(id); return end
      break
    end
  end
  if not c.buf:find("\r\n\r\n", 1, true) then return end
  local path = c.buf:match("^GET%s+(%S+)") or "/"
  if path:sub(1, 8) == "/tableau" and tableau then
    -- le tableau part en morceaux de 32 Ko (/tableau?de=0, ?de=32768…) : chaque réponse reste petite
    local de = tonumber(path:match("[?&]de=(%d+)")) or 0
    local f = io.open(tableau.chemin, "rb")
    local body = ""
    if f then f:seek("set", de); body = f:read(32768) or ""; f:close() end
    reply(id, "application/octet-stream", body)
  else
    last_poll = os.time()
    reply(id, "application/json; charset=utf-8", state_json())
  end
end
-- toutes les connexions en attente d'un coup : avec deux pages ouvertes, l'événement n'arrive qu'une fois pour
-- deux connexions, et la 2e restait sans réponse (le tableau n'arrivait pas en entier)
local function on_accept()
  for _ = 1, 16 do
    local sock = server:accept()
    if not sock then return end
    local id = next_id; next_id = next_id + 1
    clients[id] = { sock = sock, buf = "" }
    sock:add("received", function() on_data(id) end)
    sock:add("error", function() close(id) end)
  end
end
local function start_server()
  local err
  server, err = socket.bind("127.0.0.1", PORT)
  if not server then server, err = socket.bind(nil, PORT) end
  if not server then console:error("Script Viewer: port " .. PORT .. " already in use (" .. tostring(err) .. ")"); return end
  local _
  _, err = server:listen()
  if err then console:error("listen: " .. tostring(err)); return end
  server:add("received", on_accept)
  console:log("Script Viewer: ready on http://127.0.0.1:" .. PORT .. "/state")
end

---------------------------------------------------------------- démarrage
local ok, err = pcall(start_server)
if not ok then console:error("Server: " .. tostring(err)) end
if emu then pcall(load_reader) else state.error = "No game loaded" end
callbacks:add("start", function() pcall(load_reader) end)
callbacks:add("reset", function()
  last = nil
  local j = journal()
  if j and j.reset then pcall(j.reset) end
end)
callbacks:add("shutdown", end_journal)
callbacks:add("stop", end_journal)
callbacks:add("frame", function()
  if server then pcall(on_accept) end   -- au cas où l'événement de connexion n'est pas arrivé
  for id, c in pairs(clients) do if c.out then pump(id) end end
  local ok2, e2 = pcall(on_frame)
  if not ok2 and not TJ_ERR then TJ_ERR = true; console:error("Script Viewer: " .. tostring(e2)) end
end)

-- la page s'ouvre seulement si elle ne l'est pas déjà (ex. ouverte par Script Overlay) : on attend 3 s qu'elle se manifeste
if OPEN_PAGE and package.config:sub(1, 1) == "\\" then
  local t0 = os.time()
  callbacks:add("frame", function()
    if t0 and os.time() - t0 >= 3 then
      t0 = nil
      if os.time() - last_poll > 3 then
        local page = (DIR .. "/Script Viewer.html"):gsub("/", "\\")
        pcall(os.execute, 'start "" "' .. page .. '"')
      end
    end
  end)
end
