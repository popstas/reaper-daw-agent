---
title: "Libraries & Code Organization"
impact: HIGH
tags:
  - libraries
  - includes
  - namespacing
  - organization
  - jsfx-inc
---

# Libraries & Code Organization

JSFX supports reusable code libraries via `.jsfx-inc` files. This enables modular design, code sharing, and maintainable plugins.

## Official Documentation

- [JSFX Programming Reference](https://www.reaper.fm/sdk/js/js.php) (import section)
- [JSFX User Functions](https://www.reaper.fm/sdk/js/userfunc.php)

---

## Include Files (.jsfx-inc)

### Basic Usage

```
// In your .jsfx file:
import my_library.jsfx-inc

// Or with path:
import lib/filters.jsfx-inc
import ../shared/utils.jsfx-inc
```

### Search Paths

JSFX looks for imported files in:
1. Same directory as the importing .jsfx file
2. REAPER's `Effects/` folder
3. `Data/` subfolder

---

## Creating a Library

### Basic Library Structure

**filters.jsfx-inc:**
```
@init

// Library initialization (optional)
// Runs when the importing plugin's @init runs

// ============================================
// ONE-POLE LOWPASS FILTER
// ============================================

function onepole_lp.set_freq(freq)
  instance(coeff)
(
  coeff = 1 - exp(-2 * $pi * freq / srate);
);

function onepole_lp.process(input)
  instance(state, coeff)
(
  state += coeff * (input - state);
  state;
);

function onepole_lp.reset()
  instance(state)
(
  state = 0;
);
```

**Using the library:**
```
desc:Filtered Output
import filters.jsfx-inc

slider1:cutoff=1000<20,20000,1:log>Cutoff (Hz)

@init
filter_l.onepole_lp.reset();
filter_r.onepole_lp.reset();

@slider
filter_l.onepole_lp.set_freq(cutoff);
filter_r.onepole_lp.set_freq(cutoff);

@sample
spl0 = filter_l.onepole_lp.process(spl0);
spl1 = filter_r.onepole_lp.process(spl1);
```

---

## Namespacing Patterns

### Instance-Based (Recommended)

The `instance()` declaration creates namespace-scoped variables:

```
function filter.init(freq, q)
  instance(b0, b1, b2, a1, a2, z1, z2)
  local(omega, alpha, cos_omega, a0_inv)
(
  omega = 2 * $pi * freq / srate;
  cos_omega = cos(omega);
  alpha = sin(omega) / (2 * q);

  a0_inv = 1 / (1 + alpha);
  b0 = ((1 - cos_omega) / 2) * a0_inv;
  b1 = (1 - cos_omega) * a0_inv;
  b2 = b0;
  a1 = (-2 * cos_omega) * a0_inv;
  a2 = (1 - alpha) * a0_inv;

  z1 = z2 = 0;
);

function filter.process(input)
  instance(b0, b1, b2, a1, a2, z1, z2)
  local(output, in_z1, in_z2)
(
  output = b0 * input + z1;
  z1 = b1 * input - a1 * output + z2;
  z2 = b2 * input - a2 * output;
  output;
);

// Usage creates separate state for each instance:
lp_left.filter.init(1000, 0.707);
lp_right.filter.init(1000, 0.707);
hp_left.filter.init(200, 0.707);

// Each has its own z1, z2, coefficients, etc.
// lp_left.z1, lp_right.z1, hp_left.z1 are all separate
```

### The `this.` Prefix

Access instance variables with `this.`:

```
function osc.set_freq(freq)
  instance(dt)
(
  dt = freq / srate;
);

function osc.process()
  instance(t, dt)
(
  t += dt;
  t >= 1 ? t -= 1;
  sin(2 * $pi * t);
);

function osc.sync_to(other_osc)
(
  // Access another instance's variables with this.
  this.t = other_osc.t;
);
```

### The `this..` Prefix (Parent Scope)

Navigate up the namespace:

```
function voice.osc.process()
  instance(t, dt)
(
  t += dt;
  t >= 1 ? t -= 1;

  // Access parent (voice) scope
  this..velocity;  // voice.velocity
  this..note;      // voice.note

  sin(2 * $pi * t) * this..velocity;
);
```

---

## Library Design Patterns

### 1. Stateless Utility Functions

For pure calculations, no namespace needed:

```
// utils.jsfx-inc

function db_to_lin(db)
(
  10^(db / 20);
);

function lin_to_db(lin)
(
  lin > 0 ? 20 * log10(lin) : -144;
);

function ms_to_samples(ms)
(
  ms * srate / 1000;
);

function samples_to_ms(samples)
(
  samples * 1000 / srate;
);

function hz_to_midi(hz)
(
  69 + 12 * log(hz / 440) / log(2);
);

function midi_to_hz(note)
(
  440 * pow(2, (note - 69) / 12);
);

function lerp(a, b, t)
(
  a + t * (b - a);
);

function clamp(val, min_val, max_val)
(
  max(min_val, min(max_val, val));
);
```

### 2. Stateful Processor Classes

For DSP that maintains state:

```
// envelope.jsfx-inc

function env.adsr.init(attack_ms, decay_ms, sustain, release_ms)
  instance(attack_coeff, decay_coeff, sustain_level, release_coeff)
  instance(state, stage, output)
(
  attack_coeff = exp(-1 / (attack_ms * srate / 1000));
  decay_coeff = exp(-1 / (decay_ms * srate / 1000));
  sustain_level = sustain;
  release_coeff = exp(-1 / (release_ms * srate / 1000));
  state = 0;
  stage = 0;  // 0=idle, 1=attack, 2=decay, 3=sustain, 4=release
  output = 0;
);

function env.adsr.trigger()
  instance(stage, state)
(
  stage = 1;  // Attack
);

function env.adsr.release()
  instance(stage)
(
  stage = 4;  // Release
);

function env.adsr.process()
  instance(attack_coeff, decay_coeff, sustain_level, release_coeff)
  instance(state, stage, output)
(
  stage == 1 ? (  // Attack
    state = attack_coeff * state + (1 - attack_coeff);
    state >= 0.999 ? (
      state = 1;
      stage = 2;  // Decay
    );
    output = state;
  ) : stage == 2 ? (  // Decay
    state = decay_coeff * state + (1 - decay_coeff) * sustain_level;
    state <= sustain_level * 1.001 ? (
      stage = 3;  // Sustain
    );
    output = state;
  ) : stage == 3 ? (  // Sustain
    output = sustain_level;
  ) : stage == 4 ? (  // Release
    state = release_coeff * state;
    state < 0.0001 ? (
      state = 0;
      stage = 0;  // Idle
    );
    output = state;
  ) : (  // Idle
    output = 0;
  );

  output;
);
```

### 3. Factory Pattern with Memory Allocation

For libraries that need memory buffers:

```
// delay.jsfx-inc

function delay.create(mem_offset, max_samples)
  instance(buffer, size, write_pos)
(
  buffer = mem_offset;
  size = max_samples;
  write_pos = 0;

  // Clear buffer
  memset(buffer, 0, size);

  // Return next available memory offset
  buffer + size;
);

function delay.write(input)
  instance(buffer, size, write_pos)
(
  buffer[write_pos] = input;
  write_pos += 1;
  write_pos >= size ? write_pos = 0;
);

function delay.read(delay_samples)
  instance(buffer, size, write_pos)
  local(read_pos)
(
  read_pos = write_pos - delay_samples;
  read_pos < 0 ? read_pos += size;
  buffer[read_pos];
);

function delay.read_interp(delay_samples)
  instance(buffer, size, write_pos)
  local(read_pos, frac, idx0, idx1)
(
  read_pos = write_pos - delay_samples;
  read_pos < 0 ? read_pos += size;

  idx0 = floor(read_pos);
  frac = read_pos - idx0;
  idx1 = idx0 + 1;
  idx1 >= size ? idx1 = 0;

  buffer[idx0] * (1 - frac) + buffer[idx1] * frac;
);

// Usage:
@init
mem_ptr = 0;
mem_ptr = delay_l.delay.create(mem_ptr, srate * 2);  // 2 sec max
mem_ptr = delay_r.delay.create(mem_ptr, srate * 2);
freembuf(mem_ptr);

@sample
delay_l.delay.write(spl0);
delay_r.delay.write(spl1);
spl0 += delay_l.delay.read(delay_samples) * feedback;
spl1 += delay_r.delay.read(delay_samples) * feedback;
```

---

## Community Libraries

### Tale's JSFX Libraries

Comprehensive, well-documented libraries: [taletn.com](https://www.taletn.com/reaper/mono_synth/)

- `rbj_filter.jsfx-inc` - Biquad filters (RBJ cookbook)
- `zdf_filter.jsfx-inc` - Zero-delay feedback filters
- `poly_blep.jsfx-inc` - Anti-aliased oscillators
- `adsr.jsfx-inc` - ADSR envelope
- `midi_queue.jsfx-inc` - Sample-accurate MIDI
- `malloc.jsfx-inc` - Memory allocation
- `array.jsfx-inc` - 2D arrays

### Geraint's UI Library

Custom UI components: [jsfx-ui-lib](https://geraintluff.github.io/jsfx-ui-lib/)

---

## Best Practices

### 1. Document Your Library

```
// filters.jsfx-inc
// =================
// Audio filter library for JSFX
//
// Provides:
//   - onepole_lp: One-pole lowpass filter
//   - biquad: General biquad filter with multiple modes
//   - svf: State variable filter
//
// Usage:
//   import filters.jsfx-inc
//
//   @init
//   myfilter.biquad.init(1000, 0.707, "lp");
//
//   @sample
//   spl0 = myfilter.biquad.process(spl0);
//
// Author: Your Name
// License: MIT
// =================
```

### 2. Consistent Naming Convention

```
// Functions: lowercase with dots for namespacing
function filter.set_freq(freq)
function osc.poly_saw()

// Instance variables: lowercase with underscores
instance(sample_rate, filter_coeff, z1_state)

// Constants: UPPER_CASE
TWO_PI = 2 * $pi;
MAX_VOICES = 16;
```

### 3. Provide Reset Functions

```
function filter.reset()
  instance(z1, z2, z1_out, z2_out)
(
  z1 = z2 = z1_out = z2_out = 0;
);
```

### 4. Handle Sample Rate Changes

```
@init
// Libraries should recalculate on srate change
filter_l.biquad.init(cutoff, resonance);
filter_r.biquad.init(cutoff, resonance);
```

### 5. Return Memory Offset for Chaining

```
function mybuffer.create(offset, size)
  instance(buf, len)
(
  buf = offset;
  len = size;
  offset + size;  // Return next available offset
);

// Allows chaining:
@init
ptr = 0;
ptr = buf1.mybuffer.create(ptr, 1024);
ptr = buf2.mybuffer.create(ptr, 2048);
ptr = buf3.mybuffer.create(ptr, 512);
freembuf(ptr);
```

---

## Library File Structure

Organize larger projects:

```
MyPlugin/
├── MyPlugin.jsfx           # Main plugin
├── lib/
│   ├── filters.jsfx-inc    # Filter algorithms
│   ├── delay.jsfx-inc      # Delay lines
│   ├── envelope.jsfx-inc   # Envelope generators
│   ├── utils.jsfx-inc      # Utility functions
│   └── ui.jsfx-inc         # UI components
└── README.txt              # Documentation
```

```
// In MyPlugin.jsfx:
import lib/filters.jsfx-inc
import lib/delay.jsfx-inc
import lib/envelope.jsfx-inc
import lib/utils.jsfx-inc
import lib/ui.jsfx-inc
```

---

## Testing Libraries

Create test plugins for your libraries:

```
desc:Filter Library Test
import lib/filters.jsfx-inc

slider1:freq=1000<20,20000,1:log>Frequency
slider2:q=0.707<0.1,10,0.01>Q
slider3:mode=0<0,3,1{LP,HP,BP,Notch}>Mode

@init
test_filter_l.biquad.init(freq, q, mode);
test_filter_r.biquad.init(freq, q, mode);

@slider
test_filter_l.biquad.set_params(freq, q, mode);
test_filter_r.biquad.set_params(freq, q, mode);

@sample
spl0 = test_filter_l.biquad.process(spl0);
spl1 = test_filter_r.biquad.process(spl1);

@gfx 400 200
gfx_x = gfx_y = 10;
gfx_drawstr("Filter Test - Frequency Response");
// ... draw frequency response
```
