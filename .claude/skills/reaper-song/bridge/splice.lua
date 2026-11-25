-- Тело splice.sh: таблицу A {proj, ta, tb, xf, guard} собирает splice.sh перед этим кодом.
-- Врезка повтора из того же дубля: на каждом треке, где айтем покрывает ta и tb,
-- оригинал остаётся до ta - guard, повтор начинается так, что его атака tb встаёт на место атаки ta,
-- середина (ta .. tb) выкидывается, всё после tb сдвигается влево на tb - ta.
-- Перекрёстный фейд xf линейный и заканчивается за guard до атаки. Времена - таймлайн до правки.
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
if not (A.tb > A.ta) then error("атака повтора должна быть позже атаки оригинала") end
out("project", path)

local delta = A.tb - A.ta
local E = A.ta - A.guard            -- конец оригинала
local S = A.tb - A.guard - A.xf     -- начало повтора (старый таймлайн)
local function fmt(t) return string.format("%d:%06.3f", math.floor(t / 60), t % 60) end

-- план: проверить всё до первой правки
local plan, shift = {}, {}
for ti = 0, reaper.CountTracks(0) - 1 do
  local tr = reaper.GetTrack(0, ti)
  local _, name = reaper.GetTrackName(tr)
  for k = 0, reaper.CountTrackMediaItems(tr) - 1 do
    local it = reaper.GetTrackMediaItem(tr, k)
    local pos = reaper.GetMediaItemInfo_Value(it, "D_POSITION")
    local fin = pos + reaper.GetMediaItemInfo_Value(it, "D_LENGTH")
    local tk = reaper.GetActiveTake(it)
    if pos < S and fin > A.tb then
      if not tk or reaper.TakeIsMIDI(tk) then error(name .. ": айтем на месте реза не аудио") end
      if math.abs(reaper.GetMediaItemTakeInfo_Value(tk, "D_PLAYRATE") - 1) > 1e-9 then
        error(name .. ": у айтема PLAYRATE не 1") end
      if pos > E - A.xf then error(name .. ": айтем начинается позже точки реза") end
      table.insert(plan, {tr = tr, name = name, it = it, pos = pos, fin = fin,
        soffs = reaper.GetMediaItemTakeInfo_Value(tk, "D_STARTOFFS")})
    elseif pos >= A.tb then
      table.insert(shift, it)
    elseif fin > E then
      error(name .. ": айтем " .. fmt(pos) .. "-" .. fmt(fin) .. " задевает вырезаемый кусок, но не покрывает рез")
    end
  end
end
if #plan == 0 then error("ни один айтем не покрывает " .. fmt(A.ta) .. " и " .. fmt(A.tb)) end

reaper.Undo_BeginBlock()
local ok, err = pcall(function()
  for _, p in ipairs(plan) do
    local right = reaper.SplitMediaItem(p.it, E)
    if not right then error(p.name .. ": SplitMediaItem не разрезал") end
    reaper.SetMediaItemInfo_Value(p.it, "D_FADEOUTLEN", A.xf)
    reaper.SetMediaItemInfo_Value(p.it, "D_FADEOUTLEN_AUTO", -1)
    reaper.SetMediaItemInfo_Value(p.it, "C_FADEOUTSHAPE", 0)
    local tk = reaper.GetActiveTake(right)
    reaper.SetMediaItemTakeInfo_Value(tk, "D_STARTOFFS", p.soffs + (S - p.pos))
    reaper.SetMediaItemInfo_Value(right, "D_POSITION", E - A.xf)
    reaper.SetMediaItemInfo_Value(right, "D_LENGTH", p.fin - S)
    reaper.SetMediaItemInfo_Value(right, "D_FADEINLEN", A.xf)
    reaper.SetMediaItemInfo_Value(right, "D_FADEINLEN_AUTO", -1)
    reaper.SetMediaItemInfo_Value(right, "C_FADEINSHAPE", 0)
    out("splice", p.name, "оригинал " .. fmt(p.pos) .. "-" .. fmt(E),
        "повтор с " .. fmt(S) .. " встал на " .. fmt(E - A.xf) .. ", до " .. fmt(p.fin - delta))
  end
  for _, it in ipairs(shift) do
    reaper.SetMediaItemInfo_Value(it, "D_POSITION", reaper.GetMediaItemInfo_Value(it, "D_POSITION") - delta)
  end
  if #shift > 0 then out("сдвинуто айтемов после повтора", #shift) end
  -- регион этого выреза (от атаки до атаки) и регионы-кандидаты, начатые внутри вырезанного, - удалить
  -- (со слов пользователя 25.11: после выреза регионы вырезов не нужны)
  local del, j = {}, 0
  while true do
    local r, isrgn, mpos, rend, mname, num = reaper.EnumProjectMarkers(j)
    if r == 0 then break end
    if isrgn and ((math.abs(mpos - A.ta) < 0.01 and math.abs(rend - A.tb) < 0.01) or (mpos > A.ta and mpos < A.tb)) then
      del[#del + 1] = {num, mname}
    end
    j = j + 1
  end
  for _, d in ipairs(del) do reaper.DeleteProjectMarker(0, d[1], true); out("регион выреза удалён:", d[2]) end
  -- маркеры после повтора - за ним, внутри вырезанного - предупредить
  local n, idx = 0, 0
  while true do
    local r, isrgn, mpos, rend, mname, num = reaper.EnumProjectMarkers(idx)
    if r == 0 then break end
    if mpos >= A.tb then
      reaper.SetProjectMarker(num, isrgn, mpos - delta, isrgn and rend - delta or 0, mname); n = n + 1
    elseif mpos > E then out("маркер внутри вырезанного, не тронут:", mname, fmt(mpos)) end
    idx = idx + 1
  end
  if n > 0 then out("сдвинуто маркеров", n) end
end)
reaper.Undo_EndBlock("reaper-song splice", -1)
if not ok then
  if reaper.Undo_CanUndo2(0) == "reaper-song splice" then reaper.Undo_DoUndo2(0) end
  error("не применено: " .. tostring(err))
end
reaper.UpdateArrange()
reaper.Main_SaveProject(0, false)
out("вырезано", string.format("%.3f с", delta), "saved, dirty", reaper.IsProjectDirty(0))
