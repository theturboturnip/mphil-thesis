---
bibliography:
- thesis.bib
---

# Introduction[]{#wc:start label="wc:start"}[]{#chap:intro label="chap:intro"}

Since 2010, the Cambridge Computer Lab (in association with SRI) has
been developing the CHERI[^1] architecture extension, which improves the
security of any given architecture by checking all memory accesses in
hardware. The core impact of CHERI, on a hardware level, is that memory
can no longer be accessed directly through raw addresses, but must pass
through a *capability*[@TR-941]. Capabilities are unforgeable tokens
that grant fine-grained access to ranges of memory. Instead of
generating them from scratch, capabilities must be *derived* from
another capability with greater permissions. For example, a capability
giving read-write access to an array of structures can be used to create
a sub-capability granting read-only access to a single element. This
vastly reduces the scope of security violations through spatial errors
(e.g. buffer overflows[@szekeresSoKEternalWar2013]), and creates
interesting opportunities for software
compartmentalization[@watsonCHERIHybridCapabilitySystem2015].

Industry leaders have recognized the value CHERI provides. Arm Inc have
manufactured the Morello System-on-Chip, based on their Neoverse N1 CPU,
which incorporates CHERI capabilities into the Armv8.2 ISA. While this
represents a great step forward, there are still elements on the SoC
that haven't fully embraced CHERI (e.g. the GPU), and architecture
extensions that haven't been investigated in the context of CHERI. One
such example is Arm's Scalable Vector Extension (introduced in Armv8.2
but not included in Neoverse N1), which is designed to remain in use
well into the future[@stephensARMScalableVector2017]. Supporting this
and other scalable vector ISAs in CHERI is essential to CHERI's
long-term relevance.

In the context of modern computer architecture, vector processing is the
practice of dividing a large hardware register into a *vector* of
multiple *elements* and executing the same operation on each element in
a single instruction[^2]. This data-level parallelism can drastically
increase throughput, particularly for arithmetic-heavy programs.
However, before computing arithmetic, the vectors must be populated with
data.

## Motivation

