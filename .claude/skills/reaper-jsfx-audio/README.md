# REAPER JSFX Audio Effects

DSP algorithms and patterns for audio effects in JSFX. Covers filters, dynamics processors, delays, reverbs, distortion, and modulation effects.

## Installation

```bash
npx skills add mthines/jsfx-agent-skills
```

## Prerequisites

Requires [reaper-jsfx-core](../reaper-jsfx-core/README.md) for language fundamentals.

## When to Use

Use this skill when building:
- Equalizers and filters
- Compressors, limiters, gates
- Delay and echo effects
- Reverb algorithms
- Distortion and saturation
- Chorus, flanger, phaser

## Rules

| Rule | Impact | Description |
|------|--------|-------------|
| [filters](./rules/filters.md) | CRITICAL | Biquad, SVF, ZDF, one-pole filters with coefficient calculation |
| [dynamics](./rules/dynamics.md) | HIGH | Compressor, limiter, gate, expander, envelope detection |
| [delays](./rules/delays.md) | HIGH | Delay lines, circular buffers, chorus, flanger, comb filters |
| [reverb](./rules/reverb.md) | HIGH | Algorithmic reverb, allpass networks, FDN, early reflections |
| [distortion](./rules/distortion.md) | MEDIUM | Waveshaping, soft/hard clipping, saturation, tube emulation |
| [modulation](./rules/modulation.md) | MEDIUM | LFO patterns, tremolo, vibrato, phaser, ring modulation |

## Quick Start

Simple lowpass filter:

```
desc:Simple Lowpass
slider1:cutoff=1000<20,20000,1:log>Cutoff (Hz)
slider2:q=0.707<0.1,10,0.01>Q

@init
z1_l = z2_l = z1_r = z2_r = 0;

@slider
omega = 2 * $pi * cutoff / srate;
alpha = sin(omega) / (2 * q);
a0_inv = 1 / (1 + alpha);
b0 = ((1 - cos(omega)) / 2) * a0_inv;
b1 = (1 - cos(omega)) * a0_inv;
b2 = b0;
a1 = (-2 * cos(omega)) * a0_inv;
a2 = (1 - alpha) * a0_inv;

@sample
out_l = b0 * spl0 + z1_l;
z1_l = b1 * spl0 - a1 * out_l + z2_l;
z2_l = b2 * spl0 - a2 * out_l;
spl0 = out_l;

out_r = b0 * spl1 + z1_r;
z1_r = b1 * spl1 - a1 * out_r + z2_r;
z2_r = b2 * spl1 - a2 * out_r;
spl1 = out_r;
```

## Resources

- [Audio EQ Cookbook](https://webaudio.github.io/Audio-EQ-Cookbook/audio-eq-cookbook.html)
- [Tale's JSFX Libraries](https://www.taletn.com/reaper/mono_synth/)
- [musicdsp.org](https://www.musicdsp.org/)
- [DAFX Book](https://www.dafx.de/)

## Related Skills

- **reaper-jsfx-core** - Required foundation
- **reaper-jsfx-ui** - Graphics for visualizations

## License

MIT
