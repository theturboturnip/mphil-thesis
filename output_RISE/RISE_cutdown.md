---
bibliography:
- thesis.bib
csl:
- institute-of-physics-numeric-modified.csl
---

TODO note url for project?
TODO note that royal 'we' is used throughout, I was the sole contributor

# Introduction

The CHERI architecture project improves computer
security by checking all memory accesses in
hardware.
Under CHERI, memory cannot be accessed with integer addresses, but must pass
through a *capability*[@TR-941] - unforgeable tokens
that grant fine-grained access to ranges of memory. Instead of
generating them from scratch, capabilities must be *derived* from
another capability with greater permissions.
This
vastly reduces the scope of security violations through spatial errors
(e.g. buffer overflows[@szekeresSoKEternalWar2013]), and creates
interesting opportunities for software
compartmentalization[@watsonCHERIHybridCapabilitySystem2015].

Industry leaders have recognized the value CHERI provides. Arm Inc have
manufactured the Morello System-on-Chip
which incorporates CHERI into the Armv8.2 ISA.
However some features haven't fully embraced CHERI, such as 
Arm's Scalable Vector Extension (SVE)
, which is designed to remain in use
well into the future[@stephensARMScalableVector2017]. Supporting this
and other scalable vector ISAs is essential to CHERI's
long-term relevance.

## Motivation

Modern vector implementations all provide vector load/store instructions.
Vector-enabled CHERI CPUs must support those instructions, 
but adding CHERI's bounds-checking for each vector element could impact performance.

Vector memory access performance is critical, because
vectors aren't just used for computation.
For example, `glibc` uses vector memory accesses to implement `memcpy` where available.
These implementations are written in assembly and
heavily optimized. If they hit the cache, extra cycles of bounds-checking for each access could make a difference.

`memcpy` also raises the important question of how vectors
interact with capabilities. In non-CHERI processors, `memcpy` will copy
pointers around in memory. An equivalent CHERI-enabled vector
memcpy would need to load/store
capabilities from vectors without violating security guarantees.

The goal of this project is to investigate the impact of, and the
roadblocks for, integrating a scalable vector architecture with CHERI's
memory protection system. Specifically we focus on integrating the RISC-V Vector
extension[@specification-RVV-v1.0] (RVV)
with the CHERI-RISC-V ISA, with the aim of enabling a future CHERI-RVV
implementation and informing the approach for a future CHERI Arm SVE
implementation.

The full dissertation addresses nine hypotheses, but for the sake of brevity we examine four here.
Chapters 2-5 each cover one hypothesis in order, and Chapter 6 concludes.

1. It is possible to use CHERI capabilities as memory references in all vector instructions.
2. The capability bounds checks for vector elements within a known range (e.g. a cache line) can be performed in a single check, amortizing the cost.
3. Legacy vector code can be compiled into a pure-capability form with no changes.
4. It is possible for a vector architecture to load, store, and manipulate capabilities in vector registers without violating CHERI security principles.

# Background

This chapter provides background on CHERI and RVV.
It has been cut down to only include information relevant to the rest of this summary.

## CHERI

In CHERI, addresses/pointers are replaced with capabilities: unforgeable
tokens that provide *specific kinds of access* to an *address* within a
*range of memory*. The above statement is enough to understand what
capabilities contain:

-   Permission bits, to restrict access

-   The *cursor*, i.e. the address it currently points to

-   The *bounds*, i.e. the range of addresses this capability could
    point to

By using floating-point, all of this data has been reduced to just 2x the architectural register
size (see [@woodruffCHERIConcentratePractical2019]).
For example, on 64-bit RISC-V a standard capability is 128-bits
long, and we assume capabilities are 128-bits
long throughout this summary.

A CHERI implementation has to enforce three security properties about
its capabilities[@TR-951 Section 1.2.1]:

-   Provenance - Capabilities must always be derived from valid
    manipulations of other capabilities.

-   Integrity - Corrupted capabilities cannot be dereferenced.

-   Monotonicity - Capabilities cannot increase their rights.

Integrity is enforced by tagging registers and memory. Every 128-bit
register and aligned 128-bit region of memory has an associated tag bit,
which denotes if its data encodes a valid capability. If any
non-capability data is written to any part of the region the tag bit is
zeroed out. Instructions that perform memory accesses can only do so if
the provided capability has a valid tag bit. As above, significant work
has gone into the implementation to reduce the DRAM overhead of this
method (see [@joannouEfficientTaggedMemory2017]).

