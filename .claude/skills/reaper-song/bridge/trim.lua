-- Тело trim.sh: таблицу A {proj, specs = {{track, s0, s1, fo}, ...}, zero} собирает trim.sh перед этим кодом.
-- Резы начала и конца во времени файла дубля: первому аудио-айтему трека начало файла s0 (звук остаётся на своём месте
-- таймлайна), последнему - конец s1 и фейд fo. Айтемы между ними (врезки) не трогаются.
-- zero: весь проект сдвигается так, чтобы самое раннее обрезанное начало встало на 0 - айтемы всех треков и маркеры.
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
if reaper.IsProjectDirty(0) == 1 and not A.mark then error("в проекте несохранённые правки, сначала сохранить: " .. path) end
out("project", path)
reaper.Main_OnCommand(40101, 0)   -- медиа онлайн: без фокуса окна REAPER его отключает, длина источника тогда 0
local function fmt(t) local s = t < 0 and "-" or ""; t = math.abs(t); return string.format("%s%d:%06.3f", s, math.floor(t / 60), t % 60) end

local function track(name)
  local hit
  for ti = 0, reaper.CountTracks(0) - 1 do
    local tr = reaper.GetTrack(0, ti)
    local _, n = reaper.GetTrackName(tr)
    if n == name then if hit then error("треков «" .. name .. "» несколько") end; hit = tr end
  end
  if not hit then error("нет трека «" .. name .. "»") end
  return hit
end

-- план: проверить всё до первой правки
local plan, firsts = {}, {}
for _, s in ipairs(A.specs) do
  local tr = track(s.track)
  local its, file = {}, nil
  for k = 0, reaper.CountTrackMediaItems(tr) - 1 do
    local it = reaper.GetTrackMediaItem(tr, k)
    local tk = reaper.GetActiveTake(it)
    if tk and not reaper.TakeIsMIDI(tk) then
      if math.abs(reaper.GetMediaItemTakeInfo_Value(tk, "D_PLAYRATE") - 1) > 1e-9 then error(s.track .. ": у айтема PLAYRATE не 1") end
      local src = reaper.GetMediaItemTake_Source(tk)
      local fn = reaper.GetMediaSourceFileName(src, "")
      if file and fn ~= file then error(s.track .. ": на треке айтемы разных файлов - песня из нескольких проходов, резать руками") end
      file = fn
      local pos, len = reaper.GetMediaItemInfo_Value(it, "D_POSITION"), reaper.GetMediaItemInfo_Value(it, "D_LENGTH")
      local so = reaper.GetMediaItemTakeInfo_Value(tk, "D_STARTOFFS")
      table.insert(its, {it = it, tk = tk, pos = pos, len = len, so = so, srclen = reaper.GetMediaSourceLength(src)})
    end
  end
  if #its == 0 then error(s.track .. ": нет аудио-айтемов") end
  local f, l = its[1], its[1]
  for _, x in ipairs(its) do
    if x.so < f.so then f = x end
    if x.so + x.len > l.so + l.len then l = x end
  end
  if l.srclen <= 0 then out(s.track .. ": длина файла неизвестна (медиа офлайн?), конец не проверен") end
  if l.srclen > 0 and s.s1 > l.srclen + 1e-6 then error(s.track .. string.format(": конец %.3f дальше конца файла %.3f", s.s1, l.srclen)) end
  local d = s.s0 - f.so
  local p = {name = s.track, f = f, l = l, s0 = s.s0, s1 = s.s1, fo = s.fo, newpos = f.pos + d, newlen = f.len - d}
  p.lastlen = s.s1 - (l == f and s.s0 or l.so)
  if p.newlen <= 0 or p.lastlen <= 0 then error(s.track .. ": после реза айтем в ноль длины") end
  if l == f then p.newlen = p.lastlen end
  table.insert(plan, p); firsts[f.it] = p
