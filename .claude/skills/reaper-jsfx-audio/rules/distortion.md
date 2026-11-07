---
title: "Distortion & Saturation"
impact: MEDIUM
tags:
  - distortion
  - saturation
  - waveshaping
  - clipping
  - overdrive
---

# Distortion & Saturation

Waveshaping, clipping, saturation, and overdrive implementations with aliasing mitigation.

## References

- [Waveshaping Synthesis](https://ccrma.stanford.edu/~jos/pasp/Waveshaping.html)
- [Virtual Analog Modeling](https://www.native-instruments.com/fileadmin/ni_media/downloads/pdf/VAFilterDesign_2.1.0.pdf)

---

## Basic Waveshaping

### Hard Clipping

```
@sample
// Simple hard clip to [-1, 1]
spl0 = max(-1, min(1, spl0 * drive));
spl1 = max(-1, min(1, spl1 * drive));

// Or with threshold parameter
spl0 = max(-threshold, min(threshold, spl0 * drive)) / threshold;
```

### Soft Clipping (Tanh)

```
@slider
drive_lin = 10^(drive_db / 20);

@sample
// Tanh soft clip - natural saturation character
spl0 = tanh(spl0 * drive_lin);
spl1 = tanh(spl1 * drive_lin);

// Note: EEL2 doesn't have tanh(), use approximation or exp():
// tanh(x) = (exp(2x) - 1) / (exp(2x) + 1)
function tanh(x)
(
  x = exp(2 * x);
  (x - 1) / (x + 1);
);
```

### Polynomial Soft Clip

```
@sample
// Cubic soft clipper
x = spl0 * drive;
abs(x) < 1 ? (
  spl0 = x - x*x*x/3;
) : (
  spl0 = sign(x) * 2/3;
);
```

### Sine Waveshaper

```
@sample
// Sine fold - creates harmonics
x = spl0 * drive;
spl0 = sin(x * $pi / 2);
```

### Asymmetric Clipping

For tube-like even harmonics:

```
@slider
// Asymmetry: 0 = symmetric, 1 = full asymmetry
asymmetry = asym_slider;
pos_gain = 1 + asymmetry * 0.5;
neg_gain = 1 - asymmetry * 0.5;

@sample
x = spl0 * drive;
x > 0 ? (
  spl0 = tanh(x * pos_gain);
) : (
  spl0 = tanh(x * neg_gain);
);
```

---

## Tube Emulation

### Simple Tube Stage

```
@init
// DC offset for asymmetry
dc_offset = 0.1;

@sample
// Add bias
x = spl0 * drive + dc_offset;

// Asymmetric soft clip
x > 0 ? (
  x = 1 - exp(-x);
) : (
  x = -1 + exp(x);
);

// Remove DC
spl0 = x - dc_offset * 0.5;
```

### Triode Model

```
function triode(x, mu, bias)
  local(grid_voltage, plate_current)
(
  // Simplified triode model
  grid_voltage = x - bias;
  grid_voltage > 0 ? (
    // Conducting
    plate_current = pow(grid_voltage, 1.5) / mu;
  ) : (
    // Cutoff
    plate_current = 0;
  );
  plate_current;
);

@sample
// Push-pull stage
positive = triode(spl0 * drive, 100, 0.5);
negative = triode(-spl0 * drive, 100, 0.5);
spl0 = (positive - negative) * output_level;
```

---

## Aliasing Mitigation

Nonlinear processing creates harmonics that can alias. Use oversampling to reduce.

### 2x Oversampling

```
@init
last_input_l = 0;
last_input_r = 0;
last_output_l = 0;
last_output_r = 0;

@sample
// Upsample (linear interpolation)
in_0_l = spl0;
in_0_r = spl1;
in_1_l = (spl0 + last_input_l) * 0.5;
in_1_r = (spl1 + last_input_r) * 0.5;

// Process both samples
out_0_l = saturate(in_0_l * drive);
out_0_r = saturate(in_0_r * drive);
out_1_l = saturate(in_1_l * drive);
out_1_r = saturate(in_1_r * drive);

// Downsample (average)
spl0 = (out_0_l + out_1_l) * 0.5;
spl1 = (out_0_r + out_1_r) * 0.5;

last_input_l = in_0_l;
last_input_r = in_0_r;
```

### 4x Oversampling with Filtering

```
@init
// Polyphase FIR coefficients for 4x
// ... setup filter coefficients ...

@sample
// Upsample to 4x
// ... polyphase upsampler ...

// Process at 4x rate
loop(4,
  oversampled[i] = saturate(upsampled[i] * drive);
  i += 1;
);

// Downsample with anti-aliasing filter
// ... polyphase downsampler ...
```

---

## Bitcrusher

### Sample Rate Reduction

```
@slider
reduction = floor(slider1);  // 1 = no reduction, 2 = half rate, etc.

@init
held_l = held_r = 0;
counter = 0;

@sample
counter += 1;
counter >= reduction ? (
  held_l = spl0;
  held_r = spl1;
  counter = 0;
);

spl0 = held_l;
spl1 = held_r;
```

### Bit Depth Reduction

```
@slider
bits = floor(slider1);  // 1-16 bits
levels = pow(2, bits);
step = 2 / levels;

@sample
// Quantize to N bits
spl0 = floor(spl0 / step + 0.5) * step;
spl1 = floor(spl1 / step + 0.5) * step;
```

### Combined Bitcrusher

```
desc:Bitcrusher
slider1:bits=8<1,16,1>Bit Depth
slider2:downsample=1<1,32,1>Downsample Factor
slider3:mix=100<0,100,1>Mix (%)

@init
held_l = held_r = 0;
counter = 0;

@slider
levels = pow(2, bits);
step = 2 / levels;
wet = mix / 100;
dry = 1 - wet;

@sample
// Store dry
dry_l = spl0;
dry_r = spl1;

// Sample rate reduction
counter += 1;
counter >= downsample ? (
  held_l = spl0;
  held_r = spl1;
  counter = 0;
);

// Bit depth reduction
crushed_l = floor(held_l / step + 0.5) * step;
crushed_r = floor(held_r / step + 0.5) * step;

// Mix
spl0 = dry_l * dry + crushed_l * wet;
spl1 = dry_r * dry + crushed_r * wet;
```

---

## Fuzz / Distortion Pedal

```
desc:Fuzz Pedal
slider1:gain=50<0,100,1>Gain
slider2:tone=50<0,100,1>Tone
slider3:level=50<0,100,1>Level

@init
// Tone control filter states
tone_z1_l = tone_z1_r = 0;

@slider
drive = pow(10, gain / 25) - 1;  // Exponential drive
output_level = level / 100;

// Tone control (simple tilt EQ)
tone_freq = 200 + tone * 40;  // 200-4200 Hz
tone_coeff = 1 - exp(-2 * $pi * tone_freq / srate);

@sample
// Input stage gain
x_l = spl0 * drive;
x_r = spl1 * drive;

// Asymmetric clipping (fuzz character)
x_l > 0 ? (
  x_l = 1 - exp(-x_l * 2);
) : (
  x_l = -(1 - exp(x_l));
);

x_r > 0 ? (
  x_r = 1 - exp(-x_r * 2);
) : (
  x_r = -(1 - exp(x_r));
);

// Tone control (lowpass)
tone_z1_l += tone_coeff * (x_l - tone_z1_l);
tone_z1_r += tone_coeff * (x_r - tone_z1_r);

// Mix filtered and direct for tone control
tone_mix = tone / 100;
x_l = x_l * (1 - tone_mix) + tone_z1_l * tone_mix;
x_r = x_r * (1 - tone_mix) + tone_z1_r * tone_mix;

// Output level
spl0 = x_l * output_level;
spl1 = x_r * output_level;
```

---

## Tape Saturation

```
desc:Tape Saturation
slider1:drive_db=0<0,24,0.1>Drive (dB)
slider2:bias=0.5<0,1,0.01>Bias
slider3:hf_rolloff=0.7<0,1,0.01>HF Rolloff

@init
lp_z1_l = lp_z1_r = 0;
hp_z1_l = hp_z1_r = 0;
last_l = last_r = 0;

@slider
drive = 10^(drive_db / 20);

// HF rolloff filter
lp_coeff = 1 - hf_rolloff * 0.5;

@sample
// Input with drive
x_l = spl0 * drive;
x_r = spl1 * drive;

// Tape-style soft saturation with hysteresis
x_l = tanh(x_l + last_l * bias * 0.1);
x_r = tanh(x_r + last_r * bias * 0.1);

// HF rolloff (tape head loss)
lp_z1_l = lp_z1_l + lp_coeff * (x_l - lp_z1_l);
lp_z1_r = lp_z1_r + lp_coeff * (x_r - lp_z1_r);

// Slight HF boost before rolloff (tape pre-emphasis)
x_l = x_l * 0.3 + lp_z1_l * 0.7;
x_r = x_r * 0.3 + lp_z1_r * 0.7;

last_l = x_l;
last_r = x_r;

spl0 = x_l;
spl1 = x_r;
```

---

## Wavefolder

```
@slider
folds = floor(slider1);  // Number of folds
gain = slider2;

@sample
x = spl0 * gain;

// Fold back and forth
i = 0;
loop(folds,
  x = abs(x);
  x > 1 ? x = 2 - x;
  x < -1 ? x = -2 - x;
  i += 1;
);

spl0 = x;
```

---

## Complete Saturation Plugin

```
desc:Multi-Mode Saturator
slider1:drive_db=0<0,36,0.1>Drive (dB)
slider2:mode=0<0,4,1{Soft,Hard,Tube,Tape,Fuzz}>Mode
slider3:mix=100<0,100,1>Mix (%)
slider4:output_db=0<-24,6,0.1>Output (dB)

@init
z1_l = z1_r = 0;

@slider
drive = 10^(drive_db / 20);
output = 10^(output_db / 20);
wet = mix / 100;
dry = 1 - wet;

@sample
dry_l = spl0;
dry_r = spl1;

x_l = spl0 * drive;
x_r = spl1 * drive;

mode == 0 ? (  // Soft (tanh)
  x_l = tanh(x_l);
  x_r = tanh(x_r);
) : mode == 1 ? (  // Hard
  x_l = max(-1, min(1, x_l));
  x_r = max(-1, min(1, x_r));
) : mode == 2 ? (  // Tube
  x_l = x_l > 0 ? 1 - exp(-x_l) : -1 + exp(x_l);
  x_r = x_r > 0 ? 1 - exp(-x_r) : -1 + exp(x_r);
) : mode == 3 ? (  // Tape
  x_l = tanh(x_l * 0.8) * 1.1;
  x_r = tanh(x_r * 0.8) * 1.1;
  // Add slight filtering
  z1_l += 0.1 * (x_l - z1_l);
  z1_r += 0.1 * (x_r - z1_r);
  x_l = z1_l;
  x_r = z1_r;
) : (  // Fuzz
  x_l = sign(x_l) * (1 - exp(-abs(x_l) * 3));
  x_r = sign(x_r) * (1 - exp(-abs(x_r) * 3));
);

// Mix and output
spl0 = (dry_l * dry + x_l * wet) * output;
spl1 = (dry_r * dry + x_r * wet) * output;
```
