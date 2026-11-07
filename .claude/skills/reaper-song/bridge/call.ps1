# Серверная часть моста: отдаёт cmd.lua.tmp мосту и ждёт result.txt. Вызывается из bridge.sh.
param([int]$Timeout = 60)
$d = Join-Path $env:APPDATA 'REAPER\bridge'
$alive = Join-Path $d 'alive.txt'; $cmd = Join-Path $d 'cmd.lua'; $res = Join-Path $d 'result.txt'; $done = Join-Path $d 'result.done'
if (-not (Get-Process reaper -ErrorAction SilentlyContinue)) { 'BRIDGE_DOWN reaper not running'; exit 2 }
if (-not (Test-Path $alive) -or ((Get-Date) - (Get-Item $alive).LastWriteTime).TotalSeconds -gt 10) { 'BRIDGE_DOWN no heartbeat'; exit 2 }
if (Test-Path $cmd) { 'BRIDGE_BUSY'; exit 3 }
Remove-Item $res, $done -ErrorAction SilentlyContinue
Rename-Item "$cmd.tmp" 'cmd.lua'
$t0 = Get-Date
while (-not (Test-Path $res)) {
  if (((Get-Date) - $t0).TotalSeconds -gt $Timeout) { Remove-Item $cmd -ErrorAction SilentlyContinue; 'BRIDGE_TIMEOUT'; exit 4 }
  Start-Sleep -Milliseconds 150
}
Rename-Item $res 'result.done'
'BRIDGE_DONE'