Modern vector implementations all provide vector load/store instructions
to access a whole vector's worth of memory. These range from simple
contiguous accesses (where all elements are next to each other), to
complex indexed accesses (where each element loads from a different
location based on another vector). They can also have per-element
semantics, e.g. "elements must be loaded in order, so if one element
fails the preceding elements are still valid"[@specification-RVV-v1.0
Section 7.7]. If CHERI CPUs want to benefit from vector processing's
increased performance and throughput, they must support those
instructions at some level. But adding CHERI's bounds-checking to the
mix may affect these semantics, and could impact performance (e.g.
checking each element's access in turn may be slow).

[]{#vectorized_memcpy label="vectorized_memcpy"}Vector memory access
performance is more critical than one may initially assume, because
vectors are used for more than just computation. A prime example is
`memcpy`: for `x86_64`, `glibc` includes multiple versions of the
function[^3] taking advantage of vector platforms, then selects one to
use at runtime[^4]. These implementations are written in assembly and
heavily optimized. If the memory accesses are hitting the cache, a few
extra cycles of bounds-checking for each access could actually make a
noticeable difference.

`memcpy` also raises the important question of how the vector model
interacts with capabilities. In non-CHERI processors, `memcpy` will copy
pointers around in memory without fuss. For a CHERI-enabled vector
processor to support this, it would need to be able to load/store
capabilities from vectors without violating any security guarantees.
This may require more constraints --- for example, each vector register
likely needs to be at least as large as a single capability.

To explore this topic, we chose to focus on the RISC-V Vector
extension[@specification-RVV-v1.0] (shortened to RVV throughout). As of
November 2021 this has been ratified by RISC-V International[^5], and
will be RISC-V's standard vector instruction set moving forward. This
has two key benefits. Studying RVV will allow reference "CHERI-RVV"
implementations to be built for the CHERI project's open-source RISC-V
cores[^6], which don't currently support vector processing. Secondly,
RVV is a *scalable* vector model, where the length of each vector is
implementation-dependent. This has more potential roadblocks than a
fixed-length vector model, and investigating them here will make life
easier if Arm wish to integrate their Scalable Vector Extension with
CHERI later down the road.

## Hypotheses and Aims

The goal of this project is to investigate the impact of, and the
roadblocks for, integrating a scalable vector architecture with CHERI's
memory protection system. In particular, we focus on integrating RVV
with the CHERI-RISC-V ISA, with the aim of enabling a future CHERI-RVV
implementation and informing the approach for a future CHERI Arm SVE
implementation.

The investigation was carried out by designing and testing a CHERI-RVV
emulator written in Rust, but that is only a single implementation. To
show that RVV can be integrated with CHERI-RISC-V for a wide range of
processors, we use information gathered from the emulator to check nine
hypotheses ([1.1](#tab:hypotheses){reference-type="ref"
reference="tab:hypotheses"}).
[\[hyp:hw_cap_as_vec_mem_ref,hyp:hw_cap_bounds_checks_amortized\]](#hyp:hw_cap_as_vec_mem_ref,hyp:hw_cap_bounds_checks_amortized){reference-type="ref"
reference="hyp:hw_cap_as_vec_mem_ref,hyp:hw_cap_bounds_checks_amortized"}
consider basic feasibility and potential hardware performance issues.
[\[hyp:sw_vec_legacy,hyp:sw_pure_compat,hyp:sw_stack_vectors,hyp:sw_multiproc\]](#hyp:sw_vec_legacy,hyp:sw_pure_compat,hyp:sw_stack_vectors,hyp:sw_multiproc){reference-type="ref"
reference="hyp:sw_vec_legacy,hyp:sw_pure_compat,hyp:sw_stack_vectors,hyp:sw_multiproc"}
ensure that vector software is compatible with potential CHERI-RVV
software stacks.
[\[hyp:cap_in_vec_storage,hyp:cap_in_vec_load_store,hyp:cap_in_vec_manip\]](#hyp:cap_in_vec_storage,hyp:cap_in_vec_load_store,hyp:cap_in_vec_manip){reference-type="ref"
reference="hyp:cap_in_vec_storage,hyp:cap_in_vec_load_store,hyp:cap_in_vec_manip"}
considers capabilities-in-vectors: the conditions under which vector
registers can hold capabilities, and vectorized instructions can
manipulate them.

This document also examines current practical realities, such as the
limitations of the current CHERI-RVV software stack, and explains how to
compile/execute CHERI-RVV code on bare-metal platforms. The RVV and
CHERI-RISC-V specifications are succinctly explained in
[\[chap:background\]](#chap:background){reference-type="ref"
reference="chap:background"}.

::: {#tab:hypotheses}
  --------------------------------------------------------------------------------------------------------------------------
  *Hardware Hypotheses ---                                   
  [\[chap:hardware\]](#chap:hardware){reference-type="ref"   
  reference="chap:hardware"}*                                
  ---------------------------------------------------------- ---------------------------------------------------------------
  H- []{#hyp:hw_cap_as_vec_mem_ref                           It is possible to use CHERI capabilities as memory references
  label="hyp:hw_cap_as_vec_mem_ref"}                         in all vector instructions.

  H- []{#hyp:hw_cap_bounds_checks_amortized                  The capability bounds checks for vector elements within a known
  label="hyp:hw_cap_bounds_checks_amortized"}                range (e.g. a cache line) can be performed in a single check,
                                                             amortizing the cost.

  *Software Hypotheses ---                                   
  [\[chap:software\]](#chap:software){reference-type="ref"   
  reference="chap:software"}*                                

  H- []{#hyp:sw_vec_legacy label="hyp:sw_vec_legacy"}        Vector code can be compiled in legacy forms (with integer
                                                             addressing) and function correctly on CHERI with no source code
                                                             changes.

  H- []{#hyp:sw_pure_compat label="hyp:sw_pure_compat"}      Legacy vector code can be compiled into a pure-capability form
                                                             with no changes.

  H- []{#hyp:sw_stack_vectors label="hyp:sw_stack_vectors"}  Vector code that saves/restores variable-length vectors to/from
                                                             the stack can be compiled on CHERI-RVV with no source code
                                                             changes.

  H- []{#hyp:sw_multiproc label="hyp:sw_multiproc"}          CHERI-vector code can run correctly in multiprocessing systems,
                                                             where execution may be paused and resumed on interrupts or
                                                             context switches.

  *Capabilities-in-Vectors ---                               
  [\[chap:capinvec\]](#chap:capinvec){reference-type="ref"   
  reference="chap:capinvec"}*                                

  H- []{#hyp:cap_in_vec_storage                              It is possible for vector registers to hold capabilities to
  label="hyp:cap_in_vec_storage"}                            enable copying without violating CHERI security principles.

  H- []{#hyp:cap_in_vec_load_store                           It is possible for vector memory accesses to load and store
  label="hyp:cap_in_vec_load_store"}                         capabilities from vector registers without violating CHERI
                                                             security principles.

  H- []{#hyp:cap_in_vec_manip label="hyp:cap_in_vec_manip"}  It is possible for vector instructions to manipulate
                                                             capabilities in vector registers without violating CHERI
                                                             security principles.
  --------------------------------------------------------------------------------------------------------------------------

  : Project Hypotheses
:::

# Background[]{#chap:background label="chap:background"}

This chapter describes RISC-V
([2.1](#chap:bg:sec:riscv){reference-type="ref"
reference="chap:bg:sec:riscv"}), RVV (), and CHERI
([2.6](#chap:bg:sec:cheri){reference-type="ref"
reference="chap:bg:sec:cheri"}) to the detail required to understand the
rest of the dissertation. It summarizes the relevant sections of the
RISC-V unprivileged spec[@specification-RISCV-vol1-20191213], the RISC-V
"V" extension specification v1.0[@specification-RVV-v1.0 Sections 1--9,
17], the TR-951 CHERI ISAv8 technical report[@TR-951 Chapters 5, 8], and
the TR-949 technical report about C/C++ safety on CHERI[@TR-949
Section 4.4, Appendix C]. Both vectors and CHERI are described, because
this dissertation caters to those who may be familiar with one but not
the other.

## RISC-V {#chap:bg:sec:riscv}

RISC-V is an open family of ISAs which defines "base integer ISAs" (e.g.
all 64-bit RISC-V cores implement the RV64I base ISA) and extensions
(e.g. the "M" extension for integer multiplication). A base instruction
set combined with a set of extensions is known as a RISC-V ISA. Because
RISC-V is open, anyone can design, manufacture, and sell chips
implementing any RISC-V ISA.

Each RISC-V implementation has a set of constant parameters. The most
common example is `XLEN`, the length of an integer register in bits,
which is tied to the base integer ISA (e.g. 64-bit ISA implies
`XLEN=64`). Other constant parameters include `CLEN`, the length of a
capability in bits, defined by CHERI relative to `XLEN`; and `VLEN` and
`ELEN`, which are used by RVV and entirely implementation-defined.

The extensions of most relevance to this project are the "V" vector
extension (RVV, specified in [@specification-RVV-v1.0]) and the CHERI
extension (specified in [@TR-951]). RVV has recently been officially
ratified, and is the de facto vector extension for RISC-V. The following
sections summarize the vector extension, how it accesses memory, and
previous implementations in academia.

## A brief history of vector processing {#chap:bg:rvvstart}

Many vector implementations (Intel SSE/AVX, Arm's Advanced SIMD and
Neon) use fixed-length vectors - e.g. 128-bit vectors which a program
interprets as four 32-bit elements. As the industry's desire for
parallelism grew, new implementations had to be designed with longer
vectors of more elements. For example, Intel SSE/SSE2 (both 128-bit) was
succeeded by AVX (128 and 256-bit), then AVX2 (entirely 256-bit), then
AVX-512 (512-bit). Programs built for one extension, and hence designed
for a specific vector size, could not automatically take advantage of
longer vectors.

Scalable vectors address this by not specifying the vector length, and
instead calculating it on the fly. Instead of hardcoding "this loop
iteration uses a single vector of four 32-bit elements", the program has
to ask "how many 32-bit elements will this iteration use?". This gives
hardware designers more freedom, letting them select a suitable hardware
vector length for their power/timing targets, while guaranteeing
consistent execution of programs on arbitrarily-sized vectors. RVV uses
a scalable vector model.

## The RVV vector model {#chap:bg:sec:rvv:vector_model}

*Summarizes [@specification-RVV-v1.0 Sections 1-6, 17]*

RVV defines thirty-two vector registers, each of an
implementation-defined constant width `VLEN`. These registers can be
interpreted as *vectors* of *elements*. The program can configure the
size of elements, and the implementation defines a maximum width `ELEN`.
[\[fig:RVV_simple_widths\]](#fig:RVV_simple_widths){reference-type="ref"
reference="fig:RVV_simple_widths"} shows a simple example.

RVV also adds some state that defines how the vector registers are used
(see
[\[fig:RVV_added_state\]](#fig:RVV_added_state){reference-type="ref"
reference="fig:RVV_added_state"}). These are stored in RISC-V Control
and Status Registers (CSRs), which the program can read. `vtype`
([2.3.1](#chap:bg:subsec:vtype){reference-type="ref"
reference="chap:bg:subsec:vtype"}) defines how the vector registers are
split into elements. `vstart` and `vl`
([2.3.2](#chap:bg:subsec:vlvstart){reference-type="ref"
reference="chap:bg:subsec:vlvstart"}) divides the elements into three
disjoint subsets: *prestart*, the *body*, and the *tail*. Masked
accesses ([2.3.3](#chap:bg:subsec:rvvmasking){reference-type="ref"
reference="chap:bg:subsec:rvvmasking"}) further divide the *body* into
*active* and *inactive* elements. This section also describes the vector
exception model
([2.3.4](#chap:bg:subsec:vexceptions){reference-type="ref"
reference="chap:bg:subsec:vexceptions"}).

### `vtype` {#chap:bg:subsec:vtype}

The `vtype` CSR contains two key fields that describe how vector
instructions interpret the contents of vector registers. The first is
the Selected Element Width (`SEW`), which is self-explanatory. It can be
8, 16, 32, or 64. 128-bit elements are referenced a few times throughout
but haven't been formally specified (see [@specification-RVV-v1.0 p10,
p32]).

The second field is the Vector Register Group Multiplier (`LMUL`).
Vector instructions don't just operate over a single register, but over
a register *group* as defined by this field. For example, if `LMUL=8`
then each instruction would operate over 8 register's worth of elements.
These groups must use aligned register indices, so if `LMUL=4` all
vector register operands should be multiples of 4 e.g. `v0`, `v4`, `v8`
etc. In some implementations this may increase throughput, which by
itself is beneficial for applications.

However, the true utility of `LMUL` lies in widening/narrowing
operations (see
[\[fig:RVV_LMUL_widening\]](#fig:RVV_LMUL_widening){reference-type="ref"
reference="fig:RVV_LMUL_widening"}). For example, an 8-by-8-bit
multiplication can produce 16-bit results. Because the element size
doubles, the number of vector registers required to hold the same number
of elements also doubles. Doubling `LMUL` after such an operation allows
subsequent instructions to handle all the results at once. At the start
of such an operation, fractional `LMUL` (1/2, 1/4, or 1/8) can be used
to avoid subsequent results using too many registers.

`vtype` also encodes two flags: mask-agnostic and tail-agnostic. If
these are set, the implementation is *allowed* to overwrite any
masked-out or tail elements with all 1s.

Most vector instructions will interpret their operands using `vtype`,
but this is not always the case. Some instructions (such as memory
accesses) use different Effective Element Widths (`EEW`) and Effective
LMULs (`EMUL`) for their operands. In the case of memory accesses, the
`EEW` is encoded in the instruction bits and the `EMUL` is calculated to
keep the number of elements consistent. Another example is
widening/narrowing operations, which by definition have to interpret the
destination registers differently from the sources.

Programs update `vtype` through the `vsetvl` family of instructions.
These are designed for a "stripmining" paradigm, where each iteration of
a loop processes some elements until all elements are processed.
`vsetvl` instructions take a requested `vtype` and the number of
remaining elements to process (the Application Vector Length or `AVL`),
and return the number of elements that will be processed in this
iteration. This value is saved in a register for the program to use, and
also saved in the internal `vl` CSR.

### `vl` and `vstart` --- Prestart, body, tail {#chap:bg:subsec:vlvstart}

The first CSR is the Vector Length `vl`, which holds the number of
elements that could be updated from a vector instruction. The program
updates this value through fault-only-first loads
([2.5.2](#chap:bg:sec:rvv:fof){reference-type="ref"
reference="chap:bg:sec:rvv:fof"}) and more commonly `vsetvl`
instructions.

In the simple case, `vl` is equal to the total available elements (see
[\[fig:RVV_vl_full\]](#fig:RVV_vl_full){reference-type="ref"
reference="fig:RVV_vl_full"}). It can also be fewer (see
[\[fig:RVV_vl_short\]](#fig:RVV_vl_short){reference-type="ref"
reference="fig:RVV_vl_short"}), in which case vector instructions will
not write to elements in the "tail" (i.e. elements past `vl`). This
eliminates the need for a 'cleanup loop' common in fixed-length vector
programs.

In a similar vein, `vstart` specifies "the index of the first element to
be executed by a vector instruction". Elements before `vstart` are known
as the *prestart* and are not touched by executed instructions. It is
usually only set by the hardware whenever it is interrupted
mid-instruction (see
[\[fig:RVV_vstart_trap\]](#fig:RVV_vstart_trap){reference-type="ref"
reference="fig:RVV_vstart_trap"} and
[2.3.4](#chap:bg:subsec:vexceptions){reference-type="ref"
reference="chap:bg:subsec:vexceptions"}) so that the instruction can be
re-executed later without corrupting completed values. Whenever a vector
instruction completes, `vstart` is reset to zero.

The program *can* set `vstart` manually, but it may not always work. If
an implementation couldn't arrive at the value itself, then it is
allowed to reject it. The specification gives an example where a vector
implementation never takes interrupts during an arithmetic instruction,
so it would never set `vstart` during an arithmetic instruction, so it
could raise an exception if `vstart` was nonzero for an arithmetic
instruction.

### Masking --- Active/inactive elements {#chap:bg:subsec:rvvmasking}

Most vector instructions allow for per-element *masking* (see
[\[fig:RVV_mask_example\]](#fig:RVV_mask_example){reference-type="ref"
reference="fig:RVV_mask_example"}). When masking is enabled, register
`v0` acts as the 'mask register', where each bit corresponds to an
element in the vector[^7]. If the mask bit is 0, that element is
*active* and will be used as normal. If the mask bit is 1, that element
will be *inactive* and not written to (or depending on the mask-agnostic
setting, overwritten with 1s). When masking is disabled, all elements
are *active*.

### Exception handling {#chap:bg:subsec:vexceptions}

*Summarizes [@specification-RVV-v1.0 Section 17]*

During the execution of a vector instruction, two events can prevent an
instruction from fully completing: a synchronous exception in the
instruction itself, or an asynchronous interrupt from another part of
the system. Implementations may choose to wait until an instruction
fully completes before handling asynchronous interrupts, making it
unnecessary to pause the instruction halfway through, but synchronous
exceptions cannot be avoided in this way (particularly where page fault
exceptions must be handled transparently).

The RVV specification defines two modes for 'trapping' these events,
which implementations may choose between depending on the context (e.g.
the offending instruction), and notes two further modes which may be
used in further extensions. All modes start by saving the PC of the
trapping instruction to a CSR `*epc`.

#### Imprecise vector traps

Imprecise traps are intended for events that are not recoverable, where
"reporting an error and terminating execution is the appropriate
response". They do not impose any extra requirements on the
implementation. For example, an implementation that executes
instructions out-of-order does not need to guarantee that instructions
older than `*epc` have completed, and is allowed to have completed
instructions newer than `*epc`.

If the trap was triggered by a synchronous exception, the `vstart` CSR
must be updated with the element that caused it. The specification calls
out synchronous exceptions in particular, but does not mention
asynchronous interrupts. It's likely that imprecise traps for
asynchronous interrupts should also set `vstart`, but this issue has
been raised with the authors for further clarification[^8]. The
specification also states "There is no support for imprecise traps in
the current standard extensions", meaning that the other standard RISC-V
exceptions do not use and have not considered imprecise traps.

#### Precise vector traps

Precise vector traps are intended for instructions that can be resumed
after handling the interrupting event. This means the architectural
state (i.e. register values) when starting the trap could be saved and
reloaded before continuing execution. Therefore it must look like
instructions were completed in-order, even if the implementation is
out-of-order:

-   Instructions older than `*epc` must have completed (committed all
    results to the architectural state)

-   Instructions newer than `*epc` must **not** have altered
    architectural state.

On a precise trap, regardless of what caused it, the `vstart` CSR must
be set to the element index on which the trap was taken. The
save-and-reload expectation then add two constraints on the trapping
instruction's execution:

-   Operations affecting elements preceding `vstart` must have committed
    their results

-   Operations affecting elements at or following `vstart` must either

    -   not have committed results or otherwise affected architectural
        state

    -   be *idempotent* i.e. produce exactly the same result when
        repeated.

The idempotency option gives implementations a lot of leeway. Some
instructions, such as indexed segment loads
([2.5.3](#rvv:indexedmem){reference-type="ref"
reference="rvv:indexedmem"}), are specifically prohibited from
overwriting their inputs to make them idempotent. If an instruction is
idempotent, an implementation is even allowed to repeat operations on
elements *preceding* `vstart`. However for memory accesses the
idempotency depends on the memory being accessed. For example, reading
or writing a memory-mapped I/O region may not be idempotent.

Another memory-specific issue is that of *demand-paging*, where the OS
needs to step in and move virtual memory pages into physical memory for
an instruction to use. This use-case is specifically called out by the
specification for precise traps. Usually, this is triggered by some
element of a vector memory access raising a synchronous exception,
invoking a precise trap, and writing the "Machine Trap Value" scalar
register with the offending address[@specification-RISCV-vol2-20211203
Section 3.1.21]. `vstart` must be set to an element at (or before[^9])
the one that demanded the page, because that element must perform the
access after reloading. If an implementation sets `vstart` to the
offending element, because operations preceding `vstart` must have
completed, any elements that could potentially trigger demand-paging
*must* wait for the preceding elements to complete.

#### Other modes

The RVV spec notes two other possible future trap modes. First is
"Selectable precise/imprecise traps", where an implementation allows the
user to select precise or imprecise traps for e.g. debugging or
performance.

The second mode is "Swappable traps", where a trap handler could use
special instructions to "save and restore the vector unit
microarchitectural state". The intent seems to be to support context
switching with imprecise traps, which could also require the *opaque*
state (i.e. internal state not visible to the program) to be saved and
restored. Right now, it seems that context switching always requires a
precise trap.

### Summary {#chap:bg:subsec:rvvsummary}

[\[fig:RVV_examples_combined\]](#fig:RVV_examples_combined){reference-type="ref"
reference="fig:RVV_examples_combined"} shows all of the above features
used in a single configuration:

-   The instruction was previously interrupted with a precise trap and
    restarted, so `vstart=2`

-   Elements are 16-bit

-   `LMUL=4` to try and increase throughput

-   Only 29 of the 32 available elements were requested, so `vl=29` (3
    tail elements)

-   Some elements are masked out/inactive (in this case seemingly at
    random)

-   Overall, 21 elements are active

## Previous RVV implementations[]{#chap:bg:rvvend label="chap:bg:rvvend"}

Academia and industry have implemented RVV even before v1.0 was
released. The scalable vector model allows great diversity:
@johnsMinimalRISCVVector2020 integrated a minimal vector processor into
a microcontroller's scalar pipeline
(`VLEN=32`) [@johnsMinimalRISCVVector2020],
@dimascioOnBoardDecisionMaking2021 used RVV for deep learning in
space[@dimascioOnBoardDecisionMaking2021], and AndesCode, SiFive, and
Alibaba have released cores with `VLEN`s up to
512[@AndesCoreNX27VProcessor][@SiFiveIntelligenceX280][@chenXuantie910CommercialMultiCore2020].
Other academic examples include Ara[@cavalcanteAra1GHzScalable2020],
Arrow[@assirArrowRISCVVector2021],
RISC-$\text{V}^2$[@patsidisRISCV2ScalableRISCV2020], and
Vicuna[@platzerVicunaTimingPredictableRISCV2021], which all decouple the
vector processing from the scalar pipeline.

Very recently, more implementations were revealed at RISC-V Week in
Paris (May 2022). Vitruvius[@minerviniVitruviusAreaEfficientRISCV2022]
uses extremely long vectors `VLEN = 16384`, is implemented as a
decoupled processor, and is the first RISC-V processor to support the
Open Vector Interface (OVI)[^10] to communicate with the scalar core.
VecProM[@mahaleRISCVVPUVery2021] splits its approach into two, where
vectors beyond a certain length are strip-mined and processed in
hardware using a scratch memory, using OVI to connect multiple
heterogeneous vector processors to a scalar core. Both were produced
from the Barcelona Supercomputing Center under the European Processor
Initiative. It seems that adoption of RVV will continue, making it a
good choice for adapting to CHERI.

## RVV memory instructions[]{#chap:bg:sec:rvvmemory label="chap:bg:sec:rvvmemory"}

*Summarizes [@specification-RVV-v1.0 Sections 7-9]*

RVV defines three broad categories of memory access instructions, which
can be further split into five archetypes with different semantics. This
section summarizes each archetype, their semantics, their assembly
mnemonics, and demonstrates how they map memory accesses to vector
elements.

For the most part, memory access instructions handle their operands as
described in [2.3](#chap:bg:sec:rvv:vector_model){reference-type="ref"
reference="chap:bg:sec:rvv:vector_model"}. `EEW` and `EMUL` are usually
derived from the instruction encoding, rather than reading the `vtype`
CSR. In a few cases the Effective Vector Length `EVL` is different from
the `vl` CSR, so for simplicity all instructions are described in terms
of `EVL`.

### Segmented accesses {#segmented-accesses .unnumbered}

Three of the five archetypes (unit/strided, fault-only-first, and
indexed) support *segmented* access. This is used for unpacking
contiguous structures of $1 \le {\texttt{nf}} \le 8$ *fields* and
placing each field in a separate vector. In these instructions, the
values of `vl`, `vstart`, and the mask register are interpreted in terms
of segments.

[\[fig:RVV_mem_unit\]](#fig:RVV_mem_unit){reference-type="ref"
reference="fig:RVV_mem_unit"} demonstrates a common example: the
extraction of separate R, G, and B components from a color. Without
segmentation, i.e. $n = 1$, each consecutive memory address maps to a
consecutive element in a single vector register group. With
segmentation, elements are grouped into segments of $n > 1$ fields,
where each field is mapped to a different vector register group. This
principle extends to `LMUL > 1`
([\[fig:RVV_mem_lmul_3seg\]](#fig:RVV_mem_lmul_3seg){reference-type="ref"
reference="fig:RVV_mem_lmul_3seg"}).

### Unit and Strided accesses {#chap:bg:sec:rvv:unitstrideaccess}

::: subtable
            Mnemonic                Data    Address      Stride     Masked
  --------- ---------------------- ------- ---------- ------------ --------
  Unit      `vlseg<nf>e<eew>.v`     `vd,`   `(rs1),`   *implicit*    `vm`
  Strided   `vlsseg<nf>e<eew>.v`    `vd,`   `(rs1),`     `rs2,`      `vm`
:::

::: subtable
0.5

  ----------- ----------------------
  Masked?     `vm == 0`
  `EEW`       `<eew>`
  `EVL`       `vl`
  `EMUL`      `VLEN * <eew> / EVL`
  `NFIELDS`   `<nf>`
  ----------- ----------------------
:::

![Example of a segmented strided access\
`EEW=8-bits`, `nf=3`,
`stride=4`,`EVL=4`](Figures/RVV_mem_strided_3seg.pdf){#fig:RVV_mem_strided_3seg
width="\\textwidth"}

This archetype moves active elements of `nf` vector register groups
to/from contiguous segments of memory, where the start of each segment
is separated by `stride` bytes.

-   Unit-stride instructions tightly pack segments, i.e.
    `stride = nf * eew / 8`.

-   Strided instructions read `stride` from register `rs2`.

    -   `stride` may be positive, negative, or zero.

-   These instructions don't do anything if `vstart >= EVL`.

Strided accesses where `rs2` is register `x0` may perform fewer than
`EVL` memory accesses. Otherwise, even if `stride = 0`, implementations
must appear to perform all accesses.

#### Ordering {#ordering .unnumbered}

There are no ordering guarantees, other than those required by precise
vector traps (if used).

#### Exception Handling {#exception-handling .unnumbered}

If any element within segment $i$ triggers a synchronous exception,
`vstart` is set to $i$ and a precise or imprecise trap is triggered.
Load instructions may overwrite active segments past the segment index
at which the trap is reported, but not past
`EVL`.[@specification-RVV-v1.0 Section 7.7] Upon entering a trap, it is
implementation-defined how much of the faulting segment's accesses are
performed.

### Unit fault-only-first loads {#chap:bg:sec:rvv:fof}

::: subtable
  Mnemonic                 Data    Address    Masked
  ----------------------- ------- ---------- --------
  `vlseg<nf>e<eew>ff.v`    `vd,`   `(rs1),`    `vm`
:::

::: subtable
  ----------- ----------------------
  Masked?     `vm == 0`
  `EEW`       `<eew>`
  `EVL`       `vl`
  `EMUL`      `VLEN * <eew> / EVL`
  `NFIELDS`   `<nf>`
  ----------- ----------------------
:::

This archetype is equivalent to a unit load in all respects but
exception handling. If any access in segment 0 raises an exception[^11],
`vl` is not modified and the trap is taken as usual. If any access in
any active segment $> 0$ raises an exception, the trap is not taken,
`vl` is reduced to the index of the offending segment, and the
instruction finishes. If an asynchronous interrupt is encountered at any
point, the trap is taken and `vstart` is set as usual.

This archetype is intended for "loops with data-dependent exit
conditions", and is commonly used for string operations. The
specification uses it in a `strcmp` example ([@specification-RVV-v1.0
Section A.9]).

Similar to plain loads, if an exception is encountered the instruction
is allowed to update segments past the offender (but not past the
original `vl`). If any synchronous exception or asynchronous interrupt
occurs, regardless of the segment index, it is implementation-defined
how much of the faulting segment's accesses are performed.

### Indexed accesses {#rvv:indexedmem}

::: subtable
  Mnemonic                     Data    Address    Indices   Masked
  --------------------------- ------- ---------- --------- --------
  `vl<u|o>xseg<nf>e<eew>.v`    `vd,`   `(rs1),`   `vs2,`     `vm`
:::

::: subtable
0.5

  Masked?          `vm == 0`
  ---------------- ----------------------
  Element `EEW`    `vtype.SEW`
  Element `EMUL`   `vtype.LMUL`
  Ordered?         `<u|o>`
  Index Vector     `vs2`
  Index `EEW`      `<eew>`
  Index `EMUL`     `VLEN * <eew> / EVL`
  `NFIELDS`        `<nf>`
  `EVL`            `vl`
:::

![Example of a segmented indexed access\
`EEW=8-bits`,
`nf=3`](Figures/RVV_mem_index_3seg.pdf){#fig:RVV_mem_index_3seg
width="\\textwidth"}

This archetype moves elements of `nf` vector register groups to/from
contiguous segments of memory, where each segment is offset by an index
(in bytes) taken from another vector.

-   The start of each segment is defined by `address + index_vector[i]`.

-   These instructions don't do anything if `vstart >= EVL`.

-   Indexed segment loads may not overwrite the index vector[^12].

#### Ordering {#ordering-1 .unnumbered}

Accesses within each segment are not ordered relative to each other. If
the ordered variant of this instruction is used, then the segments must
be accessed in order (i.e. 17, 53, 8, 44 for
[2.2](#fig:RVV_mem_index_3seg){reference-type="ref"
reference="fig:RVV_mem_index_3seg"}). Otherwise, segment ordering is not
guaranteed.

#### Exception Handling {#exception-handling-1 .unnumbered}

If any element within segment $i$ triggers a synchronous exception,
`vstart` is set to $i$ and a precise or imprecise trap is triggered.
Load instructions may overwrite active segments past the segment index
at which the trap is reported, but not past
`EVL`[@specification-RVV-v1.0 Section 7.7]. Upon entering a trap, it is
implementation-defined how much of the faulting segment's accesses are
performed.

### Unit whole-register accesses

::: subtable
0.5

  Mnemonic               Data    Address
  --------------------- ------- ---------
  `vl<nreg>re<eew>.v`    `vd,`   `(rs1)`
:::

::: subtable
0.5

  ----------- ------------------------
  Masked?     False
  Registers   `<nreg>`
  `EEW`       `<eew>`
  `EVL`       `NFIELDS * VLEN / EEW`
  `EMUL`      1
  ----------- ------------------------
:::

This archetype moves the contents of `nreg` vector registers to/from a
contiguous range in memory. Equivalent to a unit-stride access where
`EVL` equals the total number of elements in `nreg` registers.

-   `nreg` must be a power of two.

-   These instructions don't support segmented access.

-   These instructions don't do anything if `vstart >= EVL`.

Ordering and exception handling are identical to unit-stride accesses
([2.5.1](#chap:bg:sec:rvv:unitstrideaccess){reference-type="ref"
reference="chap:bg:sec:rvv:unitstrideaccess"}).

### Unit bytemask accesses

::: subtable
0.5

  Mnemonic    Data    Address
  ---------- ------- ---------
  `vlm.v`     `vd,`   `(rs1)`
:::

::: subtable
0.5

  --------- --------------
  Masked?   False
  `EEW`     8-bits
  `EVL`     `ceil(vl/8)`
  `EMUL`    1
  --------- --------------
:::

This archetype moves the contents of a mask register to/from a
contiguous range of memory. It transfers at least `vl` bits, one bit for
each element that could be used in subsequent vector instructions. This
will always fit in a single vector register (see
[2.3.3](#chap:bg:subsec:rvvmasking){reference-type="ref"
reference="chap:bg:subsec:rvvmasking"}), hence `EMUL = 1` in all cases.

-   These instructions operate as if the tail-agnostic setting of
    `vtype` is true.

-   These instructions don't support segmented access.

-   These instructions don't do anything if `vstart >= EVL`.

Ordering and exception handling are identical to unit-stride accesses
([2.5.1](#chap:bg:sec:rvv:unitstrideaccess){reference-type="ref"
reference="chap:bg:sec:rvv:unitstrideaccess"}).

## CHERI {#chap:bg:sec:cheri}

In CHERI, addresses/pointers are replaced with capabilities: unforgeable
tokens that provide *specific kinds of access* to an *address* within a
*range of memory*. The above statement is enough to understand what
capabilities contain[^13]:

-   Permission bits, to restrict access

-   The *cursor*, i.e. the address it currently points to

-   The *bounds*, i.e. the range of addresses this capability could
    point to

A great deal of work has gone into compressing capabilities down into a
reasonable size (see [@woodruffCHERIConcentratePractical2019],
[2.3](#cheri:compressedcap){reference-type="ref"
reference="cheri:compressedcap"}), and using the magic of floating-point
all of this data has been reduced to just 2x the architectural register
size. For example, on 64-bit RISC-V a standard capability is 128-bits
long. The rest of this dissertation assumes capabilities are 128-bits
long for simplicity.

![128-bit compressed capability representation ---
from [@TR-941]](./figures/cheri_compressed_cap.png){#cheri:compressedcap
width="80%"}

A CHERI implementation has to enforce three security properties about
its capabilities[@TR-951 Section 1.2.1]:

-   Provenance --- Capabilities must always be derived from valid
    manipulations of other capabilities.

-   Integrity --- Corrupted capabilities cannot be dereferenced.

-   Monotonicity --- Capabilities cannot increase their rights.

Integrity is enforced by tagging registers and memory. Every 128-bit
register and aligned 128-bit region of memory has an associated tag bit,
which denotes if its data encodes a valid capability[^14]. If any
non-capability data is written to any part of the region the tag bit is
zeroed out. Instructions that perform memory accesses can only do so if
the provided capability has a valid tag bit. As above, significant work
has gone into the implementation to reduce the DRAM overhead of this
method (see [@joannouEfficientTaggedMemory2017]).

Provenance and Monotonicity are enforced by all instructions that
manipulate capabilities. If an implementation detects a violation of
either property, it will zero out the tag bit and rely on Integrity
enforcement to ensure it is not dereferenced. Some CHERI-enabled
architectures, such as CHERI-RISC-V, also raise a synchronous exception
when this occurs.

### CHERI-RISC-V ISA

The Cambridge Computer Lab's TR-951 report[@TR-951] describes the latest
version of the CHERI architecture (CHERI ISAv8) and proposes
applications to MIPS, x86-64, and RISC-V. CHERI-RISC-V is a mostly
straightforward set of additions to basic RISC-V ISAs. It adds
thirty-two general-purpose capability registers, thirty-two Special
Capability Registers (SCRs), and many new instructions.

The new general-purpose capability registers are each of size
`CLEN = 2 * XLEN` plus a tag bit. These registers store compressed
capabilities. While there is always a logical distinction between the
pre-existing *integer* registers `x0-x31` and the *capability* registers
`cx0-cx31`, the architecture may store them in a Split or Merged
register file.[]{#chap:bg:subsec:cherimergedreg
label="chap:bg:subsec:cherimergedreg"} A Split register file stores the
integer registers separately from capability registers, so programs can
manipulate them independently. A Merged register file stores thirty-two
registers of length `CLEN`, using the full width for the capability
registers, and aliases the integer registers to the bottom `XLEN` bits.
Under a merged register file, writing to an integer register makes the
capability counterpart invalid, so programs have to be more careful with
register usage.

Many of the new SCRs are intended to support the privileged ISA
extensions for e.g. hypervisors or operating systems. The emulator
doesn't use these, so their SCRs are not listed here, but there are two
highly relevant SCRs for all modes: the Program Counter Capability and
the Default Data Capability.

The PCC replaces the program counter and adds more metadata, ensuring
instruction fetches have the same security properties as normal loads
and stores. The DDC is used to sandbox integer addressing modes.
CHERI-RISC-V includes new instructions which use integer addressing, and
allows legacy (i.e. integer addressed) code to function on CHERI systems
without recompiling for CHERI-RISC-V. These instructions all use integer
addresses relative to the DDC, and the DDC controls the permissions
those instructions have.

### Instruction changes {#cheri_instructions}

TR-951[@TR-951 Chapter 8] specifies a suite of new instructions, as well
as a set of modifications to pre-existing instructions. Many of the new
instructions are unrelated to pre-existing instructions, and implement
capability-specific operations like accessing fields of capability
registers. The most relevant new instructions for our case are the
various loads/stores.

CHERI-RISC-V adds new instructions for loading integer and capability
data, either via capabilities or using integer addressing through the
DDC ([2.1](#tab:new_cheri_instrs){reference-type="ref"
reference="tab:new_cheri_instrs"}). These instructions are intended for
hybrid-capability code (see
[2.6.4](#cheri_purecap_hybrid){reference-type="ref"
reference="cheri_purecap_hybrid"}, [@TR-951 p151]), so are more limited
and don't support immediate offsets. The behaviour of basic RISC-V
load/store opcodes changes to either use capabilities as memory
references or use integer addressing via the DDC, depending on the
encoding mode. If any instruction tries to dereference an invalid
capability, it raises a synchronous exception.

::: {#tab:new_cheri_instrs}
  Name                  Direction   Data type   Address calculation
  -------------------- ----------- ------------ -------------------------
  L\[BHWD\]\[U\].CAP      Load       Integer    via capability register
  L\[BHWD\]\[U\].DDC      Load       Integer    via DDC
  LC.CAP                  Load      Capability  via capability register
  LC.DDC                  Load      Capability  via DDC
  S\[BHWD\].CAP           Store      Integer    via capability register
  S\[BHWD\].DDC           Store      Integer    via DDC
  SC.CAP                  Store     Capability  via capability register
  SC.DDC                  Store     Capability  via DDC

  : New CHERI load/store instructions
:::

::: {#tab:legacy_cheri_instrs}
  ---------------- ----------- ------------ ---------------------------
  Name              Direction   Data type       Address calculation
                                             (Capability/Integer mode)
  \[C\]LC             Load      Capability      via capability/DDC
  \[C\]SC             Store     Capability      via capability/DDC
  L\[BWHD\]\[U\]      Load       Integer        via capability/DDC
  S\[BWHD\]           Store      Integer        via capability/DDC
  FL\[WDQ\]           Load        Float         via capability/DDC
  FS\[WDQ\]           Store       Float         via capability/DDC
  LR                  Load       Integer        via capability/DDC
  SC                  Store      Integer        via capability/DDC
  AMO                  ---       Integer        via capability/DDC
  ---------------- ----------- ------------ ---------------------------

  : Preexisting RISC-V load/store instructions modified by CHERI-RISC-V
:::

### Capability and Integer encoding mode[]{#chap:bg:subsec:cheriencodingmode label="chap:bg:subsec:cheriencodingmode"}

CHERI-RISC-V specifies two encoding modes, selected using a flag in the
PCC `flags` field. *Capability mode* modifies the behaviour of
pre-existing instructions to take address operands as capabilities. This
makes the basic load/store instruction behaviour exactly equivalent to
newly introduced counterparts: e.g. `L[BWHD][U] == L[BWHD][U].CAP`. The
DDC may still be used in this mode via the new instructions e.g.
`S[BWHD].DDC`.

*Integer mode* seeks to emulate a standard CHERI-less RISC-V
architecture as much as possible. All pre-existing RISC-V memory access
instructions take address operands as integers, which are dereferenced
relative to the DDC[^15]. This makes the basic load/store instruction
behaviour exactly equivalent to newly introduced counterparts: e.g.
`L[BWHD][U] == L[BWHD][U].DDC`. The new instructions may still be used
to dereference and inspect capability registers, but all other
instructions access registers in an integer context i.e. ignoring the
upper bits and tag from merged register files.

### Pure-capability and Hybrid compilation modes {#cheri_purecap_hybrid}

CHERI-Clang[^16], the main CHERI-enabled compiler, supports two ways to
compile CHERI-RISC-V which map to the different encoding modes.

*Pure-capability* mode treats all pointers as capabilities, and emits
pre-existing RISC-V instructions that expect to be run in capability
mode[^17].

*Hybrid* mode treats pointers as integer addresses, dereferenced
relative to the DDC, unless they are annotated with `__capability`. This
mode emits pre-existing RISC-V instructions that take integer operands,
and uses capabilities through the new instructions. All capabilities in
hybrid mode are created manually by the program by copying and shrinking
the DDC.

Hybrid mode allows programs to be gradually ported to CHERI, making it
very easy to adopt on legacy/large codebases. Any extensions to the
model (e.g. CHERI-RVV) should try and retain this property.

### Capability relocations[]{#chap:bg:subsec:cherirelocs label="chap:bg:subsec:cherirelocs"}

*Summarizes [@TR-949 Section 4.4, Appendix C]*

Binary applications compiled in pure-capability mode require some
"global" capabilities to exist at startup, e.g. the capability which
points to the `main()` function. It would be a security risk to
synthesize these capabilities from thin air, or to allow the binary file
itself to contain tag bits.

Instead, CHERI ELF binaries contain a set of requested "relocations"
(the `__cap_relocs` section) which instruct the runtime environment to
create capabilities with specific permissions and bounds in specific
places. This process uses the normal CHERI capability instructions, so
any invalid requests will cause a program crash, maintaining security.
Further complexity is introduced with dynamic linking, and in the future
these relocations may change format, both described in TR-949[@TR-949],
but the above description is sufficient to understand the rest of this
paper.

# Hardware emulation investigation[]{#chap:hardware label="chap:hardware"}

In order to experiment with integrating CHERI and RVV, we implemented a
RISC-V emulator in the Rust programming language named `riscv-v-lite`.
The emulator can partially emulate four unprivileged[^18] RISC-V ISAs
([3.1](#tab:emu_arches){reference-type="ref"
reference="tab:emu_arches"}), and was also used as the base for
capabilities-in-vectors research
([\[chap:capinvec\]](#chap:capinvec){reference-type="ref"
reference="chap:capinvec"}). This chapter explores the development of
the emulator, the implementation of CHERI support (including
supplementary libraries), the addition of vector support, and the
conclusions drawn about CHERI-RVV.

::: {#tab:emu_arches}
   Architecture                        Extensions
  -------------- --------------------- ----------------------------------------
      32-bit     `rv32imv`             Multiply, CSR, Vector
      64-bit     `rv64imv`             Multiply, CSR, Vector
      64-bit     `rv64imvxcheri`       Multiply, CSR, Vector, CHERI
      64-bit     `rv64imvxcheri-int`   Multiply, CSR, Vector, CHERI (Integer)

  : `riscv-v-lite` supported architectures
:::

## Developing the emulator {#chap:software:sec:emu}

Each architecture is simulated in the same way. A `Processor` struct
holds the register file and memory, and a separate `ProcessorModules`
struct holds the ISA modules the architecture can use. Each ISA module
uses a "connector" struct to manipulate data in the `Processor`. For
example, the RV64 Integer ISA's connector contains the current PC, a
virtual reference to a register file, and a virtual reference to memory.
This allows different `Processor` structs (e.g. a normal RV64 and a
CHERI-enabled RV64) to reuse the same ISA modules despite using
different register file implementations.

Each `Processor` implements a single stage pipeline. Instructions are
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
implementing it from scratch. Rust has generally decent interoperability
with C, but some of the particulars of this library caused issues.

#### `rust-cheri-compressed-cap`

`cheri-compressed-cap` provides two versions of the library by default,
for 64-bit and 128-bit capabilities, which are generated from a common
source through extensive use of the preprocessor. Each variant defines a
set of preprocessor macros (e.g. the widths of various fields) before
including two common header files `cheri_compressed_cap_macros.h` and
`cheri_compressed_cap_common.h`. The latter then defines every relevant
structure or function based on those preprocessor macros. For example, a
function `compute_base_top` is generated twice, once as
`cc64_decompress_mem` returning `cc64_cap_t` and another time as
`cc128_decompress_mem` returning `cc128_cap_t`. Elegantly capturing both
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

The CHERI-RISC-V documentation contains formal specifications of all the
new CHERI instructions, expressed in the Sail architecture definition
language[^23]. These definitions are used in the CHERI-RISC-V formal
model[^24], and require a few helper functions (see [@TR-951
Chapter 8.2]). To make it easier to port the formal definitions directly
into the emulator the `rust-cheri-compressed-cap` library also defines
those helper functions.

The above work is available online[^25], and includes documentation for
all C functions (which is not documented in the main repository). That
documentation is also available online[^26] and partially reproduced in
[\[appx:docs:rustcherilib\]](#appx:docs:rustcherilib){reference-type="ref"
reference="appx:docs:rustcherilib"}.

#### Integrating into the emulator

Integrating capabilities into the emulator was relatively simple thanks
to the modular emulator structure. A capability-addressed memory type
was created, which wraps a simple integer-addressed memory in logic
which performs the relevant capability checks. For integer encoding
mode, a further integer-addressed memory type was created where integer
addresses are bundled with the DDC before passing through to a
capability-addressed memory (see
[\[fig:emulatormemory\]](#fig:emulatormemory){reference-type="ref"
reference="fig:emulatormemory"}). Similarly, a merged capability
register file type was created that exposed integer-mode and
capability-mode accesses. This layered approach meant code for basic
RV64I operations did not need to be modified to handle CHERI at all ---
simply passing the integer-mode memory and register file would perform
all relevant checks.

Integrating capability instructions was also simple. Two new ISA modules
were created: `XCheri64` for the new CHERI instructions, and
`Rv64imCapabilityMode` to override the behaviour of legacy instructions
in capability-encoding-mode (see
[\[fig:module_algorithm\]](#fig:module_algorithm){reference-type="ref"
reference="fig:module_algorithm"}). The actual Processor structure was
left mostly unchanged. Integer addresses were changed to capabilities
throughout, memory and register file types were changed as described
above, and the PCC/DDC were added.

![image](Figures/cheri_memory.pdf){width="\\linewidth"}
[]{#fig:emulatormemory label="fig:emulatormemory"}

::: algorithmic
handle with `XCheri64` handle with `Rv64imCapabilityMode` wrap memory
with DDC-relative handle with `Rv64im` handle with vector unit wrap
memory in DDC-relative handle with vector unit
:::

[]{#fig:module_algorithm label="fig:module_algorithm"}

The capability model presented by the C/Rust library has one
flaw.[]{#safetaggedcap label="safetaggedcap"} Each `CcxCap` instance
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
interpreted as a capability by accident and enforcing Provenance.

The final hurdle was the capability relocations outlined in
[\[chap:bg:subsec:cherirelocs\]](#chap:bg:subsec:cherirelocs){reference-type="ref"
reference="chap:bg:subsec:cherirelocs"}. Because we're emulating a
bare-metal platform, there is no operating system to do this step for
us. A bare-metal C function has been written to perform the
relocations[^27], which could be compiled into the emulated program. We
decided it would be quicker to implement this in the simulator, but in
the future we should be able to perform the relocations entirely in
bare-metal C.

### Emulating vectors

Vector instructions are executed by a Vector ISA module, which stores
all registers and other state. `VLEN` is hardcoded as 128-bits, chosen
because it's the largest integer primitive provided by Rust that's large
enough to hold a capability. `ELEN` is also 128-bits, which isn't
supported by the specification, but is required for
capabilities-in-vectors
([\[chap:capinvec\]](#chap:capinvec){reference-type="ref"
reference="chap:capinvec"}). Scaling `VLEN` and `ELEN` any higher would
require the creation and integration of new types that were more than
128-bits long.

To support both CHERI and non-CHERI execution pointers are separated
into an address and a *provenance*[^28]. The vector unit retrieves an
address + provenance pair from the base register, generates a stream of
addresses to access, then rejoins each address with the provenance to
access memory. When using capabilities, provenance is defined in terms
of the base register e.g. "the provenance is provided by capability
register X", or defined by the DDC in integer mode[^29]. On non-CHERI
platforms the vector unit doesn't check provenance.

Arithmetic and configuration instructions are generally simple to
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
hardware would need to do.

#### Decoding phase {#chap:hardware:subsec:decoding}

Decoding is split into two steps: finding the encoded `nf` and element
widths, then interpreting them based on the encoded archetype. Vector
memory accesses reuse instruction encodings from the F extension's
floating-point load/store instructions, which encode an "element width"
in the `mew` and `width` bits (see
[\[fig:stupid\]](#fig:stupid){reference-type="ref"
reference="fig:stupid"}). The vector extension adds four extra width
values which imply the access is vectorized (see
[\[tab:capinvec:accesswidth\]](#tab:capinvec:accesswidth){reference-type="ref"
reference="tab:capinvec:accesswidth"}). If any of these values are
found, the instruction is interpreted as a vector access and `nf` is
extracted.

Once the generic parameters are extracted, the addressing method is
determined from `mop` (Unit, Strided, Indexed-Ordered, or
Indexed-Unordered). If a unit access is selected, the second argument
field `umop` selects a unit-stride archetype (normal access,
fault-only-first, whole register, or bytemask). Extra archetype-specific
calculations are performed (e.g. computing `EVL = ceil(vl/8)` for
bytemask accesses), and the relevant information is returned as a
`DecodedMemOp` enum.

::: tabular
F@I@W@I@R@R@F@R@O  31 29  & &  27 26  & &  24 20  &  19 15  &  14 12  &
 11 7  &  6 0 \
& & & & & & & &\
:::

#### Fast-path checking phase {#chap:hardware:subsec:checking}

The initial motivation for this project was investigating the impact of
capability checks on performance. Rather than check each element's
access individually, we determine a set of "fast-path" checks which
count as checks for multiple elements at once. In the emulator, this is
done by computing the "tight bounds" for each access, i.e. the exact
range of bytes that will be accessed, and doing a single capability
check with that bounds.
[\[chap:hardware:sec:fastpath\]](#chap:hardware:sec:fastpath){reference-type="ref"
reference="chap:hardware:sec:fastpath"} describes methods for
calculating the "tight bounds" for each access type, and ways that
architectural complexity can be traded off to calculate *wider* bounds.

If the tight bounds don't pass the capability check, the emulator raises
an imprecise trap and stops immediately. In the case of fault-only-first
loads, where synchronous exceptions (e.g. capability checks) are
explicitly handled, the access continues regardless and elements are
checked individually. This is also the expected behaviour if a
capability check for *wider* bounds fails. The emulator deviates from
the spec in that `vstart` is *not* set when the tight bounds check
fails, as it does not know exactly which element would have triggered
the exception. As noted in
[\[chap:hardware:sec:fastpath\]](#chap:hardware:sec:fastpath){reference-type="ref"
reference="chap:hardware:sec:fastpath"}, a fully compliant machine must
check each access to find `vstart` in these cases.

#### Execution phase {#chap:hardware:subsec:execution}

If the fast-path check deems it appropriate, the emulator continues
execution of the instruction in two phases. First, the mapping of vector
elements to accessed memory addresses is found. The code for this step
is independent of the access direction, and an effective description of
how each type of access works. It can be found in
[\[appx:code:vector_mem_access\]](#appx:code:vector_mem_access){reference-type="ref"
reference="appx:code:vector_mem_access"}. The previously computed tight
bounds are sanity-checked against these accesses, and the accesses are
actually performed.

#### Integer vs. Capability encoding mode[]{#chap:emu:rvv_int_mode label="chap:emu:rvv_int_mode"}

As noted in
[\[chap:bg:subsec:cheriencodingmode\]](#chap:bg:subsec:cheriencodingmode){reference-type="ref"
reference="chap:bg:subsec:cheriencodingmode"}, CHERI-RISC-V defines two
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

We do not define new mode-agnostic instructions, like `S[BHWD][U].CAP`
and `S[BHWD].DDC` ([2.6.2](#cheri_instructions){reference-type="ref"
reference="cheri_instructions"}), which means vector programs cannot mix
capability and integer addressing without changing encoding modes. This
may make incremental adoption more difficult, and in the future we
should examine existing vanilla RVV programs to determine if it's worth
adding those instructions.

## Fast-path calculations[]{#chap:hardware:sec:fastpath label="chap:hardware:sec:fastpath"}

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
0.5

  Success          All accesses will succeed
  ---------------- ----------------------------
  Failure          At least one access *will*
                   raise an exception
  Likely-Failure   At least one access *may*
  *or* Unchecked   raise an exception
:::

::: algorithmic
Success Likely-Failure Likely-Failure Failure
:::

### Whole-access fast-paths {#chap:hardware:subsec:wholeaccessfastpath}

It is technically possible to calculate a fast-path for the entirety of
an access (see
[\[appx:fastpathfull\]](#appx:fastpathfull){reference-type="ref"
reference="appx:fastpathfull"}), but for some situations it may be
equally/more expensive than checking each access. For example, the
bounds for masked accesses depend on finding the minimum and maximum
active indices, which in hardware may require a linear scan. Indexed
accesses require finding the minimum/maximum offset values, which likely
requires an expensive parallel reduction over all/some elements. In
these cases hardware implementations could defer to the slow-path on all
masked/indexed accesses, or for masked accesses use the wider, unmasked
bounds and generate Likely-Failure outcomes. Unit and strided accesses
are much easier to handle.

Arbitrarily strided accesses (which may have positive, negative, or
zero-valued strides) are relatively simple to calculate. After
calculating the segment width (i.e.
$\text{number of fields} * \text{element width}$) the full bounds just
depends on the sign of the stride
([\[eq:tightboundsstrided\]](#eq:tightboundsstrided){reference-type="ref"
reference="eq:tightboundsstrided"}). Unit-stride accesses simplify this
further, because the stride is equal to the segment width and guaranteed
to be positive
([\[eq:tightboundsunit\]](#eq:tightboundsunit){reference-type="ref"
reference="eq:tightboundsunit"}).

::: mycapequ
$$\label{eq:tightboundsstrided}
{\texttt{base}}{}\ +\ \begin{cases}
        {\texttt{[{\texttt{vstart}}{} * {\texttt{stride}}, ({\texttt{evl}}{} - 1) * {\texttt{stride}} + {\texttt{nf}} * {\texttt{eew}})}} & {\texttt{stride}} \ge 0 \\
            
        {\texttt{[({\texttt{evl}}{} - 1) * {\texttt{stride}}, {\texttt{vstart}}{} * {\texttt{stride}} + {\texttt{nf}} * {\texttt{eew}})}} & {\texttt{stride}} < 0
    \end{cases}$$
:::

::: mycapequ
$$\label{eq:tightboundsunit}
    {\texttt{base}}{}\ +\ {\texttt{[{\texttt{vstart}}{} * {\texttt{nf}} * {\texttt{eew}}, {\texttt{evl}}{} * {\texttt{nf}} * {\texttt{eew}})}}$$
:::

Ultimately, the potential up-front latency seemed like a dealbreaker for
this approach. We turned our attention to fast-pathing smaller groups of
elements.

### $m$-element known-range fast-paths

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

## Going beyond the emulator

The emulator is a single example of a conformant CHERI-RVV
implementation, and does not exercise every part of the specification.
Four properties stand out:

-   The emulator assumes all element accesses are naturally aligned, but
    the spec allows misaligned accesses.

-   The emulator doesn't consider multiple hardware threads, essentially
    assuming all accesses are atomic.

-   Segments/elements are always accessed in order, despite the spec not
    enforcing ordering

-   Imprecise traps are used for all exceptions - precise trap behaviour
    is not explored.

This section notes how relaxed access ordering and precise exceptions
may affect the hardware in ways not previously explored.

### Misaligned accesses

Implementations are allowed to handle vector accesses that are not
aligned to the size of the element. This support is independent of
misaligned scalar access support, so if e.g. misaligned 64-bit scalar
accesses are allowed, misaligned vector accesses of 64-bit elements do
*not* have to be allowed.

Changing the emulator to allow misaligned accesses of integer data would
not have any impact on CHERI correctness. Capability loads/stores must
be aligned to `CLEN`[@TR-951 Section 3.5.2], and an implementation
cannot change this. Writing misaligned integer values across a `CLEN`
boundary would need to make sure to zero the tag bit on both regions,
but this applies to scalar implementations as much as vector ones.
Alignment only impacts CHERI-RVV to the extent that it impacts
capabilities-in-vectors
([\[chap:capinvec:hyp_load_store\]](#chap:capinvec:hyp_load_store){reference-type="ref"
reference="chap:capinvec:hyp_load_store"}).

### Atomicity of accesses/General memory model

Vector memory instructions are specified to follow the RISC-V Weak
Memory Ordering model[@specification-RVV-v1.0][^33], although this model
hasn't been fully explained in terms of vectors yet. RVWMO defines a
global order of "memory operations": atomic operations that are either
loads, stores, or both[@specification-RISCV-vol1-20191213 Chapter 14].
The RVWMO spec assumes all memory instructions create exactly one memory
operation but calls out that once the vector model is formalized, vector
accesses may be defined to create multiple operations.

The RVV spec states "vector misaligned memory accesses follow the same
rules for atomicity as scalar misaligned memory accesses", i.e. that
misaligned accesses may be decomposed into multiple memory operations of
any granularity[^34]. This is the only mention of atomicity in that
document.

Again, atomicity of integer data doesn't really impact the fusion of
CHERI and RVV, as long as tag bits are correctly zeroed on all integer
writes. However, it does impact capabilities-in-vectors
([\[chap:capinvec:hyp_load_store\]](#chap:capinvec:hyp_load_store){reference-type="ref"
reference="chap:capinvec:hyp_load_store"}).

### Relaxed access ordering and precise traps

Ordering is only enforced insofar as it is observable. The only
instructions that are forced to perform their accesses in order are
indexed-ordered accesses, which can be used to write to e.g. I/O regions
where order matters, and instructions that trigger precise traps.
Precise traps require `vstart` to be set to a value such that all
elements before `vstart` have completed their accesses, and all accesses
on/after `vstart` have not completed or are idempotent.

If a vector memory access instruction is 1. not indexed-ordered and 2.
guaranteed not to trigger a precise trap[^35] then it may execute out of
order. This does not affect CHERI-RVV in any way.

## Testing and evaluation

We tested the emulator using a set of test programs described in
[\[chap:software:eval,chap:capinvec:eval\]](#chap:software:eval,chap:capinvec:eval){reference-type="ref"
reference="chap:software:eval,chap:capinvec:eval"}, and found that all
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

# The CHERI-RVV software stack[]{#chap:software label="chap:software"}

This chapter explores the current state of the CHERI-RVV software stack:
mainstream compiler support for vanilla RVV
([4.1](#chap:software:sec:compilersupport){reference-type="ref"
reference="chap:software:sec:compilersupport"}) and the modifications
required to bring support to CHERI-Clang
([4.2](#chap:software:sec:chericlang){reference-type="ref"
reference="chap:software:sec:chericlang"}). The software hypotheses are
tested with this knowledge
([4.3](#chap:software:sec:hypotheses){reference-type="ref"
reference="chap:software:sec:hypotheses"}), and we recommend a set of
changes to bring CHERI-Clang support up to par
([4.4](#chap:software:sec:chericlangchanges){reference-type="ref"
reference="chap:software:sec:chericlangchanges"}).

## Compiling vector code {#chap:software:sec:compilersupport}

Modern compilers provide many ways to generate vectorized code. While
this support is very advanced for well established vector models, like
x86-64 AVX, newer vector models like RVV don't have as many options. It
can even be difficult to get the compiler to generate any vector
instructions at all. This section examines support across the Clang and
GCC compilers for various vectorization methods on RVV.

### Available compilers

Compiler support for RVV varies. On Clang 13 and other LLVM-13-based
compilers, version 0.1(?[^36]) of the vector specification is supported
as an experimental extension. Clang/LLVM 14 and up support RVV v1.0.

GCC is an interesting case --- there is a version based on RISC-V GCC
10.1 that partially supports RVV (see
[\[compilerdifferences\]](#compilerdifferences){reference-type="ref"
reference="compilerdifferences"}), but it was left untouched for a year
and deleted as of 17th May 2022. GCC RVV support has also been
deprioritized in favour of LLVM[^37]. See
[\[appx:building_rvv_gcc_toolchain\]](#appx:building_rvv_gcc_toolchain){reference-type="ref"
reference="appx:building_rvv_gcc_toolchain"} for more information on
finding and building this version, and
[\[tab:rvv_cmdline_nocheri\]](#tab:rvv_cmdline_nocheri){reference-type="ref"
reference="tab:rvv_cmdline_nocheri"} for the required command-line
arguments to enable RVV.

### Automatic vectorization

Compilers with auto-vectorization can automatically create vectorized
code from a scalar program. For example, a scalar loop over an array
that increments each element could be converted to a vectorized loop
that increments multiple elements at once. Clang and GCC support
auto-vectorization in Arm SVE, explored further in
[4.1.5](#chap:soft:compiling:armsve){reference-type="ref"
reference="chap:soft:compiling:armsve"}, but don't yet support it for
RVV. Arm SVE and RVV are quite similar, so there shouldn't be anything
blocking auto-vectorization for RVV, it just requires engineering
effort.

### Vector intrinsics {#chap:software:subsec:vectorintrinsics}

"Intrinsics" are functions defined by the compiler that can invoke
low-level functionality and instructions directly for a specific
architecture. When automatic vectorization is not available, intrinsics
are the next best thing --- they aren't portable across different ISAs,
but present a familiar high-level interface (function calls) that gives
fine-grained control over instructions. The compiler then handles
low-level decisions like register allocation under the hood, and
sometimes may provide extra functionality for ease of use.

RVV has a comprehensive set of vector
intrinsics[@specification-RVV-intrinsics]. With these, the general
strip-mining loop is easy to construct:

1.  Use a `vsetvl` intrinsic to get the vector length for this
    iteration.

2.  Allocate vector registers by declaring variables with vector types
    (e.g. `vuint32m8_t` represents 8 registers worth of 32-bit unsigned
    integers).

3.  Pass the vector length to the computation/memory intrinsics, which
    operate on the vector variables.

[\[example:rvv\]](#example:rvv){reference-type="ref"
reference="example:rvv"} contains an example.

### Inline assembly

If a compiler doesn't supply complete intrinsics, or if the programmer
desires even more control, inline assembly may be used. The programmer
gives a string of handwritten assembly code to the compiler, which is
parsed and directly inserted into the output. The compiler still has to
understand the instruction, but it doesn't need intrinsics to be present
(or functional[^38]).

Inline assembly can interact with C code and variables through a
template syntax. The programmer inserts a placeholder in the assembly
code with a corresponding expression, noting how the expression is
stored using a "constraint". For our purposes, constraints enforce that
a value is either in a register or in memory.

Using the constraint, the compiler determines how the expression's value
is stored, and inserts a reference to it in the assembly string. Because
this is done before the assembly string is parsed, and isn't immediately
type-checked against the assembly instruction, it can lead to some
difficult errors.

Clang and GCC support inline assembly for RVV quite well, and even
allows the intrinsic vector types to be referenced by assembly templates
(thus making the compiler do register allocation instead of the
programmer). The only caveat is that *memory* constraints are not
supported by RVV memory accesses. None of the vector memory access
instructions support address offsets, unlike their scalar counterparts.
Clang always treats the memory constraint as an offset access, even when
that offset is zero, so it adds an offset to the assembly string
([\[subfig:inline_asm_vector_memory\]](#subfig:inline_asm_vector_memory){reference-type="ref"
reference="subfig:inline_asm_vector_memory"}) making it invalid. To get
around this, one must use the pointer itself with a *register*
constraint
([\[subfig:inline_asm_vector_ptr_reg\]](#subfig:inline_asm_vector_ptr_reg){reference-type="ref"
reference="subfig:inline_asm_vector_ptr_reg"}).

::: mdframed
``` {.c gobble="4" firstline="6" lastline="6"}
```
:::

::: mdframed
``` {.c gobble="4" firstline="7" lastline="10"}
```
:::

::: mdframed
``` {.c gobble="4" firstline="20" lastline="23"}
```
:::

::: mdframed
``` {.c gobble="4" firstline="32" lastline="35"}
```
:::

Broadly speaking, inline assembly supports more RVV instructions than
intrinsics do. It is used extensively in the testbench code for the
evaluation
([\[chap:software:eval\]](#chap:software:eval){reference-type="ref"
reference="chap:software:eval"}) alongside intrinsics where possible.

### RVV vs. Arm SVE {#chap:soft:compiling:armsve}

Arm SVE uses a similar model to RVV, where the vector length may scale
between 128 and 2048[^39] and the instructions are designed to be
totally agnostic across different
platforms[@stephensARMScalableVector2017]. Arm have released a C
language extension to support SVE development
([@armltdARMLanguageExtensions2020]), supported by the Arm Compiler for
Embedded[^40], Clang, and GCC. They support all of the previously
examined vectorization types.

Auto-vectorization is supported, and the main focus of the user guide
([@armltdArmCompilerScalable2019]) is helping the compiler decide
whether to auto-vectorize. Intrinsics are also supported, and seem to
cover all of the SVE instructions, but take a slightly different
approach to RVV. Arm SVE intrinsics do not directly map to available
instructions, but aim to "provide a regular interface and leave the
compiler to pick the best mapping to SVE instructions", while RVV
intrinsics (at least for memory) tend to map 1:1 to existing
instructions. Arm's approach gives more flexibility for future
extensions, as the same intrinsics could be compiled to new instructions
with newer compilers.

Arm SVE also supports inline assembly, but the experience is noticeably
worse than for RVV. The two standout issues are a lack of register
allocation and the use of condition code flags for branching. Unlike
RVV, the intrinsic types for vector values cannot be referenced in
inline assembly[@stephensARMScalableVector2017], so all vector registers
must be allocated and tracked by the programmer. Arm SVE's equivalent of
`vsetvl`, the `while` family[@armltdARMLanguageExtensions2020], do not
return the number of updated elements, and instead set the condition
flags based on how many elements are updated. Because there is no way to
branch based on the condition flags in C, the programmer must manually
insert a label for the top of the loop, and a branch to that label,
which is more error prone than the RVV method. See
[\[example:armsvec\]](#example:armsvec){reference-type="ref"
reference="example:armsvec"} for examples of Arm SVE code with
auto-vectorization, intrinsics, and inline ASM.

::: mdframed
``` {.c gobble="4" firstline="43" lastline="46"}
```
:::

::: mdframed
``` {.c gobble="4" firstline="57" lastline="67"}
```
:::

## Compiling vector code with CHERI-Clang {#chap:software:sec:chericlang}

Current CHERI compiler work is done on CHERI-Clang, a fork of Clang and
other LLVM tools that supports capabilities. It's based on LLVM 13, and
supports vanilla RVV v0.1, but the vector-related code had not been
updated to handle capabilities. This section outlines the changes
required to compile vector programs for CHERI-RVV using CHERI-Clang. The
required command-line options for CHERI-Clang are noted in
[\[chericlang_cmdline\]](#chericlang_cmdline){reference-type="ref"
reference="chericlang_cmdline"}.

### Adapting vector assembly instructions to CHERI {#addingtochericlang}

LLVM uses a domain-specific language to describe the instructions it can
emit for a given target. The RISC-V target describes multiple register
sets that RISC-V instructions can use. Vanilla RVV vector memory
accesses use the General Purpose Registers (GPR) to store the base
address of each access. CHERI-Clang added a GPCR set, i.e. the General
Purpose Capability Registers, which use a different register constraint.
We created two mutually exclusive versions of each vector access
instruction: one for integer mode using a GPR base address; and one for
capability mode using GPCR.

With the above changes, inline assembly could be used to insert
capability-enabled vector instructions
([\[subfig:inline_asm_vector_cap_reg\]](#subfig:inline_asm_vector_cap_reg){reference-type="ref"
reference="subfig:inline_asm_vector_cap_reg"}). However, as this
requires using a capability register constraint for the base address,
inline assembly code written for CHERI-RVV is not inherently compatible
with vanilla RVV. For un-annotated pointers (e.g. `int*`), which are
always capabilities in pure-capability code and integers in legacy or
hybrid code, a conditional macro can be used to insert the correct
constraint
([\[subfig:inline_asm_vector_portable\]](#subfig:inline_asm_vector_portable){reference-type="ref"
reference="subfig:inline_asm_vector_portable"}). However, this falls
apart in hybrid code for manually annotated pointers (e.g.
`int* __capability`) because the macro cannot detect the annotation.

### Adapting vector intrinsics to CHERI

Vector intrinsics are another story entirely. When compiling for
pure-capability libraries, all attempts to use vector intrinsics crash
CHERI-Clang. This is due to a similar issue to inline assembly: the
intrinsics (both the Clang intrinsic functions and the underlying LLVM
IR intrinsics) were designed to take regular pointers and cannot handle
it when capabilities are used instead. Unfortunately the code for
generating the intrinsics is spread across many files, and there's no
simple way to change the pointers to capabilities (much less changing it
on-the-fly for capability vs. integer mode).

It seems that significant engineering work is required to bring vector
intrinsics up to scratch on CHERI-Clang. We did experiment with creating
replacement wrapper functions, where each function tried to mimic an
intrinsic using inline asssembly. These were rejected for two reasons:
the overhead of a function call for every vector instruction[^41], and
lack of support for passing vector types as arguments or return values.
The RISC-V ABI treats all vector registers as temporary and explicitly
states that "vector registers are not used for passing arguments or
return values"[@specification-RISCV-ABI-v1.0rc2]. CHERI-Clang would try
to return them by saving them to the stack, but this had its own issues.

### Storing scalable vectors on the stack

If a program uses more data than can fit in registers, or calls a
function which may overwrite important register values, the compiler
will save those register values to memory on the stack. Because vector
registers are temporary, and thus may be overwritten by called
functions, they must also be saved/restored from the stack (see
[\[example:saverestore\]](#example:saverestore){reference-type="ref"
reference="example:saverestore"}). This also applies to multiprocessing
systems where a process can be paused, have the state saved, and resume
later. RVV provides the whole-register memory access instructions
explicitly to make this process easy[@specification-RVV-v1.0
Section 7.9].

CHERI-Clang contains an LLVM IR pass[^42] which enforces strict bounds
on so-called "stack capabilities" (capabilities pointing to
stack-allocated data), which by definition requires knowing the size of
the data ahead of time. This pass assumes all stack-allocated data has a
static size, and crashes when dynamically-sized types e.g. scalable
vectors are allocated. It is therefore impossible (for now) to save
vectors on the stack in CHERI-Clang, although it's clear that it's
theoretically possible. For example, the length of the required vector
allocations could be calculated based on `VLEN` before each stack
allocation is performed, or if performance is a concern stack bounds for
those allocations could potentially be ignored altogether. These
possibilities are investigated further in the next section.

## Testing and evaluation {#chap:software:sec:hypotheses}

[]{#chap:software:eval label="chap:software:eval"} We developed a
self-checking test program for the emulator to execute, which helped
gather information for the hypotheses and find bugs in the compiler and
emulator. Initially it was hand-written, but in order to test a wide
range of `vtype`s we began generating it with a Python script. It
consists of fifty-seven tests of different vector memory access
archetypes under various configurations
([4.1](#tab:vectormemcpyschemes){reference-type="ref"
reference="tab:vectormemcpyschemes"}).

The test code uses intrinsics wherever the compiler supports them (see
[\[compilerdifferences\]](#compilerdifferences){reference-type="ref"
reference="compilerdifferences"}), and falls back to inline assembly
otherwise. Inline assembly uses the preprocessor macro from
[\[subfig:inline_asm_vector_portable\]](#subfig:inline_asm_vector_portable){reference-type="ref"
reference="subfig:inline_asm_vector_portable"} to handle CHERI and
non-CHERI platforms.

The tests are run inside *harnesses*, which provide setup and
self-checking code for common cases: The Vanilla harness tests a simple
`memcpy` between two arrays; Masked tests that every other element is
copied, not all of them; Segmented tests a `memcpy` into four separate
output arrays, each a different field of a four-field structure. There
is also a special test for fault-only-first: FoF loads are performed at
the edge of mapped memory, and the test shows that out-of-bounds
exceptions are swallowed and `vl` is reduced accordingly. All tests were
successful when they ran, but some testbenches could not be built with
some compilers. The full set of test results is available in
[\[chap:fullresults\]](#chap:fullresults){reference-type="ref"
reference="chap:fullresults"}.

::: {#tab:vectormemcpyschemes}
  Test Scheme                   Harness      Compilers
  --------------------------- ----------- ----------------
  Unit Stride                   Vanilla         All
  Strided                       Vanilla         All
  Indexed                       Vanilla         All
  Whole Register                Vanilla         All
  Fault-only-First              Vanilla         All
  Unit Stride (Masked)          Masked          All
  Bytemask Load                 Masked     `llvm-15` only
  Unit Stride (Segmented)      Segmented        All
  Fault-only-First Boundary       ---           All

  : `vector_memcpy` test schemes and harnesses
:::

### [\[hyp:sw_vec_legacy\]](#hyp:sw_vec_legacy){reference-type="ref" reference="hyp:sw_vec_legacy"} - Compiling/running legacy code in integer mode {#hypsw_vec_legacy---compilingrunning-legacy-code-in-integer-mode .unnumbered}

This is true for CHERI-RVV, when running the compiled programs in
integer mode, as long as the programs only access memory within the DDC.

All vanilla RVV instructions have counterparts with identical encodings
and behaviour in CHERI-RVV integer mode, assuming the accessed addresses
are all accessible through the DDC. There are no changes to instruction
behaviour that require the compiler's handling of them to change, so a
non-CHERI compiler and an integer-mode-CHERI compiler can always produce
the same vector instructions from the same code. This does not apply to
capability-mode-CHERI, because integer addressing is not supported in
capability-mode-CHERI-RVV.

All legacy vector programs should produce equivalent binaries when
compiled for integer-mode-CHERI. On top of that, all binaries compiled
for vanilla RVV platforms should produce the same results when run on an
equivalent integer-mode-CHERI-RVV platform. Both claims assume the
program doesn't perform out-of-bounds accesses relative to the DDC.

### [\[hyp:sw_pure_compat\]](#hyp:sw_pure_compat){reference-type="ref" reference="hyp:sw_pure_compat"} - Converting legacy code to pure-capability code {#hypsw_pure_compat---converting-legacy-code-to-pure-capability-code .unnumbered}

This is true for CHERI-RVV, but cannot be done in practice yet.
Engineering effort is required to support this in CHERI-Clang. Because
this argument concerns source code, all three ways to generate CHERI-RVV
instructions must be examined.

#### Inline Assembly --- Unlikely {#inline-assembly-unlikely .unnumbered}

For GCC-style inline assembly, it is currently impossible for
integer-addressed RVV source code to be recompiled in pure-capability
mode without modification. Integer-addressed RVV uses general-purpose
registers for the base address, but pure-capability instructions require
capability registers instead. The base address register can either be
specified directly, so must be changed to a capability register; or
specified using template syntax and an "r" constraint, which must be
changed to a "C" constraint
([\[fig:inlineasm,fig:inlineasmcheri\]](#fig:inlineasm,fig:inlineasmcheri){reference-type="ref"
reference="fig:inlineasm,fig:inlineasmcheri"}). Using a preprocessor
macro (e.g.
[\[subfig:inline_asm_vector_portable\]](#subfig:inline_asm_vector_portable){reference-type="ref"
reference="subfig:inline_asm_vector_portable"}) could make code portable
between non-CHERI and CHERI, but this is still a source code change.

In theory, one could change the behaviour of inline assembly to
automatically convert general purpose registers/constraints to
capability versions in specific circumstances. However, this can have
wide-reaching ramifications, potentially making code more difficult to
understand, or even breaking existing code.

#### Intrinsics --- Yes {#intrinsics-yes .unnumbered}

The current specification for RVV intrinsics uses pointer types for all
base addresses[@specification-RVV-intrinsics]. In pure-capability
compilers all pointers should be treated as capabilities instead of
integers, including those in intrinsics. All RVV memory intrinsics have
equivalent RVV instructions, which all use capabilities in
pure-capability mode, so changing the intrinsics to match is valid.

Assuming all base address pointers are created in a valid manner (e.g.
through `malloc` or monotonic decrease, and not through integer
literals), the conversion to pure-capability should make them all valid
capabilities which are compatible with the intrinsics. Therefore
well-behaved code using RVV intrinsics should be compilable in
pure-capability mode without changes.

This is not currently the case for CHERI-Clang, as RVV memory access
intrinsics are broken, but this can be fixed with engineering effort.

#### Auto-vectorization --- Yes {#auto-vectorization-yes .unnumbered}

All vanilla RVV instructions have counterparts with identical encodings
and behaviour in CHERI-RVV pure-capability mode, assuming the base
addresses can be converted to valid capabilities. Any scalar code that
can be

::: enumerate*
compiled in scalar pure-capability mode[^43], and

auto-vectorized by a legacy RVV compiler,
:::

must have an equivalent pure-capability vectorized form. This form could
be acquired by performing the auto-vectorization in legacy mode,
ensuring all base addresses are available as capabilities, then making
the vector instructions use those capabilities. Therefore a
pure-capability compiler can always auto-vectorize CHERI-compliant
scalar code if some legacy compiler can also auto-vectorize it.

This is not currently possible for CHERI-Clang, as RVV
auto-vectorization is not implemented yet. Similar models (e.g. Arm SVE)
already have auto-vectorization, so RVV auto-vectorization (and thus
CHERI-RVV auto-vectorization) should be possible.

### [\[hyp:sw_stack_vectors\]](#hyp:sw_stack_vectors){reference-type="ref" reference="hyp:sw_stack_vectors"} - Saving vectors on the stack {#hypsw_stack_vectors---saving-vectors-on-the-stack .unnumbered}

This is true in theory, but not yet supported by CHERI-Clang in
practice. Placing variable-length structures on the stack is possible as
long as the length can be known at runtime (and as long as the stack has
space, of course). This isn't exclusive to CHERI --- to push and pop
values on the stack, the stack pointer must be incremented or
decremented by the size of the value. Because the length already has to
be measured, and CHERI-RISC-V supports setting capability bounds from
runtime-computed values, it's entirely possible to correctly set tight
bounds for capabilities pointing to variable-length vectors on the
stack.

A minor complication is presented by a note in TR-949[@TR-949
Section 3.8.2] concerning "re-materializing bounded stack variables".
This section implies LLVM can try to re-create a pointer-to-stack at any
time with minimal cost, but this may not be able to apply to vectors.
Measuring the bounds requires measuring `VLMAX` by changing `vl`, which
could then require saving/restoring the old value. This is only a
performance issue, and in the worst case we can just say
pointers-to-stack-vectors are not re-materializable, so it isn't a
dealbreaker. Further investigation of this issue is left as future work.

### [\[hyp:sw_multiproc\]](#hyp:sw_multiproc){reference-type="ref" reference="hyp:sw_multiproc"} - Running CHERI-RVV code in a multiprocessing system {#hypsw_multiproc---running-cheri-rvv-code-in-a-multiprocessing-system .unnumbered}

This requires two conditions: an OS must be able to save and restore
vector state, and the vector hardware must support resuming from an
interrupted state. The first condition is easy to fulfil by extending
the previous hypothesis. If it is possible to save variable-length
vectors on the stack, given their length is known at runtime, it must
also be possible to save their data on the heap. Some OSs might need to
make changes to their "current process state" structure to support
variable-length data, and they would also need to allocate space for the
`vtype` value, but it is certainly possible.

The second condition can be upheld in two ways. First, if the OS only
context switches and services interrupts while the vector hardware is in
a complete state (i.e. not partially executing an instruction), then
context switches and interrupts are completely transparent to the vector
hardware and no changes need to be made. Secondly, if context switches
and interrupts can actually interrupt vector instructions partway
through, then they can only be cleanly resumed if the vector hardware
supports precise traps for the exact instruction being executed.

## Recommended changes for CHERI-Clang {#chap:software:sec:chericlangchanges}

-   Build on current work to make all RVV memory access instructions and
    pseudoinstructions CHERI-compatible.

-   Make RVV memory access intrinsics take capabilities as arguments
    when compiled in pure-capability mode.

-   Make the CheriBoundAllocas IR pass handle scalable vectors by
    finding the length at runtime, and investigate re-materialization of
    those pointers.

-   Bring up CHERI-enabled auto-vectorization in parallel with vanilla
    auto-vectorization.

# Capabilities-in-vectors[]{#chap:capinvec label="chap:capinvec"}

Implementing `memcpy` correctly for CHERI systems requires copying the
tag bits as well as the data. As it stands, any vectorized `memcpy`
compiled and executed on the systems described in
[\[chap:software,chap:hardware\]](#chap:software,chap:hardware){reference-type="ref"
reference="chap:software,chap:hardware"} will not copy the tag bits,
because the vector registers cannot store the tag bits and indeed cannot
store valid capabilities. `memcpy` is very frequently vectorized, as
noted in
[\[vectorized_memcpy\]](#vectorized_memcpy){reference-type="ref"
reference="vectorized_memcpy"}, so it's vital that CHERI-RVV can
implement it correctly. Manipulating capabilities-in-vectors could also
accelerate CHERI-specific processes, such as revoking capabilities for
freed memory[@xiaCHERIvokeCharacterisingPointer2019].

This chapter examines the changes made to the emulator to support
storing capabilities-in-vectors, and determines the conditions required
for the related hypotheses to be true.
[\[appx:capinvec\]](#appx:capinvec){reference-type="ref"
reference="appx:capinvec"} lists the changes made and all the relevant
properties of the emulator that allow storing capabilities in vectors.

## Extending the emulator

We developed a set of goals based on
[\[hyp:cap_in_vec_storage,hyp:cap_in_vec_load_store,hyp:cap_in_vec_manip\]](#hyp:cap_in_vec_storage,hyp:cap_in_vec_load_store,hyp:cap_in_vec_manip){reference-type="ref"
reference="hyp:cap_in_vec_storage,hyp:cap_in_vec_load_store,hyp:cap_in_vec_manip"}.

-   ([\[hyp:cap_in_vec_storage\]](#hyp:cap_in_vec_storage){reference-type="ref"
    reference="hyp:cap_in_vec_storage"}) Vector registers should be able
    to hold capabilities.

-   ([\[hyp:cap_in_vec_load_store\]](#hyp:cap_in_vec_load_store){reference-type="ref"
    reference="hyp:cap_in_vec_load_store"}) At least one vector memory
    operation should be able to load/store capabilities from vectors.

    -   Because `memcpy` should copy both integer and capability data,
        vector memory operations should be able to handle both together.

-   ([\[hyp:cap_in_vec_manip\]](#hyp:cap_in_vec_manip){reference-type="ref"
    reference="hyp:cap_in_vec_manip"}) Vector instructions should be
    able to manipulate capabilities.

    -   Clearing tag bits counts as manipulation.

First, we considered the impact on the theoretical vector model. We
decided that any operation with elements smaller than `CLEN` cannot
output valid capabilities under any circumstances[^44], meaning a new
element width equal to `CLEN` must be introduced. We set
`ELEN = VLEN = CLEN = 128`[^45] for our vector unit.

Two new memory access instructions were created to take advantage of
this new element width, and the `vsetvl` family were adjusted to support
128-bit values. Similar to the CHERI-RISC-V `LC/SC` instructions, we
implemented 128-bit unit-stride vector loads and stores, which took over
officially-reserved encodings[^46] we expected official versions to use.
We have not tested other types of access, but expect them to be
noncontroversial. Indexed accesses require specific scrutiny, as they
may be expected to use 128-bit offsets on 64-bit systems. The memory
instructions had to be added to CHERI-Clang manually, and Clang already
has support for setting `SEW=128` in the `vsetvl` family
([\[tab:capinvec:vtypewidth\]](#tab:capinvec:vtypewidth){reference-type="ref"
reference="tab:capinvec:vtypewidth"}). These instruction changes
affected inline assembly only, rather than adding vector intrinsics,
because CHERI-Clang only supports inline assembly anyway.

The next step was to add capability support to the vector register file.
Our approach to capabilities-in-vectors is similar in concept to the
Merged scalar register file for CHERI-RISC-V
([\[chap:bg:subsec:cherimergedreg\]](#chap:bg:subsec:cherimergedreg){reference-type="ref"
reference="chap:bg:subsec:cherimergedreg"}), in that the same bits of a
register can be accessed in two contexts: an integer context, zeroing
the tag, or a capability context which maintains the current tag. The
only instructions which can access data in a capability context are the
aforementioned 128-bit memory accesses[^47]. All other instructions will
read out untagged integer data and clear tags when writing data.

A new CHERI-specific vector register file was created, where each
register is a `SafeTaggedCap` (p) i.e. either zero-tagged integer data
or a valid tagged capability. This makes it much harder to accidentally
violate Provenance, and reuses the code path (and related security
properties) for accessing capabilities in memory. Just like scalar
accesses, vectorized capability accesses are atomic and 128-bit aligned.

## Testing and evaluation {#chap:capinvec:eval}

We constructed a second test program to ensure `memcpy` could be
performed correctly with capabilities-in-vectors. It copies an array of
`Element` structures that hold pointers to static `Base` structures. On
CHERI platforms, even in Integer mode, capability pointers are used and
copied. The first test simply copies the data, and tests that all the
copied pointers still work, which succeeds on all
compilers/architectures. The second test is CHERI-exclusive, and
invalidates all pointers during the copy process by performing integer
arithmetic on the vector registers. The copied pointers are examined to
make sure their tag bits are all zeroed, and this test succeeds on both
CHERI configurations.

::: {#tab:fullresults:vectormemcpyptrs}
  -- -- -- -- -- -- --
                    
  -- -- -- -- -- -- --

  : `vector_memcpy_pointers` results
:::

### [\[hyp:cap_in_vec_storage\]](#hyp:cap_in_vec_storage){reference-type="ref" reference="hyp:cap_in_vec_storage"} - Holding capabilities in vectors {#hypcap_in_vec_storage---holding-capabilities-in-vectors .unnumbered}

It is possible for a single vector register to hold a capability (and
differentiate a capability from integer data) as long as `VLEN = CLEN`.
`VLEN` could also be larger, and a compliant implementation must then
have `VLEN` be an integer multiple of `CLEN`. In theory, one could also
describe a scheme where capabilities must be held by multiple registers
together (e.g. `VLEN = CLEN/2` with one tag bit for every two
registers), but this would complicate matters.

If an implementation decides, as we did, that elements of width `CLEN`
are required to produce capabilities, then
${\texttt{VLEN}} \ge {\texttt{ELEN}}$ therefore
${\texttt{VLEN}} \ge {\texttt{CLEN}}$. If a short `VLEN` is absolutely
essential, one could place precise guarantees on a specific set of
instructions to enable it (e.g. `SEW=64, LMUL=2` unit-stride unmasked
loads could guarantee atomic capability transfers) but the emulator does
not consider this. The CHERI security properties also impose some
conditions.

#### Provenance & Monotonicity {#provenance-monotonicity .unnumbered}

The tag bit must be protected such that capabilities cannot be forged
from integer data. The emulator's integer/capability context approach,
where the tag bit may only be set on copying a valid capability from
memory, and the output tag bit is zeroed on all other accesses, enforces
this correctly.

#### Integrity {#integrity .unnumbered}

Integrity is not affected by how a capability is stored, as long as the
other properties are maintained.

### [\[hyp:cap_in_vec_load_store\]](#hyp:cap_in_vec_load_store){reference-type="ref" reference="hyp:cap_in_vec_load_store"} - Sending capabilities between vectors and memory {#hypcap_in_vec_load_store---sending-capabilities-between-vectors-and-memory .unnumbered}

[]{#chap:capinvec:hyp_load_store label="chap:capinvec:hyp_load_store"}
For this to be the case, the instructions which can load/store
capabilities must fulfil certain alignment and atomicity requirements.
They must require all accesses be `CLEN`-aligned, or at least only load
valid capabilities from aligned addresses, because tag bits only apply
to `CLEN`-aligned regions. TR-951 states that capability memory accesses
must be atomic[@TR-951 Section 11.3]. This applies to vectors, even in
ways that don't apply to scalar accesses.

Individual element accesses for a vector access must be atomic relative
to each other. This is relevant for e.g. a strided store using an
unaligned stride, such that one element writes a valid capability and
another element overwrites part of that address range. If unaligned
128-bit accesses are allowed, then either the unaligned second element
should "win" and clear relevant tag bits, or the first element should
"win" and write the full capability atomically. The emulator requires
all 128-bit accesses to be aligned so meets this requirement easily.

#### Provenance {#provenance .unnumbered}

Provenance requires the accesses be atomic as described above, and
require that tag bits are copied correctly: the output tag bit must only
be set if the input had a valid tag bit. These conditions also apply to
scalar accesses.

#### Monotonicity {#monotonicity .unnumbered}

These loads/stores do not attempt to manipulate capabilities, so have no
relevance to Monotonicity.

#### Integrity {#integrity-1 .unnumbered}

The same conditions for scalar and other vector accesses apply to
maintain Integrity: namely that the base capability for each access
should be checked to ensure it is valid. The emulator doesn't allow
capabilities-in-vectors to be dereferenced directly, but if an
implementation allows it those capabilities would also need to be
checked.

### [\[hyp:cap_in_vec_manip\]](#hyp:cap_in_vec_manip){reference-type="ref" reference="hyp:cap_in_vec_manip"} - Manipulating capabilities in vectors {#hypcap_in_vec_manip---manipulating-capabilities-in-vectors .unnumbered}

The emulator limits all manipulation to clearing the tag bit, achieved
by writing data to the register in an integer context. In theory, it's
possible to do more complex transformations, which can be proven by
implementing each vector manipulation on vector elements as sequential
scalar manipulations on scalar elements.

With this method, all pre-existing scalar capability manipulations can
become vector manipulations, but the utility seems limited. For example,
instructions for creating capabilities or manipulating bounds en masse
don't have an obvious use case. If more transformations are added they
should be considered carefully, rather than creating vector equivalents
for all scalar manipulations. For example, revocation as described
in [@xiaCHERIvokeCharacterisingPointer2019] may benefit from a vector
equivalent to `CLoadTags`.

#### Provenance & Monotonicity {#provenance-monotonicity-1 .unnumbered}

Because the only possible manipulations clear the tag bit, it's
impossible to create or change capabilities, so Provenance and
Monotonicity cannot be violated. Any manipulations that create
capabilities, or potentially any manipulations that transfer
capabilities from vector registers directly to scalar registers, would
require more scrutiny.

#### Integrity {#integrity-2 .unnumbered}

As stated before, capabilities-in-vectors cannot be dereferenced
directly, so there is no impact on Integrity.

# Conclusion

This project demonstrated the viability of integrating CHERI with
scalable vector models by producing an example CHERI-RVV implementation.
This required both research effort in studying the related
specifications ([@TR-951; @specification-RVV-v1.0]), demonstrated in
[\[chap:background\]](#chap:background){reference-type="ref"
reference="chap:background"}, and a substantial implementation effort
demonstrated in
[\[chap:hardware,chap:software,chap:capinvec\]](#chap:hardware,chap:software,chap:capinvec){reference-type="ref"
reference="chap:hardware,chap:software,chap:capinvec"}. We produced four
software artifacts: a Rust wrapper for the `cheri-compressed-cap` C
library (900 lines of code), a RISC-V emulator supporting multiple
architecture extensions (5,300 LoC), a fork of CHERI-Clang supporting
CHERI-RVV (400 changed LoC), and test programs for the emulator (3,000
LoC[^48]). Developing these artifacts provided enough information to
make conclusions for the initial hypotheses
([1.1](#tab:hypotheses){reference-type="ref"
reference="tab:hypotheses"}).

## Evaluating hypotheses

[\[hyp:hw_cap_as_vec_mem_ref\]](#hyp:hw_cap_as_vec_mem_ref){reference-type="ref"
reference="hyp:hw_cap_as_vec_mem_ref"} showed that all memory references
can be replaced with capabilities in all RVV instructions while
maintaining functionality.
[\[hyp:hw_cap_bounds_checks_amortized\]](#hyp:hw_cap_bounds_checks_amortized){reference-type="ref"
reference="hyp:hw_cap_bounds_checks_amortized"} then alleviated
performance concerns by showing it was possible to combine the required
capability checks for all vector accesses, amortizing the overall cost
of checking, although with varying practical benefit.

On the software side
[\[hyp:sw_vec_legacy,hyp:sw_pure_compat\]](#hyp:sw_vec_legacy,hyp:sw_pure_compat){reference-type="ref"
reference="hyp:sw_vec_legacy,hyp:sw_pure_compat"} showed that non-CHERI
vectorized code could be run on CHERI systems, and even recompiled for
pure-capability platforms with no source code changes, but that
CHERI-Clang's current state adds some practical limitations. We
developed the `vector_memcpy` test program to show that despite those
limitations, it's possible to write correct CHERI-RVV code on current
compilers.
[\[hyp:sw_stack_vectors,hyp:sw_multiproc\]](#hyp:sw_stack_vectors,hyp:sw_multiproc){reference-type="ref"
reference="hyp:sw_stack_vectors,hyp:sw_multiproc"} address the pausing
and resuming of vector code, specifically saving and restoring
variable-length architectural state, concluding that it is entirely
possible but requires software adjustments.

Through a limited investigation of capabilities-in-vectors,
[\[hyp:cap_in_vec_storage,hyp:cap_in_vec_load_store,hyp:cap_in_vec_manip\]](#hyp:cap_in_vec_storage,hyp:cap_in_vec_load_store,hyp:cap_in_vec_manip){reference-type="ref"
reference="hyp:cap_in_vec_storage,hyp:cap_in_vec_load_store,hyp:cap_in_vec_manip"}
showed that a highly constrained implementation could enable a
fully-functional vectorized `memcpy`, as demonstrated in the
`vector_memcpy_pointers` test program, without violating CHERI security
principles. It should be possible to extend the CHERI-RVV ISA with
vector equivalents of existing CHERI scalar instructions, but we did not
investigate this further.

Clearly, scalable vector models can be adapted to CHERI without
significant loss of functionality. Most of the hypotheses are general
enough to cover other scalable models, e.g. Arm SVE, but any differences
from RVV's model will require careful examination. Given the importance
of vector processing to modern computing, and thus its importance to
CHERI, we hope that this research paves the way for future
vector-enabled CHERI processors.

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
can be implemented in CHERI-Clang[^49] and added to existing
CHERI-RISC-V processors[^50].

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

[]{#wc:end label="wc:end"}

[^1]: Capability Hardware Enhanced RISC Instructions

[^2]: This is a SIMD (Single Instruction Multiple Data) paradigm.

[^3]: It appears memcpy is implemented as a copy of memmove.

[^4]: [`sysdeps/x86_64/multiarch/ifunc-memmove.h` in `bminor/glibc` on
    GitHub](https://github.com/bminor/glibc/blob/7b1cfba79ee54221ffa7d7879433b7ee1728cd76/sysdeps/x86_64/multiarch/ifunc-memmove.h)

[^5]: <https://wiki.riscv.org/display/HOME/Recently+Ratified+Extensions>

[^6]: <https://www.cl.cam.ac.uk/research/security/ctsrd/cheri/cheri-risc-v.html>

[^7]: A single vector register will always have enough bits for all
    elements. The maximum element count is found when SEW is minimized
    (8 bits) and LMUL is maximized (8 registers), and is equal to
    `VLEN * LMUL / SEW = VLEN * 8 / 8 = VLEN`.

[^8]: <https://github.com/riscv/riscv-v-spec/issues/799>

[^9]: If the memory region is idempotent, then `vstart` could any value
    where all preceding elements had completed. It could even be zero,
    in which case all accesses would be retried on resume, as long as it
    could guarantee forward progress.

[^10]: [`semidynamics/OpenVectorInterface` on
    Github](https://github.com/semidynamics/OpenVectorInterface)

[^11]: Segment 0 may be masked out, in which case this is impossible.

[^12]: This allows restarting after raising an exception partway through
    a structure

[^13]: This is a slight simplification. For the purposes of vector
    memory accesses the *otype* of a capability can be ignored, as any
    type other than `UNSEALED` cannot be dereferenced anyway.

[^14]: This has the side-effect that capabilities must be 128-bit
    aligned in memory.

[^15]: Of course, the DDC must be valid when it is used in this mode,
    and all bounds checks etc. must still pass.

[^16]: <https://www.cl.cam.ac.uk/research/security/ctsrd/cheri/cheri-llvm.html>

[^17]: This wasn't derived from documentation, but instead from manual
    inspection of emitted code.

[^18]: i.e. entirely bare-metal without privilege levels for OSs or
    hypervisors.

[^19]: The decoder, and therefore all emulated processors, doesn't
    support RISC-V Compressed instructions.

[^20]: See <https://godbolt.org/z/qj43jssr6> for an example.

[^21]: [`clang/docs/UsersManual.rst:3384` in `llvm/llvm-project` on
    GitHub](https://github.com/llvm/llvm-project/blob/release/13.x/clang/docs/UsersManual.rst#x86)

[^22]: [`clang/lib/CodeGen/TargetInfo.cpp:2811` in `llvm/llvm-project`
    on
    GitHub](https://github.com/llvm/llvm-project/blob/75e33f71c2dae584b13a7d1186ae0a038ba98838/clang/lib/CodeGen/TargetInfo.cpp#L2811)

[^23]: [`rems-project/sail` on
    Github](https://github.com/rems-project/sail)

[^24]: [`CTSRD-CHERI/sail-cheri-riscv` on
    Github](https://github.com/CTSRD-CHERI/sail-cheri-riscv)

[^25]: [`theturboturnip/cheri-compressed-cap` on
    Github](https://github.com/theturboturnip/cheri-compressed-cap)

[^26]: <https://theturboturnip.github.io/files/doc/rust_cheri_compressed_cap/>

[^27]: [`src/crt_init_globals.c` in `CTSRD-CHERI/device-model` on
    GitHub](https://github.com/CTSRD-CHERI/device-model/blob/88e5e8e744d57b88b0dbb8e3456ee0e69afc143b/src/crt_init_globals.c)

[^28]: The "original allocation the pointer is derived
    from"[@memarianExploringSemanticsPointer2019], or in CHERI terms the
    bounds within which the pointer is valid.

[^29]: See
    [\[chap:emu:rvv_int_mode\]](#chap:emu:rvv_int_mode){reference-type="ref"
    reference="chap:emu:rvv_int_mode"} for the reasoning behind this
    decision.

[^30]: In very particular cases, e.g. unmasked unit-strided accesses
    where `nf = 1`, the capability bounds could be used to calculate
    what the offending element must have been. We believe this is too
    niche of a use case to investigate further, particularly given the
    complexity of the resulting hardware.

[^31]: Likely requires two arithmetic operations per element, for
    checking against the top and bottom bounds.

[^32]: e.g. on FPGAs multiplexers can be relatively cheap.

[^33]: Behaviour under the Total Store Ordering extension hasn't been
    defined.

[^34]: e.g. each byte could be written in a separate access.

[^35]: Even instructions that *would* trigger precise traps but are
    guaranteed not to throw an exception or respond to asynchronous
    interrupt may execute out of order.

[^36]: It is difficult to verify the actual corresponding version,
    because there is no readily available specification for v0.1, and
    the extension supports instructions only present from v0.8 such as
    whole register accesses.

[^37]: <https://github.com/riscv-collab/riscv-gcc/issues/320>

[^38]: As described later, CHERI-Clang crashes when intrinsics are used,
    so we use inline assembly instead.

[^39]: RVV slightly differs here, as it allows VLEN smaller than 128.

[^40]: <https://developer.arm.com/Tools%20and%20Software/Arm%20Compiler%20for%20Embedded>

[^41]: We tried using preprocessor macros instead of real functions, but
    they are difficult to program and do not support returning values
    like intrinsics do.

[^42]: [`llvm/lib/CodeGen/CheriBoundAllocas.cpp` in
    `CTSRD-CHERI/llvm-project` on
    GitHub](https://github.com/CTSRD-CHERI/llvm-project/blob/master/llvm/lib/CodeGen/CheriBoundAllocas.cpp)

[^43]: This ensures all memory accesses use valid capabilities.

[^44]: This avoids edge cases with masking, where one part of a
    capability could be modified while the other parts are left alone.

[^45]: The tag bits are implicitly instead of explicitly included here
    because `VLEN,ELEN` must be powers of two.

[^46]: The RVV spec mentions, but does not specify, potential encodings
    for 128-bit element widths and instructions
    ([@specification-RVV-v1.0 p10, p32],
    [\[tab:capinvec:accesswidth\]](#tab:capinvec:accesswidth){reference-type="ref"
    reference="tab:capinvec:accesswidth"}).

[^47]: The encoding mode
    ([\[chap:bg:subsec:cheriencodingmode\]](#chap:bg:subsec:cheriencodingmode){reference-type="ref"
    reference="chap:bg:subsec:cheriencodingmode"}) does not affect
    register usage: when using the Integer encoding mode, instructions
    can still access the vector registers in a capability context. This
    is just like how scalar capability registers are still accessible in
    Integer encoding mode.

[^48]: This doesn't include automatically generated code.

[^49]: See
    [4.4](#chap:software:sec:chericlangchanges){reference-type="ref"
    reference="chap:software:sec:chericlangchanges"} for the other
    required changes to CHERI-Clang.

[^50]: <https://www.cl.cam.ac.uk/research/security/ctsrd/cheri/cheri-risc-v.html>
