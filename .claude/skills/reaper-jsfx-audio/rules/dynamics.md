---
title: "Dynamics Processing"
impact: HIGH
tags:
  - dynamics
  - compressor
  - limiter
  - gate
  - envelope
---

# Dynamics Processing

Dynamics processors including compressors, limiters, gates, expanders, and envelope followers.

## References

- [Digital Dynamic Range Compressor Design](https://www.eecs.qmul.ac.uk/~josh/documents/2012/GissonReiss-DAFx2012-DRC.pdf)
- [musicdsp.org Dynamics](https://www.musicdsp.org/en/latest/Effects/index.html)

---

## Envelope Detection

The foundation of all dynamics processors.

### Peak Detection

```
@init
envelope = 0;

@slider
attack_samples = attack_ms * srate / 1000;
release_samples = release_ms * srate / 1000;
attack_coeff = exp(-1 / attack_samples);
release_coeff = exp(-1 / release_samples);

@sample
// Rectified input
input_abs = abs(spl0);

// Branched envelope follower
input_abs > envelope ? (
  envelope = attack_coeff * envelope + (1 - attack_coeff) * input_abs;
) : (
  envelope = release_coeff * envelope;
);
```

### RMS Detection

More musical, less sensitive to transients:

```
@init
rms_sum = 0;
rms_buffer = 0;
rms_size = 0;
rms_pos = 0;

@slider
// RMS window size (typically 10-300ms)
rms_size = floor(rms_window_ms * srate / 1000);
rms_size = max(1, min(rms_size, 48000));  // Clamp

@sample
// Squared input
squared = spl0 * spl0;

// Running sum (subtract old, add new)
rms_sum -= rms_buffer[rms_pos];
rms_sum += squared;
rms_buffer[rms_pos] = squared;

// Advance position
rms_pos += 1;
rms_pos >= rms_size ? rms_pos = 0;

// RMS value
envelope = sqrt(rms_sum / rms_size);
```

### Stereo Envelope (Linked)

```
@sample
// Max of both channels
input_level = max(abs(spl0), abs(spl1));

// Or true stereo peak
input_level = sqrt(spl0*spl0 + spl1*spl1);

// Apply envelope follower
input_level > envelope ? (
  envelope = attack_coeff * envelope + (1 - attack_coeff) * input_level;
) : (
  envelope = release_coeff * envelope;
);

// Same gain applied to both channels
```

---

## Compressor

### Basic Compressor

```
desc:Simple Compressor
slider1:threshold_db=-20<-60,0,0.1>Threshold (dB)
slider2:ratio=4<1,20,0.1>Ratio
slider3:attack_ms=10<0.1,100,0.1>Attack (ms)
slider4:release_ms=100<10,1000,1>Release (ms)
slider5:makeup_db=0<0,24,0.1>Makeup (dB)
slider6:knee_db=0<0,12,0.1>Knee (dB)

@init
envelope = 0;

@slider
threshold_lin = 10^(threshold_db / 20);
makeup_lin = 10^(makeup_db / 20);
attack_coeff = exp(-1 / (attack_ms * srate / 1000));
release_coeff = exp(-1 / (release_ms * srate / 1000));

// Precompute ratio inverse for soft knee
ratio_inv = 1 / ratio;

@sample
// Stereo input level
input_level = max(abs(spl0), abs(spl1));

// Envelope follower
input_level > envelope ? (
  envelope = attack_coeff * envelope + (1 - attack_coeff) * input_level;
) : (
  envelope = release_coeff * envelope;
);

// Gain calculation (in linear domain)
envelope > threshold_lin ? (
  // How much over threshold
  over = envelope / threshold_lin;

  // Apply ratio
  gain_reduction = pow(over, ratio_inv - 1);
) : (
  gain_reduction = 1;
);

// Apply gain reduction and makeup
spl0 *= gain_reduction * makeup_lin;
spl1 *= gain_reduction * makeup_lin;
```

### Soft Knee Compressor

```
@slider
// Knee width in dB
knee_width = knee_db;
knee_start = threshold_db - knee_width / 2;
knee_end = threshold_db + knee_width / 2;

@sample
// Convert envelope to dB
env_db = envelope > 0.0000001 ? 20 * log10(envelope) : -140;

// Soft knee gain calculation
env_db < knee_start ? (
  // Below knee - no compression
  gain_db = 0;
) : env_db > knee_end ? (
  // Above knee - full compression
  over_db = env_db - threshold_db;
  gain_db = over_db * (ratio_inv - 1);
) : (
  // In knee - smooth transition
  knee_factor = (env_db - knee_start) / knee_width;
  over_db = env_db - threshold_db;

  // Quadratic interpolation
  gain_db = knee_factor * knee_factor * over_db * (ratio_inv - 1) / 2;
);

// Convert to linear gain
gain_reduction = 10^(gain_db / 20);
```

### Feedforward vs Feedback

**Feedforward** (shown above): Uses input level for detection
**Feedback**: Uses output level for detection (more vintage character)

```
@sample
// FEEDBACK topology
// Detect from output instead of input
input_level = max(abs(spl0 * last_gain), abs(spl1 * last_gain));

// ... envelope and gain calculation ...

last_gain = gain_reduction * makeup_lin;
spl0 *= last_gain;
spl1 *= last_gain;
```

---

## Limiter

### Brickwall Limiter

```
desc:Brickwall Limiter
slider1:ceiling_db=-0.3<-12,0,0.1>Ceiling (dB)
slider2:release_ms=100<10,1000,1>Release (ms)

@init
envelope = 0;
// Lookahead buffer
lookahead_ms = 5;
lookahead_samples = 0;
buffer_l = 0;
buffer_r = 0;
buffer_pos = 0;

@slider
ceiling_lin = 10^(ceiling_db / 20);
release_coeff = exp(-1 / (release_ms * srate / 1000));

lookahead_samples = floor(lookahead_ms * srate / 1000);
buffer_size = lookahead_samples + 1;
freembuf(buffer_size * 2);

@sample
// Store input in lookahead buffer
buffer_l[buffer_pos] = spl0;
buffer_r[buffer_pos] = spl1;

// Current input level
input_level = max(abs(spl0), abs(spl1));

// Required gain reduction
required_reduction = input_level > ceiling_lin ? ceiling_lin / input_level : 1;

// Envelope (instant attack, smooth release)
required_reduction < envelope ? (
  envelope = required_reduction;  // Instant attack
) : (
  envelope = release_coeff * envelope + (1 - release_coeff);
);

// Read delayed signal
read_pos = buffer_pos - lookahead_samples;
read_pos < 0 ? read_pos += buffer_size;

// Apply gain to delayed signal
spl0 = buffer_l[read_pos] * envelope;
spl1 = buffer_r[read_pos] * envelope;

// Advance buffer
buffer_pos += 1;
buffer_pos >= buffer_size ? buffer_pos = 0;
```

### True Peak Limiter

Prevents inter-sample peaks by oversampling:

```
@sample
// 4x oversample to detect inter-sample peaks
s0 = spl0;
s1 = (3*last_spl0 + spl0) / 4;
s2 = (last_spl0 + spl0) / 2;
s3 = (last_spl0 + 3*spl0) / 4;
last_spl0 = spl0;

// True peak is max of oversampled values
true_peak = max(max(abs(s0), abs(s1)), max(abs(s2), abs(s3)));

// Use true_peak for limiting
```

---

## Gate / Expander

### Noise Gate

```
desc:Noise Gate
slider1:threshold_db=-40<-80,0,0.1>Threshold (dB)
slider2:attack_ms=0.5<0.1,50,0.1>Attack (ms)
slider3:hold_ms=50<0,500,1>Hold (ms)
slider4:release_ms=100<10,1000,1>Release (ms)
slider5:range_db=-80<-80,0,0.1>Range (dB)

@init
envelope = 0;
gate_gain = 0;
hold_counter = 0;

@slider
threshold_lin = 10^(threshold_db / 20);
range_lin = 10^(range_db / 20);
attack_coeff = exp(-1 / (attack_ms * srate / 1000));
release_coeff = exp(-1 / (release_ms * srate / 1000));
hold_samples = hold_ms * srate / 1000;

@sample
input_level = max(abs(spl0), abs(spl1));

// Envelope follower (fast)
input_level > envelope ? (
  envelope = 0.9 * envelope + 0.1 * input_level;
) : (
  envelope = 0.9999 * envelope;
);

// Gate state machine
envelope > threshold_lin ? (
  // Above threshold - open gate
  gate_gain = attack_coeff * gate_gain + (1 - attack_coeff);
  hold_counter = hold_samples;
) : hold_counter > 0 ? (
  // In hold phase - keep gate open
  hold_counter -= 1;
) : (
  // Below threshold - close gate
  gate_gain = release_coeff * gate_gain + (1 - release_coeff) * range_lin;
);

// Apply gate
spl0 *= gate_gain;
spl1 *= gate_gain;
```

### Expander

```
@slider
// Expansion ratio (e.g., 2:1 means 1dB below threshold becomes 2dB)
expansion_ratio = ratio;

@sample
// ... envelope detection ...

envelope < threshold_lin ? (
  // Below threshold - expand (reduce gain)
  under_db = 20 * log10(threshold_lin / max(envelope, 0.0000001));
  expand_db = under_db * (expansion_ratio - 1);
  gain = 10^(-expand_db / 20);
) : (
  gain = 1;
);
```

---

## Sidechain Processing

### External Sidechain

```
desc:Sidechain Compressor
// Channels 3-4 are sidechain input
in_pin:left input
in_pin:right input
in_pin:sidechain left
in_pin:sidechain right
out_pin:left output
out_pin:right output

@sample
// Detect from sidechain (channels 2-3, zero-indexed)
sidechain_level = max(abs(spl2), abs(spl3));

// ... envelope and compression logic using sidechain_level ...

// Apply to main signal
spl0 *= gain_reduction;
spl1 *= gain_reduction;

// Mute sidechain output
spl2 = 0;
spl3 = 0;
```

### Sidechain Filter

```
@init
// Highpass the sidechain for de-essing
sc_z1 = sc_z2 = 0;

@slider
// Sidechain HPF at e.g. 3kHz
sc_omega = 2 * $pi * sc_freq / srate;
sc_alpha = sin(sc_omega) / (2 * 0.707);
sc_a0_inv = 1 / (1 + sc_alpha);
sc_b0 = ((1 + cos(sc_omega)) / 2) * sc_a0_inv;
sc_b1 = (-(1 + cos(sc_omega))) * sc_a0_inv;
sc_b2 = sc_b0;
sc_a1 = (-2 * cos(sc_omega)) * sc_a0_inv;
sc_a2 = (1 - sc_alpha) * sc_a0_inv;

@sample
// Filter sidechain signal
sc_input = (spl0 + spl1) * 0.5;  // Or external sidechain
sc_filtered = sc_b0 * sc_input + sc_z1;
sc_z1 = sc_b1 * sc_input - sc_a1 * sc_filtered + sc_z2;
sc_z2 = sc_b2 * sc_input - sc_a2 * sc_filtered;

// Detect from filtered sidechain
input_level = abs(sc_filtered);
```

---

## Multiband Dynamics

### Simple 2-Band Compressor

```
@init
// Crossover filter states
lp_z1 = lp_z2 = 0;
hp_z1 = hp_z2 = 0;

// Per-band envelopes
env_low = env_high = 0;

@slider
// Linkwitz-Riley crossover (4th order = 2x biquad)
// ... calculate crossover coefficients ...

@sample
// Split bands
input = spl0;

// Lowpass (2nd order, will cascade for LR4)
lp_out = ... biquad lowpass ...;

// Highpass
hp_out = ... biquad highpass ...;

// Compress each band independently
// Low band
env_low = ... envelope follower on lp_out ...;
gain_low = ... compression gain calculation ...;
lp_out *= gain_low;

// High band
env_high = ... envelope follower on hp_out ...;
gain_high = ... compression gain calculation ...;
hp_out *= gain_high;

// Sum bands
spl0 = lp_out + hp_out;
```

---

## Gain Reduction Metering

Report gain reduction to host:

```
@sample
// ... dynamics processing ...

// Report to host meter (REAPER 7.0+)
ext_gr_meter = gain_reduction;  // 0-1 range, 1 = no reduction

// Store for UI
gr_display = 20 * log10(gain_reduction);  // In dB
```

---

## Complete Compressor Template

```
desc:Full Featured Compressor
slider1:threshold_db=-20<-60,0,0.1>Threshold (dB)
slider2:ratio=4<1,20,0.1>Ratio
slider3:attack_ms=10<0.1,100,0.1>Attack (ms)
slider4:release_ms=100<10,1000,1>Release (ms)
slider5:knee_db=6<0,24,0.1>Knee (dB)
slider6:makeup_db=0<0,24,0.1>Makeup (dB)
slider7:mix=100<0,100,1>Mix (%)
slider8:auto_makeup=0<0,1,1{Off,On}>Auto Makeup

in_pin:left input
in_pin:right input
out_pin:left output
out_pin:right output

@init
envelope = 0;
gr_meter = 1;

@slider
threshold_lin = 10^(threshold_db / 20);
makeup_lin = 10^(makeup_db / 20);
attack_coeff = exp(-1 / (attack_ms * srate / 1000));
release_coeff = exp(-1 / (release_ms * srate / 1000));
wet = mix / 100;
dry = 1 - wet;

// Auto makeup gain estimation
auto_makeup_gain = auto_makeup ? pow(threshold_lin, 1 - 1/ratio) : 1;

@sample
// Store dry signal
dry_l = spl0;
dry_r = spl1;

// Stereo linked detection
input_level = max(abs(spl0), abs(spl1));

// Envelope
input_level > envelope ? (
  envelope = attack_coeff * envelope + (1 - attack_coeff) * input_level;
) : (
  envelope = release_coeff * envelope;
);

// dB domain for soft knee
env_db = envelope > 0.0000001 ? 20 * log10(envelope) : -140;

// Soft knee compression curve
knee_start = threshold_db - knee_db / 2;
knee_end = threshold_db + knee_db / 2;

env_db < knee_start ? (
  gain_db = 0;
) : env_db > knee_end ? (
  over_db = env_db - threshold_db;
  gain_db = over_db * (1/ratio - 1);
) : (
  // Soft knee
  x = (env_db - knee_start) / knee_db;
  over_db = env_db - threshold_db;
  gain_db = x * x * over_db * (1/ratio - 1) / 2;
);

// Gain reduction
gr = 10^(gain_db / 20);
gr_meter = gr;  // For metering

// Apply compression
total_gain = gr * makeup_lin * auto_makeup_gain;
wet_l = spl0 * total_gain;
wet_r = spl1 * total_gain;

// Mix
spl0 = dry_l * dry + wet_l * wet;
spl1 = dry_r * dry + wet_r * wet;

// Report to host
ext_gr_meter = gr;
```
