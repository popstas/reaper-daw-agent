---
title: "EEL2 Language Reference"
impact: CRITICAL
tags:
  - eel2
  - syntax
  - operators
  - functions
---

# EEL2 Language Reference

EEL2 is the scripting language powering JSFX. It compiles on-the-fly and is optimized for real-time audio processing.

## Official Documentation

- [EEL2 Language Reference](https://www.cockos.com/EEL2/)
- [JSFX Basic Code Reference](https://www.reaper.fm/sdk/js/basiccode.php)
- [JSFX String Functions](https://www.reaper.fm/sdk/js/strings.php)

---

## Variables

### Declaration

Variables require no declaration. First use creates them with value 0.

```
my_variable = 42;        // Created and assigned
another_var += 1;        // Created as 0, then incremented to 1
```

### Naming Rules

- Case-insensitive: `myVar`, `MYVAR`, and `MyVar` are the same variable
- Start with letter or underscore
- May contain letters, numbers, underscores
- Maximum 127 characters

### Scope

Variables are **global by default**. Use `local()` in functions for local scope:

```
function process(x)
  local(temp, result)  // These are local to this function
(
  temp = x * 2;
  result = temp + 1;
  result;  // Return value
);
```

### Type

All variables are **double-precision floating-point** (64-bit). No integers, booleans, or separate types.

```
// Boolean logic uses 0 (false) and non-zero (true)
is_active = 1;        // true
is_bypassed = 0;      // false
condition && is_active ? do_something();

// Integer operations use floor() when needed
index = floor(position);
```

---

## Constants

### Predefined Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `$pi` | 3.14159... | Pi |
| `$phi` | 1.61803... | Golden ratio |
| `$e` | 2.71828... | Euler's number |

### Number Formats

```
decimal = 440;           // Decimal
hex = $xFF;              // Hexadecimal (255)
hex_alt = 0xFF;          // Hexadecimal alternate
char = $'A';             // ASCII value (65)
```

---

## Operators

### Precedence (Highest to Lowest)

| Precedence | Operators | Description |
|------------|-----------|-------------|
| 1 | `[ ]` | Memory access |
| 2 | `!` | Logical NOT |
| 3 | `-` `+` | Unary minus/plus |
| 4 | `^` | Exponentiation |
| 5 | `%` | Modulo |
| 6 | `<<` `>>` | Bitwise shift |
| 7 | `/` `*` | Division, multiplication |
| 8 | `-` `+` | Subtraction, addition |
| 9 | `\|` `&` `~` | Bitwise OR, AND, XOR (equal precedence, left-to-right) |
| 10 | `==` `===` `!=` `!==` `<` `>` `<=` `>=` | Comparison |
| 11 | `\|\|` `&&` | Logical OR, AND (short-circuit) |
| 12 | `? :` | Ternary conditional |
| 13 | `=` `+=` `-=` `*=` `/=` `%=` `^=` `\|=` `&=` `~=` | Assignment |

### Comparison Operators

```
// Approximate comparison (allows small floating-point differences)
a == b    // True if approximately equal
a != b    // True if not approximately equal

// Strict comparison (exact bit comparison)
a === b   // True only if exactly equal
a !== b   // True only if not exactly equal
```

### Bitwise Operations

```
a | b     // Bitwise OR
a & b     // Bitwise AND
a ~ b     // Bitwise XOR (NOT the C ~ operator!)
a << n    // Left shift
a >> n    // Right shift
!a        // Logical NOT (returns 0 or 1)
```

**Note**: `~` is XOR in EEL2, not bitwise NOT like in C.

### Conditional (Ternary) Operator

The primary control flow mechanism. No `if/else` keywords.

```
// Simple condition
condition ? do_if_true;

// With else clause
condition ? do_if_true : do_if_false;

// Multiple statements (use parentheses)
condition ? (
  statement1;
  statement2;
  result;
) : (
  alternative;
);

// Nested conditions
a > b ? (
  result = 1;
) : a < b ? (
  result = -1;
) : (
  result = 0;
);
```

---

## Parentheses as Code Blocks

Parentheses group multiple statements. The last expression is the block's value.

```
// Multi-statement block
(
  a = 1;
  b = 2;
  a + b;  // This is the block's value (3)
);

// Useful in conditionals
x = condition ? (
  temp = calculate();
  temp * 2;  // Returned value
) : (
  0;  // Else value
);
```

---

## Loops

### loop(count, code)

Fixed iteration count. Count is evaluated once.

```
// Iterate exactly 10 times
loop(10,
  buffer[i] = 0;
  i += 1;
);

// Process all channels
loop(num_ch,
  spl(ch) *= gain;
  ch += 1;
);
```

### while(condition) or while(code)

Two forms available:

```
// Form 1: Condition checked before each iteration
while(i < 100) (
  buffer[i] = 0;
  i += 1;
);

// Form 2: Code block, continues while last expression is non-zero
// (condition checked at END of iteration - always runs at least once)
while(
  buffer[i] = 0;
  i += 1;
  i < 100;  // Continue while true
);
```

### Iteration Limits

Loops are limited to ~1,000,000 iterations to prevent hangs.

---

## Memory Access

### Local Memory

JSFX has ~8 million words of local memory, accessed via brackets:

```
@init
// Allocate buffer starting at offset 0
buffer = 0;
buffer_size = 48000;

// Inform memory manager of usage
freembuf(buffer + buffer_size);

@sample
// Read/write memory
value = buffer[read_pos];
buffer[write_pos] = spl0;
```

### Global Shared Memory (gmem)

Shared between all JSFX instances (~1 million slots by default):

```
// Write to shared memory
gmem[0] = my_value;

// Read from shared memory
other_value = gmem[100];
```

Enable with `options:gmem=PluginName` to increase to 8 million slots.

### Shared Named Variables

Shared across all instances using `_global.` prefix:

```
// Set global variable
_global.master_gain = 0.5;

// Read global variable
local_copy = _global.master_gain;
```

---

## Math Functions

### Trigonometry

| Function | Description |
|----------|-------------|
| `sin(x)` | Sine (radians) |
| `cos(x)` | Cosine (radians) |
| `tan(x)` | Tangent (radians) |
| `asin(x)` | Arc sine |
| `acos(x)` | Arc cosine |
| `atan(x)` | Arc tangent |
| `atan2(y, x)` | Arc tangent of y/x (handles quadrants) |

### Power and Logarithms

| Function | Description |
|----------|-------------|
| `sqr(x)` | Square (x^2) - faster than x*x |
| `sqrt(x)` | Square root |
| `pow(x, y)` | x raised to power y |
| `exp(x)` | e^x |
| `log(x)` | Natural logarithm |
| `log10(x)` | Base-10 logarithm |
| `invsqrt(x)` | 1/sqrt(x) - faster than separate ops |

### Utility

| Function | Description |
|----------|-------------|
| `abs(x)` | Absolute value |
| `sign(x)` | Sign (-1, 0, or 1) |
| `min(a, b)` | Minimum of two values |
| `max(a, b)` | Maximum of two values |
| `floor(x)` | Round down to integer |
| `ceil(x)` | Round up to integer |
| `rand(x)` | Random number in [0, x) |

---

## String Handling

Strings are referenced by numeric indices. Three approaches:

### Fixed String Slots (0-1023)

```
@init
#0 = "Hello";        // Assign to slot 0
#1 = "World";        // Assign to slot 1
strcpy(#2, #0);      // Copy slot 0 to slot 2
strcat(#2, " ");     // Append space
strcat(#2, #1);      // #2 is now "Hello World"
```

### Temporary Strings

```
// # creates a temporary mutable string
temp = #;
strcpy(temp, "temporary");
```

### Named Strings

```
// #name creates a named persistent string
#my_string = "persistent value";
strcpy(#another, #my_string);
```

### String Functions

| Function | Description |
|----------|-------------|
| `strlen(s)` | String length |
| `strcpy(dest, src)` | Copy string |
| `strcat(dest, src)` | Append string |
| `strcmp(a, b)` | Compare (returns -1, 0, or 1) |
| `stricmp(a, b)` | Case-insensitive compare |
| `sprintf(dest, fmt, ...)` | Formatted output |
| `match(pattern, str)` | Pattern matching |

---

## User-Defined Functions

### Basic Syntax

```
function multiply(a, b)
(
  a * b;  // Last expression is return value
);

// Call
result = multiply(3, 4);  // result = 12
```

### Local Variables

```
function calculate(x)
  local(temp, squared)
(
  squared = x * x;
  temp = squared + 1;
  sqrt(temp);
);
```

### Instance Variables (Namespacing)

```
function filter.set_freq(freq)
  instance(omega, coeff)
(
  omega = 2 * $pi * freq / srate;
  coeff = 1 - exp(-omega);
);

function filter.process(input)
  instance(state, coeff)
(
  state += coeff * (input - state);
  state;
);

// Usage
my_filter.set_freq(1000);
output = my_filter.process(input);
// Variables: my_filter.omega, my_filter.coeff, my_filter.state
```

### Constraints

- Functions cannot be recursive
- Functions can only call functions defined before them
- Functions defined in @init are accessible everywhere
- Functions defined in other sections are local to that section

---

## Time Functions

| Function | Description |
|----------|-------------|
| `time()` | Seconds since Jan 1, 1970 (1-second resolution) |
| `time_precise()` | High-resolution timestamp for benchmarking |

---

## Common Patterns

### dB to Linear Conversion

```
// dB to linear gain
gain_lin = 10^(gain_db / 20);

// Linear to dB
gain_db = 20 * log10(gain_lin);

// With protection against log(0)
gain_db = gain_lin > 0 ? 20 * log10(gain_lin) : -144;
```

### Frequency to Angular Frequency

```
omega = 2 * $pi * frequency / srate;
```

### Clamping Values

```
// Clamp to range [min_val, max_val]
clamped = max(min_val, min(max_val, value));
```

### Linear Interpolation

```
// Interpolate between a and b by factor t (0-1)
result = a + t * (b - a);
// Or equivalently:
result = a * (1 - t) + b * t;
```
