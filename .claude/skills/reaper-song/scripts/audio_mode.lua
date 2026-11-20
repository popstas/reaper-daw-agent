-- Аудиосистема ASIO/WASAPI: переключение в один клик и подсветка кнопок на панели.
-- Кнопки - audio_asio.lua и audio_wasapi.lua, подсветку ведёт watch() из __startup.lua;
-- он же подсвечивает текущую скорость на кнопках 120 / 180 / 240.
-- API для смены аудиосистемы в REAPER нет, а Audio_Init режим из REAPER.ini не перечитывает,
-- поэтому скрипт открывает Preferences > Audio > Device (40099), выбирает пункт в списке
-- «Audio system» (комбобокс 1000) и жмёт OK. Нужен SWS (BR_Win32_*).
local M = {}
local DIR = reaper.GetResourcePath() .. "\\Scripts\\"
local BUTTONS = {ASIO = "audio_asio.lua", WASAPI = "audio_wasapi.lua"}
local CB_GETCOUNT, CB_SETCURSEL, WM_COMMAND, BM_CLICK, CBN_SELCHANGE = 0x0146, 0x014E, 0x0111, 0x00F5, 1
local GW_HWNDNEXT, GW_CHILD, GWL_ID, COMBO_ID = 2, 5, -12, 1000

function M.mode()
  local _, m = reaper.GetAudioDeviceInfo("MODE")
  return m
end

local function prefs_window()
  return reaper.BR_Win32_FindWindowEx("0", "0", "#32770", "REAPER Preferences", false, true)
end

local function find_child(h, test)
  local c = reaper.BR_Win32_GetWindow(h, GW_CHILD)
  while c do
    if test(c) then return c end
    local r = find_child(c, test)
    if r then return r end
    c = reaper.BR_Win32_GetWindow(c, GW_HWNDNEXT)
  end
end

local function is_system_combo(c)
  return reaper.BR_Win32_GetWindowLong(c, GWL_ID) == COMBO_ID
    and reaper.BR_Win32_SendMessage(c, CB_GETCOUNT, 0, 0) > 0
    and reaper.BR_Win32_CB_FindStringExact(c, -1, "WASAPI") >= 0
end

-- id команд кнопок; AddRemoveReaScript для уже добавленного скрипта возвращает его id
local ids = {}
local function cmd(m)
  if ids[m] == nil then ids[m] = reaper.AddRemoveReaScript(true, 0, DIR .. BUTTONS[m], true) end
  return ids[m]
end

local last, next_check = nil, 0
function M.update(force)
  local m = M.mode()
  if not force and m == last then return end
  last = m
  for k in pairs(BUTTONS) do
    local id = cmd(k)
    if id and id > 0 then
      reaper.SetToggleCommandState(0, id, k == m and 1 or 0)
      reaper.RefreshToolbar2(0, id)
    end
  end
end

-- кнопки скорости 120 / 180 / 240 (playrate_*.lua): подсвечена текущая, при обычной скорости - 120
local RATES = {[1.0] = "playrate_1.0x.lua", [1.5] = "playrate_1.5x.lua", [2.0] = "playrate_2.0x.lua"}
local rate_ids, last_rate, next_rate = {}, nil, 0
local function update_rate()
  local r = reaper.Master_GetPlayRate(0)
  if r == last_rate then return end
  last_rate = r
  for k, f in pairs(RATES) do
    if rate_ids[k] == nil then rate_ids[k] = reaper.AddRemoveReaScript(true, 0, DIR .. f, true) end
    local id = rate_ids[k]
    if id and id > 0 then
      reaper.SetToggleCommandState(0, id, math.abs(r - k) < 0.001 and 1 or 0)
      reaper.RefreshToolbar2(0, id)
    end
  end
end

-- фоновая подсветка: аудиосистема раз в секунду (ловит и ручное переключение в настройках), скорость - раз в 0.2 с
function M.watch()
  local t = reaper.time_precise()
  if t >= next_check then
    next_check = t + 1
    M.update(false)
  end
  if t >= next_rate then
    next_rate = t + 0.2
    update_rate()
  end
  reaper.defer(M.watch)
end

-- автозапуск: через 2 с после старта (окно REAPER уже есть) WASAPI -> ASIO, затем подсветка
function M.startup()
  local t0 = reaper.time_precise()
  local function wait()
    if reaper.time_precise() - t0 < 2 then return reaper.defer(wait) end
    if M.mode() == "WASAPI" then M.switch("ASIO") end
    M.watch()
  end
  wait()
end

function M.switch(target)
  if M.mode() == target then M.update(true) return true end
  if reaper.GetPlayState() & 4 ~= 0 then
    reaper.MB("Идёт запись - аудиосистему не переключаю.", "ASIO / WASAPI", 0)
    return false
  end
  reaper.Main_OnCommand(40099, 0) -- Audio device configuration...
  local w = prefs_window()
  local cb = w and find_child(w, is_system_combo)
  local idx = cb and reaper.BR_Win32_CB_FindStringExact(cb, -1, target) or -1
  if idx < 0 then
    reaper.MB("Не нашёл " .. target .. " в списке Audio system.", "ASIO / WASAPI", 0)
    return false
  end
  -- BR_Win32_SendMessage(hwnd, msg, wParam, lParam): третий аргумент - wParam (проверено на CB_SETCURSEL)
  reaper.BR_Win32_SendMessage(cb, CB_SETCURSEL, idx, 0)
  reaper.BR_Win32_SendMessage(reaper.BR_Win32_GetParent(cb), WM_COMMAND,
    reaper.BR_Win32_MAKEWPARAM(COMBO_ID, CBN_SELCHANGE), tonumber(reaper.BR_Win32_HwndToString(cb)))
  local ok = find_child(w, function(c)
    local _, txt = reaper.BR_Win32_GetWindowText(c)
    return reaper.BR_Win32_GetWindowLong(c, GWL_ID) == 1 and txt == "OK"
  end)
  if ok then reaper.BR_Win32_SendMessage(ok, BM_CLICK, 0, 0) end
  M.update(true)
  return M.mode() == target
end

return M
