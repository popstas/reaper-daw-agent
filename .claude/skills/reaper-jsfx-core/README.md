# REAPER JSFX Core

Foundation skill for writing JSFX audio plugins in REAPER. This skill covers the EEL2 language, code structure, and performance optimization patterns essential for any JSFX plugin.

## Installation

```bash
npx skills add mthines/jsfx-agent-skills
```

## When to Use

Use this skill when:
- Writing any JSFX plugin for REAPER
- Learning EEL2 syntax and patterns
- Optimizing plugin performance
- Creating reusable code libraries

**This skill is required for all other JSFX skills** (audio, synth, midi, ui).

## Rules

| Rule | Impact | Description |
|------|--------|-------------|
| [language](./rules/language.md) | CRITICAL | EEL2 syntax, operators, math functions, loops, strings, user-defined functions |
| [sections](./rules/sections.md) | CRITICAL | Code sections (@init, @slider, @block, @sample, @gfx, @serialize) and execution flow |
| [variables](./rules/variables.md) | CRITICAL | Special variables, slider definitions, transport state, PDC, shared memory |
| [performance](./rules/performance.md) | CRITICAL | CPU optimization, denormal handling, branchless patterns, memory efficiency |
| [libraries](./rules/libraries.md) | HIGH | Creating and using .jsfx-inc include files, namespacing, code organization |

## Quick Start

Minimal JSFX plugin:

```
desc:My Effect
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

## Resources

- [Official JSFX Documentation](https://www.reaper.fm/sdk/js/js.php)
- [EEL2 Language Reference](https://www.cockos.com/EEL2/)
- [Tale's JSFX Libraries](https://www.taletn.com/reaper/mono_synth/)
- [Geraint's JSFX Collection](https://geraintluff.github.io/jsfx/)

## Related Skills

- **reaper-jsfx-audio** - Audio effect patterns (filters, dynamics, delays, reverbs)
- **reaper-jsfx-synth** - Synthesis and instrument patterns
- **reaper-jsfx-midi** - MIDI processing patterns
- **reaper-jsfx-ui** - Graphics and UI patterns

## License

MIT
