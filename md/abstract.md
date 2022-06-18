CHERI, a generic architecture extension which improves memory safety, has garnered attention from industry partners for its low overhead and compatibility with existing source code.
CHERI has been adapted to multiple ISAs, including RISC-V and Arm, but not to any scalable vector processors.

Vector processing, where the same operation is performed on multiple elements of a "vector" in parallel, is used everywhere in modern computing from high-performance number-crunching to the humble `memcpy`.
[Arm SVE][1] and [RISC-V "V" (a.k.a. RVV)][2] are new flagship vector extensions for Arm and RISC-V, which use a "vector-length agnostic programming model" to allow hardware implementations to choose their vector lengths.
These scalable vector models are intended to stay in use long into the future, and it is essential for CHERI to support them.

This dissertation focuses on RVV, presenting and evaluating a possible "CHERI-RVV" combination ISA by building and testing a reference implementation in Rust.
We find that RVV is easily adaptable to CHERI with no issues, even maintaining binary compatibility with vanilla RVV programs, although other models like Arm SVE may require more investigation.
We find a set of issues with the current CHERI compiler that make source-level compatibility difficult, and show they can be easily resolved with engineering effort.
Finally, we explore storing capabilities-in-vectors in a limited context, to allow implementing `memcpy` with vector instructions, and show it does not violate security properties.

We conclude that it is viable to combine RVV with CHERI to enable vectorized arithmetic and `memcpy` operations without sacrificing performance, source-level compatibility, or memory protection.

[1]: https://arxiv.org/abs/1803.06185 "The Arm Scalable Vector Extension"
[2]: https://github.com/riscv/riscv-v-spec/releases/tag/v1.0 "The RISC-V V Vector extension working draft"