Provenance and Monotonicity are enforced by all instructions that
manipulate capabilities. If an instruction violates either property,
it will zero out the tag bit and rely on Integrity
enforcement to ensure it is not dereferenced. Some CHERI-enabled
architectures, such as CHERI-RISC-V, also raise a synchronous exception
when this occurs.

### CHERI-RISC-V ISA

CHERI-RISC-V (described in [@TR-951]) is a
straightforward set of additions to basic RISC-V ISAs. It adds
thirty-two general-purpose capability registers `cx0-cx31`, thirty-two Special
Capability Registers (SCRs), and many new instructions.
<!-- The new general-purpose capability registers are each of size
`CLEN = 2 * XLEN` plus a tag bit. -->
Many of the new SCRs are intended to support the privileged ISA
extensions for e.g. hypervisors or operating systems and are unused here.
The two most relevant SCRs are the Program Counter Capability (PCC) and Default Data Capability (DDC).

The PCC replaces the program counter and adds more metadata, ensuring
instruction fetches have the same security properties as normal loads
and stores. The DDC is used to sandbox integer addressing modes.
CHERI-RISC-V includes new instructions which use integer addressing, and
allows legacy (i.e. integer addressed) code to function on CHERI systems
without recompiling for CHERI-RISC-V. These instructions all use integer
addresses relative to the DDC, and the DDC controls the permissions
those instructions have.

### Capability and Integer encoding mode

CHERI-RISC-V specifies two encoding modes, selected using a flag in the
PCC `flags` field. *Capability mode* modifies the behaviour of
pre-existing instructions (e.g. Load Byte) to use capability addressing,
and *Integer mode* keeps those instructions using integer addresses
but dereferences them relative to the DDC.
This allows legacy code to run in a sandbox defined by the DDC without recompiling.


### Pure-capability and Hybrid compilation modes {#cheri_purecap_hybrid}

CHERI-Clang, the main CHERI-enabled compiler, supports two ways to
compile CHERI-RISC-V which map to the different encoding modes.

*Pure-capability* mode treats all pointers as capabilities, and emits
pre-existing RISC-V instructions that expect to be run in capability
mode.

*Hybrid* mode treats pointers as integer addresses, dereferenced
relative to the DDC, unless they are annotated with `__capability`. This
mode emits a mix of capability-addressed and integer-addressed memory instructions.
All capabilities in
hybrid mode are created manually by the program by copying and shrinking
the DDC.

Hybrid mode allows programs to be gradually ported to CHERI, making it
very easy to adopt on legacy/large codebases. Any extensions to the
model (e.g. CHERI-RVV) should try and retain this property.




## The RVV vector model
RVV defines thirty-two vector registers, each of an
implementation-defined constant width `VLEN`. These registers can be
interpreted as *vectors* of *elements*. The program can configure the
size of elements, and the implementation defines a maximum width `ELEN`.

RVV instructions operate on *groups* of vector registers.
The implementation holds two status registers, `vstart` and `vl`, which define the start and length of the "body" section within the vector.
Instructions only operate on body elements, and some allow elements within the body to be masked out and ignored.

### RVV memory instructions

The only RVV instructions that interact with memory are vectorized loads and stores.
These instructions take a register index to use as the "base address", and calculates offsets from that base for each individual vector element.
The offsets can be calculated in three ways:

- Unit-stride, where elements are tightly packed together.
- Strided, where a second register specifies the distance between consecutive elements.
- Indexed, where a vector register holds the offsets for each vector element.

Additionally, unit-stride accesses support a few alternate modes of operation.
The most relevant one here is the fault-only-first unit-strided load.
This loads as much contiguous data as possible from the base address, until one of the elements triggers an exception (such as a capability bounds violation).
That exception will be silently swallowed, and `vl` will be shrunk to the index of the offending element.

### Exception handling

If synchronous exceptions (e.g. invalid memory access) or asynchronous interrupts
are encountered while executing a vector instruction, RVV defines two ways
to trap them.
In both cases, the PC of the instruction is saved in a register `*epc`.

If the instruction should be resumed after handling the trap, e.g. in the case of demand paging,
the implementation may use a "precise trap".
The implementation must complete all instructions up to `*epc`, and no instructions after that,
and save the index of the offending vector element in `vstart`.
Within the instruction, all vector elements before `vstart` must have committed their results, and all other elements must either
1) not have committed results, or
2) be idempotent e.g. repeatable without changing the outcome.

