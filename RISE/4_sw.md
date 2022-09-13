# The CHERI-RVV software stack

This chapter, being less relevant to RISE/hardware security, has been greatly condensed.

As part of the project, we considered how adding CHERI to RVV would affect the software stack.
We tested our hypotheses by adding CHERI-RVV to Clang, which is the current focus for CHERI and RVV compiler development.
Clang supports three methods of vectorization:

1) Auto-vectorization, where the compiler converts scalar code to vector code
2) Vector intrinsics, where the programmer writes vector code and the compiler handles low-level details e.g. register allocation
3) Inline assembly, where the programmer directly describes the assembly instructions to execute.

Clang currently supports intrinsics and inline assembly for RVV, but not auto-vectorization yet.
This just requires engineering work - Arm SVE, a similar model, has great auto-vectorization.

## Our changes to CHERI-Clang
The first step was to fix up the pre-existing RVV definition in Clang to use capability registers for the base address.
This meant CHERI-RVV assembly code could be compiled, as long as it explicitly referenced capability registers.
Unfortunately, non-CHERI inline assembly could not be automatically compiled under this method.

We investigated updating vector intrinsics to support CHERI, but found the code defining the intrinsics was more complicated than for assembly.
We believe it is possible to update the intrinsics, but it requires significant engineering work.

TODO this is really short lol

## The Hypothesis

*Legacy vector code can be compiled into a pure-capability form with no changes.*

This is true for CHERI-RVV, but cannot be done in practice yet.
Engineering effort is required to support this in CHERI-Clang. Because
this argument concerns source code, all three ways to generate CHERI-RVV
instructions must be examined.

### Inline assembly
For GCC-style inline assembly, where register types are specified in the source code, this is impossible.
Legacy integer-addressed RVV instructions will specify general-purpose registers for the base address, and 
the new pure-capability versions require capability registers instead.
A programmer will have to change the register types by hand before the code compiles in pure-capability form.

### Intrinsics
The current RVV intrinsics use pointer types for all
base addresses[@specification-RVV-intrinsics]. In pure-capability
compilers these pointers should be treated as capabilities instead of
integers. All RVV memory intrinsics have
equivalent RVV instructions, which all use capabilities in
pure-capability mode, so changing the intrinsics to match is valid.

This is not currently the case for CHERI-Clang, as RVV memory access
intrinsics are broken, but this can be fixed with engineering effort.

### Auto-vectorization
All vanilla RVV instructions have counterparts with identical encodings
and behaviour in CHERI-RVV pure-capability mode, assuming the base
addresses can be converted to valid capabilities.
Any auto-vectorized legacy code which uses valid base addresses can thus be
converted to pure-capability CHERI-RVV code with no changes.

This is not currently possible for CHERI-Clang, as RVV
auto-vectorization is not implemented yet.