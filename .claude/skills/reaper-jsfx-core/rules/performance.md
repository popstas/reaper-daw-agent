---
title: "Performance Optimization"
impact: CRITICAL
tags:
  - performance
  - optimization
  - cpu
  - denormals
  - memory
---

# Performance Optimization

JSFX runs in real-time audio context. Poor performance causes audio glitches, dropouts, and CPU spikes. This guide covers critical optimization techniques.

## Official Documentation

- [EEL2 Preprocessor](https://www.reaper.fm/sdk/js/preproc.php)
- [JSFX Special Variables](https://www.reaper.fm/sdk/js/vars.php)

---

## The Golden Rule

**The @sample section is your hot path.** At 96kHz stereo, it runs 192,000 times per second. Every operation counts.

```
// PERFORMANCE PRIORITY ORDER:
// 1. Move calculations to @init (runs once)
// 2. Move calculations to @slider (runs on parameter change)
// 3. Move calculations to @block (runs per block, ~100-1000x/sec)
// 4. Only put essential operations in @sample (runs per sample)
```

---

## Precomputation Strategies

### Move Constants to @init

```
// BAD: Recalculating constant every sample
@sample
output = input * (2 * $pi * 440 / srate);

// GOOD: Calculate once
@init
TWO_PI = 2 * $pi;
freq_coeff = TWO_PI * 440 / srate;

@sample
output = input * freq_coeff;
```

### Move Slider-Dependent Values to @slider

```
// BAD: Calculating coefficients every sample
@sample
gain = 10^(slider1 / 20);
spl0 *= gain;

// GOOD: Calculate on slider change only
@slider
gain = 10^(slider1 / 20);

@sample
spl0 *= gain;
```

### Use @block for Block-Level Operations

```
// BAD: Checking tempo every sample
@sample
beat_length = 60 / tempo * srate;

// GOOD: Calculate once per block
@block
beat_length = 60 / tempo * srate;

@sample
// Use beat_length
```

---

## Avoid Branching in @sample

Branches (conditionals) can cause CPU pipeline stalls. Minimize them in the sample loop.

### Use Multiplication Instead of Conditionals

```
// BAD: Branch per sample
@sample
bypass ? (
  // pass through
) : (
  spl0 = process(spl0);
);

// GOOD: Branchless mixing
@slider
dry_mix = bypass;
wet_mix = 1 - bypass;

@sample
processed = process(spl0);
spl0 = spl0 * dry_mix + processed * wet_mix;
```

### Branchless Min/Max

```
// Standard min/max are fine (compiler optimizes)
clamped = max(0, min(1, value));

// For custom branchless clamping:
// Clip to [-1, 1] using branchless technique
clipped = value - (value - 1) * (value > 1) - (value + 1) * (value < -1);
```

### Branchless Sign

```
// Instead of: sign = value >= 0 ? 1 : -1;
sign = 1 - 2 * (value < 0);
```

### Branchless Circular Buffer Wrap

```
// BAD: Branch for wrap-around
pos += 1;
pos >= buffer_size ? pos = 0;

// GOOD: Branchless wrap
pos += 1;
pos *= (pos < buffer_size);  // Resets to 0 when pos >= buffer_size

// ALTERNATIVE: Modulo (slower but clearer)
pos = (pos + 1) % buffer_size;
```

---

## Denormal Handling

Denormal (subnormal) numbers are tiny floating-point values that can cause massive CPU slowdowns (10-100x).

### The Problem

```
// Feedback loops can produce denormals
@sample
state = state * 0.999;  // Eventually becomes denormal
spl0 = state;           // Processing denormals is SLOW
```

### Solution 1: Anti-Denormal Noise (Default)

JSFX automatically adds tiny noise to prevent denormals. This is usually fine.

### Solution 2: Disable Auto + Handle Manually

```
@init
ext_nodenorm = 1;  // Disable automatic anti-denormal

// Define threshold (smallest normalized float is ~1.18e-38)
DENORM_THRESHOLD = 1e-30;

@sample
// Add DC offset technique
DC_OFFSET = 1e-25;
state = (input + DC_OFFSET) * feedback;
state = state - DC_OFFSET;

// OR: Flush to zero
abs(state) < DENORM_THRESHOLD ? state = 0;
```

### Solution 3: Flush-to-Zero Function

```
function flush_denorm(x)
(
  abs(x) < 1e-30 ? 0 : x;
);

@sample
state = flush_denorm(state * feedback + input);
```

### When Denormals Occur

- Feedback loops (delay, filter, envelope)
- Exponential decay (reverb tails)
- Very small multiplications

---

## Memory Access Optimization

### Variables vs Memory Arrays

```
// FASTER: Named variables
state1 = value;
output = state1 * coeff;

// SLOWER: Memory array access
states[0] = value;
output = states[0] * coeff;
```

### Minimize Memory Access Count

```
// BAD: Multiple reads of same location
@sample
output = buffer[pos] * gain + buffer[pos] * wet;

// GOOD: Single read, store in variable
@sample
sample = buffer[pos];
output = sample * gain + sample * wet;
```

### Sequential Memory Access

```
// GOOD: Sequential access (cache-friendly)
i = 0;
loop(size,
  buffer[i] = 0;
  i += 1;
);

// BAD: Random access (cache-unfriendly)
loop(size,
  buffer[rand(size)] = 0;
);
```

### Use freembuf()

```
@init
buffer = 0;
buffer_size = 48000;

// Tell memory manager we're using this range
freembuf(buffer + buffer_size);

// This helps JSFX optimize memory layout
```

---

## Function Call Overhead

Function calls have overhead. For the hottest paths, consider inlining.

### When to Inline

```
// Small, frequently-called function - consider inlining
function soft_clip(x)
(
  x = max(-1, min(1, x));  // Simple operation
  x - x*x*x/3;
);

// INLINED VERSION (faster for @sample):
@sample
x = spl0;
x = max(-1, min(1, x));
spl0 = x - x*x*x/3;
```

### When to Use Functions

```
// Complex operations - keep as function for readability
function calculate_filter_coeffs(freq, q)
  instance(b0, b1, b2, a1, a2)
  local(omega, alpha, cos_omega, a0_inv)
(
  omega = 2 * $pi * freq / srate;
  cos_omega = cos(omega);
  alpha = sin(omega) / (2 * q);
  // ... etc
);

@slider
// Called infrequently - function overhead doesn't matter
filter.calculate_filter_coeffs(cutoff, resonance);
```

---

## Loop Optimization

### Fixed Loop Count

```
// GOOD: Count known at compile time allows optimization
loop(8,
  buffer[i] = 0;
  i += 1;
);

// LESS OPTIMAL: Variable count
loop(num_ch,  // Unknown at compile time
  spl(ch) *= gain;
  ch += 1;
);
```

### Unroll Small Loops

```
// Instead of loop for stereo processing:
// loop(2, spl(ch) *= gain; ch += 1; );

// Just write it out:
spl0 *= gain;
spl1 *= gain;
```

### Loop vs Explicit Code

```
// For small, fixed iterations, explicit is often faster
// BAD for 2 channels:
ch = 0;
loop(2,
  spl(ch) *= gain;
  ch += 1;
);

// GOOD for 2 channels:
spl0 *= gain;
spl1 *= gain;
```

---

## Preprocessor for Performance

REAPER 6.74+ supports compile-time code generation:

### Generate Unrolled Loops

```
// Generates filter code for 8 bands at compile time
<?
loop(8,
  printf("b%d_out = b0_%d * in + b1_%d * z1_%d + b2_%d * z2_%d - a1_%d * z1_out_%d - a2_%d * z2_out_%d;\n",
    i, i, i, i, i, i, i, i, i, i);
  printf("z2_%d = z1_%d; z1_%d = in;\n", i, i, i);
  printf("z2_out_%d = z1_out_%d; z1_out_%d = b%d_out;\n", i, i, i, i);
  i += 1;
);
?>
```

### Generate Lookup Tables

```
@init
<?
// Generate sine table at compile time
printf("sin_table = 0;\n");
loop(256,
  printf("sin_table[%d] = %.15f;\n", i, sin(2 * $pi * i / 256));
  i += 1;
);
?>
```

---

## Avoid These Anti-Patterns

### String Operations in @sample

```
// NEVER: String operations are slow
@sample
sprintf(#debug, "Level: %f", spl0);  // DON'T DO THIS

// String operations belong in @gfx or @init only
```

### Heavy Math Every Sample

```
// BAD: Expensive functions every sample
@sample
spl0 = pow(spl0, 1/gamma);  // pow() is expensive
spl0 = log(exp(spl0));      // Both expensive

// GOOD: Use lookup tables or approximations
@init
// Build gamma correction table
gamma_table = 0;
i = 0;
loop(1024,
  gamma_table[i] = pow(i/1023, 1/gamma);
  i += 1;
);

@sample
// Table lookup (much faster)
idx = floor(abs(spl0) * 1023);
idx = min(1023, idx);
spl0 = sign(spl0) * gamma_table[idx];
```

### Allocating Memory in @sample

```
// NEVER: Memory allocation in @sample
@sample
buffer = new_buffer(1024);  // Would be catastrophic

// All allocation happens in @init
@init
buffer = 0;
buffer_size = 1024;
freembuf(buffer + buffer_size);
```

---

## Profiling Techniques

### Using time_precise()

```
@init
profile_start = 0;
profile_total = 0;
profile_count = 0;

@sample
profile_start = time_precise();

// ... your processing code ...

profile_total += time_precise() - profile_start;
profile_count += 1;

@gfx
// Display average time per sample
avg_time = profile_total / max(1, profile_count);
gfx_x = gfx_y = 10;
gfx_printf("Avg sample time: %.3f us", avg_time * 1000000);

// Reset periodically
profile_count > srate ? (
  profile_total = 0;
  profile_count = 0;
);
```

### Comparing Implementations

```
@init
use_fast_version = 1;

@sample
use_fast_version ? (
  // Implementation A
  spl0 = fast_process(spl0);
) : (
  // Implementation B
  spl0 = slow_process(spl0);
);

// Toggle in @gfx or via slider to compare CPU usage
```

---

## Performance Checklist

Before shipping a JSFX plugin:

1. **@sample contains only essential operations?**
   - No slider-dependent calculations
   - No constant calculations
   - No string operations
   - No memory allocation

2. **Minimized branching in @sample?**
   - Used branchless alternatives where possible
   - Mode/bypass selection done in @slider

3. **Memory access optimized?**
   - Used freembuf() to inform memory manager
   - Cached repeated memory reads in variables
   - Sequential access patterns where possible

4. **Denormal handling?**
   - Either using default anti-denormal noise
   - Or manually handling with ext_nodenorm + flush

5. **Tested at high sample rates?**
   - 96kHz and 192kHz operation verified
   - No buffer size assumptions

6. **Profiled CPU usage?**
   - Compared to similar plugins
   - No unexpected spikes
