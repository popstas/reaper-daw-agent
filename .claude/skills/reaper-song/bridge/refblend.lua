-- Тело refblend.sh: таблицу A собирает refblend.sh перед этим кодом (proj, file, soffs, ref_db, mix_db, name, bus).
-- Чужой мастер поверх нашего, как blend.py, но в проекте: все треки уходят в папку A.bus, цепочка мастера
-- переезжает на неё (лимитер жмёт только наш микс), фейдер папки A.mix_db; чужой мастер - трек A.name после папки,
-- айтем файла A.file с позиции 0 и SOFFS A.soffs, фейдер A.ref_db. Мастер проекта остаётся без FX, фейдер не трогается.
-- Одним undo-шагом «reaper-song refblend», сохранение. Проект с несохранёнными правками не трогается.
local proj, path
local i = 0
while true do
  local p, f = reaper.EnumProjects(i)
  if not p then break end
  if f:find(A.proj, 1, true) then
    if proj then error("под «" .. A.proj .. "» несколько вкладок") end
    proj, path = p, f
  end
  i = i + 1
end
if not proj then error("нет открытой вкладки с «" .. A.proj .. "»") end
reaper.SelectProjectInstance(proj)
if reaper.IsProjectDirty(0) == 1 then error("в проекте несохранённые правки, сначала сохранить: " .. path) end
local dir = path:match("^(.*)[\\/]")
local full = A.file:find("^%a:[\\/]") and A.file or (dir .. "\\" .. A.file)
if not reaper.file_exists(full) then error("нет файла " .. full) end
for k = 0, reaper.CountTracks(0) - 1 do
  local _, n = reaper.GetTrackName(reaper.GetTrack(0, k))
  if n == A.bus or n == A.name then error("трек «" .. n .. "» уже есть - refblend уже сделан?") end
end
out("project", path)

reaper.Undo_BeginBlock()
reaper.PreventUIRefresh(1)
local ok, err = pcall(function()
  local n = reaper.CountTracks(0)
  -- папка: новый трек 0 открывает её, последний трек закрывает на один уровень больше
  reaper.InsertTrackAtIndex(0, false)
  local bus = reaper.GetTrack(0, 0)
  reaper.GetSetMediaTrackInfo_String(bus, "P_NAME", A.bus, true)
  reaper.SetMediaTrackInfo_Value(bus, "I_FOLDERDEPTH", 1)
  local last = reaper.GetTrack(0, n)
  reaper.SetMediaTrackInfo_Value(last, "I_FOLDERDEPTH", reaper.GetMediaTrackInfo_Value(last, "I_FOLDERDEPTH") - 1)
  -- цепочка мастера - на папку, по порядку; выключенные звенья остаются выключенными
  local m = reaper.GetMasterTrack(0)
  local moved = 0
  while reaper.TrackFX_GetCount(m) > 0 do
    reaper.TrackFX_CopyToTrack(m, 0, bus, moved, true); moved = moved + 1
  end
  reaper.SetMediaTrackInfo_Value(bus, "D_VOL", 10 ^ (A.mix_db / 20))
  out("bus", A.bus, "FX с мастера: " .. moved, string.format("фейдер %+.1f dB", A.mix_db))
  -- чужой мастер после папки
  reaper.InsertTrackAtIndex(n + 1, false)
  local ref = reaper.GetTrack(0, n + 1)
  reaper.GetSetMediaTrackInfo_String(ref, "P_NAME", A.name, true)
  reaper.SetMediaTrackInfo_Value(ref, "D_VOL", 10 ^ (A.ref_db / 20))
  local src = reaper.PCM_Source_CreateFromFile(full)
  if not src then error("REAPER не открыл " .. full) end
  local len = reaper.GetMediaSourceLength(src) - A.soffs
  local it = reaper.AddMediaItemToTrack(ref)
  local tk = reaper.AddTakeToMediaItem(it)
  reaper.SetMediaItemTake_Source(tk, src)
  reaper.SetMediaItemTakeInfo_Value(tk, "D_STARTOFFS", A.soffs)
  reaper.SetMediaItemInfo_Value(it, "D_POSITION", 0)
  reaper.SetMediaItemInfo_Value(it, "D_LENGTH", len)
  reaper.GetSetMediaItemTakeInfo_String(tk, "P_NAME", A.file:match("[^\\/]+$"), true)
  out("ref", A.name, A.file, string.format("SOFFS %.6f, длина %.2f, фейдер %+.1f dB", A.soffs, len, A.ref_db))
end)
reaper.PreventUIRefresh(-1)
reaper.Undo_EndBlock("reaper-song refblend", -1)
if not ok then
  if reaper.Undo_CanUndo2(0) == "reaper-song refblend" then reaper.Undo_DoUndo2(0) end
  error("не применено: " .. tostring(err))
end
reaper.TrackList_AdjustWindows(false)
reaper.UpdateArrange()
reaper.Main_SaveProject(0, false)
out("saved, dirty", reaper.IsProjectDirty(0))