In other cases "imprecise traps" may be used, which allow instructions after `*epc` and vector elements after `vstart` to commit their results.
`vstart` must still be recorded, however.
   


## The Hypothesis

*It is possible to use CHERI capabilities as memory references in all vector instructions.*

This is entirely true - all RVV memory instructions take the index of a "base address register" in the scalar register file, and it is trivial to index into the capability register file instead.
This can be applied to other ISAs wherever memory references are accessed through a scalar register file, e.g. all Arm Morello scalar instructions and most of Arm SVE's memory instructions.
Notably Arm SVE's `u64base` addressing mode, which uses a vector directly as a set of 64-bit integer addresses[@armltdArmCompilerScalable2019], is not as simple to port to CHERI.

# Hardware emulation investigation

In order to experiment with integrating CHERI and RVV, we implemented a
RISC-V emulator in the Rust programming language named `riscv-v-lite`.
The emulator supports the Multiply, CSR, Vector, and CHERI extensions,
and was also used as the base for
capabilities-in-vectors research.

The emulator is very modular, such that each ISA extension is defined as 
a separate module which can easily be plugged into different processor implementations.
Each ISA module uses a "connector" structure, containing e.g. virtual references to register files and memory, 
which allows different processors to reuse ISA modules despite using different register file/memory implementations.

Each processor implements a single stage pipeline. Instructions are
fetched, decoded with a common decoder function, and executed. The
processor asks each ISA module in turn if it wants to handle the
instruction, and uses the first module to say yes. If the ISA module
returns a new PC value it is immediately applied, otherwise it is
automatically incremented. This structure easily represents basic RISC-V
architectures, and can scale up to support many different new modules.

## Emulating CHERI

Manipulating CHERI capabilities securely and correctly is a must for any
CHERI-enabled emulator. Capability encoding logic is not trivial by any
means, so the `cheri-compressed-cap` C library was re-used rather than
implementing it from scratch. There were a few issues with implementing Rust/C interoperation, which are addressed in the dissertation.

Integrating capabilities into the emulator was relatively simple thanks
to the modular emulator structure.
CHERI-specific memory and register file types were created, which could expose both integer and capability functionality.
The CHERI register file exposed integer-mode and capability-mode accesses, and memory was built in three layers:

1) Normal integer-addressed memory
2) Capability-addressed CHERI memory, which checks capability properties before accessing 1)
3) Integer-mode CHERI memory, which adds an integer address to the DDC before accessing 2)

This approach meant code for basic
RV64I operations did not need to be modified for CHERI at all -
simply passing the integer-mode memory and register file would perform
all relevant checks.

Integrating capability instructions was also simple. Two new ISA modules
were created: `XCheri64` for the new CHERI instructions, and
`Rv64imCapabilityMode` to override legacy instructions
in capability-encoding-mode. Integer addresses were changed to capabilities
throughout, memory and register file types were changed as described
above, and the PCC/DDC were added.

To reduce the chances of accidentally converting integers to capabilities,
the emulator defines a `SafeTaggedCap` type: a sum type which represents either a
`CcxCap` with the tag bit set, or raw data with the tag bit unset. This
adds type safety, as the Rust compiler forces every usage of
`SafeTaggedCap` to consider both options, preventing raw data from being
interpreted as a capability by accident and enforcing Provenance.

## Emulating vectors

Vector instructions are executed by a Vector ISA module, which stores
all registers and other state. `VLEN` is hardcoded as 128-bits, chosen
because it's the largest integer primitive provided by Rust that's large
enough to hold a capability. `ELEN` is also 128-bits, which isn't
supported by the specification, but is required for
capabilities-in-vectors.

To support both CHERI and non-CHERI execution pointers are separated
into an address and a *provenance*[^28]. The vector unit retrieves an
address + provenance pair from the base register, generates a stream of
addresses to access, then rejoins each address with the provenance to
access memory. When using capabilities, provenance is defined in terms
of the base register e.g. "the provenance is provided by capability
register X", or defined by the DDC in integer mode. On non-CHERI
platforms the vector unit doesn't check provenance.

The initial motivation for this project was investigating the impact of
capability checks on performance. Rather than check each element's
access individually, we determine a set of "fast-path" checks which
count as checks for multiple elements at once.

