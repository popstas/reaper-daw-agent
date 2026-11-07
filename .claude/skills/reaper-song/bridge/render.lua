-- Тело рендера для render.sh: таблицу A собирает render.sh перед этим кодом.
-- Ставит временные правки, рендерит по настройкам проекта (42230), уносит файл в <имя>.<ext>, всё возвращает.
local undo = {}
local function push(f) undo[#undo + 1] = f end
local dirty0 = reaper.IsProjectDirty(0)
local _, target = reaper.GetSetProjectInfo_String(0, "RENDER_TARGETS", "", false)
if target == "" or target:find(";") then error("цель рендера не одна: " .. target) end
local dest = target:match("^(.*\\)") .. A.name .. (target:match("%.%w+$") or "")

local function trackinfo(tr, key, v)
  local old = reaper.GetMediaTrackInfo_Value(tr, key)
  push(function() reaper.SetMediaTrackInfo_Value(tr, key, old) end)
  reaper.SetMediaTrackInfo_Value(tr, key, v)
end

local ok, err = pcall(function()
  for _, n in ipairs(A.solo) do trackinfo(track(n), "I_SOLO", 1) end
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

  -- чужой файл с именем цели убрать на время рендера, иначе REAPER спросит про перезапись и мост повиснет
  if reaper.file_exists(target) then
    local keep = target .. ".keep"
    os.remove(keep); assert(os.rename(target, keep))
    push(function() os.rename(keep, target) end)
  end
  reaper.Main_OnCommand(40101, 0) -- Set all media online: без фокуса окна REAPER отключает медиа и рендер выходит тишиной
  local t0 = reaper.time_precise()
  reaper.Main_OnCommand(42230, 0)
  out("render_s", string.format("%.1f", reaper.time_precise() - t0))
  os.remove(dest) -- os.rename в Windows не пишет поверх существующего
  local r, e = os.rename(target, dest)
  if not r then error("файл рендера не найден: " .. tostring(e)) end
  out("DEST", dest)
end)
for i = #undo, 1, -1 do undo[i]() end
if not ok then error(err) end
if dirty0 == 0 and reaper.IsProjectDirty(0) == 1 then reaper.Main_SaveProject(0, false); out("правки возвращены, проект пересохранён") end
out("dirty", reaper.IsProjectDirty(0))
