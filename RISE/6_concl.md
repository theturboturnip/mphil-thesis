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

Based on the hypotheses examined in this write-up and the original dissertation,
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

TODO below is 700 words

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