## Fast-path calculations
A fast-path check can be performed over various sets of elements. The
emulator chooses to perform a single fast-path check for each vector
access, calculating the tight bounds before starting the actual access,
but in hardware this may introduce prohibitive latency. This section
describes the general principles surrounding fast-paths for CHERI-RVV,
notes the areas where whole-access fast-paths are difficult to
calculate, and describes possible approaches for hardware.

### Possible fast-path outcomes

In some cases, a failed address range check may not mean the access
fails. The obvious case is fault-only-first loads, where capability
exceptions may be handled without triggering a trap. Implementations may
also choose to calculate wider bounds than accessed for the sake of
simplicity, or even forego a fast-path check altogether. Thus, a
fast-path check can have four outcomes depending on the circumstances.

- Success - All accesses will succeed
- Failure - At least one access *will* raise an exception
- Likely-Failure *or* Unchecked - At least one access *may* raise an exception

A Success means no per-access capability checks are required.
Likely-Failure and Unchecked results mean each access must be checked,
to see if any of them actually raise an exception. Unfortunately,
accesses still need to be checked under Failure, because both precise
and imprecise traps need to report the offending element in
`vstart`.
Because all archetypes may have Failure or Likely-Failure outcomes,
and thus require a fallback slow-path which checks elements individually,
computing the fast-path can only be worthwhile if Success is the common case.

### *m*-element known-range fast-paths

A hardware implementation of a vector unit may be able to issue *m*
requests within a set range in parallel. For example, elements in the
same cache line may be accessible all at once. In these cases, checking
elements individually would either require *m* parallel bounds checks,
*m* checks' worth of latency, or something in-between. In this
subsection we consider a fast-path check for *m* elements for unit and strided accesses.
Indexed addressing has very little opportunity for fast-path checking, which is discussed in the full dissertation.

We consider two approaches for these accesses.
First, one could amortize the checking logic cost over multiple sets of
*m* elements by operating in terms of cache lines. Iterating through all
accessed cache lines, and then iterating over the elements inside,
allows the fast-path to hardcode the bounds width and do one check for
multiple cycles of work (if cache lines contain more than *m* elements).
Cache-line-aligned allocations benefit here, as all fast-path checks
will be in-bounds i.e. Successful, but misaligned data is guaranteed to
create at least one Likely-Failure outcome per access (requiring a
slow-path check). Calculating tight bounds for the *m* accessed elements
per cycle could address this.

Another approach is to simply calculate the bounds occupied by *m* elements,
which is simple for unit and strided accesses.
The minimum and maximum can then be picked easily to generate
tight bounds. An *m*-way multiplexer is still required for taking the
minimum and maximum, because `evl` and `vstart` may not be *m*-aligned.
If *m* is small, this also neatly extends to handle masked/inactive
elements. This may use less logic overall than *m* parallel bounds
checks, depending on the hardware platform[^32], but it definitely uses
more logic than the cache-line approach. Clearly, there's a trade-off to
be made.

## The Hypothesis

*The capability bounds checks for vector elements within a known range (e.g. a cache line) can be performed in a single check, amortizing the cost.*

This is true for Successful accesses. Because the RVV
spec requires that the faulting element is *always*
recorded[@specification-RVV-v1.0 Section 17], a Failure due to a
capability violation requires elements to be checked individually.

There are fast-path checks that consume less logic than *m*
parallel checks for unit and strided accesses. Even though a slow-path is
always necessary, it can be implemented in a slow way (e.g. doing one
check per cycle) to save on logic. Particularly if other parts of the
system rely on constraining the addresses accessed in each cycle, a
fast-path check can take advantage of those constraints.

# The CHERI-RVV software stack

This chapter, being less relevant to RISE/hardware security, has been greatly condensed.

As part of the project, we considered how adding CHERI to RVV would affect the software stack.
We tested our hypotheses by adding CHERI-RVV to Clang, which is the current focus for CHERI and RVV compiler development.
Clang supports three methods of vectorization:

1) Auto-vectorization, where the compiler converts scalar code to vector code
2) Vector intrinsics, where the programmer writes vector code and the compiler handles low-level details e.g. register allocation
3) Inline assembly, where the programmer directly describes the assembly instructions to execute.

## Our changes to CHERI-Clang
The first step was to fix up the pre-existing RVV definition in Clang to use capability registers for the base address.
This meant CHERI-RVV assembly code could be compiled, as long as it explicitly referenced capability registers.
Unfortunately, non-CHERI inline assembly could not be automatically compiled under this method.

