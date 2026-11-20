import os, sys
import pytest

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SKILL)

# Минимальный проект: guitar (gate, hpflpf, rbj4eq, Blue Cat, 1175, ReaVerb), drums (MT-PowerDrumKit, MIDI, ReaVerb выкл),
# mic (hpflpf, 1175, deesser, ReaVerb), мастер (1175 выкл, MGA_JSLimiterST). Строки - как в настоящих .rpp REAPER 7.
RPP = '''<REAPER_PROJECT 0.1 "7.85/win64" 1763700000
  RIPPLE 0
  SAMPLERATE 48000 0 0
  RENDER_FILE C:\\rec\\2026
  <MASTERFXLIST
    WNDRECT 200 200 892 540
    SHOW 0
    LASTSEL 0
    DOCKED 0
    BYPASS 1 0 0
    <JS sstillwell/1175 ""
      -14 5 0 20 250 100 - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    >
    FLOATPOS 0 0 0 0
    FXID {00000000-0000-0000-0000-000000009001}
    WAK 0 0
    BYPASS 0 0 0
    <JS loser/MGA_JSLimiterST ""
      -8 200 75 -1.4 - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    >
    FLOATPOS 0 0 0 0
    FXID {00000000-0000-0000-0000-000000009002}
    WAK 0 0
  >
  <TRACK {00000000-0000-0000-0000-000000001000}
    NAME guitar
    VOLPAN 0.70794578 0 -1 -1 1
    MUTESOLO 0 0 0
    SEL 0
    FX 1
    TRACKID {00000000-0000-0000-0000-000000001000}
    <FXCHAIN
      WNDRECT 200 200 833 318
      SHOW 0
      LASTSEL 3
      DOCKED 0
      BYPASS 0 0 0
      <JS popstas/guitar_noise_gate.jsfx ""
        -50 -54 150 1 250 -90 801.8 10 20 -120 1 1000 -54 -58 -120 1 -42 3 60 6000 -57 -120 - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      >
      FLOATPOS 0 0 0 0
      FXID {00000000-0000-0000-0000-000000001001}
      WAK 0 0
      BYPASS 0 0 0
      <JS sstillwell/hpflpf ""
        80 10000 -2 - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      >
      FLOATPOS 0 0 0 0
      FXID {00000000-0000-0000-0000-000000001002}
      WAK 0 0
      BYPASS 0 0 0
      <JS sstillwell/rbj4eq ""
        1 0 5 -3 4 -1.5 3 1.5 - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      >
      FLOATPOS 0 0 0 0
      FXID {00000000-0000-0000-0000-000000001003}
      WAK 0 0
      BYPASS 0 0 0
      <VST "VST3: Blue Cat's Free Amp (Blue Cat Audio)" "BC Free Amp VST3.vst3" 0 "" 840268532{402C399BE94649188B8D29625BC4DA0B} ""
        9HoVMu5e7f4CAAAAAQAAAAAAAAACAAAAAAAAAAIAAAABAAAAAAAAAAIAAAAAAAAA8gYAAAEAAAAAAAAA
        4gYAAAEAAADeBgAAPD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiPz48UHJlc2V0IHZlcnNpb249IjQiIHByb2dOYW1lPSJDbGFzc2ljIERyaXZlIC0g
        L20zPjwvbWV0YT48L3N0YXRlPjwvc2tpbj48L0dVST48L1ByZXNldD4AAAAAAAAAAAA=
        AAAAAAAA
      >
      FLOATPOS 0 0 0 0
      FXID {00000000-0000-0000-0000-000000001004}
      WAK 0 0
      BYPASS 0 0 0
      <JS sstillwell/1175 ""
        -14 5 0 20 250 100 - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      >
      FLOATPOS 0 0 0 0
      FXID {00000000-0000-0000-0000-000000001005}
      WAK 0 0
      BYPASS 0 0 0
      <VST "VST: ReaVerb (Cockos)" reaverb.dll 0 "" 1919252066<56535472657662726561766572620000> ""
        YnZlcu5e7f4CAAAAAQAAAAAAAAACAAAAAAAAAAIAAAABAAAAAAAAAAIAAAAAAAAATAAAAAEAAAAAABAA
        AFNtYWxsIHZvY2FsIHJldmVyABAAAAA=
      >
      PRESETNAME "Small vocal rever"
      FLOATPOS 0 0 0 0
      FXID {00000000-0000-0000-0000-000000001006}
      WAK 0 0
    >
    <ITEM
      POSITION 0
      SNAPOFFS 0
      LENGTH 6
      LOOP 1
      FADEIN 1 0.01 0 1 0 0 0 1 0 0 1 0 0
      FADEOUT 1 0.01 0 1 0 0 0 1 0 0 1 0 0
      MUTE 0 0
      SEL 0
      IGUID {00000000-0000-0000-0000-000000001101}
      IID 1
      NAME g.wav
      VOLPAN 1 0 1 -1
      SOFFS 7.5
      PLAYRATE 1 1 0 -1 0 0.0025
      CHANMODE 0
      GUID {00000000-0000-0000-0000-000000001102}
      <SOURCE WAVE
        FILE "Media\\g.wav"
      >
    >
  >
  <TRACK {00000000-0000-0000-0000-000000002000}
    NAME drums
    VOLPAN 1.41253754 0 -1 -1 1
    MUTESOLO 0 0 0
    SEL 1
    FX 1
    TRACKID {00000000-0000-0000-0000-000000002000}
    <FXCHAIN
      WNDRECT 0 0 1172 695
      SHOW 0
      LASTSEL 0
      DOCKED 0
      BYPASS 0 0 0
      <VST "VSTi: MT-PowerDrumKit (MANDA AUDIO) (16 out)" MT-PowerDrumKit.dll 0 "" 1297371204<5653544D5450446D74706F7765726472> ""
        RFBUTe5e7f4AAAAAEAAAAAEAAAAAAAAAAgAAAAAAAAAEAAAAAAAAAAgAAAAAAAAAEAAAAAAAAAAgAAAAAAAAAEAAAAAAAAAAgAAAAAAAAAAAAQAAAAAAAAACAAAAAAAA
        AAAQAAAA
      >
      PRESETNAME MT-PowerDrumKit
      FLOATPOS 621 518 961 648
      FXID {00000000-0000-0000-0000-000000002001}
      WAK 0 0
      BYPASS 1 0 0
      <VST "VST: ReaVerb (Cockos)" reaverb.dll 0 "" 1919252066<56535472657662726561766572620000> ""
        YnZlcu5e7f4CAAAAAQAAAAAAAAACAAAAAAAAAAIAAAABAAAAAAAAAAIAAAAAAAAATAAAAAEAAAAAABAA
        AAAQAAAA
      >
      FLOATPOS 0 0 0 0
      FXID {00000000-0000-0000-0000-000000002002}
      WAK 0 0
    >
    <ITEM
      POSITION 0
      SNAPOFFS 0
      LENGTH 6
      LOOP 1
      FADEIN 1 0 0 1 0 0 0 1 0 0 1 0 0
      FADEOUT 1 0 0 1 0 0 0 1 0 0 1 0 0
      MUTE 0 0
      SEL 0
      IGUID {00000000-0000-0000-0000-000000002101}
      IID 2
      NAME 02-drums-MIDI
      VOLPAN 1 0 1 -1
      SOFFS 0
      PLAYRATE 1 1 0 -1 0 0.0025
      CHANMODE 0
      GUID {00000000-0000-0000-0000-000000002102}
      <SOURCE MIDI
        HASDATA 1 960 QN
        CCINTERP 32
        E 5913 90 24 7f
        E 256 80 24 00
        E 0 b0 7b 00
      >
    >
  >
  <TRACK {00000000-0000-0000-0000-000000003000}
    NAME mic
    VOLPAN 1 0 -1 -1 1
    MUTESOLO 0 0 0
    SEL 0
    FX 1
    TRACKID {00000000-0000-0000-0000-000000003000}
    <FXCHAIN
      WNDRECT 200 200 833 318
      SHOW 0
      LASTSEL 0
      DOCKED 0
      BYPASS 0 0 0
      <JS sstillwell/hpflpf ""
        100 22000 -6 - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      >
      FLOATPOS 0 0 0 0
      FXID {00000000-0000-0000-0000-000000003001}
      WAK 0 0
      BYPASS 0 0 0
      <JS sstillwell/1175 ""
        -16 5 4 20 250 100 - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      >
      FLOATPOS 0 0 0 0
      FXID {00000000-0000-0000-0000-000000003002}
      WAK 0 0
      BYPASS 0 0 0
      <JS Liteon/deesser ""
        -30 6000 1 - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      >
      FLOATPOS 0 0 0 0
      FXID {00000000-0000-0000-0000-000000003003}
      WAK 0 0
      BYPASS 0 0 0
      <VST "VST: ReaVerb (Cockos)" reaverb.dll 0 "" 1919252066<56535472657662726561766572620000> ""
        YnZlcu5e7f4CAAAAAQAAAAAAAAACAAAAAAAAAAIAAAABAAAAAAAAAAIAAAAAAAAATAAAAAEAAAAAABAA
        AFNtYWxsIHZvY2FsIHJldmVyABAAAAA=
      >
      FLOATPOS 0 0 0 0
      FXID {00000000-0000-0000-0000-000000003004}
      WAK 0 0
    >
    <ITEM
      POSITION 0
      SNAPOFFS 0
      LENGTH 6
      LOOP 1
      FADEIN 1 0.01 0 1 0 0 0 1 0 0 1 0 0
      FADEOUT 1 0.01 0 1 0 0 0 1 0 0 1 0 0
      MUTE 0 0
      SEL 0
      IGUID {00000000-0000-0000-0000-000000003101}
      IID 3
      NAME m.wav
      VOLPAN 1 0 1 -1
      SOFFS 0
      PLAYRATE 1 1 0 -1 0 0.0025
      CHANMODE 0
      GUID {00000000-0000-0000-0000-000000003102}
      <SOURCE WAVE
        FILE "Media\\m.wav"
      >
    >
  >
>
'''.replace('\n', '\r\n')


@pytest.fixture
def rpp_text():
    return RPP
