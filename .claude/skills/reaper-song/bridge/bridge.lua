-- Мост в живую сессию REAPER: исполняет Lua-команды из файла, ответ пишет в файл.
-- Клиент кладёт bridge\cmd.lua (через rename из .tmp), мост читает, удаляет, выполняет,
-- пишет bridge\result.txt (через rename из .tmp). Первая строка ответа - OK или ERR.
-- Запускается из Scripts\__startup.lua. Каждые 2 с обновляет bridge\alive.txt.

local dir = reaper.GetResourcePath() .. "\\bridge\\"
local CMD, RES, ALIVE = dir .. "cmd.lua", dir .. "result.txt", dir .. "alive.txt"
local last_alive, last_poll = 0, 0
-- Повторный dofile (перезагрузка моста командой) запускает новый цикл, старый останавливается
BRIDGE_GEN = (BRIDGE_GEN or 0) + 1
local gen = BRIDGE_GEN

local function readf(p) local f = io.open(p, "rb"); if not f then return nil end local s = f:read("a"); f:close(); return s end
local function writef(p, s) local f = io.open(p .. ".tmp", "wb"); f:write(s); f:close(); os.remove(p); os.rename(p .. ".tmp", p) end

-- Помощники, доступные командам
local env = setmetatable({}, { __index = _G })
local buf

function env.out(...)
  local t = {}
  for i = 1, select("#", ...) do t[#t + 1] = tostring((select(i, ...))) end
  buf[#buf + 1] = table.concat(t, "\t")
end

function env.track(name)
  if name == "master" then return reaper.GetMasterTrack(0) end
  for i = 0, reaper.CountTracks(0) - 1 do
    local tr = reaper.GetTrack(0, i)
    local _, n = reaper.GetTrackName(tr)
    if n == name then return tr end
  end
  error("нет трека " .. name)
end

-- FX по подстроке отображаемого имени или файла (fx_ident, например "loser/MGA_JSLimiterST"),
-- n-е совпадение (по умолчанию первое)
function env.fx(tr, pat, n)
  if type(tr) == "string" then tr = env.track(tr) end
  n = n or 1
  for i = 0, reaper.TrackFX_GetCount(tr) - 1 do
    local _, nm = reaper.TrackFX_GetFXName(tr, i)
    local _, id = reaper.TrackFX_GetNamedConfigParm(tr, i, "fx_ident")
    if nm:find(pat, 1, true) or (id or ""):find(pat, 1, true) then n = n - 1; if n == 0 then return tr, i end end
  end
  error("нет FX " .. pat)
end

-- Номер параметра по подстроке имени
function env.param(tr, fxi, pat)
  for p = 0, reaper.TrackFX_GetNumParams(tr, fxi) - 1 do
    local _, pn = reaper.TrackFX_GetParamName(tr, fxi, p)
    if pn:find(pat, 1, true) then return p end
  end
  error("нет параметра " .. pat)
end

local function db(v) return v > 0 and 20 * math.log(v, 10) or -150 end
env.db = db

-- Сводка: треки, фейдеры, FX и параметры
function env.dump(full)
  for i = -1, reaper.CountTracks(0) - 1 do
    local tr = i < 0 and reaper.GetMasterTrack(0) or reaper.GetTrack(0, i)
    local _, n = reaper.GetTrackName(tr)
    env.out(string.format("TRACK %s vol %.2f dB fxon %d", n, db(reaper.GetMediaTrackInfo_Value(tr, "D_VOL")),
      reaper.GetMediaTrackInfo_Value(tr, "I_FXEN")))
    for f = 0, reaper.TrackFX_GetCount(tr) - 1 do
      local _, nm = reaper.TrackFX_GetFXName(tr, f)
      local _, id = reaper.TrackFX_GetNamedConfigParm(tr, f, "fx_ident")
      env.out(string.format("  FX %d %s | %s%s", f, nm, id, reaper.TrackFX_GetEnabled(tr, f) and "" or " [bypass]"))
      if full then
        for p = 0, reaper.TrackFX_GetNumParams(tr, f) - 1 do
          local _, pn = reaper.TrackFX_GetParamName(tr, f, p)
          local _, fv = reaper.TrackFX_GetFormattedParamValue(tr, f, p)
          env.out(string.format("    %d %s = %.6g (%s)", p, pn, reaper.TrackFX_GetParam(tr, f, p), fv))
        end
      end
    end
  end
end

function env.info()
  local _, path = reaper.EnumProjects(-1)
  env.out("project", path)
  env.out("dirty", reaper.IsProjectDirty(0))
  env.out("playstate", reaper.GetPlayState())
end

local function run(code)
  buf = {}
  local fn, err = load(code, "cmd", "t", env)
  if not fn then return "ERR\n" .. err end
  local ok, res = xpcall(fn, debug.traceback)
  if not ok then return "ERR\n" .. table.concat(buf, "\n") .. "\n" .. tostring(res) end
  if res ~= nil then buf[#buf + 1] = tostring(res) end
  return "OK\n" .. table.concat(buf, "\n")
end

local function loop()
  if BRIDGE_GEN ~= gen then return end
  local now = reaper.time_precise()
  if now - last_poll > 0.2 then
    last_poll = now
    local code = readf(CMD)
    if code then
      os.remove(CMD)
      writef(RES, run(code))
    end
  end
  if now - last_alive > 2 then
    last_alive = now
    writef(ALIVE, os.date("%Y-%m-%d %H:%M:%S"))
  end
  reaper.defer(loop)
end

reaper.RecursiveCreateDirectory(dir, 0)
os.remove(CMD)
loop()
