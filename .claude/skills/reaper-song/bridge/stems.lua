-- Стемы за один рендер: таблицу A собирает freeze.sh / render.sh --stems, перед этим кодом подключён temp.lua.
--   A.mode = 'freeze'  - выход трека в точке заморозки: A.tracks = {{index=0, point=3}, ...} (с 0),
--                        FX после точки выключены, фейдер 0 dB, пан по центру, FX мастера выключены,
--                        WAV 32 bit float 48 кГц, весь проект, файлы $tracknumber в A.dir
-- Печатает STEM<TAB>index<TAB>путь на nb на каждый стем. Всё временное возвращается и при ошибке.
-- WAV 32 bit float в RENDER_FORMAT: "evaw" + 0x20 (32 бит) + 0x00 0x01 - проверено rawcheck.py: FLOAT.
local WAV32F = "ZXZhdyAAAQ=="
if reaper.IsProjectDirty(0) == 1 then error("проект не сохранён (dirty): сохранить или спросить пользователя, потом повторить") end
local dirty0 = reaper.IsProjectDirty(0)

local function files(dir)
  local out_, i = {}, 0
  while true do
    local f = reaper.EnumerateFiles(dir, i)
    if not f then break end
    out_[#out_ + 1] = f; i = i + 1
  end
  return out_
end

local ok, err = pcall(function()
  temp_render_settings()
  for _, k in ipairs({"RENDER_SRATE", "RENDER_CHANNELS", "RENDER_ADDTOPROJ"}) do
    local v = reaper.GetSetProjectInfo(0, k, 0, false)
    temp_push(function() reaper.GetSetProjectInfo(0, k, v, true) end)
  end
  -- стемы выделенных треков; чужое solo заглушило бы их - снять на время
  for i = 0, reaper.CountTracks(0) - 1 do
    local tr = reaper.GetTrack(0, i)
    reaper.SetTrackSelected(tr, false)
    if reaper.GetMediaTrackInfo_Value(tr, "I_SOLO") ~= 0 then temp_trackinfo(tr, "I_SOLO", 0) end
  end
  if A.mode == "freeze" then
    for _, t in ipairs(A.tracks) do
      local tr = reaper.GetTrack(0, t.index)
      if not tr then error("нет трека " .. t.index) end
      for f = t.point + 1, reaper.TrackFX_GetCount(tr) - 1 do
        if reaper.TrackFX_GetEnabled(tr, f) then temp_fx_enabled(tr, f, false) end
      end
      temp_trackinfo(tr, "D_VOL", 1); temp_trackinfo(tr, "D_PAN", 0)
      reaper.SetTrackSelected(tr, true)
    end
    temp_trackinfo(reaper.GetMasterTrack(0), "I_FXEN", 0)
    -- стемы выделенных треков без мастера: в REAPER 7.85 это 3 (при 2 RENDER_TARGETS пуст, рендер даёт один файл 00)
    reaper.GetSetProjectInfo(0, "RENDER_SETTINGS", 3, true)
    reaper.GetSetProjectInfo_String(0, "RENDER_FORMAT", WAV32F, true)
    reaper.GetSetProjectInfo_String(0, "RENDER_PATTERN", "$tracknumber", true)
  else
    error("неизвестный режим " .. tostring(A.mode))
  end
  reaper.GetSetProjectInfo(0, "RENDER_BOUNDSFLAG", 1, true)   -- весь проект
  reaper.GetSetProjectInfo(0, "RENDER_SRATE", 48000, true)
  reaper.GetSetProjectInfo(0, "RENDER_CHANNELS", 2, true)
  reaper.GetSetProjectInfo(0, "RENDER_ADDTOPROJ", 0, true)
  reaper.RecursiveCreateDirectory(A.dir, 0)
  for _, f in ipairs(files(A.dir)) do os.remove(A.dir .. f) end   -- остатки прошлого запуска: иначе REAPER спросит про перезапись
  reaper.GetSetProjectInfo_String(0, "RENDER_FILE", A.dir, true)
  reaper.Main_OnCommand(40101, 0) -- Set all media online: без фокуса окна REAPER отключает медиа и рендер выходит тишиной
  local t0 = reaper.time_precise()
  reaper.Main_OnCommand(42230, 0)
  out("render_s", string.format("%.1f", reaper.time_precise() - t0))
  local n = 0
  for _, f in ipairs(files(A.dir)) do
    local num = tonumber(f:match("^(%d+)"))
    if num and f:lower():match("%.wav$") then out("STEM", num - 1, A.dir .. f); n = n + 1 end
  end
  if n ~= #A.tracks then error("стемов " .. n .. " вместо " .. #A.tracks .. " в " .. A.dir) end
end)
temp_finish(dirty0)
if not ok then error(err) end
