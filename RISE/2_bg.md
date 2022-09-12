# Background

TODO - something here?

<!-- RISC-V is an open family of ISAs which defines "base integer ISAs" (e.g.
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
ratified, and is the de facto vector extension for RISC-V. -->

<!-- ## A brief history of vector processing

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
a scalable vector model. -->

## The RVV vector model
RVV defines thirty-two vector registers, each of an
implementation-defined constant width `VLEN`. These registers can be
interpreted as *vectors* of *elements*. The program can configure the
size of elements, and the implementation defines a maximum width `ELEN`.

RVV instructions operate on *groups* of vector registers.
The implementation stores two variables, `vstart` and `vl`, which define the start and length of the "body" section within the vector.
Instructions only operate on body elements, and some allow elements within the body to be masked out and ignored.


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
   

<!-- ## Previous RVV implementations

TODO is this necessary  -->

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
reasonable size (see [@woodruffCHERIConcentratePractical2019]),
and using the magic of floating-point
all of this data has been reduced to just 2x the architectural register
size. For example, on 64-bit RISC-V a standard capability is 128-bits
long. The rest of this dissertation assumes capabilities are 128-bits
long for simplicity.

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
manipulate capabilities. If an implementation detects a violation of
either property, it will zero out the tag bit and rely on Integrity
enforcement to ensure it is not dereferenced. Some CHERI-enabled
architectures, such as CHERI-RISC-V, also raise a synchronous exception
when this occurs.

### CHERI-RISC-V ISA

[@TR-951] describes the latest
version of the CHERI architecture (CHERI ISAv8) and proposes
applications to MIPS, x86-64, and RISC-V. CHERI-RISC-V is a mostly
straightforward set of additions to basic RISC-V ISAs. It adds
thirty-two general-purpose capability registers, thirty-two Special
Capability Registers (SCRs), and many new instructions.

The new general-purpose capability registers are each of size
`CLEN = 2 * XLEN` plus a tag bit.
<!-- These registers store compressed
capabilities. -->
While there is always a logical distinction between the
*integer* registers `x0-x31` and *capability* registers
`cx0-cx31`, the architecture may store them in a Split or Merged
register file. A Split register file stores the
integer registers separately from capability registers, so programs can
manipulate them independently. A Merged register file stores thirty-two
registers of length `CLEN`, using the full width for the capability
registers and aliasing the integer registers to the bottom `XLEN` bits.
Under a merged register file, writing to an integer register makes the
capability counterpart invalid.
 <!-- so programs have to be more careful with -->
<!-- register usage. -->

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

### Capability and Integer encoding mode

CHERI-RISC-V specifies two encoding modes, selected using a flag in the
PCC `flags` field. *Capability mode* modifies the behaviour of
pre-existing instructions (e.g. Load Byte) to take address operands as capabilities.
 <!-- This
makes the basic load/store instruction behaviour exactly equivalent to
newly introduced counterparts: e.g. `L[BWHD][U] == L[BWHD][U].CAP`. The
DDC may still be used in this mode via the new instructions e.g.
`S[BWHD].DDC`. -->

*Integer mode* seeks to emulate a standard CHERI-less RISC-V
architecture as much as possible. All pre-existing RISC-V memory access
instructions take address operands as integers, which are dereferenced
relative to the DDC[^15].
<!-- This makes the basic load/store instruction
behaviour exactly equivalent to newly introduced counterparts: e.g.
`L[BWHD][U] == L[BWHD][U].DDC`. -->
New CHERI instructions may still be used
to dereference and inspect capability registers, but all other
instructions access registers in an integer context i.e. ignoring the
upper bits and tag from merged register files.


