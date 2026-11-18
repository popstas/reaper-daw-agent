-- Выбрать вкладку по части пути проекта (A.proj). Подключается render.sh перед телом рендера при --proj.
do
  local proj
  local i = 0
  while true do
    local p, f = reaper.EnumProjects(i)
    if not p then break end
    if f:find(A.proj, 1, true) then
      if proj then error("под «" .. A.proj .. "» несколько вкладок") end
      proj = p
    end
    i = i + 1
  end
  if not proj then error("нет открытой вкладки с «" .. A.proj .. "»") end
  reaper.SelectProjectInstance(proj)
end
