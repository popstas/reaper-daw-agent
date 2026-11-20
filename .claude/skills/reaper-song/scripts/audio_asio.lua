-- Кнопка ASIO: переключить аудиосистему на ASIO (запись). Подсвечена, когда режим ASIO.
dofile(reaper.GetResourcePath() .. "\\Scripts\\audio_mode.lua").switch("ASIO")