We investigated updating vector intrinsics to support CHERI, but found the code defining the intrinsics was more complicated than for assembly.
We believe it is possible to update the intrinsics, but it requires significant engineering work.

Clang currently supports intrinsics and inline assembly for RVV, but not auto-vectorization yet.
This just requires engineering work - Arm SVE, a similar model, has great auto-vectorization.

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


# Capabilities-in-vectors

Implementing `memcpy` correctly for CHERI systems requires copying the
tag bits as well as the data, which means the vector registers must store the tag bits and thus store valid capabilities.
`memcpy` is frequently vectorized, so it's vital that CHERI-RVV can
implement it correctly. Manipulating capabilities-in-vectors could also
accelerate CHERI-specific processes, such as revoking capabilities for
freed memory[@xiaCHERIvokeCharacterisingPointer2019].

## Extending the emulator

We defined three goals for capabilities-in-vectors:

1) Vector registers should be able to hold capabilities.
2) At least one vector memory operation should be able to load/store capabilities from vectors.
    -   Because `memcpy` should copy both integer and capability data,
        vector memory operations should be able to handle both together.
3) Vector instructions should be able to manipulate capabilities.
    -   Clearing tag bits counts as manipulation.

First, we considered the impact on the theoretical vector model. We
decided that any operation with elements smaller than `CLEN` cannot
output valid capabilities under any circumstances[^44], meaning a new
element width equal to `CLEN` must be introduced. We set
`ELEN = VLEN = CLEN = 128`[^45] for our vector unit.

Two new memory access instructions were created to take advantage of
this new element width. Similar to CHERI-RISC-V's `LC/SC` instructions, we
implemented 128-bit unit-stride vector loads and stores, which took over
officially-reserved encodings for 128-bit accesses.
We have not tested other types of access, but expect them to be
noncontroversial.
<!-- Indexed accesses require extra scrutiny, as they
may be expected to use 128-bit offsets on 64-bit systems. -->

The next step was to add capability support to the vector register file.
Our approach to capabilities-in-vectors is similar in concept to CHERI-RISC-V's
Merged scalar register file, in that the same bits of a
register can be accessed in two contexts: an integer context, zeroing
the tag, or a capability context which maintains the current tag. The
only instructions which can access data in a capability context are 128-bit memory accesses[^47].
All other instructions
read out untagged integer data and clear tags when writing data.

A new CHERI-specific vector register file was created, where each
register is a `SafeTaggedCap` i.e. either zero-tagged integer data
or a valid tagged capability. This makes it much harder to accidentally
violate Provenance, and reuses the code path (and related security
properties) for accessing capabilities in memory. Just like scalar
accesses, vectorized capability accesses are atomic and 128-bit aligned.

## The Hypothesis

*It is possible for a vector architecture to load, store, and manipulate capabilities in vector registers without violating CHERI security principles.*

We considered this from three perspectives, checking they each fulfil Provenance, Monotonicity, and Integrity.

### Holding capabilities in vector registers
As long as `VLEN = CLEN`, and a tag bit is stored alongside each one, a single vector register can hold a capability and differentiate it from integer data.
One could also hold multiple capabilities in a register if `VLEN` was an integer multiple of `CLEN`, but this was not tested.
We decided that only `CLEN`-width operations could produce capabilities, thus we had to ensure `ELEN = CLEN`.
Our implementation sets `VLEN = ELEN = CLEN = 128bits`.

To ensure Provenance and Monotonicity were upheld, we decided that the tag bit for a register would only be set when loading a valid capability from memory, and cleared in all other circumstances.
Integrity is not affected by how a capability is stored.

### Moving capabilities between vector registers and memory

Memory access instructions must follow the same rules as scalar capability accesses.
To maintain Provenance they must be `CLEN`-aligned, or at least only load
valid capabilities from aligned addresses, because tag bits only apply
to `CLEN`-aligned regions; and they must be atomic[@TR-951 Section 11.3].

This atomicity requirement applies to the individual element accesses within each vector access too.
If multiple elements within a vector access try to write to the same 128-bit region non-atomically, it could result in a corrupted/malformed/forged capability.

Monotonicity is not affected by simply loading/storing capabilities from memory.
Integrity requires that the accesses themselves are checked against a valid base capability, just like normal scalar and vector accesses.

### Manipulating capabilities in vector registers

