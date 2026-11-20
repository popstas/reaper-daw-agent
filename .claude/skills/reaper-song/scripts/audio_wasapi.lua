-- Кнопка WASAPI: переключить аудиосистему на WASAPI (звук REAPER слышен в записи видео). Подсвечена, когда режим WASAPI.
dofile(reaper.GetResourcePath() .. "\\Scripts\\audio_mode.lua").switch("WASAPI")
