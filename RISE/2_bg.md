# Background

TODO - something here?


## CHERI {#chap:bg:sec:cheri}

In CHERI, addresses/pointers are replaced with capabilities: unforgeable
tokens that provide *specific kinds of access* to an *address* within a
*range of memory*. The above statement is enough to understand what
capabilities contain[^13]:

-   Permission bits, to restrict access

-   The *cursor*, i.e. the address it currently points to

-   The *bounds*, i.e. the range of addresses this capability could
    point to

By using floating-point, all of this data has been reduced to just 2x the architectural register
size (see [@woodruffCHERIConcentratePractical2019]).
For example, on 64-bit RISC-V a standard capability is 128-bits
long, and we assume capabilities are 128-bits
long throughout this write-up.

A CHERI implementation has to enforce three security properties about
its capabilities[@TR-951 Section 1.2.1]:

-   Provenance - Capabilities must always be derived from valid
    manipulations of other capabilities.

-   Integrity - Corrupted capabilities cannot be dereferenced.

-   Monotonicity - Capabilities cannot increase their rights.

Integrity is enforced by tagging registers and memory. Every 128-bit
register and aligned 128-bit region of memory has an associated tag bit,
which denotes if its data encodes a valid capability[^14]. If any
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

CHERI-Clang[^16], the main CHERI-enabled compiler, supports two ways to
compile CHERI-RISC-V which map to the different encoding modes.

*Pure-capability* mode treats all pointers as capabilities, and emits
pre-existing RISC-V instructions that expect to be run in capability
mode[^17].

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

TODO - different addressing modes, FoF

### Exception handling

If synchronous exceptions (e.g. invalid memory access) or asynchronous interrupts
are encountered while executing a vector instruction, RVV defines two ways
to trap them.
In both cases, the PC of the instruction is saved in a register "*epc".

If the instruction should be resumed after handling the trap, e.g. in the case of demand paging,
the implementation may use a "precise trap".
The implementation must complete all instructions up to "*epc", and no instructions after that,
and save the index of the offending vector element in "vstart".
Within the instruction, all vector elements before "vstart" must have committed their results, and all other elements must either
1) not have committed results, or
2) be idempotent e.g. repeatable without changing the outcome.

In other cases "imprecise traps" may be used, which allow instructions after "*epc" and vector elements after "vstart" to commit their results.
"vstart" must still be recorded, however.
   


## The Hypothesis

*It is possible to use CHERI capabilities as memory references in all vector instructions.*

This is entirely true - all RVV memory instructions take the index of a "base address register" in the scalar register file, and it is trivial to index into the capability register file instead.
This can be applied to other ISAs wherever memory references are accessed through a scalar register file, e.g. all Arm Morello scalar instructions and most of Arm SVE's memory instructions.
Notably Arm SVE's `u64base` addressing mode, which uses a vector directly as a set of 64-bit integer addresses[@armltdArmCompilerScalable2019], is not as simple to port to CHERI.

