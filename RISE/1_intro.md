---
bibliography:
- thesis.bib
csl:
- din-1505-2-alphanumeric.csl
---

# Introduction

The CHERI[^1] architecture extension improves computer
security by checking all memory accesses in
hardware.
Under CHERI, memory cannot be accessed with integer addresses, but must pass
through a *capability*[@TR-941] - unforgeable tokens
that grant fine-grained access to ranges of memory. Instead of
generating them from scratch, capabilities must be *derived* from
another capability with greater permissions.
<!-- For example, a capability
giving read-write access to an array of structures can be used to create
a sub-capability granting read-only access to a single element. -->
This
vastly reduces the scope of security violations through spatial errors
(e.g. buffer overflows[@szekeresSoKEternalWar2013]), and creates
interesting opportunities for software
compartmentalization[@watsonCHERIHybridCapabilitySystem2015].

Industry leaders have recognized the value CHERI provides. Arm Inc have
manufactured the Morello System-on-Chip
<!-- , based on their Neoverse N1 CPU, -->
which incorporates CHERI into the Armv8.2 ISA. 
<!-- While this
represents a great step forward, there are still elements on the SoC
that haven't fully embraced CHERI (e.g. the GPU), and architecture
extensions that haven't been investigated in the context of CHERI. -->
However some features haven't fully embraced CHERI, such as 
Arm's Scalable Vector Extension (SVE)
<!-- (introduced in Armv8.2
but not included in Neoverse N1) -->
, which is designed to remain in use
well into the future[@stephensARMScalableVector2017]. Supporting this
and other scalable vector ISAs is essential to CHERI's
long-term relevance.

<!-- In the context of modern computer architecture, vector processing is the
practice of dividing a large hardware register into a *vector* of
multiple *elements* and executing the same operation on each element in
a single instruction[^2]. This data-level parallelism can drastically
increase throughput, particularly for arithmetic-heavy programs.
However, before computing arithmetic, the vectors must be populated with
data. -->

## Motivation

<!-- Modern vector implementations all provide vector load/store instructions
to access a whole vector's worth of memory. These range from simple
contiguous accesses, to
complex indexed accesses. They can also have per-element
semantics, e.g. "elements must be loaded in order, so if one element
fails the preceding elements are still valid"[@specification-RVV-v1.0
Section 7.7]. If CHERI CPUs want to benefit from vector processing's
increased performance and throughput, they must support those
instructions at some level. But adding CHERI's bounds-checking to the
mix may affect these semantics, and could impact performance (e.g.
checking each element's access in turn may be slow). -->
Modern vector implementations all provide vector load/store instructions.
Vector-enabled CHERI CPUs must support those instructions, 
<!-- For CHERI CPUs  to benefit from vector processing's performance and throughput,
they must support those
instructions, -->
but adding CHERI's bounds-checking for each vector element could impact performance.
<!-- (e.g. checking each element's access in turn may be slow). -->

Vector memory access performance is critical, because
vectors aren't just used for computation.
For example, `glibc` uses vector memory accesses to implement `memcpy` where available.
<!-- includes multiple versions of the
function[^3] taking advantage of vector platforms, then selects one to
use at runtime[^4]. -->
These implementations are written in assembly and
heavily optimized. If they hit the cache, extra cycles of bounds-checking for each access could make a difference.

`memcpy` also raises the important question of how vectors
interact with capabilities. In non-CHERI processors, `memcpy` will copy
pointers around in memory. An equivalent CHERI-enabled vector
memcpy would need to load/store
capabilities from vectors without violating security guarantees.
<!-- This may require more constraints - for example, each vector register
likely needs to be at least as large as a single capability. -->
<!-- 
To explore this topic, we focus on the RISC-V Vector
extension[@specification-RVV-v1.0] (shortened to RVV throughout). This has been ratified by RISC-V International and
will be RISC-V's standard vector ISA moving forward.
Studying RVV will allow reference "CHERI-RVV"
implementations to be built for the CHERI project's open-source RISC-V
cores[^6].
RVV is also a *scalable* vector model, where the length of each vector is
implementation-dependent, which has more potential roadblocks than a
fixed-length vector model. Investigating them here will make it
easier for Arm to combine the Scalable Vector Extension with
CHERI. -->

<!-- ## Hypotheses and Aims -->

The goal of this project is to investigate the impact of, and the
roadblocks for, integrating a scalable vector architecture with CHERI's
memory protection system. Specifically we focus on integrating the RISC-V Vector
extension[@specification-RVV-v1.0] (RVV)
with the CHERI-RISC-V ISA, with the aim of enabling a future CHERI-RVV
implementation and informing the approach for a future CHERI Arm SVE
implementation.

The full dissertation addresses nine hypotheses, but for the sake of brevity we examine four here:
1. It is possible to use CHERI capabilities as memory references in all vector instructions.
2. The capability bounds checks for vector elements within a known range (e.g. a cache line) can be performed in a single check, amortizing the cost.
3. Legacy vector code can be compiled into a pure-capability form with no changes.
4. It is possible for a vector architecture to load, store, and manipulate capabilities in vector registers without violating CHERI security principles.


<!-- 
The investigation was carried out by designing and testing a CHERI-RVV
emulator written in Rust, but that is only a single implementation. To
show that CHERI-RVV is viable for a wide range of processors,
we test nine hypotheses (see TODO). -->


