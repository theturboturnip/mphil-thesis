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
Sections 2-5 each cover one hypothesis in order, and Section 6 concludes.

1. It is possible to use CHERI capabilities as memory references in all vector instructions.
2. The capability bounds checks for vector elements within a known range (e.g. a cache line) can be performed in a single check, amortizing the cost.
3. Legacy vector code can be compiled into a pure-capability form with no changes.
4. It is possible for a vector architecture to load, store, and manipulate capabilities in vector registers without violating CHERI security principles.

