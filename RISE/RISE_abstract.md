Submission for RISE Competition for Projects in Hardware & Embedded System Security

# Abstract (max 1000 chars)
CHERI, a generic architecture extension which improves memory safety, has garnered attention from industry partners for its low overhead and compatibility with existing source code. CHERI has been adapted to multiple ISAs, including Arm and RISC-V, but not to their scalable vector extensions (Arm SVE and RISC-V "V"/RVV). These extensions are meant to remain relevant long into the future, so it is essential for CHERI to support them.

This project focuses on RVV, presenting and evaluating a "CHERI-RVV" combination ISA by building/testing a reference implementation. We find that RVV is easily adaptable to CHERI with no issues, although other models like Arm SVE may require more investigation. We explore storing capabilities-in-vectors to allow `memcpy` with vector instructions, and show it does not violate security properties.

We conclude that CHERI-RVV is viable and enables secure vectorized `memcpy` without sacrificing performance, source-level compatibility, or memory protection.
