---
name: 'reaper-jsfx-audio'
description: 'Audio effects patterns for JSFX plugins. Use when implementing filters, EQs, compressors, limiters, delays, reverbs, distortion, or modulation effects. Triggers on requests for audio effect DSP, equalizer, dynamics processing, or time-based effects in JSFX.'
disable-model-invocation: true
license: MIT
metadata:
  author: mthines
  author_name: Mads Thines Coello
  author_email: madsthines@gmail.com
  version: '1.0.0'
  workflow_type: 'implementation'
  tags:
    - jsfx
    - reaper
    - audio
    - dsp
    - effects
    - filter
    - dynamics
    - delay
    - reverb
---

# REAPER JSFX Audio Effects

DSP algorithms and patterns for audio effects in JSFX. Covers filters, dynamics processors, delays, reverbs, and modulation effects.

**Requires:** [reaper-jsfx-core](../reaper-jsfx-core/SKILL.md) for language fundamentals.

## Rules

| Rule | Description |
|------|-------------|
| [filters](./rules/filters.md) | Biquad, SVF, ZDF, one-pole filters with coefficient calculation |
| [dynamics](./rules/dynamics.md) | Compressor, limiter, gate, expander, envelope detection |
| [delays](./rules/delays.md) | Delay lines, circular buffers, chorus, flanger, comb filters |
| [reverb](./rules/reverb.md) | Algorithmic reverb, allpass networks, FDN, early reflections |
| [distortion](./rules/distortion.md) | Waveshaping, soft/hard clipping, saturation, tube emulation |
| [modulation](./rules/modulation.md) | LFO patterns, tremolo, vibrato, phaser, ring modulation |

## Official Documentation

- [JSFX Programming Reference](https://www.reaper.fm/sdk/js/js.php)
- [JSFX Memory/FFT Functions](https://www.reaper.fm/sdk/js/advfunc.php)

## External References

- [Audio EQ Cookbook](https://webaudio.github.io/Audio-EQ-Cookbook/audio-eq-cookbook.html) - Biquad filter coefficients
- [Tale's JSFX Libraries](https://www.taletn.com/reaper/mono_synth/) - Reference implementations
- [musicdsp.org](https://www.musicdsp.org/) - DSP algorithms and code

## Key Principles

### 1. Coefficient Calculation in @slider

Always calculate filter coefficients when parameters change, not per-sample:

```
@slider
omega = 2 * $pi * cutoff / srate;
sin_omega = sin(omega);
cos_omega = cos(omega);
alpha = sin_omega / (2 * q);

// Lowpass coefficients (RBJ cookbook)
a0 = 1 + alpha;
b0 = ((1 - cos_omega) / 2) / a0;
b1 = (1 - cos_omega) / a0;
b2 = b0;
a1 = (-2 * cos_omega) / a0;
a2 = (1 - alpha) / a0;

@sample
// Only apply coefficients here
out = b0*in + b1*z1 + b2*z2 - a1*z1_out - a2*z2_out;
```

### 2. State Variable Preservation

Filter and delay states must persist between samples:

```
@init
// Initialize filter states to zero
z1 = z2 = 0;
z1_out = z2_out = 0;

@sample
// Update states after processing
z2 = z1;
z1 = input;
z2_out = z1_out;
z1_out = output;
```

### 3. Gain Staging

Maintain proper gain throughout the signal chain:

```
@init
// Keep track of gain changes
input_gain = 1;
output_gain = 1;

@slider
// Convert dB to linear
input_gain = 10^(input_db / 20);
output_gain = 10^(output_db / 20);

@sample
// Apply input gain
sample = spl0 * input_gain;

// Process
processed = do_something(sample);

// Apply output gain and makeup
spl0 = processed * output_gain;
```

### 4. Oversampling for Nonlinear Processing

Distortion and saturation benefit from oversampling to reduce aliasing:

```
@init
oversample = 2;  // 2x oversampling

@sample
// Upsample (simple interpolation)
s1 = spl0;
s2 = (spl0 + last_input) * 0.5;
last_input = spl0;

// Process at higher rate
s1 = saturate(s1);
s2 = saturate(s2);

// Downsample (simple averaging)
spl0 = (s1 + s2) * 0.5;
```

## Quick Reference

| Use Case | Rule |
|----------|------|
| EQ / Filter | [filters](./rules/filters.md) |
| Compressor / Limiter | [dynamics](./rules/dynamics.md) |
| Delay / Echo | [delays](./rules/delays.md) |
| Reverb | [reverb](./rules/reverb.md) |
| Distortion / Saturation | [distortion](./rules/distortion.md) |
| Chorus / Flanger / Phaser | [modulation](./rules/modulation.md) |

## Common Effect Patterns

### Stereo Processing

```
@sample
// Process left and right identically
spl0 = process(spl0);
spl1 = process(spl1);

// Or use mid-side
mid = (spl0 + spl1) * 0.5;
side = (spl0 - spl1) * 0.5;
mid = process_mid(mid);
side = process_side(side);
spl0 = mid + side;
spl1 = mid - side;
```

### Dry/Wet Mix

```
@slider
dry = 1 - wet_amount;
wet = wet_amount;

@sample
dry_signal = spl0;
wet_signal = process(spl0);
spl0 = dry_signal * dry + wet_signal * wet;
```

### Bypass with Smoothing

```
@slider
bypass_target = bypass ? 0 : 1;

@sample
// Smooth bypass transition
bypass_smooth += 0.001 * (bypass_target - bypass_smooth);

dry_signal = spl0;
wet_signal = process(spl0);
spl0 = dry_signal * (1 - bypass_smooth) + wet_signal * bypass_smooth;
```
