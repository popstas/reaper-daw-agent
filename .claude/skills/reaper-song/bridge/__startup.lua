-- Автозапуск: мост в живую сессию (bridge\bridge.lua)
dofile(reaper.GetResourcePath() .. "\\bridge\\bridge.lua")
-- ASIO / WASAPI (Scripts\audio_mode.lua): при старте WASAPI переключается на ASIO, кнопки на панели подсвечиваются
local ok, audio = pcall(dofile, reaper.GetResourcePath() .. "\\Scripts\\audio_mode.lua")
if ok then audio.startup() end
