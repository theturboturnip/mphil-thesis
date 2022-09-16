# Conclusion

This project demonstrated the viability of integrating CHERI with
scalable vector models by producing an example CHERI-RVV implementation.
This required both research effort in studying the related
specifications and a substantial implementation effort. We produced four
software artifacts: a Rust wrapper for the `cheri-compressed-cap` C
library (900 lines of code), a RISC-V emulator supporting multiple
architecture extensions (5,300 LoC), a fork of CHERI-Clang supporting
CHERI-RVV (400 changed LoC), and test programs for the emulator (3,000
LoC[^48]). Developing these artifacts provided enough information to
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
TODO mention testing!!

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

[^28]: The "original allocation the pointer is derived
    from"[@memarianExploringSemanticsPointer2019], or in CHERI terms the
    bounds within which the pointer is valid.

[^32]: e.g. on FPGAs multiplexers can be relatively cheap.

[^44]: This avoids edge cases with masking, where one part of a
    capability could be modified while the other parts are left alone.

[^45]: The tag bits are implicitly instead of explicitly included here
    because `VLEN,ELEN` must be powers of two.

[^47]: The encoding mode
    ([\[chap:bg:subsec:cheriencodingmode\]](#chap:bg:subsec:cheriencodingmode){reference-type="ref"
    reference="chap:bg:subsec:cheriencodingmode"}) does not affect
    register usage: when using the Integer encoding mode, instructions
    can still access the vector registers in a capability context. This
    is just like how scalar capability registers are still accessible in
    Integer encoding mode.

[^48]: This doesn't include automatically generated code.


[^50]: <https://www.cl.cam.ac.uk/research/security/ctsrd/cheri/cheri-risc-v.html>
