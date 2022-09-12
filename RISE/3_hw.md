# Hardware emulation investigation

In order to experiment with integrating CHERI and RVV, we implemented a
RISC-V emulator in the Rust programming language named `riscv-v-lite`.
The emulator supports the Multiply, CSR, Vector, and CHERI extensions,
and was also used as the base for
capabilities-in-vectors research.

## Developing the emulator

The emulator is very modular, such that each ISA extension is defined as 
a separate module which can easily be plugged into different processor implementations.
Each ISA module uses a "connector" structure, containing e.g. virtual references to register files and memory, 
which allows different processors to reuse ISA modules despite using different register file/memory implementations.
<!-- Each architecture is simulated in the same way. A `Processor` struct
holds the register file and memory, and a separate `ProcessorModules`
struct holds the ISA modules the architecture can use. Each ISA module
uses a "connector" struct to manipulate data in the `Processor`. For
example, the RV64 Integer ISA's connector contains the current PC, a
virtual reference to a register file, and a virtual reference to memory.
This allows different `Processor` structs (e.g. a normal RV64 and a
CHERI-enabled RV64) to reuse the same ISA modules despite using
different register file implementations. -->

Each processor implements a single stage pipeline. Instructions are
fetched, decoded with a common decoder function[^19], and executed. The
processor asks each ISA module in turn if it wants to handle the
instruction, and uses the first module to say yes. If the ISA module
returns a new PC value it is immediately applied, otherwise it is
automatically incremented. This structure easily represents basic RISC-V
architectures, and can scale up to support many different new modules.

### Emulating CHERI

Manipulating CHERI capabilities securely and correctly is a must for any
CHERI-enabled emulator. Capability encoding logic is not trivial by any
means, so the `cheri-compressed-cap` C library was re-used rather than
implementing it from scratch. There were a few issues with implementing Rust/C interoperation, which are addressed in the dissertation.

<!-- #### `rust-cheri-compressed-cap`

`cheri-compressed-cap` provides two versions of the library by default,
for 64-bit and 128-bit capabilities, which are generated from a common
source through extensive use of the C preprocessor. Each variant defines a
set of preprocessor macros (e.g. the widths of various fields) before
including two common header files `cheri_compressed_cap_macros.h` and
`cheri_compressed_cap_common.h` which defines the relevant
structures and functions. For example, a
function `compute_base_top` is generated twice, once as
`cc64_decompress_mem` returning `cc64_cap_t` and another time as
`cc128_decompress_mem` returning `cc128_cap_t`. 
Elegantly capturing both
sets was the main challenge for the Rust wrapper.

One of Rust's core language elements is the Trait - a set of functions
and "associated types" that can be *implemented* for any type. This
gives a simple way to define a consistent interface: define a trait
`CompressedCapability` with all of the functions from
`cheri_compressed_cap_common.h`, and implement it for two empty
structures `Cc64` and `Cc128`. In the future, this would allow the
Morello versions of capabilities to be added easily. A struct
`CcxCap<T>` is also defined which uses specific types for addresses and
lengths pulled from a `CompressedCapability`. For example, the 64-bit
capability structure holds a 32-bit address, and the 128-bit capability
a 64-bit address.

128-bit capabilities can cover a 64-bit address range, and thus can have
a length of $2^{64}$. Storing this length requires 65-bits, so all math
in `cheri_compressed_cap_common.h` uses 128-bit length values. C doesn't
have any standardized 128-bit types, but GCC and LLVM provide so-called
"extension types" which are used instead. Although the x86-64 ABI does
specify how 128-bit values should be stored and passed as
arguments[@specification-x86-psABI-v1.0], these rules do not seem
consistently applied[^20]. This causes great pain to anyone who needs to
pass them across a language boundary.

Rust explicitly warns against passing 128-bit values across language
boundaries, and the Clang User's Manual even states that passing `i128`
by value is incompatible with the Microsoft x64 calling convention[^21].
This could be resolved through careful examination: for example, on LLVM
128-bit values are passed to functions in two 64-bit registers[^22],
which could be replicated in Rust by passing two 64-bit values. For
convenience, we instead rely on the Rust and Clang compilers using
compatible LLVM versions and having identical 128-bit semantics.

