-- Копия .rpp текущей вкладки под латинским именем A.dir .. "project.rpp": freeze.sh сверяет её с локальной копией.
local _, path = reaper.EnumProjects(-1)
if path == "" then error("вкладка без файла проекта") end
reaper.RecursiveCreateDirectory(A.dir, 0)
local fi = assert(io.open(path, "rb")); local data = fi:read("a"); fi:close()
local fo = assert(io.open(A.dir .. "project.rpp", "wb")); fo:write(data); fo:close()
out("RPP", A.dir .. "project.rpp")
out("dirty", reaper.IsProjectDirty(0))
