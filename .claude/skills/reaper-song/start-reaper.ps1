# Запустить REAPER в сессии пользователя на nb (из ssh GUI напрямую не стартует)
if (Get-Process reaper -ErrorAction SilentlyContinue) { "already running"; exit 0 }
$a = New-ScheduledTaskAction -Execute 'C:\Program Files\REAPER (x64)\reaper.exe'
$p = New-ScheduledTaskPrincipal -UserId (whoami) -LogonType Interactive
Register-ScheduledTask -TaskName reaper-start -Action $a -Principal $p -Force | Out-Null
Start-ScheduledTask reaper-start
for ($i = 0; $i -lt 10; $i++) { Start-Sleep 2; if (Get-Process reaper -ErrorAction SilentlyContinue) { break } }
"running=" + [bool](Get-Process reaper -ErrorAction SilentlyContinue) + " task=" + (Get-ScheduledTask reaper-start).State
Unregister-ScheduledTask reaper-start -Confirm:$false
