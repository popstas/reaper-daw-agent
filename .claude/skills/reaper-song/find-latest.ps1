# Последний изменённый .rpp в __ROOT__ (без AutoSaves и .rpp-bak); __Q__ - фильтр по имени
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$q = '__Q__'
$all = Get-ChildItem '__ROOT__' -Recurse -File -Filter *.rpp -ErrorAction SilentlyContinue |
  ? { $_.FullName -notmatch '\\AutoSaves\\' -and ($q -eq '' -or $_.Name -like "*$q*") } | Sort LastWriteTime -Descending
$all | Select -First 5 | % { "{0:dd.MM HH:mm}  {1}" -f $_.LastWriteTime, $_.FullName }
if ($all) { "RPP=" + $all[0].FullName }
"REAPER_RUNNING=" + [bool](Get-Process reaper -ErrorAction SilentlyContinue)
