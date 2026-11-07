---
title: "Modulation Effects"
impact: MEDIUM
tags:
  - modulation
  - lfo
  - tremolo
  - vibrato
  - phaser
  - ringmod
---

# Modulation Effects

LFO patterns, tremolo, vibrato, phaser, ring modulation, and auto-wah/envelope follower effects.

## References

- [LFO Design](https://ccrma.stanford.edu/~jos/pasp/Low_Frequency_Oscillators.html)
- [Phaser Design](https://ccrma.stanford.edu/~jos/pasp/Phasing.html)

---

## LFO (Low Frequency Oscillator)

### Basic LFO Shapes

```
@init
lfo_phase = 0;

@slider
lfo_freq = rate;  // Hz
lfo_inc = lfo_freq / srate;

@sample
// Advance phase
lfo_phase += lfo_inc;
lfo_phase >= 1 ? lfo_phase -= 1;

// Sine
lfo_sine = sin(2 * $pi * lfo_phase);

// Triangle
lfo_tri = abs(lfo_phase * 4 - 2) - 1;

// Saw (up)
lfo_saw = lfo_phase * 2 - 1;

// Saw (down)
lfo_saw_down = 1 - lfo_phase * 2;

// Square
lfo_square = lfo_phase < 0.5 ? 1 : -1;

// Pulse (variable width)
lfo_pulse = lfo_phase < pulse_width ? 1 : -1;

// Sample & Hold
lfo_phase < lfo_inc ? (
  lfo_sh = rand(2) - 1;  // New random on phase wrap
);

// Smoothed random (filtered S&H)
lfo_phase < lfo_inc ? lfo_sh_target = rand(2) - 1;
lfo_sh_smooth += 0.01 * (lfo_sh_target - lfo_sh_smooth);
```

### Tempo-Synced LFO

```
@slider
// Note division: 0=1/16, 1=1/8, 2=1/4, 3=1/2, 4=1, 5=2, 6=4
note_div == 0 ? beats = 0.25 :
note_div == 1 ? beats = 0.5 :
note_div == 2 ? beats = 1 :
note_div == 3 ? beats = 2 :
note_div == 4 ? beats = 4 :
note_div == 5 ? beats = 8 :
beats = 16;

// Apply dotted/triplet
dotted ? beats *= 1.5;
triplet ? beats *= 2/3;

@block
// Calculate LFO increment from tempo
beats_per_sample = tempo / (60 * srate);
lfo_inc = beats_per_sample / beats;

@sample
lfo_phase += lfo_inc;
lfo_phase >= 1 ? lfo_phase -= 1;
lfo_out = sin(2 * $pi * lfo_phase);
```

### LFO with Smoothing

```
@slider
// Smoothing coefficient (lower = smoother)
smooth_coeff = exp(-2 * $pi * 20 / srate);

@sample
lfo_phase += lfo_inc;
lfo_phase >= 1 ? lfo_phase -= 1;

// Raw LFO
lfo_raw = sin(2 * $pi * lfo_phase);

// Smoothed LFO (for parameter modulation)
lfo_smooth = smooth_coeff * lfo_smooth + (1 - smooth_coeff) * lfo_raw;
```

---

## Tremolo

### Simple Tremolo

```
desc:Tremolo
slider1:rate=5<0.1,20,0.01>Rate (Hz)
slider2:depth=50<0,100,1>Depth (%)

@init
lfo_phase = 0;

@slider
lfo_inc = rate / srate;
depth_amount = depth / 100;

@sample
// LFO
lfo_phase += lfo_inc;
lfo_phase >= 1 ? lfo_phase -= 1;
lfo = sin(2 * $pi * lfo_phase);

// Tremolo: modulate amplitude
// Map LFO [-1,1] to [1-depth, 1]
mod = 1 - depth_amount * (1 - lfo) * 0.5;

spl0 *= mod;
spl1 *= mod;
```

### Stereo Tremolo (Pan)

```
@slider
stereo_phase = 0.5;  // 0.5 = opposite phase

@sample
lfo_phase += lfo_inc;
lfo_phase >= 1 ? lfo_phase -= 1;

lfo_l = sin(2 * $pi * lfo_phase);
lfo_r = sin(2 * $pi * (lfo_phase + stereo_phase));

mod_l = 1 - depth * (1 - lfo_l) * 0.5;
mod_r = 1 - depth * (1 - lfo_r) * 0.5;

spl0 *= mod_l;
spl1 *= mod_r;
```

---

## Vibrato

Modulates pitch via delay line modulation.

```
desc:Vibrato
slider1:rate=5<0.1,10,0.01>Rate (Hz)
slider2:depth_cents=20<0,100,1>Depth (cents)

@init
buffer_size = srate / 10;  // 100ms buffer
buffer_l = 0;
buffer_r = buffer_size;
freembuf(buffer_size * 2);
write_pos = 0;
lfo_phase = 0;

// Base delay (center of modulation)
base_delay = buffer_size / 2;

@slider
lfo_inc = rate / srate;
// Convert cents to delay modulation
// 100 cents = 1 semitone = ~6% pitch change
// pitch_ratio = 2^(cents/1200)
// delay_mod = base_delay * (1 - pitch_ratio)
max_delay_mod = base_delay * (1 - pow(2, -depth_cents / 1200));

@sample
// LFO
lfo_phase += lfo_inc;
lfo_phase >= 1 ? lfo_phase -= 1;
lfo = sin(2 * $pi * lfo_phase);

// Modulated delay time
delay_samples = base_delay + lfo * max_delay_mod;

// Read with interpolation
read_pos = write_pos - delay_samples;
read_pos < 0 ? read_pos += buffer_size;

idx = floor(read_pos);
frac = read_pos - idx;
idx_next = idx + 1;
idx_next >= buffer_size ? idx_next = 0;

// Linear interpolation
out_l = buffer_l[idx] * (1 - frac) + buffer_l[idx_next] * frac;
out_r = buffer_r[idx] * (1 - frac) + buffer_r[idx_next] * frac;

// Write to buffer
buffer_l[write_pos] = spl0;
buffer_r[write_pos] = spl1;

spl0 = out_l;
spl1 = out_r;

write_pos += 1;
write_pos >= buffer_size ? write_pos = 0;
```

---

## Phaser

Series of allpass filters with modulated frequency.

```
desc:Phaser
slider1:rate=0.5<0.01,5,0.01>Rate (Hz)
slider2:depth=80<0,100,1>Depth (%)
slider3:feedback=0.7<0,0.95,0.01>Feedback
slider4:stages=4<2,12,1>Stages
slider5:mix=50<0,100,1>Mix (%)

@init
// Max 12 stages, stereo
max_stages = 12;
ap_state_l = 0;
ap_state_r = max_stages;
freembuf(max_stages * 2);
memset(ap_state_l, 0, max_stages);
memset(ap_state_r, 0, max_stages);

lfo_phase = 0;
feedback_l = feedback_r = 0;

// Frequency range for allpass modulation
min_freq = 200;
max_freq = 4000;

@slider
lfo_inc = rate / srate;
depth_amount = depth / 100;
wet = mix / 100;
dry = 1 - wet;
num_stages = floor(stages);

@sample
// LFO
lfo_phase += lfo_inc;
lfo_phase >= 1 ? lfo_phase -= 1;
lfo = sin(2 * $pi * lfo_phase);

// Map LFO to frequency range
mod_freq = min_freq + (max_freq - min_freq) * (lfo * 0.5 + 0.5) * depth_amount;

// Allpass coefficient from frequency
ap_coeff = (1 - tan($pi * mod_freq / srate)) / (1 + tan($pi * mod_freq / srate));

// Process through allpass chain
in_l = spl0 + feedback_l * feedback;
in_r = spl1 + feedback_r * feedback;

i = 0;
loop(num_stages,
  // Left channel allpass
  temp = ap_state_l[i];
  ap_state_l[i] = in_l * ap_coeff + temp;
  in_l = temp - in_l * ap_coeff;

  // Right channel allpass
  temp = ap_state_r[i];
  ap_state_r[i] = in_r * ap_coeff + temp;
  in_r = temp - in_r * ap_coeff;

  i += 1;
);

// Store for feedback
feedback_l = in_l;
feedback_r = in_r;

// Mix
spl0 = spl0 * dry + in_l * wet;
spl1 = spl1 * dry + in_r * wet;
```

---

## Ring Modulator

```
desc:Ring Modulator
slider1:freq=440<20,2000,1>Frequency (Hz)
slider2:mix=100<0,100,1>Mix (%)

@init
osc_phase = 0;

@slider
osc_inc = freq / srate;
wet = mix / 100;
dry = 1 - wet;

@sample
// Carrier oscillator
osc_phase += osc_inc;
osc_phase >= 1 ? osc_phase -= 1;
carrier = sin(2 * $pi * osc_phase);

// Ring modulation (multiply)
ring_l = spl0 * carrier;
ring_r = spl1 * carrier;

// Mix
spl0 = spl0 * dry + ring_l * wet;
spl1 = spl1 * dry + ring_r * wet;
```

---

## Auto-Wah / Envelope Follower

```
desc:Auto-Wah
slider1:sensitivity=50<0,100,1>Sensitivity
slider2:attack_ms=10<1,100,1>Attack (ms)
slider3:release_ms=100<10,500,1>Release (ms)
slider4:min_freq=200<100,1000,1>Min Freq (Hz)
slider5:max_freq=2000<500,8000,1>Max Freq (Hz)
slider6:q=2<0.5,10,0.1>Resonance (Q)

@init
envelope = 0;
// Filter states
z1_l = z2_l = z1_r = z2_r = 0;

@slider
attack_coeff = exp(-1 / (attack_ms * srate / 1000));
release_coeff = exp(-1 / (release_ms * srate / 1000));
sensitivity_scale = sensitivity / 100 * 4;

@sample
// Envelope follower
input_level = max(abs(spl0), abs(spl1));

input_level > envelope ? (
  envelope = attack_coeff * envelope + (1 - attack_coeff) * input_level;
) : (
  envelope = release_coeff * envelope;
);

// Scale envelope to filter frequency
mod_freq = min_freq + (max_freq - min_freq) * min(1, envelope * sensitivity_scale);

// Calculate filter coefficients (lowpass or bandpass)
omega = 2 * $pi * mod_freq / srate;
sin_omega = sin(omega);
cos_omega = cos(omega);
alpha = sin_omega / (2 * q);

// Bandpass for wah character
a0_inv = 1 / (1 + alpha);
b0 = alpha * a0_inv;
b1 = 0;
b2 = -alpha * a0_inv;
a1 = (-2 * cos_omega) * a0_inv;
a2 = (1 - alpha) * a0_inv;

// Apply filter (Direct Form II Transposed)
out_l = b0 * spl0 + z1_l;
z1_l = b1 * spl0 - a1 * out_l + z2_l;
z2_l = b2 * spl0 - a2 * out_l;

out_r = b0 * spl1 + z1_r;
z1_r = b1 * spl1 - a1 * out_r + z2_r;
z2_r = b2 * spl1 - a2 * out_r;

spl0 = out_l;
spl1 = out_r;
```

---

## Rotary Speaker (Leslie)

```
desc:Rotary Speaker
slider1:speed=0<0,1,1{Slow,Fast}>Speed
slider2:mix=100<0,100,1>Mix (%)

@init
// Horn and drum rotate at different speeds
horn_phase = 0;
drum_phase = 0;

// Delay buffers for doppler
buffer_size = srate / 10;
buffer = 0;
freembuf(buffer_size);
write_pos = 0;

// Speeds (Hz)
horn_slow = 0.8;
horn_fast = 6.5;
drum_slow = 0.7;
drum_fast = 5.5;

// Transition smoothing
current_horn_speed = horn_slow;
current_drum_speed = drum_slow;

@slider
target_horn_speed = speed ? horn_fast : horn_slow;
target_drum_speed = speed ? drum_fast : drum_slow;
wet = mix / 100;
dry = 1 - wet;

@sample
// Smooth speed transitions (simulates motor inertia)
current_horn_speed += 0.0001 * (target_horn_speed - current_horn_speed);
current_drum_speed += 0.0001 * (target_drum_speed - current_drum_speed);

// Advance phases
horn_phase += current_horn_speed / srate;
horn_phase >= 1 ? horn_phase -= 1;
drum_phase += current_drum_speed / srate;
drum_phase >= 1 ? drum_phase -= 1;

// Horn simulation (high frequencies)
horn_mod = sin(2 * $pi * horn_phase);
horn_delay = 5 + horn_mod * 3;  // 2-8ms modulation

// Drum simulation (low frequencies)
drum_mod = sin(2 * $pi * drum_phase);

// Read from delay buffer with modulated delay
read_pos = write_pos - horn_delay * srate / 1000;
read_pos < 0 ? read_pos += buffer_size;
idx = floor(read_pos);
frac = read_pos - idx;
idx_next = idx + 1;
idx_next >= buffer_size ? idx_next = 0;

horn_out = buffer[idx] * (1 - frac) + buffer[idx_next] * frac;

// Amplitude modulation for rotation effect
horn_out *= (1 + horn_mod * 0.3);

// Write to buffer
buffer[write_pos] = (spl0 + spl1) * 0.5;

// Combine horn and direct (simplified)
rotary = horn_out;

// Stereo image from phase
pan_l = (1 + horn_mod) * 0.5;
pan_r = (1 - horn_mod) * 0.5;

spl0 = spl0 * dry + rotary * pan_l * wet;
spl1 = spl1 * dry + rotary * pan_r * wet;

write_pos += 1;
write_pos >= buffer_size ? write_pos = 0;
```

---

## LFO Library Pattern

```
// lfo.jsfx-inc

function lfo.init()
  instance(phase)
(
  phase = 0;
);

function lfo.set_freq(freq)
  instance(inc)
(
  inc = freq / srate;
);

function lfo.set_tempo_sync(beats, tempo)
  instance(inc)
  local(beats_per_sample)
(
  beats_per_sample = tempo / (60 * srate);
  inc = beats_per_sample / beats;
);

function lfo.tick()
  instance(phase, inc)
(
  phase += inc;
  phase >= 1 ? phase -= 1;
);

function lfo.sine()
  instance(phase)
(
  sin(2 * $pi * phase);
);

function lfo.tri()
  instance(phase)
(
  abs(phase * 4 - 2) - 1;
);

function lfo.saw()
  instance(phase)
(
  phase * 2 - 1;
);

function lfo.square()
  instance(phase)
(
  phase < 0.5 ? 1 : -1;
);

// Usage:
// mod_lfo.lfo.init();
// mod_lfo.lfo.set_freq(5);
// @sample
// mod_lfo.lfo.tick();
// modulation = mod_lfo.lfo.sine() * depth;
```
