-- Состояние, которое рендер обязан вернуть: dirty, настройки рендера, выделение, фейдеры, паны, mute/solo, включённость FX.
-- Снимок до и после рендера сравнивается побайтно (renderstate.sh).
out("dirty", reaper.IsProjectDirty(0))
for _, k in ipairs({"RENDER_SETTINGS", "RENDER_BOUNDSFLAG"}) do out(k, reaper.GetSetProjectInfo(0, k, 0, false)) end
for _, k in ipairs({"RENDER_FORMAT", "RENDER_FILE", "RENDER_PATTERN"}) do out(k, (select(2, reaper.GetSetProjectInfo_String(0, k, "", false)))) end
for i = -1, reaper.CountTracks(0) - 1 do
  local tr = i < 0 and reaper.GetMasterTrack(0) or reaper.GetTrack(0, i)
  local _, n = reaper.GetTrackName(tr)
  out("track", n, "sel", reaper.IsTrackSelected(tr) and 1 or 0,
    "vol", string.format("%.6f", reaper.GetMediaTrackInfo_Value(tr, "D_VOL")),
    "pan", string.format("%.6f", reaper.GetMediaTrackInfo_Value(tr, "D_PAN")),
    "mute", reaper.GetMediaTrackInfo_Value(tr, "B_MUTE"), "solo", reaper.GetMediaTrackInfo_Value(tr, "I_SOLO"),
    "fxen", reaper.GetMediaTrackInfo_Value(tr, "I_FXEN"), "nfx", reaper.TrackFX_GetCount(tr))
  for f = 0, reaper.TrackFX_GetCount(tr) - 1 do
    local _, nm = reaper.TrackFX_GetFXName(tr, f, "")
    out("  fx", f, nm, reaper.TrackFX_GetEnabled(tr, f) and 1 or 0)
  end
end
