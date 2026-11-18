-- Тело рендера для render.sh: таблицу A собирает render.sh перед этим кодом.
-- Ставит временные правки, рендерит по настройкам проекта (42230), уносит файл в <имя>.<ext>, всё возвращает.
local undo = {}
local function push(f) undo[#undo + 1] = f end
local dirty0 = reaper.IsProjectDirty(0)
local _, target = reaper.GetSetProjectInfo_String(0, "RENDER_TARGETS", "", false)
if target == "" or target:find(";") then error("цель рендера не одна: " .. target) end
local dest = A.final and target or target:match("^(.*\\)") .. A.name .. (target:match("%.%w+$") or "")

local function trackinfo(tr, key, v)
  local old = reaper.GetMediaTrackInfo_Value(tr, key)
  push(function() reaper.SetMediaTrackInfo_Value(tr, key, old) end)
  reaper.SetMediaTrackInfo_Value(tr, key, v)
end

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
  for _, a in ipairs(A.addfx or {}) do
    local tr, idx = addfx(a)
    push(function() reaper.TrackFX_Delete(tr, idx) end)
  end
  for _, n in ipairs(A.solo) do trackinfo(track(n), "I_SOLO", 1) end
  for _, m in ipairs(A.mute or {}) do trackinfo(track(m[1]), "B_MUTE", m[2]); out("mute", m[1], m[2]) end
  if A.nomaster then trackinfo(reaper.GetMasterTrack(0), "I_FXEN", 0) end
  for _, b in ipairs(A.bypass) do
    local tr, i = fx(b[1], b[2])
    local old = reaper.TrackFX_GetEnabled(tr, i)
    push(function() reaper.TrackFX_SetEnabled(tr, i, old) end)
    reaper.TrackFX_SetEnabled(tr, i, false)
  end
  for _, s in ipairs(A.set) do
    local tr, i = fx(s[1], s[2])
    local p = tonumber(s[3]) or param(tr, i, s[3])
    local old = reaper.TrackFX_GetParam(tr, i, p)
    push(function() reaper.TrackFX_SetParam(tr, i, p, old) end)
    reaper.TrackFX_SetParam(tr, i, p, s[4])
    local _, nm = reaper.TrackFX_GetFXName(tr, i, "")
    local _, pn = reaper.TrackFX_GetParamName(tr, i, p, "")
    local _, fv = reaper.TrackFX_GetFormattedParamValue(tr, i, p, "")
    out("set", s[1], nm, p .. " " .. pn, fv)
  end
  for _, v in ipairs(A.vol) do trackinfo(track(v[1]), "D_VOL", 10 ^ (v[2] / 20)); out("vol", v[1], v[2]) end
  for _, v in ipairs(A.itemvol) do
    local tr = track(v[1])
    for k = 0, reaper.CountTrackMediaItems(tr) - 1 do
      local it = reaper.GetTrackMediaItem(tr, k)
      local old = reaper.GetMediaItemInfo_Value(it, "D_VOL")
      push(function() reaper.SetMediaItemInfo_Value(it, "D_VOL", old) end)
      reaper.SetMediaItemInfo_Value(it, "D_VOL", 10 ^ (v[2] / 20))
    end
    out("itemvol", v[1], v[2], reaper.CountTrackMediaItems(tr) .. " айтемов")
  end

  -- чужой файл с именем цели убрать на время рендера, иначе REAPER спросит про перезапись и мост повиснет
  local old = target .. ".old"
  if reaper.file_exists(target) then
    os.remove(old); assert(os.rename(target, old))
    if not A.final then push(function() os.rename(old, target) end) end
  end
  reaper.Main_OnCommand(40101, 0) -- Set all media online: без фокуса окна REAPER отключает медиа и рендер выходит тишиной
  local t0 = reaper.time_precise()
  reaper.Main_OnCommand(42230, 0)
  out("render_s", string.format("%.1f", reaper.time_precise() - t0))
  if not reaper.file_exists(target) then
    if A.final and reaper.file_exists(old) then os.rename(old, target) end
    error("файл рендера не найден: " .. target)
  end
  if A.final then
    os.remove(old) -- прежний итоговый рендер заменён
    -- копия под латинским именем: scp до nb путь с пробелами и кириллицей не разбирает
    local tmp = target:match("^(.*\\)") .. "reaper-song-final" .. (target:match("%.%w+$") or "")
    local fi = assert(io.open(target, "rb")); local data = fi:read("a"); fi:close()
    local fo = assert(io.open(tmp, "wb")); fo:write(data); fo:close()
    out("FINAL", target)
    dest = tmp
  else
    os.remove(dest) -- os.rename в Windows не пишет поверх существующего
    local r, e = os.rename(target, dest)
    if not r then error("файл рендера не переименован: " .. tostring(e)) end
  end
  out("DEST", dest)
end)
for i = #undo, 1, -1 do undo[i]() end
if not ok then error(err) end
if dirty0 == 0 and reaper.IsProjectDirty(0) == 1 then reaper.Main_SaveProject(0, false); out("правки возвращены, проект пересохранён") end
out("dirty", reaper.IsProjectDirty(0))
