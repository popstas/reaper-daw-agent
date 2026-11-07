---
title: "Delays & Time-Based Effects"
impact: HIGH
tags:
  - delay
  - echo
  - chorus
  - flanger
  - buffer
---

# Delays & Time-Based Effects

Delay lines, circular buffers, and time-based effects including chorus, flanger, and comb filters.

## References

- [Delay Effects and Circular Buffers - DAFX](https://www.dafx.de/)
- [musicdsp.org Delays](https://www.musicdsp.org/en/latest/Effects/index.html)

---

## Basic Delay Line

### Simple Delay

```
desc:Simple Delay
slider1:delay_ms=250<0,2000,1>Delay (ms)
slider2:feedback=0.3<0,0.95,0.01>Feedback
slider3:mix=50<0,100,1>Mix (%)

@init
max_delay_ms = 2000;
buffer_size = ceil(max_delay_ms * srate / 1000);
buffer_l = 0;
buffer_r = buffer_size;
freembuf(buffer_size * 2);
write_pos = 0;

// Clear buffers
memset(buffer_l, 0, buffer_size);
memset(buffer_r, 0, buffer_size);

@slider
delay_samples = delay_ms * srate / 1000;
wet = mix / 100;
dry = 1 - wet;

@sample
// Calculate read position
read_pos = write_pos - delay_samples;
read_pos < 0 ? read_pos += buffer_size;

// Read delayed samples
delayed_l = buffer_l[read_pos];
delayed_r = buffer_r[read_pos];

// Write to buffer (input + feedback)
buffer_l[write_pos] = spl0 + delayed_l * feedback;
buffer_r[write_pos] = spl1 + delayed_r * feedback;

// Mix output
spl0 = spl0 * dry + delayed_l * wet;
spl1 = spl1 * dry + delayed_r * wet;

// Advance write position
write_pos += 1;
write_pos >= buffer_size ? write_pos = 0;
```

### Stereo Ping-Pong Delay

```
@slider
delay_samples = delay_ms * srate / 1000;
// Stereo spread
spread_samples = spread_ms * srate / 1000;

@sample
// Read positions with spread
read_l = write_pos - delay_samples;
read_r = write_pos - delay_samples - spread_samples;
read_l < 0 ? read_l += buffer_size;
read_r < 0 ? read_r += buffer_size;

// Cross-feedback for ping-pong
delayed_l = buffer_l[read_l];
delayed_r = buffer_r[read_r];

// Write with crossed feedback
buffer_l[write_pos] = spl0 + delayed_r * feedback;  // Right feeds left
buffer_r[write_pos] = spl1 + delayed_l * feedback;  // Left feeds right

// Output
spl0 = spl0 * dry + delayed_l * wet;
spl1 = spl1 * dry + delayed_r * wet;
```

---

## Fractional Delay (Interpolation)

For smooth delay time modulation (chorus, flanger, pitch effects).

### Linear Interpolation

```
@sample
// Fractional read position
read_pos = write_pos - delay_samples;
read_pos < 0 ? read_pos += buffer_size;

// Integer and fractional parts
idx = floor(read_pos);
frac = read_pos - idx;

// Next index with wrapping
idx_next = idx + 1;
idx_next >= buffer_size ? idx_next = 0;

// Linear interpolation
delayed = buffer[idx] * (1 - frac) + buffer[idx_next] * frac;
```

### Cubic Interpolation (Higher Quality)

```
@sample
read_pos = write_pos - delay_samples;
read_pos < 0 ? read_pos += buffer_size;

idx = floor(read_pos);
frac = read_pos - idx;

// Get 4 surrounding samples
idx0 = idx - 1; idx0 < 0 ? idx0 += buffer_size;
idx1 = idx;
idx2 = idx + 1; idx2 >= buffer_size ? idx2 -= buffer_size;
idx3 = idx + 2; idx3 >= buffer_size ? idx3 -= buffer_size;

y0 = buffer[idx0];
y1 = buffer[idx1];
y2 = buffer[idx2];
y3 = buffer[idx3];

// Cubic Hermite interpolation
c0 = y1;
c1 = 0.5 * (y2 - y0);
c2 = y0 - 2.5 * y1 + 2 * y2 - 0.5 * y3;
c3 = 0.5 * (y3 - y0) + 1.5 * (y1 - y2);

delayed = ((c3 * frac + c2) * frac + c1) * frac + c0;
```

### Allpass Interpolation

Best for small delay modulations:

```
@init
ap_z1 = 0;

@sample
read_pos = write_pos - delay_samples;
read_pos < 0 ? read_pos += buffer_size;

idx = floor(read_pos);
frac = read_pos - idx;

// Allpass coefficient
ap_coeff = (1 - frac) / (1 + frac);

// Get sample
idx_next = idx + 1;
idx_next >= buffer_size ? idx_next = 0;

// Allpass interpolation
input = buffer[idx];
delayed = ap_coeff * (input - ap_z1) + buffer[idx_next];
ap_z1 = delayed;
```

---

## Chorus

### Basic Chorus

```
desc:Chorus
slider1:rate=0.5<0.1,5,0.01>Rate (Hz)
slider2:depth_ms=3<0,10,0.1>Depth (ms)
slider3:mix=50<0,100,1>Mix (%)

@init
buffer_size = srate;  // 1 second buffer
buffer_l = 0;
buffer_r = buffer_size;
freembuf(buffer_size * 2);
write_pos = 0;
lfo_phase = 0;

// Base delay (center of modulation)
base_delay_ms = 20;

@slider
lfo_inc = rate / srate;
depth_samples = depth_ms * srate / 1000;
base_delay_samples = base_delay_ms * srate / 1000;
wet = mix / 100;
dry = 1 - wet;

@sample
// LFO
lfo_phase += lfo_inc;
lfo_phase >= 1 ? lfo_phase -= 1;
lfo = sin(2 * $pi * lfo_phase);

// Modulated delay time
delay_samples = base_delay_samples + lfo * depth_samples;

// Read with interpolation
read_pos = write_pos - delay_samples;
read_pos < 0 ? read_pos += buffer_size;

idx = floor(read_pos);
frac = read_pos - idx;
idx_next = idx + 1;
idx_next >= buffer_size ? idx_next = 0;

// Linear interpolation
delayed_l = buffer_l[idx] * (1 - frac) + buffer_l[idx_next] * frac;
delayed_r = buffer_r[idx] * (1 - frac) + buffer_r[idx_next] * frac;

// Write current input
buffer_l[write_pos] = spl0;
buffer_r[write_pos] = spl1;

// Mix
spl0 = spl0 * dry + delayed_l * wet;
spl1 = spl1 * dry + delayed_r * wet;

write_pos += 1;
write_pos >= buffer_size ? write_pos = 0;
```

### Stereo Chorus (Multi-Voice)

```
@init
// Multiple LFO phases for richness
lfo_phase_1 = 0;
lfo_phase_2 = 0.33;  // 120 degrees offset
lfo_phase_3 = 0.66;  // 240 degrees offset

@sample
// Three modulated delay reads
lfo1 = sin(2 * $pi * lfo_phase_1);
lfo2 = sin(2 * $pi * lfo_phase_2);
lfo3 = sin(2 * $pi * lfo_phase_3);

delay1 = base_delay + lfo1 * depth;
delay2 = base_delay + lfo2 * depth;
delay3 = base_delay + lfo3 * depth;

// Read three delayed signals (with interpolation)
d1 = read_buffer(buffer_l, delay1);
d2 = read_buffer(buffer_l, delay2);
d3 = read_buffer(buffer_l, delay3);

// Mix for stereo
spl0 = spl0 * dry + (d1 + d2 * 0.7) * wet;
spl1 = spl1 * dry + (d1 + d3 * 0.7) * wet;

// Advance phases
lfo_phase_1 += lfo_inc;
lfo_phase_2 += lfo_inc;
lfo_phase_3 += lfo_inc;
lfo_phase_1 >= 1 ? lfo_phase_1 -= 1;
lfo_phase_2 >= 1 ? lfo_phase_2 -= 1;
lfo_phase_3 >= 1 ? lfo_phase_3 -= 1;
```

---

## Flanger

Shorter delays than chorus, with feedback for resonance.

```
desc:Flanger
slider1:rate=0.3<0.01,2,0.01>Rate (Hz)
slider2:depth=0.8<0,1,0.01>Depth
slider3:feedback=0.7<-0.99,0.99,0.01>Feedback
slider4:mix=50<0,100,1>Mix (%)

@init
buffer_size = srate / 10;  // 100ms max
buffer_l = 0;
buffer_r = buffer_size;
freembuf(buffer_size * 2);
write_pos = 0;
lfo_phase = 0;

// Flanger delay range: 0.1ms - 10ms
min_delay_ms = 0.1;
max_delay_ms = 10;

@slider
lfo_inc = rate / srate;
min_delay = min_delay_ms * srate / 1000;
max_delay = max_delay_ms * srate / 1000;
delay_range = max_delay - min_delay;
wet = mix / 100;
dry = 1 - wet;

@sample
// Triangle LFO for flanger (smoother than sine)
lfo_phase += lfo_inc;
lfo_phase >= 1 ? lfo_phase -= 1;
lfo = abs(lfo_phase * 4 - 2) - 1;  // Triangle -1 to 1

// Modulated delay
delay_samples = min_delay + (lfo * 0.5 + 0.5) * delay_range * depth;

// Read with interpolation
read_pos = write_pos - delay_samples;
read_pos < 0 ? read_pos += buffer_size;

idx = floor(read_pos);
frac = read_pos - idx;
idx_next = idx + 1;
idx_next >= buffer_size ? idx_next = 0;

delayed_l = buffer_l[idx] * (1 - frac) + buffer_l[idx_next] * frac;
delayed_r = buffer_r[idx] * (1 - frac) + buffer_r[idx_next] * frac;

// Write with feedback
buffer_l[write_pos] = spl0 + delayed_l * feedback;
buffer_r[write_pos] = spl1 + delayed_r * feedback;

// Mix
spl0 = spl0 * dry + delayed_l * wet;
spl1 = spl1 * dry + delayed_r * wet;

write_pos += 1;
write_pos >= buffer_size ? write_pos = 0;
```

---

## Comb Filter

Fixed delay with feedback, creates harmonic series.

### Feedforward Comb (FIR)

```
@sample
// Read delayed
delayed = buffer[read_pos];

// FIR comb: y[n] = x[n] + g * x[n-D]
output = spl0 + delayed * gain;

// Write current input
buffer[write_pos] = spl0;
```

### Feedback Comb (IIR)

```
@sample
// Read delayed
delayed = buffer[read_pos];

// IIR comb: y[n] = x[n] + g * y[n-D]
output = spl0 + delayed * feedback;

// Write OUTPUT (not input) for IIR
buffer[write_pos] = output;

spl0 = output;
```

### Allpass Comb

Used in reverbs for dispersion without coloring frequency response:

```
@sample
// Read delayed
delayed = buffer[read_pos];

// Allpass comb
output = -gain * spl0 + delayed + gain * delayed;

// Or equivalently:
output = delayed + gain * (delayed - spl0);

// Write
buffer[write_pos] = spl0 + gain * delayed;

spl0 = output;
```

---

## Tempo-Synced Delay

```
desc:Tempo Sync Delay
slider1:note_value=2<0,6,1{1/16,1/8,1/4,1/2,1,2,4}>Note Value
slider2:dotted=0<0,1,1{Off,Dotted}>
slider3:triplet=0<0,1,1{Off,Triplet}>

@slider
// Convert note value to beats
note_value == 0 ? beats = 0.25 :   // 1/16
note_value == 1 ? beats = 0.5 :    // 1/8
note_value == 2 ? beats = 1 :      // 1/4
note_value == 3 ? beats = 2 :      // 1/2
note_value == 4 ? beats = 4 :      // 1
note_value == 5 ? beats = 8 :      // 2 bars
beats = 16;                         // 4 bars

// Apply modifiers
dotted ? beats *= 1.5;
triplet ? beats *= 2/3;

@block
// Calculate delay from tempo
beat_length_samples = srate * 60 / tempo;
delay_samples = beats * beat_length_samples;

// Clamp to buffer size
delay_samples = min(delay_samples, buffer_size - 1);
```

---

## Multi-Tap Delay

```
desc:Multi-Tap Delay
slider1:tap1_ms=125<0,2000,1>Tap 1 (ms)
slider2:tap1_level=0<-60,6,0.1>Tap 1 Level (dB)
slider3:tap2_ms=250<0,2000,1>Tap 2 (ms)
slider4:tap2_level=-3<-60,6,0.1>Tap 2 Level (dB)
slider5:tap3_ms=375<0,2000,1>Tap 3 (ms)
slider6:tap3_level=-6<-60,6,0.1>Tap 3 Level (dB)
slider7:tap4_ms=500<0,2000,1>Tap 4 (ms)
slider8:tap4_level=-9<-60,6,0.1>Tap 4 Level (dB)
slider9:feedback=0.3<0,0.95,0.01>Feedback

@slider
tap1_samples = tap1_ms * srate / 1000;
tap1_gain = 10^(tap1_level / 20);
tap2_samples = tap2_ms * srate / 1000;
tap2_gain = 10^(tap2_level / 20);
tap3_samples = tap3_ms * srate / 1000;
tap3_gain = 10^(tap3_level / 20);
tap4_samples = tap4_ms * srate / 1000;
tap4_gain = 10^(tap4_level / 20);

@sample
// Read all taps
t1 = read_buffer(tap1_samples) * tap1_gain;
t2 = read_buffer(tap2_samples) * tap2_gain;
t3 = read_buffer(tap3_samples) * tap3_gain;
t4 = read_buffer(tap4_samples) * tap4_gain;

// Sum taps
delayed = t1 + t2 + t3 + t4;

// Write with feedback from last tap
buffer[write_pos] = spl0 + t4 * feedback;

// Output
spl0 = spl0 + delayed;
```

---

## Modulated Delay Line Library

Reusable delay with interpolation:

```
// moddelay.jsfx-inc

function moddelay.init(mem_offset, max_samples)
  instance(buffer, size, write_pos, last_out)
(
  buffer = mem_offset;
  size = max_samples;
  write_pos = 0;
  last_out = 0;
  memset(buffer, 0, size);
  mem_offset + size;
);

function moddelay.write(input)
  instance(buffer, size, write_pos)
(
  buffer[write_pos] = input;
  write_pos += 1;
  write_pos >= size ? write_pos = 0;
);

function moddelay.read(delay_samples)
  instance(buffer, size, write_pos, last_out)
  local(read_pos, idx, frac, idx_next)
(
  read_pos = write_pos - delay_samples;
  read_pos < 0 ? read_pos += size;

  idx = floor(read_pos);
  frac = read_pos - idx;
  idx_next = idx + 1;
  idx_next >= size ? idx_next = 0;

  // Linear interpolation
  last_out = buffer[idx] * (1 - frac) + buffer[idx_next] * frac;
  last_out;
);

function moddelay.tap(delay_samples, level)
(
  this.read(delay_samples) * level;
);
```

Usage:
```
@init
ptr = 0;
ptr = delay_l.moddelay.init(ptr, srate * 2);
ptr = delay_r.moddelay.init(ptr, srate * 2);
freembuf(ptr);

@sample
delayed_l = delay_l.moddelay.read(delay_samples);
delayed_r = delay_r.moddelay.read(delay_samples);

delay_l.moddelay.write(spl0 + delayed_l * feedback);
delay_r.moddelay.write(spl1 + delayed_r * feedback);

spl0 += delayed_l * wet;
spl1 += delayed_r * wet;
```
