-- Временные правки на время рендера, одна реализация для render.lua и stems.lua.
-- Каждая правка ставит свой откат через temp_push; temp_restore() откатывает в обратном порядке.
-- Подключается render.sh / freeze.sh перед телом рендера: функции глобальные в окружении мост-вызова.
local undo = {}
function temp_push(f) undo[#undo + 1] = f end

function temp_restore()
  for i = #undo, 1, -1 do
    local ok, e = pcall(undo[i])
    if not ok then out("откат не удался: " .. tostring(e)) end
  end
  undo = {}
end

function temp_trackinfo(tr, key, v)
  local old = reaper.GetMediaTrackInfo_Value(tr, key)
  temp_push(function() reaper.SetMediaTrackInfo_Value(tr, key, old) end)
  reaper.SetMediaTrackInfo_Value(tr, key, v)
end

function temp_fx_enabled(tr, idx, on)
  local old = reaper.TrackFX_GetEnabled(tr, idx)
  temp_push(function() reaper.TrackFX_SetEnabled(tr, idx, old) end)
  reaper.TrackFX_SetEnabled(tr, idx, on)
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
  temp_push(function() reaper.TrackFX_Delete(tr, idx) end)
end

-- правки render.sh: addfx, solo, mute, nomaster, bypass, set, vol, itemvol
function temp_apply(A)
  for _, a in ipairs(A.addfx or {}) do addfx(a) end
  for _, n in ipairs(A.solo or {}) do temp_trackinfo(track(n), "I_SOLO", 1) end
  for _, m in ipairs(A.mute or {}) do temp_trackinfo(track(m[1]), "B_MUTE", m[2]); out("mute", m[1], m[2]) end
  if A.nomaster then temp_trackinfo(reaper.GetMasterTrack(0), "I_FXEN", 0) end
  for _, b in ipairs(A.bypass or {}) do
    local tr, i = fx(b[1], b[2])
    temp_fx_enabled(tr, i, false)
  end
  for _, s in ipairs(A.set or {}) do
    local tr, i = fx(s[1], s[2])
    local p = tonumber(s[3]) or param(tr, i, s[3])
    local old = reaper.TrackFX_GetParam(tr, i, p)
    temp_push(function() reaper.TrackFX_SetParam(tr, i, p, old) end)
    reaper.TrackFX_SetParam(tr, i, p, s[4])
    local _, nm = reaper.TrackFX_GetFXName(tr, i, "")
    local _, pn = reaper.TrackFX_GetParamName(tr, i, p, "")
    local _, fv = reaper.TrackFX_GetFormattedParamValue(tr, i, p, "")
    out("set", s[1], nm, p .. " " .. pn, fv)
  end
  for _, v in ipairs(A.vol or {}) do temp_trackinfo(track(v[1]), "D_VOL", 10 ^ (v[2] / 20)); out("vol", v[1], v[2]) end
  for _, v in ipairs(A.itemvol or {}) do
    local tr = track(v[1])
    for k = 0, reaper.CountTrackMediaItems(tr) - 1 do
      local it = reaper.GetTrackMediaItem(tr, k)
      local old = reaper.GetMediaItemInfo_Value(it, "D_VOL")
      temp_push(function() reaper.SetMediaItemInfo_Value(it, "D_VOL", old) end)
      reaper.SetMediaItemInfo_Value(it, "D_VOL", 10 ^ (v[2] / 20))
    end
    out("itemvol", v[1], v[2], reaper.CountTrackMediaItems(tr) .. " айтемов")
  end
end

-- настройки рендера проекта и выделение треков: запомнить и поставить на откат
function temp_render_settings()
  for _, k in ipairs({"RENDER_SETTINGS", "RENDER_BOUNDSFLAG"}) do
    local v = reaper.GetSetProjectInfo(0, k, 0, false)
    temp_push(function() reaper.GetSetProjectInfo(0, k, v, true) end)
  end
  for _, k in ipairs({"RENDER_FORMAT", "RENDER_FILE", "RENDER_PATTERN"}) do
    local _, v = reaper.GetSetProjectInfo_String(0, k, "", false)
    temp_push(function() reaper.GetSetProjectInfo_String(0, k, v, true) end)
  end
  local sel = {}
  for i = 0, reaper.CountTracks(0) - 1 do
    local tr = reaper.GetTrack(0, i); sel[#sel + 1] = {tr, reaper.IsTrackSelected(tr)}
  end
  temp_push(function() for _, s in ipairs(sel) do reaper.SetTrackSelected(s[1], s[2]) end end)
end

-- откатить всё; проект, сохранённый до рендера, пересохранить, если откат сделал его dirty
function temp_finish(dirty0)
  temp_restore()
  if dirty0 == 0 and reaper.IsProjectDirty(0) == 1 then reaper.Main_SaveProject(0, false); out("правки возвращены, проект пересохранён") end
  out("dirty", reaper.IsProjectDirty(0))
end

-- MT-PowerDrumKit сам помечает проект изменённым (undo «Edit FX parameter: … MT-PowerDrumKit»), в файле при этом меняется
-- только время сохранения. Такой dirty - не правка пользователя: сохранить перед рендером (решение пользователя 21.11).
function temp_save_drumkit_dirty()
  if reaper.IsProjectDirty(0) == 1 and (reaper.Undo_CanUndo2(0) or ""):find("MT%-PowerDrumKit") then
    reaper.Main_SaveProject(0, false)
    out("сохранён: последний шаг undo - параметр MT-PowerDrumKit, плагин меняет его сам")
  end
end
