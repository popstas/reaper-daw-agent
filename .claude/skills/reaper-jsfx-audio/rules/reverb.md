---
title: "Reverb"
impact: HIGH
tags:
  - reverb
  - ambience
  - fdn
  - allpass
  - diffusion
---

# Reverb

Algorithmic reverb implementations including Schroeder reverb, FDN (Feedback Delay Network), and diffusion networks.

## References

- [Schroeder Reverberator](https://ccrma.stanford.edu/~jos/pasp/Schroeder_Reverberators.html)
- [FDN Reverb](https://ccrma.stanford.edu/~jos/pasp/Feedback_Delay_Networks.html)
- [Dattorro Reverb](https://ccrma.stanford.edu/~dattorro/EffectDesignPart1.pdf)
- [Freeverb](https://ccrma.stanford.edu/~jos/pasp/Freeverb.html)

---

## Building Blocks

### Allpass Filter (Diffusion)

```
@init
ap_buffer = 0;
ap_size = 0;
ap_pos = 0;

function allpass_init(mem_offset, delay_samples)
  instance(buffer, size, pos)
(
  buffer = mem_offset;
  size = delay_samples;
  pos = 0;
  memset(buffer, 0, size);
  mem_offset + size;
);

function allpass_process(input, coeff)
  instance(buffer, size, pos)
  local(delayed, output)
(
  delayed = buffer[pos];
  output = delayed - coeff * input;
  buffer[pos] = input + coeff * delayed;

  pos += 1;
  pos >= size ? pos = 0;

  output;
);
```

### Comb Filter (Resonator)

```
function comb_init(mem_offset, delay_samples)
  instance(buffer, size, pos)
(
  buffer = mem_offset;
  size = delay_samples;
  pos = 0;
  memset(buffer, 0, size);
  mem_offset + size;
);

function comb_process(input, feedback, damping)
  instance(buffer, size, pos, filter_state)
  local(output)
(
  output = buffer[pos];

  // Lowpass in feedback path (damping)
  filter_state = output * (1 - damping) + filter_state * damping;

  buffer[pos] = input + filter_state * feedback;

  pos += 1;
  pos >= size ? pos = 0;

  output;
);
```

---

## Schroeder Reverb

Classic reverb structure: parallel combs + series allpasses.

```
desc:Schroeder Reverb
slider1:decay=2<0.1,10,0.1>Decay (s)
slider2:damping=0.5<0,1,0.01>Damping
slider3:mix=30<0,100,1>Mix (%)

@init
// Allocate comb filters (parallel)
ptr = 0;
ptr = comb1.comb_init(ptr, 1557);
ptr = comb2.comb_init(ptr, 1617);
ptr = comb3.comb_init(ptr, 1491);
ptr = comb4.comb_init(ptr, 1422);
ptr = comb5.comb_init(ptr, 1277);
ptr = comb6.comb_init(ptr, 1356);
ptr = comb7.comb_init(ptr, 1188);
ptr = comb8.comb_init(ptr, 1116);

// Allocate allpass filters (series)
ptr = ap1.allpass_init(ptr, 225);
ptr = ap2.allpass_init(ptr, 556);
ptr = ap3.allpass_init(ptr, 441);
ptr = ap4.allpass_init(ptr, 341);

freembuf(ptr);

@slider
// Calculate feedback from decay time
// RT60 = decay time in seconds
// feedback = 10^(-3 * delay / (srate * RT60))
fb1 = pow(10, -3 * 1557 / (srate * decay));
fb2 = pow(10, -3 * 1617 / (srate * decay));
fb3 = pow(10, -3 * 1491 / (srate * decay));
fb4 = pow(10, -3 * 1422 / (srate * decay));
fb5 = pow(10, -3 * 1277 / (srate * decay));
fb6 = pow(10, -3 * 1356 / (srate * decay));
fb7 = pow(10, -3 * 1188 / (srate * decay));
fb8 = pow(10, -3 * 1116 / (srate * decay));

wet = mix / 100;
dry = 1 - wet;

@sample
// Input (mono sum for reverb)
input = (spl0 + spl1) * 0.5;

// Parallel comb filters
c1 = comb1.comb_process(input, fb1, damping);
c2 = comb2.comb_process(input, fb2, damping);
c3 = comb3.comb_process(input, fb3, damping);
c4 = comb4.comb_process(input, fb4, damping);
c5 = comb5.comb_process(input, fb5, damping);
c6 = comb6.comb_process(input, fb6, damping);
c7 = comb7.comb_process(input, fb7, damping);
c8 = comb8.comb_process(input, fb8, damping);

// Sum combs
reverb = (c1 + c2 + c3 + c4 + c5 + c6 + c7 + c8) * 0.125;

// Series allpass filters (diffusion)
reverb = ap1.allpass_process(reverb, 0.5);
reverb = ap2.allpass_process(reverb, 0.5);
reverb = ap3.allpass_process(reverb, 0.5);
reverb = ap4.allpass_process(reverb, 0.5);

// Mix
spl0 = spl0 * dry + reverb * wet;
spl1 = spl1 * dry + reverb * wet;
```

---

## Freeverb Implementation

Popular open-source reverb algorithm.

```
desc:Freeverb
slider1:room_size=0.5<0,1,0.01>Room Size
slider2:damping=0.5<0,1,0.01>Damping
slider3:width=1<0,1,0.01>Width
slider4:mix=30<0,100,1>Mix (%)

@init
// Freeverb uses prime-ish delay lengths
// Left channel combs
ptr = 0;
ptr = combL1.comb_init(ptr, 1116);
ptr = combL2.comb_init(ptr, 1188);
ptr = combL3.comb_init(ptr, 1277);
ptr = combL4.comb_init(ptr, 1356);
ptr = combL5.comb_init(ptr, 1422);
ptr = combL6.comb_init(ptr, 1491);
ptr = combL7.comb_init(ptr, 1557);
ptr = combL8.comb_init(ptr, 1617);

// Right channel combs (offset by stereo spread)
STEREO_SPREAD = 23;
ptr = combR1.comb_init(ptr, 1116 + STEREO_SPREAD);
ptr = combR2.comb_init(ptr, 1188 + STEREO_SPREAD);
ptr = combR3.comb_init(ptr, 1277 + STEREO_SPREAD);
ptr = combR4.comb_init(ptr, 1356 + STEREO_SPREAD);
ptr = combR5.comb_init(ptr, 1422 + STEREO_SPREAD);
ptr = combR6.comb_init(ptr, 1491 + STEREO_SPREAD);
ptr = combR7.comb_init(ptr, 1557 + STEREO_SPREAD);
ptr = combR8.comb_init(ptr, 1617 + STEREO_SPREAD);

// Allpasses
ptr = apL1.allpass_init(ptr, 556);
ptr = apL2.allpass_init(ptr, 441);
ptr = apL3.allpass_init(ptr, 341);
ptr = apL4.allpass_init(ptr, 225);
ptr = apR1.allpass_init(ptr, 556 + STEREO_SPREAD);
ptr = apR2.allpass_init(ptr, 441 + STEREO_SPREAD);
ptr = apR3.allpass_init(ptr, 341 + STEREO_SPREAD);
ptr = apR4.allpass_init(ptr, 225 + STEREO_SPREAD);

freembuf(ptr);

// Constants
FIXED_GAIN = 0.015;
SCALE_WET = 3;
SCALE_DRY = 2;
SCALE_DAMP = 0.4;
SCALE_ROOM = 0.28;
OFFSET_ROOM = 0.7;

@slider
roomsize1 = room_size * SCALE_ROOM + OFFSET_ROOM;
damp1 = damping * SCALE_DAMP;
wet1 = mix / 100 * SCALE_WET;
wet2 = wet1 * width;
dry_gain = (1 - mix / 100) * SCALE_DRY;

// Wet levels for stereo width
wet_l1 = wet1 + wet2;
wet_r1 = wet1 - wet2;

@sample
// Input
input_l = spl0;
input_r = spl1;
input = (input_l + input_r) * FIXED_GAIN;

// Left channel
outL = combL1.comb_process(input, roomsize1, damp1);
outL += combL2.comb_process(input, roomsize1, damp1);
outL += combL3.comb_process(input, roomsize1, damp1);
outL += combL4.comb_process(input, roomsize1, damp1);
outL += combL5.comb_process(input, roomsize1, damp1);
outL += combL6.comb_process(input, roomsize1, damp1);
outL += combL7.comb_process(input, roomsize1, damp1);
outL += combL8.comb_process(input, roomsize1, damp1);

outL = apL1.allpass_process(outL, 0.5);
outL = apL2.allpass_process(outL, 0.5);
outL = apL3.allpass_process(outL, 0.5);
outL = apL4.allpass_process(outL, 0.5);

// Right channel
outR = combR1.comb_process(input, roomsize1, damp1);
outR += combR2.comb_process(input, roomsize1, damp1);
outR += combR3.comb_process(input, roomsize1, damp1);
outR += combR4.comb_process(input, roomsize1, damp1);
outR += combR5.comb_process(input, roomsize1, damp1);
outR += combR6.comb_process(input, roomsize1, damp1);
outR += combR7.comb_process(input, roomsize1, damp1);
outR += combR8.comb_process(input, roomsize1, damp1);

outR = apR1.allpass_process(outR, 0.5);
outR = apR2.allpass_process(outR, 0.5);
outR = apR3.allpass_process(outR, 0.5);
outR = apR4.allpass_process(outR, 0.5);

// Output with stereo width
spl0 = outL * wet_l1 + outR * wet_r1 + input_l * dry_gain;
spl1 = outR * wet_l1 + outL * wet_r1 + input_r * dry_gain;
```

---

## FDN (Feedback Delay Network)

More flexible and modern reverb topology.

```
desc:4x4 FDN Reverb
slider1:decay=2<0.1,10,0.1>Decay (s)
slider2:modulation=0.3<0,1,0.01>Modulation

@init
// 4 delay lines with prime-ish lengths
delay_times[0] = 1453;
delay_times[1] = 1867;
delay_times[2] = 2293;
delay_times[3] = 2791;

// Allocate delay buffers
ptr = 0;
loop(4,
  delay_buffers[i] = ptr;
  delay_sizes[i] = delay_times[i];
  delay_positions[i] = 0;
  memset(ptr, 0, delay_times[i]);
  ptr += delay_times[i];
  i += 1;
);
freembuf(ptr);

// Hadamard matrix (4x4) for mixing
// Normalized Hadamard: multiply by 0.5
// [1  1  1  1]
// [1 -1  1 -1]
// [1  1 -1 -1]
// [1 -1 -1  1]

@slider
// Calculate feedback gains from decay time
i = 0;
loop(4,
  feedback_gains[i] = pow(10, -3 * delay_times[i] / (srate * decay));
  i += 1;
);

@sample
// Read from delay lines
loop(4,
  outputs[i] = delay_buffers[i][delay_positions[i]];
  i += 1;
);

// Hadamard mixing matrix
h0 = (outputs[0] + outputs[1] + outputs[2] + outputs[3]) * 0.5;
h1 = (outputs[0] - outputs[1] + outputs[2] - outputs[3]) * 0.5;
h2 = (outputs[0] + outputs[1] - outputs[2] - outputs[3]) * 0.5;
h3 = (outputs[0] - outputs[1] - outputs[2] + outputs[3]) * 0.5;

// Input distribution
input = (spl0 + spl1) * 0.5;

// Write to delay lines (mixed output + input + feedback)
delay_buffers[0][delay_positions[0]] = input + h0 * feedback_gains[0];
delay_buffers[1][delay_positions[1]] = input + h1 * feedback_gains[1];
delay_buffers[2][delay_positions[2]] = input + h2 * feedback_gains[2];
delay_buffers[3][delay_positions[3]] = input + h3 * feedback_gains[3];

// Advance positions
loop(4,
  delay_positions[i] += 1;
  delay_positions[i] >= delay_sizes[i] ? delay_positions[i] = 0;
  i += 1;
);

// Output (stereo from different taps)
reverb_l = (outputs[0] + outputs[2]) * 0.5;
reverb_r = (outputs[1] + outputs[3]) * 0.5;

spl0 = spl0 * 0.7 + reverb_l * 0.3;
spl1 = spl1 * 0.7 + reverb_r * 0.3;
```

---

## Early Reflections

Simulates discrete room reflections before diffuse tail.

```
@init
// Early reflection taps (in samples)
// Simulates first reflections from walls/ceiling
er_taps[0] = 0.012 * srate;  // ~12ms
er_taps[1] = 0.019 * srate;  // ~19ms
er_taps[2] = 0.028 * srate;  // ~28ms
er_taps[3] = 0.037 * srate;  // ~37ms
er_taps[4] = 0.048 * srate;  // ~48ms
er_taps[5] = 0.059 * srate;  // ~59ms

// Gains (decay with distance)
er_gains[0] = 0.8;
er_gains[1] = 0.7;
er_gains[2] = 0.6;
er_gains[3] = 0.5;
er_gains[4] = 0.4;
er_gains[5] = 0.3;

// Pan positions (-1 to 1)
er_pans[0] = -0.3;
er_pans[1] = 0.5;
er_pans[2] = -0.7;
er_pans[3] = 0.8;
er_pans[4] = -0.2;
er_pans[5] = 0.4;

@sample
er_l = 0;
er_r = 0;

// Sum early reflections
i = 0;
loop(6,
  pos = write_pos - er_taps[i];
  pos < 0 ? pos += buffer_size;

  tap = buffer[pos] * er_gains[i];

  // Pan
  pan = er_pans[i];
  er_l += tap * (1 - pan) * 0.5;
  er_r += tap * (1 + pan) * 0.5;

  i += 1;
);

// Add early reflections to output
spl0 += er_l * er_level;
spl1 += er_r * er_level;
```

---

## Pre-Delay

Separates direct sound from reverb.

```
@init
predelay_buffer_l = 0;
predelay_buffer_r = predelay_max_samples;
predelay_pos = 0;

@slider
predelay_samples = predelay_ms * srate / 1000;

@sample
// Read pre-delayed signal
read_pos = predelay_pos - predelay_samples;
read_pos < 0 ? read_pos += predelay_max_samples;

predelayed_l = predelay_buffer_l[read_pos];
predelayed_r = predelay_buffer_r[read_pos];

// Write current input
predelay_buffer_l[predelay_pos] = spl0;
predelay_buffer_r[predelay_pos] = spl1;

predelay_pos += 1;
predelay_pos >= predelay_max_samples ? predelay_pos = 0;

// Feed pre-delayed signal to reverb
reverb_input = (predelayed_l + predelayed_r) * 0.5;
```

---

## Complete Reverb Template

```
desc:Algorithmic Reverb
slider1:predelay_ms=20<0,100,1>Pre-Delay (ms)
slider2:decay=2<0.1,10,0.1>Decay (s)
slider3:damping=0.5<0,1,0.01>Damping
slider4:diffusion=0.7<0,1,0.01>Diffusion
slider5:size=0.5<0,1,0.01>Size
slider6:er_level=0.3<0,1,0.01>Early Reflections
slider7:mix=30<0,100,1>Mix (%)

@init
// ... allocate all buffers ...

// Report tail length to host
ext_tail_size = srate * 10;  // 10 second max tail

@slider
// Recalculate all coefficients
wet = mix / 100;
dry = 1 - wet;

// Scale delay times by size
// ...

@sample
// Pre-delay
// ...

// Early reflections
// ...

// Diffusion (input allpasses)
// ...

// Main reverb body (combs or FDN)
// ...

// Output diffusion
// ...

// Mix
spl0 = spl0 * dry + reverb_l * wet;
spl1 = spl1 * dry + reverb_r * wet;
```
