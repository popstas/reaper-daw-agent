-- Временные правки на время рендера, одна реализация для render.lua и stems.lua.
-- Каждая правка ставит свой откат через temp_push; temp_restore() откатывает в обратном порядке.
-- Подключается render.sh / freeze.sh перед телом рендера: функции глобальные в окружении мост-вызова.
local undo = {}
function temp_push(f) undo[#undo + 1] = f end

-- true - всё откатилось; false - какой-то откат не удался (напечатан)
function temp_restore()
  local all = true
  for i = #undo, 1, -1 do
    local ok, e = pcall(undo[i])
    if not ok then out("откат не удался: " .. tostring(e)); all = false end
  end
  undo = {}
  return all
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
  local cur = {idx = reaper.TrackFX_AddByName(tr, a[2], false, -1)}
  if cur.idx < 0 then error("FX не найден: " .. a[2]) end
  temp_push(function() reaper.TrackFX_Delete(tr, cur.idx) end)   -- сразу: ошибка в поиске @ПОСЛЕ не оставит FX в проекте
  if a[3] then
    local _, after = fx(tr, a[3])
    if after + 1 ~= cur.idx then reaper.TrackFX_CopyToTrack(tr, cur.idx, tr, after + 1, true); cur.idx = after + 1 end
  end
  local _, nm = reaper.TrackFX_GetFXName(tr, cur.idx, "")
  out("addfx", a[1], nm, "позиция " .. (cur.idx + 1))
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
-- откатить всё; проект, сохранённый до рендера, пересохранить, если откат сделал его dirty.
-- Если какой-то откат не удался - не сохранять: проект остаётся dirty, его можно закрыть без сохранения или откатить undo
function temp_finish(dirty0)
  local all = temp_restore()
  if dirty0 == 0 and reaper.IsProjectDirty(0) == 1 then
    if all then reaper.Main_SaveProject(0, false); out("правки возвращены, проект пересохранён")
    else out("ВНИМАНИЕ: не все временные правки вернулись, проект НЕ сохранён - проверить и закрыть без сохранения или Ctrl+Z") end
  end
  out("dirty", reaper.IsProjectDirty(0))
end

-- MT-PowerDrumKit сам помечает проект изменённым (undo «Edit FX parameter: … MT-PowerDrumKit»), в файле при этом меняется
-- только время сохранения. Такой dirty - не правка пользователя: сохранить перед рендером (решение пользователя 21.11).
-- Сохраняется, только если живые треки совпадают с сохранённым файлом во всём, кроме блока MT-PowerDrumKit и
-- изменчивых строк: иначе в проекте есть и правки пользователя - не сохранять, рендер откажет по dirty.
local VOLATILE = {SEL = 1, FLOATPOS = 1, FLOAT = 1, WAK = 1, SHOW = 1, LASTSEL = 1, FXID = 1, IID = 1, GUID = 1, IGUID = 1,
  WNDRECT = 1, DOCKED = 1, CFGEDITVIEW = 1, CFGEDIT = 1}
function temp_norm_track(text)
  local out_, skip, depth, vst = {}, false, 0, nil
  for l in (text .. "\n"):gmatch("([^\n]*)\n") do
    l = l:gsub("\r", ""):match("^%s*(.-)%s*$")
    if vst then   -- состояние VST в base64: в чанке и в файле строки разбиты по-разному - склеить
      if l == ">" then out_[#out_ + 1] = table.concat(vst); out_[#out_ + 1] = ">"; vst = nil else vst[#vst + 1] = l end
    elseif skip then
      if l:sub(1, 1) == "<" then depth = depth + 1 elseif l == ">" then depth = depth - 1; if depth == 0 then skip = false end end
    elseif l:find('^<VST "VSTi?: MT%-PowerDrumKit') then
      skip, depth = true, 1
      if out_[#out_] and out_[#out_]:find("^BYPASS ") then out_[#out_] = nil end
    elseif l ~= "" and not VOLATILE[l:match("^(%S+)") or ""] and not l:find("^PRESETNAME ") then
      -- чанк трека: <TRACK без GUID и абсолютные пути FILE, в файле - GUID и пути от папки проекта
      if l:find("^<TRACK") then l = "<TRACK" elseif l:find('^FILE "') then l = 'FILE "' .. (l:match('([^\\/"]+)"') or "") .. '"' end
      out_[#out_ + 1] = l
      if l:find("^<VST ") then vst = {} end
    end
  end
  return table.concat(out_, "\n")
end

function temp_saved_tracks(path)
  local f = io.open(path, "rb"); if not f then return nil end
  local data = f:read("a"); f:close()
  local tracks, cur, depth = {}, nil, 0
  for l in data:gmatch("([^\n]*)\n") do
    local s = l:gsub("\r", ""):match("^%s*(.-)%s*$")
    if not cur and s:find("^<TRACK") and depth == 1 then cur = {l} ; depth = depth + 1
    elseif cur then
      cur[#cur + 1] = l
      if s:sub(1, 1) == "<" then depth = depth + 1 elseif s == ">" then depth = depth - 1; if depth == 1 then tracks[#tracks + 1] = table.concat(cur, "\n"); cur = nil end end
    else
      if s:sub(1, 1) == "<" then depth = depth + 1 elseif s == ">" then depth = depth - 1 end
    end
  end
  return tracks
end

-- треки, которыми живой проект отличается от сохранённого файла (без MT-PowerDrumKit и изменчивых строк); nil - файл не прочитан
function temp_unsaved_tracks()
  local _, path = reaper.EnumProjects(-1)
  local saved = temp_saved_tracks(path)
  if not saved then return nil end
  local diff = {}
  if #saved ~= reaper.CountTracks(0) then diff[#diff + 1] = "число треков" end
  for i = 0, reaper.CountTracks(0) - 1 do
    local tr = reaper.GetTrack(0, i)
    local _, chunk = reaper.GetTrackStateChunk(tr, "", false)
    if not saved[i + 1] or temp_norm_track(chunk) ~= temp_norm_track(saved[i + 1]) then
      local _, n = reaper.GetTrackName(tr); diff[#diff + 1] = n
    end
  end
  return diff
end

-- Автоактивация барабанов (настроена пользователем 22.11) открывает и закрывает окно цепочки: undo «Close FX chain: Track N drums».
-- Такой dirty тоже сохранять (решение пользователя 22.11), если на треке N стоит MT-PowerDrumKit.
function temp_drumkit_undo(u)
  if u:find("MT%-PowerDrumKit") then return true end
  local n = tonumber(u:match("^%a+ FX chain: Track (%d+)"))
  local tr = n and reaper.GetTrack(0, n - 1)
  if not tr then return false end
  for k = 0, reaper.TrackFX_GetCount(tr) - 1 do
    local _, name = reaper.TrackFX_GetFXName(tr, k, "")
    if name:find("MT%-PowerDrumKit") then return true end
  end
  return false
end

function temp_save_drumkit_dirty()
  if reaper.IsProjectDirty(0) ~= 1 or not temp_drumkit_undo(reaper.Undo_CanUndo2(0) or "") then return end
  local diff = temp_unsaved_tracks()
  if diff and #diff == 0 then
    reaper.Main_SaveProject(0, false)
    out("сохранён: несохранено было только состояние MT-PowerDrumKit (плагин или его автоактивация)")
  else
    out("не сохраняю: кроме MT-PowerDrumKit не сохранены правки треков " .. table.concat(diff or {"?"}, ", "))
  end
end