end
-- маркеры будущих резов: имя начинается с MARK, обычный trim.sh их удаляет (со слов пользователя 25.11)
local MARK = "рез "
local function is_mark(isrgn, name) return not isrgn and name:sub(1, #MARK) == MARK end
if A.mark then
  local dirty0 = reaper.IsProjectDirty(0)
  local pts = {}   -- {время таймлайна, подпись, треки}
  local function add(tl, what, name)
    for _, q in ipairs(pts) do
      if math.abs(q.tl - tl) < 0.001 and q.what == what then q.names = q.names .. "+" .. name; return end
    end
    table.insert(pts, {tl = tl, what = what, names = name})
  end
  for _, p in ipairs(plan) do
    add(p.f.pos + (p.s0 - p.f.so), "начало", p.name)
    add(p.l.pos + (p.s1 - p.l.so), p.fo and string.format("конец, фейд %.2f с", p.fo) or "конец", p.name)
  end
  reaper.Undo_BeginBlock()
  local _, nm, nr = reaper.CountProjectMarkers(0)
  for k = nm + nr - 1, 0, -1 do
    local _, isrgn, _, _, name = reaper.EnumProjectMarkers(k)
    if is_mark(isrgn, name) then reaper.DeleteProjectMarkerByIndex(0, k) end
  end
  for _, q in ipairs(pts) do
    local name = MARK .. q.names .. ": " .. q.what
    reaper.AddProjectMarker(0, false, q.tl, 0, name, -1); out("маркер", fmt(q.tl), name)
  end
  reaper.Undo_EndBlock("reaper-song trim markers", -1)
  reaper.UpdateArrange()
  if dirty0 == 0 then reaper.Main_SaveProject(0, false); out("saved, dirty", reaper.IsProjectDirty(0))
  else out("проект был с несохранёнными правками - не сохранён") end
  return
end
local t = 0
if A.zero then
  t = math.huge
  for _, p in ipairs(plan) do t = math.min(t, p.newpos) end
end
-- остальные айтемы и маркеры сдвигаются на -t: ничто не должно уйти левее 0
for ti = 0, reaper.CountTracks(0) - 1 do
  local tr = reaper.GetTrack(0, ti)
  local _, n = reaper.GetTrackName(tr)
  if t ~= 0 then
    for e = 0, reaper.CountTrackEnvelopes(tr) - 1 do
      if reaper.CountEnvelopePoints(reaper.GetTrackEnvelope(tr, e)) > 1 then
        error(n .. ": на треке автоматизация, сдвиг проекта её не тронет - резать с --keep-pos или руками") end
    end
  end
  for k = 0, reaper.CountTrackMediaItems(tr) - 1 do
    local it = reaper.GetTrackMediaItem(tr, k)
    if not firsts[it] and reaper.GetMediaItemInfo_Value(it, "D_POSITION") - t < -1e-6 then
      error(n .. ": айтем на " .. fmt(reaper.GetMediaItemInfo_Value(it, "D_POSITION")) .. " ушёл бы левее 0 - резать с --keep-pos") end
  end
end
for _, p in ipairs(plan) do
  if p.newpos - t < -1e-6 then error(p.name .. ": начало ушло бы левее 0 - без --keep-pos") end
end

reaper.Undo_BeginBlock()
local ok, err = pcall(function()
  for _, p in ipairs(plan) do
    local f, l = p.f, p.l
    local was = string.format("файл %s-%s, таймлайн %s, фейд %.2f", fmt(f.so), fmt(l.so + l.len), fmt(f.pos),
      reaper.GetMediaItemInfo_Value(l.it, "D_FADEOUTLEN"))
    reaper.SetMediaItemTakeInfo_Value(f.tk, "D_STARTOFFS", p.s0)
    reaper.SetMediaItemInfo_Value(f.it, "D_POSITION", p.newpos - t)
    reaper.SetMediaItemInfo_Value(f.it, "D_LENGTH", p.newlen)
    if l ~= f then reaper.SetMediaItemInfo_Value(l.it, "D_LENGTH", p.lastlen) end
    if p.fo then
      reaper.SetMediaItemInfo_Value(l.it, "D_FADEOUTLEN", p.fo)
      reaper.SetMediaItemInfo_Value(l.it, "D_FADEOUTLEN_AUTO", -1)
    end
    out("trim", p.name, was .. " -> " .. string.format("файл %s-%s, таймлайн %s, фейд %.2f", fmt(p.s0), fmt(p.s1),
      fmt(p.newpos - t), reaper.GetMediaItemInfo_Value(l.it, "D_FADEOUTLEN")))
  end
  local _, nm0, nr0 = reaper.CountProjectMarkers(0)
  for k = nm0 + nr0 - 1, 0, -1 do
    local _, isrgn, _, _, name = reaper.EnumProjectMarkers(k)
    if is_mark(isrgn, name) then reaper.DeleteProjectMarkerByIndex(0, k); out("маркер реза удалён:", name) end
  end
  if t ~= 0 then
    local n = 0
    for ti = 0, reaper.CountTracks(0) - 1 do
      local tr = reaper.GetTrack(0, ti)
      for k = 0, reaper.CountTrackMediaItems(tr) - 1 do
        local it = reaper.GetTrackMediaItem(tr, k)
        if not firsts[it] then
          reaper.SetMediaItemInfo_Value(it, "D_POSITION", reaper.GetMediaItemInfo_Value(it, "D_POSITION") - t); n = n + 1
        end
      end
    end
    local idx, nm = 0, 0
    local marks = {}
    while true do
      local r, isrgn, mpos, rend, mname, num = reaper.EnumProjectMarkers(idx)
      if r == 0 then break end
      table.insert(marks, {isrgn, mpos, rend, mname, num}); idx = idx + 1
    end
    for _, m in ipairs(marks) do
      reaper.SetProjectMarker(m[5], m[1], math.max(0, m[2] - t), m[1] and math.max(0, m[3] - t) or 0, m[4]); nm = nm + 1
    end
    out("проект сдвинут", string.format("%+.3f с", -t), "айтемов", n, "маркеров", nm)
  end
end)
reaper.Undo_EndBlock("reaper-song trim", -1)
if not ok then
  if reaper.Undo_CanUndo2(0) == "reaper-song trim" then reaper.Undo_DoUndo2(0) end
  error("не применено: " .. tostring(err))
end
reaper.UpdateArrange()
reaper.Main_SaveProject(0, false)
out("saved, dirty", reaper.IsProjectDirty(0))
