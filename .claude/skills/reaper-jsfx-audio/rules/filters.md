---
title: "Filters"
impact: CRITICAL
tags:
  - filter
  - eq
  - biquad
  - svf
  - lowpass
  - highpass
---

# Filters

Filter implementations for JSFX including biquad (RBJ cookbook), state variable filters (SVF), zero-delay feedback (ZDF), and simple one-pole filters.

## References

- [Audio EQ Cookbook](https://webaudio.github.io/Audio-EQ-Cookbook/audio-eq-cookbook.html) - Robert Bristow-Johnson
- [Tale's rbj_filter.jsfx-inc](https://www.taletn.com/reaper/mono_synth/)
- [Tale's zdf_filter.jsfx-inc](https://www.taletn.com/reaper/mono_synth/)

---

## One-Pole Filter (6dB/octave)

Simplest filter, good for smoothing and basic tone shaping.

### Lowpass

```
@init
z1 = 0;

@slider
// Cutoff frequency to coefficient
coeff = 1 - exp(-2 * $pi * cutoff / srate);

@sample
z1 += coeff * (spl0 - z1);
spl0 = z1;
```

### Highpass

```
@init
z1 = 0;
last_input = 0;

@slider
coeff = exp(-2 * $pi * cutoff / srate);

@sample
output = coeff * (z1 + spl0 - last_input);
last_input = spl0;
z1 = output;
spl0 = output;
```

### RC Filter (Alternative Formulation)

```
@init
z1 = 0;

@slider
// RC time constant
rc = 1 / (2 * $pi * cutoff);
dt = 1 / srate;
alpha = dt / (rc + dt);

@sample
z1 = z1 + alpha * (spl0 - z1);
spl0 = z1;
```

---

## Biquad Filter (12dB/octave)

Standard second-order IIR filter using RBJ cookbook coefficients.

### Direct Form II Transposed (Recommended)

Most numerically stable form:

```
@init
z1 = z2 = 0;

@slider
omega = 2 * $pi * cutoff / srate;
sin_omega = sin(omega);
cos_omega = cos(omega);
alpha = sin_omega / (2 * q);

// Normalize by a0
a0_inv = 1 / (1 + alpha);

// Lowpass
b0 = ((1 - cos_omega) / 2) * a0_inv;
b1 = (1 - cos_omega) * a0_inv;
b2 = b0;
a1 = (-2 * cos_omega) * a0_inv;
a2 = (1 - alpha) * a0_inv;

@sample
output = b0 * spl0 + z1;
z1 = b1 * spl0 - a1 * output + z2;
z2 = b2 * spl0 - a2 * output;
spl0 = output;
```

### All Biquad Types (RBJ Cookbook)

```
@slider
omega = 2 * $pi * cutoff / srate;
sin_omega = sin(omega);
cos_omega = cos(omega);
alpha = sin_omega / (2 * q);

filter_type == 0 ? (  // Lowpass
  b0 = (1 - cos_omega) / 2;
  b1 = 1 - cos_omega;
  b2 = (1 - cos_omega) / 2;
  a0 = 1 + alpha;
  a1 = -2 * cos_omega;
  a2 = 1 - alpha;
) : filter_type == 1 ? (  // Highpass
  b0 = (1 + cos_omega) / 2;
  b1 = -(1 + cos_omega);
  b2 = (1 + cos_omega) / 2;
  a0 = 1 + alpha;
  a1 = -2 * cos_omega;
  a2 = 1 - alpha;
) : filter_type == 2 ? (  // Bandpass (constant skirt gain)
  b0 = sin_omega / 2;
  b1 = 0;
  b2 = -sin_omega / 2;
  a0 = 1 + alpha;
  a1 = -2 * cos_omega;
  a2 = 1 - alpha;
) : filter_type == 3 ? (  // Bandpass (constant peak gain)
  b0 = alpha;
  b1 = 0;
  b2 = -alpha;
  a0 = 1 + alpha;
  a1 = -2 * cos_omega;
  a2 = 1 - alpha;
) : filter_type == 4 ? (  // Notch
  b0 = 1;
  b1 = -2 * cos_omega;
  b2 = 1;
  a0 = 1 + alpha;
  a1 = -2 * cos_omega;
  a2 = 1 - alpha;
) : filter_type == 5 ? (  // Allpass
  b0 = 1 - alpha;
  b1 = -2 * cos_omega;
  b2 = 1 + alpha;
  a0 = 1 + alpha;
  a1 = -2 * cos_omega;
  a2 = 1 - alpha;
) : filter_type == 6 ? (  // Peaking EQ
  A = 10^(gain_db / 40);  // sqrt of gain
  b0 = 1 + alpha * A;
  b1 = -2 * cos_omega;
  b2 = 1 - alpha * A;
  a0 = 1 + alpha / A;
  a1 = -2 * cos_omega;
  a2 = 1 - alpha / A;
) : filter_type == 7 ? (  // Low Shelf
  A = 10^(gain_db / 40);
  b0 = A * ((A + 1) - (A - 1) * cos_omega + 2 * sqrt(A) * alpha);
  b1 = 2 * A * ((A - 1) - (A + 1) * cos_omega);
  b2 = A * ((A + 1) - (A - 1) * cos_omega - 2 * sqrt(A) * alpha);
  a0 = (A + 1) + (A - 1) * cos_omega + 2 * sqrt(A) * alpha;
  a1 = -2 * ((A - 1) + (A + 1) * cos_omega);
  a2 = (A + 1) + (A - 1) * cos_omega - 2 * sqrt(A) * alpha;
) : filter_type == 8 ? (  // High Shelf
  A = 10^(gain_db / 40);
  b0 = A * ((A + 1) + (A - 1) * cos_omega + 2 * sqrt(A) * alpha);
  b1 = -2 * A * ((A - 1) + (A + 1) * cos_omega);
  b2 = A * ((A + 1) + (A - 1) * cos_omega - 2 * sqrt(A) * alpha);
  a0 = (A + 1) - (A - 1) * cos_omega + 2 * sqrt(A) * alpha;
  a1 = 2 * ((A - 1) - (A + 1) * cos_omega);
  a2 = (A + 1) - (A - 1) * cos_omega - 2 * sqrt(A) * alpha;
);

// Normalize
a0_inv = 1 / a0;
b0 *= a0_inv;
b1 *= a0_inv;
b2 *= a0_inv;
a1 *= a0_inv;
a2 *= a0_inv;
```

### Complete Stereo Biquad Implementation

```
desc:Stereo Biquad Filter
slider1:cutoff=1000<20,20000,1:log>Cutoff (Hz)
slider2:q=0.707<0.1,10,0.01:log>Q
slider3:type=0<0,8,1{LP,HP,BP Skirt,BP Peak,Notch,Allpass,Peaking,Low Shelf,High Shelf}>Type
slider4:gain_db=0<-24,24,0.1>Gain (dB) [Peaking/Shelf only]

@init
// Left channel state
z1_l = z2_l = 0;
// Right channel state
z1_r = z2_r = 0;

@slider
omega = 2 * $pi * cutoff / srate;
sin_omega = sin(omega);
cos_omega = cos(omega);
alpha = sin_omega / (2 * q);
A = 10^(gain_db / 40);

// [Calculate coefficients based on type - see above]
// ...normalize coefficients...

@sample
// Left channel
out_l = b0 * spl0 + z1_l;
z1_l = b1 * spl0 - a1 * out_l + z2_l;
z2_l = b2 * spl0 - a2 * out_l;
spl0 = out_l;

// Right channel
out_r = b0 * spl1 + z1_r;
z1_r = b1 * spl1 - a1 * out_r + z2_r;
z2_r = b2 * spl1 - a2 * out_r;
spl1 = out_r;
```

---

## State Variable Filter (SVF)

Provides multiple outputs simultaneously. Good for synth-style filtering.

### Basic SVF

```
@init
low = band = high = notch = 0;
ic1eq = ic2eq = 0;

@slider
g = tan($pi * cutoff / srate);
k = 1 / q;  // Damping

@sample
input = spl0;

// Tick the filter
v1 = (input - ic2eq - k * ic1eq) / (1 + g * k + g * g);
v2 = v1 * g + ic1eq;
v3 = v2 * g + ic2eq;

ic1eq = v2 + v1 * g;
ic2eq = v3 + v2 * g;

// Outputs
low = v3;
band = v2;
high = input - k * v2 - v3;
notch = input - k * v2;

// Select output
spl0 = filter_type == 0 ? low :
       filter_type == 1 ? high :
       filter_type == 2 ? band : notch;
```

### Multimode SVF (Morph Between Types)

```
@slider
// morph: 0=LP, 0.5=BP, 1=HP
low_mix = max(0, 1 - 2 * morph);
band_mix = 1 - abs(2 * morph - 1);
high_mix = max(0, 2 * morph - 1);

@sample
// ... SVF processing ...

spl0 = low * low_mix + band * band_mix + high * high_mix;
```

---

## Zero-Delay Feedback Filter (ZDF)

Eliminates the one-sample delay in traditional filters. Better for modulation.

### ZDF One-Pole

```
@init
s = 0;  // State

@slider
g = tan($pi * cutoff / srate);

@sample
// Lowpass
v = (spl0 - s) * g / (1 + g);
lp = v + s;
s = lp + v;

// Highpass
hp = spl0 - lp;

spl0 = lp;  // or hp
```

### ZDF SVF (TPT Structure)

```
@init
ic1eq = ic2eq = 0;

@slider
g = tan($pi * cutoff / srate);
k = 2 - 2 * resonance;  // 0-2 range for resonance

@sample
input = spl0;

v1 = (input - ic2eq - k * ic1eq) / (1 + g * (g + k));
v2 = v1 * g + ic1eq;
v3 = v2 * g + ic2eq;

ic1eq = v2 + v1 * g;
ic2eq = v3 + v2 * g;

low = v3;
band = v2;
high = input - k * v2 - v3;

spl0 = low;  // or band, high
```

---

## Filter Cascading

### 24dB/octave (4-pole)

Cascade two biquads:

```
@init
// Stage 1
z1_1 = z2_1 = 0;
// Stage 2
z1_2 = z2_2 = 0;

@slider
// Calculate Butterworth Q for 4-pole
// Q values: 0.541, 1.307 for flat response
q1 = 0.541;
q2 = 1.307;

// Calculate coefficients for each stage
// Stage 1 with q1
// Stage 2 with q2
// ...

@sample
// Stage 1
temp = b0_1 * spl0 + z1_1;
z1_1 = b1_1 * spl0 - a1_1 * temp + z2_1;
z2_1 = b2_1 * spl0 - a2_1 * temp;

// Stage 2
out = b0_2 * temp + z1_2;
z1_2 = b1_2 * temp - a1_2 * out + z2_2;
z2_2 = b2_2 * temp - a2_2 * out;

spl0 = out;
```

### Butterworth Q Values

| Order | Poles | Q Values |
|-------|-------|----------|
| 2 | 2 | 0.707 |
| 4 | 4 | 0.541, 1.307 |
| 6 | 6 | 0.518, 0.707, 1.932 |
| 8 | 8 | 0.510, 0.601, 0.900, 2.563 |

---

## DC Blocking Filter

Remove DC offset from signal:

```
@init
dc_x1 = dc_y1 = 0;

@slider
// Cutoff around 10-20 Hz
R = 1 - ($pi * 2 * 20 / srate);

@sample
// Highpass at ~20 Hz
dc_y1 = spl0 - dc_x1 + R * dc_y1;
dc_x1 = spl0;
spl0 = dc_y1;
```

---

## Allpass Filter

Useful for phase manipulation (phasers, dispersive delays):

```
@init
z1 = z2 = 0;

@slider
omega = 2 * $pi * cutoff / srate;
sin_omega = sin(omega);
cos_omega = cos(omega);
alpha = sin_omega / (2 * q);

a0_inv = 1 / (1 + alpha);
b0 = (1 - alpha) * a0_inv;
b1 = (-2 * cos_omega) * a0_inv;
b2 = (1 + alpha) * a0_inv;
a1 = b1;
a2 = b0;

@sample
out = b0 * spl0 + z1;
z1 = b1 * spl0 - a1 * out + z2;
z2 = b2 * spl0 - a2 * out;
spl0 = out;
```

---

## Filter Modulation Smoothing

Prevent zipper noise when modulating filter parameters:

```
@init
cutoff_smooth = cutoff;
smooth_coeff = exp(-2 * $pi * 50 / srate);  // 50 Hz smoothing

@slider
cutoff_target = cutoff;

@sample
// Smooth cutoff changes
cutoff_smooth = smooth_coeff * cutoff_smooth + (1 - smooth_coeff) * cutoff_target;

// Recalculate coefficients per-sample (expensive but smooth)
omega = 2 * $pi * cutoff_smooth / srate;
// ... calculate coeffs ...
// ... process sample ...
```

### Alternative: Per-Block Smoothing

More efficient, slight stepping at block boundaries:

```
@block
// Smooth once per block
cutoff_smooth += (cutoff_target - cutoff_smooth) * 0.1;

omega = 2 * $pi * cutoff_smooth / srate;
// ... calculate coefficients ...

@sample
// Just apply filter, coeffs already calculated
```

---

## Filter Library Pattern

Reusable filter as include file:

```
// biquad.jsfx-inc

function biquad.init()
  instance(z1, z2)
(
  z1 = z2 = 0;
);

function biquad.set_lp(freq, q)
  instance(b0, b1, b2, a1, a2)
  local(omega, sin_omega, cos_omega, alpha, a0_inv)
(
  omega = 2 * $pi * freq / srate;
  sin_omega = sin(omega);
  cos_omega = cos(omega);
  alpha = sin_omega / (2 * q);

  a0_inv = 1 / (1 + alpha);
  b0 = ((1 - cos_omega) / 2) * a0_inv;
  b1 = (1 - cos_omega) * a0_inv;
  b2 = b0;
  a1 = (-2 * cos_omega) * a0_inv;
  a2 = (1 - alpha) * a0_inv;
);

function biquad.process(input)
  instance(b0, b1, b2, a1, a2, z1, z2)
  local(output)
(
  output = b0 * input + z1;
  z1 = b1 * input - a1 * output + z2;
  z2 = b2 * input - a2 * output;
  output;
);

// Usage:
// filter_l.biquad.init();
// filter_l.biquad.set_lp(1000, 0.707);
// spl0 = filter_l.biquad.process(spl0);
```
