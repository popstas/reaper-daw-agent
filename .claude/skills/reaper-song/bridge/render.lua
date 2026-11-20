-- Тело рендера для render.sh: таблицу A собирает render.sh, перед этим кодом подключён temp.lua.
-- Ставит временные правки (temp_apply), рендерит по настройкам проекта (42230), уносит файл в <имя>.<ext>, всё возвращает.
local dirty0 = reaper.IsProjectDirty(0)
local _, target = reaper.GetSetProjectInfo_String(0, "RENDER_TARGETS", "", false)
if target == "" or target:find(";") then error("цель рендера не одна: " .. target) end
local dest = A.final and target or target:match("^(.*\\)") .. A.name .. (target:match("%.%w+$") or "")

local ok, err = pcall(function()
  temp_apply(A)
  -- чужой файл с именем цели убрать на время рендера, иначе REAPER спросит про перезапись и мост повиснет
  local old = target .. ".old"
  if reaper.file_exists(target) then
    os.remove(old); assert(os.rename(target, old))
    if not A.final then temp_push(function() os.rename(old, target) end) end
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
temp_finish(dirty0)
if not ok then error(err) end
