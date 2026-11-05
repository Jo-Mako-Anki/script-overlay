-- Personal settings of Script Viewer.
-- Copy this file as config.lua (in the same folder as script_viewer.lua) and edit it: config.lua is not shared.
return {
  port = 8890,          -- address read by the page: http://127.0.0.1:8890/state
  ouvrir_page = true,   -- false: never open the page by itself (otherwise: only if it is not already open)

  -- Dialogue table of a game kept somewhere else (default: Games\<game>\<game>.sop, .xlsx or table.xlsx).
  tableaux = {
    -- ["Pokemon Crystal"] = [[C:\Jeux\Pokemon Crystal\Pokemon Crystal.xlsx]],
  },

  -- Log of the lines and screenshots (to make subtitles or Anki cards), per game.
  -- Remove the two dashes in front of each line to turn it on.
  journal = {
    -- ["Pokemon Crystal"] = {
    --   dossier = [[C:\Jeux\Pokemon Crystal\mGBA]],   -- texts (Pokemon Crystal.txt), journal.tsv, captures\
    --   dossier_jeu = [[C:\Jeux\Pokemon Crystal]],     -- passed to the end-of-session processing
    --   traitement = [[C:\Jeux\traiter_session.bat]],  -- run at the end of the session if auto = true
    --   auto = false,
    -- },
  },
}
