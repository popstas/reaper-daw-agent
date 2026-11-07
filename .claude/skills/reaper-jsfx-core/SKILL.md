---
name: 'reaper-jsfx-core'
description: 'Foundation for REAPER JSFX plugin development. Use when writing any JSFX plugin - covers EEL2 language syntax, code sections, special variables, performance optimization, and reusable library patterns. Triggers on requests for JSFX, JS effects, EEL2, or Reaper plugin development.'
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
    - eel2
    - audio
    - dsp
    - plugin
---

# REAPER JSFX Core

Foundation skill for writing JSFX audio plugins in REAPER. This skill covers the EEL2 language, code structure, and performance optimization patterns essential for any JSFX plugin.

**Always load this skill when working with JSFX.** Other JSFX skills (audio, synth, midi, ui) build upon this foundation.

## Rules

| Rule | Description |
|------|-------------|
| [language](./rules/language.md) | EEL2 syntax, operators, math functions, loops, strings, user-defined functions |
| [sections](./rules/sections.md) | Code sections (@init, @slider, @block, @sample, @gfx, @serialize) and execution flow |
| [variables](./rules/variables.md) | Special variables, slider definitions, transport state, PDC, shared memory |
| [performance](./rules/performance.md) | CPU optimization, denormal handling, branchless patterns, memory efficiency |
| [libraries](./rules/libraries.md) | Creating and using .jsfx-inc include files, namespacing, code organization |

## Official Documentation

- [JSFX Programming Reference](https://www.reaper.fm/sdk/js/js.php)
- [EEL2 Language Reference](https://www.cockos.com/EEL2/)
- [JSFX Basic Code Reference](https://www.reaper.fm/sdk/js/basiccode.php)
- [JSFX Special Variables](https://www.reaper.fm/sdk/js/vars.php)

## Key Principles

### 1. Performance First

JSFX runs in real-time audio context. The `@sample` section executes thousands of times per second (e.g., 44,100 times/sec at 44.1kHz). Every operation matters:

```
// BAD: Branch in sample loop
@sample
condition ? (
  spl0 *= gain1;
) : (
  spl0 *= gain2;
);

// GOOD: Branchless - compute gain once in @slider
@slider
gain = condition ? gain1 : gain2;

@sample
spl0 *= gain;
```

### 2. Precompute in Appropriate Sections

Move calculations to the earliest possible section:

| Section | Runs | Use For |
|---------|------|---------|
| `@init` | Once on load/reset | Memory allocation, lookup tables, constants |
| `@slider` | On parameter change | Coefficient calculation, derived values |
| `@block` | Per audio block (~1-10ms) | Tempo sync, MIDI preprocessing |
| `@sample` | Per sample (44100+/sec) | Only essential sample processing |

### 3. Variables Are Global by Default

EEL2 variables don't need declaration and are global. Use meaningful names and conventions:

```
// Slider-derived values: prefix with slider name
slider1:volume_db=0<-60,12,0.1>Volume (dB)
@slider
volume_db_lin = 10^(volume_db/20);  // Linear gain from dB

// State variables: descriptive names
filter_z1 = 0;  // Filter state (z^-1)
env_current = 0;  // Envelope current value

// Constants: UPPER_CASE or prefix
TWO_PI = 2 * $pi;
MAX_DELAY_SAMPLES = 192000;
```

### 4. Use Memory for Buffers, Variables for State

```
@init
// Buffers in memory (addressable array)
delay_buffer = 0;  // Start at memory offset 0
delay_length = 48000;
freembuf(delay_buffer + delay_length);  // Inform memory manager

// State in named variables (faster access)
delay_write_pos = 0;
delay_read_pos = 0;

@sample
// Memory access for buffer
delay_buffer[delay_write_pos] = spl0;

// Variable access for state
delay_write_pos += 1;
delay_write_pos >= delay_length ? delay_write_pos = 0;
```

## Quick Reference

| Task | Rule |
|------|------|
| Understanding EEL2 syntax | [language](./rules/language.md) |
| Structuring plugin code | [sections](./rules/sections.md) |
| Using sliders and special vars | [variables](./rules/variables.md) |
| Optimizing CPU performance | [performance](./rules/performance.md) |
| Creating reusable code | [libraries](./rules/libraries.md) |

## Minimal Plugin Template

```
desc:My Effect
tags:effect utility

slider1:gain_db=0<-24,24,0.1>Gain (dB)

in_pin:left input
in_pin:right input
out_pin:left output
out_pin:right output

@init
// Initialize state here

@slider
// Recalculate coefficients when sliders change
gain_lin = 10^(gain_db/20);

@sample
// Process audio
spl0 *= gain_lin;
spl1 *= gain_lin;
```
