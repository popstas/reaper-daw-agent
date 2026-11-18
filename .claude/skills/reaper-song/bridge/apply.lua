-- Тело apply.sh: таблицу A собирает apply.sh перед этим кодом.
-- Выбирает вкладку по части пути, применяет правки одним undo-шагом, сохраняет проект.
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
out("project", path)

reaper.Undo_BeginBlock()
local function addfx(a)
  -- a = {трек, имя для TrackFX_AddByName ("JS:guitar/chorus"), после какого FX (подстрока) или nil}
  local tr = track(a[1])
  local idx = reaper.TrackFX_AddByName(tr, a[2], false, -1)
  if idx < 0 then error("FX не найден: " .. a[2]) end
  if a[3] then
    local _, after = fx(tr, a[3])
    if after + 1 ~= idx then reaper.TrackFX_CopyToTrack(tr, idx, tr, after + 1, true); idx = after + 1 end
  end
  local _, nm = reaper.TrackFX_GetFXName(tr, idx, "")
  out("addfx", a[1], nm, "позиция " .. (idx + 1))
  return tr, idx
end
local ok, err = pcall(function()
  for _, a in ipairs(A.addfx or {}) do addfx(a) end
  for _, s in ipairs(A.set) do
    local tr, k = fx(s[1], s[2])
    local p = tonumber(s[3]) or param(tr, k, s[3])
    local _, was = reaper.TrackFX_GetFormattedParamValue(tr, k, p, "")
    reaper.TrackFX_SetParam(tr, k, p, s[4])
    local _, nm = reaper.TrackFX_GetFXName(tr, k, "")
    local _, pn = reaper.TrackFX_GetParamName(tr, k, p, "")
    local _, now = reaper.TrackFX_GetFormattedParamValue(tr, k, p, "")
    out("set", s[1], nm, p .. " " .. pn, was .. " -> " .. now)
  end
  for _, v in ipairs(A.vol) do
    local tr = track(v[1])
    local was = db(reaper.GetMediaTrackInfo_Value(tr, "D_VOL"))
    reaper.SetMediaTrackInfo_Value(tr, "D_VOL", 10 ^ (v[2] / 20))
    out("vol", v[1], string.format("%.1f -> %.1f dB", was, v[2]))
  end
  for _, v in ipairs(A.itemvol) do
    local tr = track(v[1])
    for k = 0, reaper.CountTrackMediaItems(tr) - 1 do
      local it = reaper.GetTrackMediaItem(tr, k)
      local was = db(reaper.GetMediaItemInfo_Value(it, "D_VOL"))
      reaper.SetMediaItemInfo_Value(it, "D_VOL", 10 ^ (v[2] / 20))
      out("itemvol", v[1], "айтем " .. (k + 1), string.format("%.1f -> %.1f dB", was, v[2]))
    end
  end
end)
reaper.Undo_EndBlock("reaper-song apply", -1)
if not ok then
  -- пустой блок undo-шага не создаёт: откатывать только свой, иначе уйдёт правка пользователя
  if reaper.Undo_CanUndo2(0) == "reaper-song apply" then reaper.Undo_DoUndo2(0) end
  error("не применено: " .. tostring(err))
end
reaper.UpdateArrange()
reaper.Main_SaveProject(0, false)
out("saved, dirty", reaper.IsProjectDirty(0))
