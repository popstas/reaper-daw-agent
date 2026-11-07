---
title: "Special Variables & Sliders"
impact: CRITICAL
tags:
  - variables
  - sliders
  - audio
  - midi
  - transport
---

# Special Variables & Sliders

JSFX provides numerous special variables for accessing audio samples, transport state, and host information.

## Official Documentation

- [JSFX Special Variables](https://www.reaper.fm/sdk/js/vars.php)
- [JSFX MIDI Functions](https://www.reaper.fm/sdk/js/midi.php)

---

## Audio Sample Variables

### Direct Sample Access

| Variable | Context | Description |
|----------|---------|-------------|
| `spl0` - `spl63` | @sample | Audio samples for channels 0-63 (read/write) |
| `spl(n)` | @sample | Programmatic channel access (REAPER 2.018+) |

```
@sample
// Direct access (fastest)
spl0 *= gain;  // Left
spl1 *= gain;  // Right

// Programmatic access (for multi-channel)
ch = 0;
loop(num_ch,
  spl(ch) *= gain;
  ch += 1;
);
```

### Channel Information

| Variable | Context | Description |
|----------|---------|-------------|
| `num_ch` | All | Number of input/output channels (read-only) |

```
@init
// Allocate per-channel state
filter_states = 0;
freembuf(filter_states + num_ch * 2);  // 2 state vars per channel
```

---

## Slider Variables

### Slider Definition Syntax

```
sliderN:variable=default<min,max,step>Label
sliderN:variable=default<min,max,step:scale>Label
sliderN:variable=default<min,max,step{Opt1,Opt2,...}>Label
```

### Slider Types

**Continuous (default):**
```
slider1:gain_db=0<-60,12,0.1>Gain (dB)
slider2:freq=1000<20,20000,1>Frequency (Hz)
```

**Logarithmic scaling:**
```
slider1:freq=1000<20,20000,1:log>Frequency (Hz)
// Slider moves logarithmically (good for frequency, ratio)
```

**Quadratic scaling:**
```
slider1:curve=0.5<0,1,0.01:sqr>Curve
// Slider moves quadratically
```

**Dropdown menu:**
```
slider1:mode=0<0,3,1{Off,Low,Medium,High}>Mode
// Shows dropdown with options
```

**Hidden parameter (automation only):**
```
slider1:-internal_state=0<0,1,1>Hidden
// Not shown in UI, but can be automated
```

**File browser:**
```
slider1:file:6:impulse_response:Load IR
// Opens file browser, index 6, named "impulse_response"
```

### Slider Functions

```
@slider
// Sliders automatically update their named variables
// slider1 = gain_db (if named)

// Manual slider access
value = slider(1);  // Read slider 1 value
slider(1) = new_value;  // Set slider 1 value

// Notify host of change (for automation recording)
slider_automate(slider1);

// Sample-accurate automation (in @sample)
slider_next_chg(slider1, next_value) ? (
  // Parameter changes at this exact sample
  gain_lin = 10^(next_value / 20);
);
```

---

## Audio Configuration

| Variable | Context | Description |
|----------|---------|-------------|
| `srate` | All | Sample rate in Hz (e.g., 44100, 48000, 96000) |
| `samplesblock` | @block, @sample | Samples in current block |
| `num_ch` | All | Number of channels |

```
@init
// Calculate time-based constants
ms_per_sample = 1000 / srate;
samples_per_ms = srate / 1000;
nyquist = srate / 2;

@slider
// Convert milliseconds to samples
attack_samples = attack_ms * srate / 1000;
// Or equivalently:
attack_samples = attack_ms * samples_per_ms;

// Frequency-dependent calculations
omega = 2 * $pi * cutoff_freq / srate;
```

---

## Transport State

| Variable | Context | Description |
|----------|---------|-------------|
| `play_state` | All | Playback state (see table below) |
| `play_position` | All | Playback position in seconds |
| `beat_position` | All | Playback position in beats |
| `tempo` | All | Project tempo in BPM |
| `ts_num` | All | Time signature numerator |
| `ts_denom` | All | Time signature denominator |

### Play State Values

| Value | State |
|-------|-------|
| 0 | Stopped |
| 1 | Playing |
| 2 | Paused |
| 5 | Recording |
| 6 | Record paused |

```
@block
// Tempo-synced delay
beat_length_samples = srate * 60 / tempo;
quarter_note_delay = beat_length_samples;
eighth_note_delay = beat_length_samples / 2;
measure_delay = beat_length_samples * ts_num;

// Only process when playing
play_state == 1 || play_state == 5 ? (
  // Playing or recording
);

// Beat detection
current_beat = floor(beat_position);
current_beat != last_beat ? (
  // New beat started
  last_beat = current_beat;
  // Trigger something on beat
);
```

---

## Trigger Buttons

```
@init
// Using trigger variable enables 10 trigger buttons in UI
// trigger bits 0-9 correspond to buttons 1-10

@block
// Check if button 1 was pressed
trigger & 1 ? (
  // Button 1 pressed - reset envelope
  envelope = 0;
  trigger = trigger & ~1;  // Clear bit
);

// Check button 2
trigger & 2 ? (
  // Button 2 pressed
  trigger = trigger & ~2;
);
```

---

## Plugin Delay Compensation (PDC)

For plugins that introduce latency:

| Variable | Description |
|----------|-------------|
| `pdc_delay` | Latency in samples (read/write) |
| `pdc_bot_ch` | First channel affected |
| `pdc_top_ch` | Last channel + 1 |
| `pdc_midi` | Also delay MIDI output |

```
@init
// Linear-phase filter with 512 sample latency
pdc_delay = 512;
pdc_bot_ch = 0;    // Start at channel 0
pdc_top_ch = 2;    // Channels 0 and 1 affected

// For MIDI-generating instruments
pdc_midi = 1;      // Delay MIDI by same amount
```

---

## Extended Variables

| Variable | Description |
|----------|-------------|
| `ext_noinit` | Set to 1 to prevent @init on playback start |
| `ext_nodenorm` | Set to 1 to disable anti-denormal noise |
| `ext_tail_size` | Plugin tail length in samples (REAPER 6.71+) |
| `ext_gr_meter` | Gain reduction for host meter (REAPER 7.0+) |

```
@init
// Don't re-run @init when playback starts
ext_noinit = 1;

// Disable anti-denormal noise (handle denormals yourself)
ext_nodenorm = 1;

// Tell host plugin has 2-second tail (reverb, delay)
ext_tail_size = srate * 2;

@sample
// Report gain reduction for host meter display
ext_gr_meter = gain_reduction;  // 0-1 range
```

---

## Shared Memory

### Inter-Plugin Communication (gmem)

```
@init
// Enable extended gmem (add to file header)
// options:gmem=MyPluginName

// Write to shared memory
gmem[0] = level;
gmem[1] = frequency;

@sample
// Read from another plugin's shared data
external_level = gmem[1000];
```

### Shared Named Variables

```
@init
// Variables with _global. prefix are shared across all instances
_global.master_level = 1;
_global.sync_beat = 0;

@block
// Read/write shared state
_global.sync_beat = beat_position;

// In another instance:
synced_beat = _global.sync_beat;
```

### Register Variables (reg00-reg99)

Shared between effects in the same FX chain:

```
@sample
// Write to register
reg00 = spl0;

// In next effect, read the value
prev_effect_output = reg00;
```

---

## Pin Configuration

Define input/output channel names:

```
// Stereo effect
in_pin:left input
in_pin:right input
out_pin:left output
out_pin:right output

// Mid-side processor
in_pin:mid input
in_pin:side input
out_pin:mid output
out_pin:side output

// No audio I/O (MIDI-only effect)
in_pin:none
out_pin:none

// Multi-channel
in_pin:input 1
in_pin:input 2
in_pin:input 3
in_pin:input 4
out_pin:output 1
out_pin:output 2
out_pin:output 3
out_pin:output 4
```

---

## MIDI Variables

| Variable | Description |
|----------|-------------|
| `midi_bus` | Current MIDI bus (0-15) |
| `ext_midi_bus` | Set to 1 to enable multi-bus MIDI |

```
@init
ext_midi_bus = 1;  // Enable multi-bus MIDI

@block
while(midirecv(offset, msg1, msg2, msg3)) (
  current_bus = midi_bus;  // Which bus this came from

  // Route to different bus
  midi_bus = 2;
  midisend(offset, msg1, msg2, msg3);
  midi_bus = current_bus;  // Restore
);
```

---

## Graphics Variables

Available in @gfx section:

| Variable | Description |
|----------|-------------|
| `gfx_w` | UI width in pixels |
| `gfx_h` | UI height in pixels |
| `gfx_x`, `gfx_y` | Current drawing position |
| `gfx_r`, `gfx_g`, `gfx_b`, `gfx_a` | Current color (0-1) |
| `gfx_texth` | Text line height |
| `gfx_ext_retina` | HiDPI scale factor |
| `mouse_x`, `mouse_y` | Mouse position |
| `mouse_cap` | Mouse button/modifier state |

```
@gfx 400 300

// Retina/HiDPI support
gfx_ext_retina > 1 ? (
  // Scale coordinates for high-DPI
  scale = gfx_ext_retina;
  gfx_setfont(1, "Arial", 14 * scale);
);

// Mouse state
mouse_cap & 1 ? (/* left button */);
mouse_cap & 2 ? (/* right button */);
mouse_cap & 4 ? (/* ctrl held */);
mouse_cap & 8 ? (/* shift held */);
mouse_cap & 16 ? (/* alt held */);
mouse_cap & 64 ? (/* middle button */);
```

---

## Host Interaction

| Function | Description |
|----------|-------------|
| `get_host_numchan()` | Get track channel count |
| `set_host_numchan(n)` | Set track channel count |
| `get_host_placement()` | Get track index and position |

```
@gfx
// Get current track info
track_idx = get_host_placement(chain_pos, flags);
// flags: 1=input FX, 2=monitor FX, 4=offline rendering

// Show track info
gfx_x = gfx_y = 10;
gfx_printf("Track %d, FX position %d", track_idx, chain_pos);
```

---

## Common Variable Patterns

### Level Metering

```
@init
peak_l = peak_r = 0;
peak_hold_samples = srate * 2;  // 2 second hold
peak_counter = 0;

@sample
// Track peaks
abs(spl0) > peak_l ? peak_l = abs(spl0);
abs(spl1) > peak_r ? peak_r = abs(spl1);

@block
// Decay peaks
peak_counter += samplesblock;
peak_counter >= peak_hold_samples ? (
  peak_l *= 0.9;
  peak_r *= 0.9;
  peak_l < 0.0001 ? peak_l = 0;
  peak_r < 0.0001 ? peak_r = 0;
  peak_counter = 0;
);
```

### Tempo-Synced LFO

```
@init
lfo_phase = 0;

@slider
// Rate in beats (1 = quarter note, 0.5 = eighth, etc.)
lfo_rate_beats = slider1;

@block
// Calculate phase increment per sample
beats_per_sample = tempo / (60 * srate);
lfo_increment = beats_per_sample / lfo_rate_beats;

@sample
// Advance LFO
lfo_phase += lfo_increment;
lfo_phase >= 1 ? lfo_phase -= 1;

// Generate LFO output
lfo_out = sin(2 * $pi * lfo_phase);
```

### Smoothed Parameter Changes

```
@init
gain_smooth = 0;
smooth_coeff = exp(-1 / (0.005 * srate));  // 5ms smoothing

@slider
gain_target = 10^(gain_db / 20);

@sample
// Exponential smoothing
gain_smooth = smooth_coeff * gain_smooth + (1 - smooth_coeff) * gain_target;

spl0 *= gain_smooth;
spl1 *= gain_smooth;
```
