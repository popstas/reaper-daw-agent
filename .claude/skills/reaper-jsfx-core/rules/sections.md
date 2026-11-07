---
title: "JSFX Code Sections"
impact: CRITICAL
tags:
  - sections
  - init
  - slider
  - block
  - sample
  - gfx
  - serialize
---

# JSFX Code Sections

JSFX plugins are organized into sections that execute at different times. Understanding when each section runs is essential for correct and efficient plugin design.

## Official Documentation

- [JSFX Programming Reference](https://www.reaper.fm/sdk/js/js.php)

---

## Section Execution Order

```
Plugin Load / Sample Rate Change / Playback Start
                    │
                    ▼
              ┌─────────┐
              │  @init  │ ◄── Once: Initialize state, allocate memory
              └────┬────┘
                   │
                   ▼
              ┌──────────┐
              │ @slider  │ ◄── On parameter change: Recalculate coefficients
              └────┬─────┘
                   │
        ┌──────────┴──────────┐
        │   Audio Block Loop  │
        │                     │
        │    ┌─────────┐      │
        │    │ @block  │      │ ◄── Per block: Process MIDI, prep for samples
        │    └────┬────┘      │
        │         │           │
        │    ┌────┴────┐      │
        │    │@sample  │      │ ◄── Per sample: Audio processing (HOT PATH)
        │    │ (loop)  │      │
        │    └─────────┘      │
        │                     │
        └─────────────────────┘
                   │
              ┌────┴────┐
              │  @gfx   │ ◄── ~30 Hz: UI rendering (separate thread)
              └─────────┘

State Save/Load
       │
       ▼
 ┌───────────┐
 │@serialize │ ◄── Save/restore state beyond sliders
 └───────────┘
```

---

## Description Lines (File Header)

Before any code section, JSFX files begin with description lines:

```
desc:My Amazing Effect
// First line should be desc: for quick identification

tags:effect dynamics compressor
// Space-separated tags for categorization
// Use "instrument" tag for instruments (REAPER 6.74+)

slider1:threshold_db=-20<-60,0,0.1>Threshold (dB)
slider2:ratio=4<1,20,0.1>Ratio
slider3:attack_ms=10<0.1,100,0.1>Attack (ms)
slider4:release_ms=100<10,1000,1>Release (ms)
// Up to 256 sliders (slider1-slider256)

in_pin:left input
in_pin:right input
out_pin:left output
out_pin:right output
// Name audio pins for routing display

filename:0,impulse.wav
// Reference data files

options:no_meter
// Plugin options (see Options section below)

import my_library.jsfx-inc
// Import external code libraries
```

### Slider Syntax

```
sliderN:variable=default<min,max,step>Label

// Examples:
slider1:gain=0<-60,12,0.1>Gain (dB)
slider2:mode=0<0,2,1{Off,Soft,Hard}>Mode
slider3:freq=1000<20,20000,1:log>Frequency
slider4:file:6:impulse_response:Impulse File
slider5:-hidden_param=1<0,1,1>Hidden
```

**Slider options:**
- `{Option1,Option2,...}` - Dropdown menu
- `:log` - Logarithmic scaling
- `:sqr` - Quadratic scaling
- `file:N:path:` - File browser
- `-` prefix - Hidden parameter

---

## @init

**When it runs:**
- Plugin load
- Sample rate change
- Playback starts (unless `ext_noinit = 1`)
- User clicks "Reset" in plugin UI

**Use for:**
- Memory allocation
- Lookup table generation
- Constant calculation
- Initial state setup

```
@init

// Memory allocation
buffer = 0;                    // Start at offset 0
buffer_size = ceil(srate * 2); // 2 seconds max delay
freembuf(buffer + buffer_size); // Inform memory manager

// Lookup tables
sin_table = buffer + buffer_size;
table_size = 1024;
i = 0;
loop(table_size,
  sin_table[i] = sin(2 * $pi * i / table_size);
  i += 1;
);
freembuf(sin_table + table_size);

// Constants
TWO_PI = 2 * $pi;
INV_SRATE = 1 / srate;
MAX_CHANNELS = 64;

// Initial state
write_pos = 0;
envelope = 0;
```

### Preventing Re-initialization

```
@init
ext_noinit = 1;  // Don't re-run @init on playback start
```

---

## @slider

**When it runs:**
- User moves a slider
- Automation changes a parameter
- Host sends parameter change

**Use for:**
- Coefficient calculation
- Derived value computation
- Mode switching logic

```
@slider

// Convert dB to linear
gain_lin = 10^(gain_db / 20);

// Calculate filter coefficients
omega = 2 * $pi * cutoff_freq / srate;
alpha = sin(omega) / (2 * q);
a0 = 1 + alpha;
a1 = -2 * cos(omega);
a2 = 1 - alpha;
b0 = (1 - cos(omega)) / 2;
b1 = 1 - cos(omega);
b2 = (1 - cos(omega)) / 2;

// Normalize coefficients
a0_inv = 1 / a0;
b0 *= a0_inv;
b1 *= a0_inv;
b2 *= a0_inv;
a1 *= a0_inv;
a2 *= a0_inv;

// Convert time to samples
attack_samples = attack_ms * srate / 1000;
attack_coeff = exp(-1 / attack_samples);
```

### Sample-Accurate Automation

For parameters that need sample-accurate changes:

```
@sample
// Check for slider changes within this sample
slider_next_chg(slider1, next_val) ? (
  // Recalculate at exact sample position
  gain_lin = 10^(next_val / 20);
);

spl0 *= gain_lin;
spl1 *= gain_lin;
```

---

## @block

**When it runs:**
- Before each audio block (typically every 1-10ms)
- Before any @sample calls for that block

**Use for:**
- MIDI processing (receive all events for upcoming block)
- Block-level calculations
- Tempo synchronization

**Available variable:** `samplesblock` - number of samples in upcoming block

```
@block

// Process all MIDI events for this block
while(midirecv(offset, msg1, msg2, msg3)) (
  status = msg1 & $xF0;  // Message type
  channel = msg1 & $x0F; // Channel (0-15)

  status == $x90 && msg3 > 0 ? (  // Note On
    note_on_count += 1;
    last_note = msg2;
    last_velocity = msg3;
  );

  status == $x80 || (status == $x90 && msg3 == 0) ? (  // Note Off
    note_on_count -= 1;
  );

  // Pass through or modify
  midisend(offset, msg1, msg2, msg3);
);

// Tempo-synced calculations
beat_length_samples = srate * 60 / tempo;
measure_samples = beat_length_samples * ts_num;
```

---

## @sample

**When it runs:**
- Once per audio sample
- 44,100 times per second at 44.1kHz
- This is the **hot path** - optimize aggressively

**Available variables:**
- `spl0`, `spl1`, ... `spl63` - Audio samples (read/write)
- `spl(n)` - Programmatic channel access

**Use for:**
- Audio processing only
- Minimal branching
- No heavy calculations

```
@sample

// Simple gain
spl0 *= gain_lin;
spl1 *= gain_lin;

// Stereo processing
left = spl0;
right = spl1;
mid = (left + right) * 0.5;
side = (left - right) * 0.5;

// Process mid/side
mid *= mid_gain;
side *= side_gain;

// Convert back
spl0 = mid + side;
spl1 = mid - side;
```

### Multi-Channel Processing

```
@sample

// Process all channels
ch = 0;
loop(num_ch,
  spl(ch) *= gain_lin;
  ch += 1;
);
```

### Delay Line Example

```
@sample

// Write to delay buffer
delay_buffer[write_pos] = spl0;

// Read from delay buffer
read_pos = write_pos - delay_samples;
read_pos < 0 ? read_pos += delay_buffer_size;
delayed = delay_buffer[read_pos];

// Mix
spl0 = spl0 * dry_mix + delayed * wet_mix;

// Advance write position
write_pos += 1;
write_pos >= delay_buffer_size ? write_pos = 0;
```

---

## @gfx

**When it runs:**
- Approximately 30 times per second
- In a separate thread from audio
- Only when UI is visible

**Optional size hint:** `@gfx 400 300` requests 400x300 pixels

**Available variables:**
- `gfx_w`, `gfx_h` - Current UI dimensions
- `gfx_x`, `gfx_y` - Drawing cursor position
- `gfx_r`, `gfx_g`, `gfx_b`, `gfx_a` - Current color
- `mouse_x`, `mouse_y`, `mouse_cap` - Mouse state

**Use for:**
- Custom UI rendering
- Visualization (meters, waveforms)
- Mouse/keyboard interaction

```
@gfx 400 300

// Clear background
gfx_r = gfx_g = gfx_b = 0.1;
gfx_a = 1;
gfx_x = gfx_y = 0;
gfx_rectto(gfx_w, gfx_h);

// Draw level meter
gfx_r = 0; gfx_g = 0.8; gfx_b = 0.2;
meter_height = gfx_h * current_level;
gfx_x = 10;
gfx_y = gfx_h - meter_height;
gfx_rectto(50, gfx_h);

// Draw text
gfx_x = 60;
gfx_y = 10;
gfx_r = gfx_g = gfx_b = 1;
gfx_drawstr("Level:");
gfx_drawnumber(current_level_db, 1);
gfx_drawstr(" dB");
```

### Mouse Handling

```
@gfx
// Mouse button states in mouse_cap:
// 1 = left button
// 2 = right button
// 4 = control key
// 8 = shift key
// 16 = alt key
// 32 = Windows key
// 64 = middle button

// Check for click in region
mouse_cap & 1 ? (
  mouse_x >= knob_x && mouse_x < knob_x + knob_size &&
  mouse_y >= knob_y && mouse_y < knob_y + knob_size ? (
    // Clicked on knob
    dragging = 1;
    drag_start_y = mouse_y;
    drag_start_val = slider1;
  );
);

// Handle drag
dragging && !(mouse_cap & 1) ? dragging = 0;  // Released
dragging ? (
  delta = (drag_start_y - mouse_y) * 0.01;
  slider1 = drag_start_val + delta * (slider1_max - slider1_min);
  slider1 = max(slider1_min, min(slider1_max, slider1));
  slider_automate(slider1);  // Notify host
);
```

---

## @serialize

**When it runs:**
- Plugin state save (project save, preset save)
- Plugin state load (project load, preset load)

**Use for:**
- Saving/restoring state beyond slider values
- Large data (samples, tables, configurations)

**Mode detection:** `file_avail(0) >= 0` in read mode, `< 0` in write mode

```
@serialize

file_avail(0) >= 0 ? (
  // Reading (loading state)
  file_var(0, custom_param1);
  file_var(0, custom_param2);
  file_mem(0, my_table, table_size);
) : (
  // Writing (saving state)
  file_var(0, custom_param1);
  file_var(0, custom_param2);
  file_mem(0, my_table, table_size);
);
```

### Versioned Serialization

```
@serialize

SERIAL_VERSION = 2;

file_avail(0) >= 0 ? (
  // Reading
  file_var(0, version);
  file_var(0, param1);
  version >= 2 ? (
    file_var(0, param2);  // Added in version 2
  ) : (
    param2 = default_param2;  // Default for old presets
  );
) : (
  // Writing
  file_var(0, SERIAL_VERSION);
  file_var(0, param1);
  file_var(0, param2);
);
```

---

## Options

Configure plugin behavior with `options:` in the header:

```
options:no_meter                    // Disable built-in meter
options:gmem=MyPluginName           // Enable 8M shared memory
options:maxmem=16000000             // Request specific memory size
options:want_all_kb                 // Receive all keyboard input in @gfx
options:gfx_idle                    // Run @gfx even when not focused
options:gfx_hz=60                   // Request specific refresh rate
```

---

## Plugin Delay Compensation (PDC)

For plugins that introduce latency:

```
@init
pdc_delay = 512;      // Latency in samples
pdc_bot_ch = 0;       // First channel affected
pdc_top_ch = 2;       // Last channel + 1

// pdc_midi = 1;      // Also delay MIDI (if applicable)
```

---

## Extended Variables

```
@init
ext_noinit = 1;       // Don't re-run @init on playback start
ext_nodenorm = 1;     // Disable anti-denormal noise
ext_tail_size = 48000; // Report tail length to host (REAPER 6.71+)
```

---

## Common Section Patterns

### Filter Plugin Structure

```
desc:Simple Lowpass Filter
slider1:cutoff=1000<20,20000,1:log>Cutoff (Hz)
slider2:resonance=0.707<0.1,10,0.01:log>Resonance (Q)

@init
z1_l = z1_r = z2_l = z2_r = 0;

@slider
omega = 2 * $pi * cutoff / srate;
alpha = sin(omega) / (2 * resonance);
a0 = 1 + alpha;
a0_inv = 1 / a0;

b0 = ((1 - cos(omega)) / 2) * a0_inv;
b1 = (1 - cos(omega)) * a0_inv;
b2 = b0;
a1 = (-2 * cos(omega)) * a0_inv;
a2 = (1 - alpha) * a0_inv;

@sample
// Left channel
in_l = spl0;
out_l = b0 * in_l + b1 * z1_l + b2 * z2_l - a1 * z1_out_l - a2 * z2_out_l;
z2_l = z1_l; z1_l = in_l;
z2_out_l = z1_out_l; z1_out_l = out_l;
spl0 = out_l;

// Right channel
in_r = spl1;
out_r = b0 * in_r + b1 * z1_r + b2 * z2_r - a1 * z1_out_r - a2 * z2_out_r;
z2_r = z1_r; z1_r = in_r;
z2_out_r = z1_out_r; z1_out_r = out_r;
spl1 = out_r;
```

### Dynamics Processor Structure

```
desc:Simple Compressor
slider1:threshold_db=-20<-60,0,0.1>Threshold (dB)
slider2:ratio=4<1,20,0.1>Ratio
slider3:attack_ms=10<0.1,100,0.1>Attack (ms)
slider4:release_ms=100<10,1000,1>Release (ms)

@init
envelope = 0;

@slider
threshold_lin = 10^(threshold_db / 20);
attack_coeff = exp(-1 / (attack_ms * srate / 1000));
release_coeff = exp(-1 / (release_ms * srate / 1000));
ratio_inv = 1 / ratio;

@sample
// Detect level (peak)
input_level = max(abs(spl0), abs(spl1));

// Envelope follower
input_level > envelope ? (
  envelope = attack_coeff * envelope + (1 - attack_coeff) * input_level;
) : (
  envelope = release_coeff * envelope + (1 - release_coeff) * input_level;
);

// Calculate gain reduction
envelope > threshold_lin ? (
  over = envelope / threshold_lin;
  gain_reduction = pow(over, ratio_inv - 1);
) : (
  gain_reduction = 1;
);

// Apply gain
spl0 *= gain_reduction;
spl1 *= gain_reduction;
```
