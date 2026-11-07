-- Диагностика «нет звука»: треки, FX, айтемы, исходники, уровни на индикаторах.
--   bash bridge.sh state.lua
-- Индикаторы живые только во время воспроизведения. Медиа офлайн (REAPER не в фокусе) - исходник есть, а звука нет.
info()
out("anysolo", reaper.AnyTrackSolo(0))
for i = -1, reaper.CountTracks(0) - 1 do
  local tr = i < 0 and reaper.GetMasterTrack(0) or reaper.GetTrack(0, i)
  local _, n = reaper.GetTrackName(tr)
  out(n, "mute", reaper.GetMediaTrackInfo_Value(tr, "B_MUTE"), "solo", reaper.GetMediaTrackInfo_Value(tr, "I_SOLO"),
    "vol", string.format("%.1f", db(reaper.GetMediaTrackInfo_Value(tr, "D_VOL"))), "fxen", reaper.GetMediaTrackInfo_Value(tr, "I_FXEN"),
    "peak", string.format("%.1f %.1f", db(reaper.Track_GetPeakInfo(tr, 0)), db(reaper.Track_GetPeakInfo(tr, 1))))
  for f = 0, reaper.TrackFX_GetCount(tr) - 1 do
    local _, nm = reaper.TrackFX_GetFXName(tr, f, "")
    out("  fx", f, nm, reaper.TrackFX_GetEnabled(tr, f) and "on" or "BYPASS", reaper.TrackFX_GetOffline(tr, f) and "OFFLINE" or "")
  end
end
for i = 0, reaper.CountMediaItems(0) - 1 do
  local it = reaper.GetMediaItem(0, i)
  local tk = reaper.GetActiveTake(it)
  local src = tk and reaper.GetMediaItemTake_Source(tk)
  local fn = src and reaper.GetMediaSourceFileName(src, "") or "?"
  local _, tn = reaper.GetTrackName(reaper.GetMediaItem_Track(it))
  out("item", tn, "pos", reaper.GetMediaItemInfo_Value(it, "D_POSITION"), "len", reaper.GetMediaItemInfo_Value(it, "D_LENGTH"),
    "mute", reaper.GetMediaItemInfo_Value(it, "B_MUTE"), "vol", string.format("%.1f", db(reaper.GetMediaItemInfo_Value(it, "D_VOL"))),
    "file", fn:match("[^\\]+$"), reaper.file_exists(fn) and "" or "НЕТ ФАЙЛА")
end