The emulator limits all manipulation to clearing the tag bit, achieved
by writing data to the register in an integer context. 
This preserves Provenance and Monotonicity, because it's impossible to create or change capabilities, and doesn't affect Integrity.

In theory it's possible to do more complex transformations, but there aren't many scalar transformations which would benefit from vectorization.
If more transformations are added they
should be considered carefully, rather than creating vector equivalents
for all scalar manipulations. For example, revocation as described
in [@xiaCHERIvokeCharacterisingPointer2019] may benefit from a vector
equivalent to `CLoadTags`.


# Conclusion

This project demonstrated the viability of integrating CHERI with
scalable vector models by producing an example CHERI-RVV implementation.
This required both research effort in studying the related
specifications and a substantial implementation effort. We produced four
software artifacts: a Rust wrapper for the `cheri-compressed-cap` C
library (900 lines of code), a RISC-V emulator supporting multiple
architecture extensions (5,300 LoC), a fork of CHERI-Clang supporting
CHERI-RVV (400 changed LoC), and test programs for the emulator (3,000
LoC). Developing these artifacts provided enough information to
make conclusions for the initial hypotheses.

Based on the hypotheses examined in this summary and the original dissertation,
scalable vector models can be adapted to CHERI without
significant loss of functionality. Most of the hypotheses are general
enough to cover other scalable models, e.g. Arm SVE, but any differences
from RVV's model will require careful examination. Given the importance
of vector processing to modern computing, and thus its importance to
CHERI, we hope that this research paves the way for future
vector-enabled CHERI processors.

## Testing
Alongside the theoretical hypotheses, the emulator was tested with a comprehensive set of self-checking test programs.
RVV memory access correctness was tested by implementing functions that mimicked `memcpy` on integer data, under various scenarios for different instructions and addressing modes.
These included unit, strided, and indexed addressing modes, "segmented" and "masked" accesses (explained in the dissertation), and fault-only-first loads.
Fault-only-first loads were also tested on the boundary of mapped memory, showing they correctly swallowed memory access exceptions.

Capabilities-in-vectors had a dedicated testbench, which would attempt to `memcpy` an array of structures holding pointers to other structures.
This had two variants. The first simply copied the data, which worked on CHERI and non-CHERI. The other would add 0 to the data after loading it from memory, which invalidates any capabilities before copying it to the output. That only worked on CHERI, showing that capability manipulation was possible.

## Future work

The stated purpose of this project was to enable future implementations
of CHERI-RVV and CHERI Arm SVE. We've shown this is feasible, and we
believe our research is enough to create an initial CHERI-RVV
specification, but both could benefit from more research on
capabilities-in-vectors.

All architectures may benefit from more advanced vectorized capability
manipulation. Because these processes are still evolving, it may be wise
to standardize the first version of CHERI-RVV based on this dissertation
and only add new instructions as required. Once created, the standard
can be implemented in CHERI-Clang and added to existing
CHERI-RISC-V processors.

More theoretically, other vector models could benefit from
*dereferencing* capabilities-in-vectors. Arm SVE has addressing modes
that directly use vector elements as memory references, as do its
predecessors and contemporaries. A draft specification of CHERI-x86 is
in the works[@TR-951 Chapter 6], and existing x86 vector models like AVX
have similar features. This may prove impractical, but this could be
mitigated by e.g. replacing these addressing modes with variants of
RVV's "indexed" mode. Once this problem is solved, CHERI will be able to
match the memory access abilities of any vector ISA it needs to, making
it that much easier for industry to adopt CHERI in the long term.

[^28]: The "original allocation the pointer is derived
    from"[@memarianExploringSemanticsPointer2019], or in CHERI terms the
    bounds within which the pointer is valid.

[^32]: e.g. on FPGAs multiplexers can be relatively cheap.

[^44]: This avoids edge cases with masking, where one part of a
    capability could be modified while the other parts are left alone.

[^45]: The tag bits are implicitly instead of explicitly included here
    because `VLEN,ELEN` must be powers of two.

[^47]: The encoding mode does not affect
    register usage: when using the Integer encoding mode, instructions
    can still access the vector registers in a capability context. This
    is just like how scalar capability registers are still accessible in
    Integer encoding mode.

[^48]: This doesn't include automatically generated code.


[^50]: <https://www.cl.cam.ac.uk/research/security/ctsrd/cheri/cheri-risc-v.html>
