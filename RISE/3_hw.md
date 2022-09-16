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