The CHERI-RISC-V documentation contains formal specifications of all
new CHERI instructions.
These definitions are used in the CHERI-RISC-V formal
model[^24], and require a few helper functions (see [@TR-951
Chapter 8.2]). The `rust-cheri-compressed-cap` library also defines
those helper functions, so the formal definitions can be ported directly into the emulator.

The above work is available online[^25], and includes documentation for
all C functions[^26] (which were not previously documented). -->

#### Integrating into the emulator

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

<!-- The capability model presented by the C/Rust library has one
flaw.
Each `CcxCap` instance
stores capability metadata (e.g. the uncompressed bounds) as well as the
compressed encoding. This makes it potentially error-prone to represent
untagged integer data with `CcxCap`, as the compressed and uncompressed
data may not be kept in sync and cause inconsistencies later down the
line. `CcxCap` also provides a simple interface to set the tag bit,
without checking whether that is valid. The emulator introduced the
`SafeTaggedCap` to resolve this: a sum type which represents either a
`CcxCap` with the tag bit set, or raw data with the tag bit unset. This
adds type safety, as the Rust compiler forces every usage of
`SafeTaggedCap` to consider both options, preventing raw data from being
interpreted as a capability by accident and enforcing Provenance. -->

### Emulating vectors

Vector instructions are executed by a Vector ISA module, which stores
all registers and other state. `VLEN` is hardcoded as 128-bits, chosen
because it's the largest integer primitive provided by Rust that's large
enough to hold a capability. `ELEN` is also 128-bits, which isn't
supported by the specification, but is required for
capabilities-in-vectors. Scaling `VLEN` and `ELEN` higher would
require new numeric types that were more than
128-bits long.

To support both CHERI and non-CHERI execution pointers are separated
into an address and a *provenance*[^28]. The vector unit retrieves an
address + provenance pair from the base register, generates a stream of
addresses to access, then rejoins each address with the provenance to
access memory. When using capabilities, provenance is defined in terms
of the base register e.g. "the provenance is provided by capability
register X", or defined by the DDC in integer mode[^29]. On non-CHERI
platforms the vector unit doesn't check provenance.

<!-- Arithmetic and configuration instructions are generally simple to
implement, so aren't covered here. The emulator splits vector memory
accesses into three phases: decoding, checking, and execution. A
separate decoding stage may technically not be necessary in hardware
(especially the parts checking for errors and reserved instruction
encodings, which a hardware platform could simply assume won't happen),
but it allows each memory access instruction to be classified into one
of the five archetypes outlined in
[\[chap:bg:sec:rvvmemory\]](#chap:bg:sec:rvvmemory){reference-type="ref"
reference="chap:bg:sec:rvvmemory"}. It is then easy to define the
checking and execution phases separately for each archetype, as the
hardware would need to do. -->

#### Fast-path checking phase {#chap:hardware:subsec:checking}

TODO the emulator describes full-access checking, but we removed that part.
TODO greatly cut this down

The initial motivation for this project was investigating the impact of
capability checks on performance. Rather than check each element's
access individually, we determine a set of "fast-path" checks which
check multiple elements at once. 
The emulator computes the "tight bounds" for each access, i.e. the exact
range of bytes that will be accessed, and doing a single capability
check with that bounds.
The full thesis describes calculating "tight bounds" for each access type, and ways that
architectural complexity can be traded off to calculate *wider* bounds.

If the tight bounds don't pass the capability check, the emulator raises
an imprecise trap and stops immediately. In the case of fault-only-first
loads, where synchronous exceptions (e.g. capability checks) are
explicitly handled, the access continues regardless and elements are
checked individually. This is also the expected behaviour if a
capability check for *wider* bounds fails. The emulator deviates from
the spec in that `vstart` is *not* set when the tight bounds check
fails, as it does not know exactly which element would have triggered
the exception. A fully compliant machine must
check each access to find `vstart` in these cases.

<!-- #### Execution phase {#chap:hardware:subsec:execution}

If the fast-path check deems it appropriate, the emulator continues
execution of the instruction in two phases. First, the mapping of vector
elements to accessed memory addresses is found. The code for this step
is independent of the access direction, and an effective description of
how each type of access works.  The previously computed tight
bounds are sanity-checked against these accesses, and the accesses are
actually performed. -->

#### Integer vs. Capability encoding mode

CHERI-RISC-V defines two
execution modes that the program can switch between. In Integer mode
"address operands to existing RISC-V load and store opcodes contain
integer addresses" which are implicitly dereferenced relative to the
default data capability, and in Capability mode those opcodes are
modified to use capability operands.

Integer mode was included in the interests of maintaining compatibility
with legacy code that hasn't been adapted to capabilities. As similar
vector code may also exist, CHERI-RVV treats vector memory access
instructions as "existing RISC-V load and store opcodes" and requires
that they respect integer/capability mode.

We do not define new mode-agnostic instructions, which means vector programs cannot mix
capability and integer addressing without changing encoding modes. This
may make incremental adoption more difficult, and in the future we
may examine existing vanilla RVV programs to determine if it's worth
adding those instructions.

## Fast-path calculations

A fast-path check can be performed over various sets of elements. The
emulator chooses to perform a single fast-path check for each vector
access, calculating the tight bounds before starting the actual access,
but in hardware this may introduce prohibitive latency.
Here, we explore other possible approaches for hardware.
 <!-- This section
describes the general principles surrounding fast-paths for CHERI-RVV,
notes the areas where whole-access fast-paths are difficult to
calculate, and describes possible approaches for hardware. -->

### Possible fast-path outcomes

In some cases, a failed address range check may not mean the access
fails. The obvious case is fault-only-first loads, where capability
exceptions may be handled without triggering a trap. Implementations may
also choose to calculate wider bounds than accessed for the sake of
simplicity, or even forego a fast-path check altogether. Thus, a
fast-path check can have four outcomes depending on the circumstances.

A Success means no per-access capability checks are required.
Likely-Failure and Unchecked results mean each access must be checked,
to see if any of them actually raise an exception. Unfortunately,
accesses still need to be checked under Failure, because both precise
and imprecise traps need to report the offending element in
`vstart`[^30].

Because all archetypes may have Failure or Likely-Failure outcomes,
hardware must provide a fallback slow-path for each archetype which
checks/performs each access in turn. In theory, a CHERI-RVV
specification could relax the `vstart` requirement for imprecise traps,
and state that all capability exceptions trigger imprecise traps. In
this case, only archetypes that produce Likely-Failure outcomes need the
slow-path. However, it is likely that for complexity reasons all masked
accesses will use wide ranges, thus producing Likely-Failure outcomes
and requiring slow-paths for all archetypes anyway. Because the
Likely-Failure and Failure cases require the slow-path anyway, computing
the fast-path can only be worthwhile if Success is the common case.

::: subtable
  Type             Meaning
  ---------------- -------------------------
  Success          All accesses will succeed
  Failure          At least one access *will*
                   raise an exception
  Likely-Failure   At least one access *may*
  *or* Unchecked   raise an exception
:::

### m-element known-range fast-paths

A hardware implementation of a vector unit may be able to issue $m$
requests within a set range in parallel. For example, elements in the
same cache line may be accessible all at once. In these cases, checking
elements individually would either require $m$ parallel bounds checks,
$m$ checks' worth of latency, or something in-between. In this
subsection we consider a fast-path check for $m$ elements.

Capability checks can be split into two steps: address-agnostic (e.g.
permissions checks, bounds decoding) and address-dependent (e.g. bounds
checks). Address-agnostic steps can be performed before any bounds
checking, and should add minimal start-up latency (bounds decoding must
complete before the checks anyway, and permission checks can be
performed in parallel). Once the bounds are decoded the actual checks
consist of minimal logic[^31], so a fast-path must have very minimal
logic to compete.

We first consider unit and strided accesses, and note two approaches.
First, one could amortize the checking logic cost over multiple sets of
$m$ elements by operating in terms of cache lines. Iterating through all
accessed cache lines, and then iterating over the elements inside,
allows the fast-path to hardcode the bounds width and do one check for
multiple cycles of work (if cache lines contain more than $m$ elements).
Cache-line-aligned allocations benefit here, as all fast-path checks
will be in-bounds i.e. Successful, but misaligned data is guaranteed to
create at least one Likely-Failure outcome per access (requiring a
slow-path check). Calculating tight bounds for the $m$ accessed elements
per cycle could address this.

For unit and strided accesses, the bounds occupied by $m$ elements is
straightforward to calculate, as the addresses can be generated in
order. The minimum and maximum can then be picked easily to generate
tight bounds. An $m$-way multiplexer is still required for taking the
minimum and maximum, because `evl` and `vstart` may not be $m$-aligned.
If $m$ is small, this also neatly extends to handle masked/inactive
elements. This may use less logic overall than $m$ parallel bounds
checks, depending on the hardware platform[^32], but it definitely uses
more logic than the cache-line approach. Clearly, there's a trade-off to
be made.

Indexed fast-paths are more complicated, because the addresses are
unsorted. The two approaches above have different advantages for indexed
accesses. If the offsets/indices are spatially close, just not sorted,
cache line checks may efficiently cover all elements. An implementation
could potentially cache the results, and refer back for each access,
instead of trying to iterate through cache lines in order. Otherwise a
$m$-way parallel reduction could be performed to find the min and max,
but that would likely take up more logic than $m$ comparisons. This may
be a moot point depending on the cache implementation though - if the
$m$ accesses per cycle must be in the same cache line, and the addresses
are spread out, you're limited to one access and therefore one check per
cycle regardless.

In summary, there are fast-path checks that consume less logic than $m$
parallel checks in certain circumstances. Even though a slow-path is
always necessary, it can be implemented in a slow way (e.g. doing one
check per cycle) to save on logic. Particularly if other parts of the
system rely on constraining the addresses accessed in each cycle, a
fast-path check can take advantage of those constraints.

## Testing and evaluation

We tested the emulator using a set of test programs described in
later sections, and found that all
instructions were implemented correctly.

### [\[hyp:hw_cap_as_vec_mem_ref\]](#hyp:hw_cap_as_vec_mem_ref){reference-type="ref" reference="hyp:hw_cap_as_vec_mem_ref"} - Feasibility {#hyphw_cap_as_vec_mem_ref---feasibility .unnumbered}

This is true. All vector memory access instructions index the scalar
general-purpose register file to read the base address, and CHERI-RVV
implementations can simply use this index for the scalar capability
register file instead. This can be considered through the lens of adding
CHERI to any RISC-V processor, and in particular adding Capability mode
to adjust the behaviour of legacy instructions. RVV instructions can
have their behaviour adjusted in exactly the same way as the scalar
memory access instructions.

That approach then scales to other base architectures that have CHERI
variants. For example, Morello's scalar Arm instructions were modified
to use CHERI capabilities as memory
references[@armltdMorelloArchitectureReference2021 Section 1.3], so one
may simply try to apply those modifications to e.g. Arm SVE
instructions. This only works where Arm SVE accesses memory references
in the same way as scalar Arm instructions did i.e. through a scalar
register file.

Arm SVE has some addressing modes like `u64base`, which uses a vector as
a set of 64-bit integer addresses[@armltdArmCompilerScalable2019]. This
has more complications, because simply dereferencing integer addresses
without a capability is insecure. Would a CHERI version convert this
mode to use capabilities-in-vectors, breaking compatibility with legacy
code that expects integer references? Another option would be to only
enable this instruction in Integer mode, and dereference relative to the
DDC. It's possible to port this to CHERI, but requires further
investigation and thought.

### [\[hyp:hw_cap_bounds_checks_amortized\]](#hyp:hw_cap_bounds_checks_amortized){reference-type="ref" reference="hyp:hw_cap_bounds_checks_amortized"} - Fast-path checks {#hyphw_cap_bounds_checks_amortized---fast-path-checks .unnumbered}

This is also true, at least for Successful accesses. Because the RVV
spec requires that the faulting element is *always*
recorded[@specification-RVV-v1.0 Section 17], a Failure due to a
capability violation requires elements to be checked individually.
CHERI-RVV could change the specification so the faulting element doesn't
need to be calculated, which would make Failures faster, but that still
requires Likely-Failures to take the slow-path.

There are many ways to combine the checks for a set of vector elements,
which can take advantage of the range constraints. For example, a
unit-stride access could a hierarchy of checks: cache-line checks until
a Likely-Failure, then tight $m$-element bounds until a Likely-Failure,
then the slow-path. However, the choice of fast-path checks is
inherently a trade-off between latency, area, energy usage, and more.
Picking the right one for the job is highly dependent on the existing
implementation, and indeed an implementation may decide that parallel
per-element checks is better than a fast-path.


