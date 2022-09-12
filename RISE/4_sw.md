# The CHERI-RVV software stack

This chapter, being less relevant to RISE/hardware security, has been greatly condensed.

As part of the project, we considered how adding CHERI to RVV would affect the software stack.
We tested our hypotheses by adding CHERI-RVV to Clang, which is the current focus for CHERI and RVV compiler development.
Clang supports three methods of vectorization:

1) Auto-vectorization, where the compiler converts scalar code to vector code
2) Vector intrinsics, where the programmer writes vector code and the compiler handles low-level details e.g. register allocation
3) Inline assembly, where the programmer directly describes the assembly instructions to execute.

Clang currently supports intrinsics and inline assembly for RVV, but not auto-vectorization yet.
This just requires engineering work - Arm SVE, a similar model, has great auto-vectorization.

## Our changes to CHERI-Clang
The first step was to fix up the pre-existing RVV definition in Clang to use capability registers for the base address.
This meant CHERI-RVV assembly code could be compiled, as long as it explicitly referenced capability registers.
Unfortunately, non-CHERI inline assembly could not be automatically compiled under this method.

We investigated updating vector intrinsics to support CHERI, but found the code defining the intrinsics was more complicated than for assembly.
We believe it is possible to update the intrinsics, but it requires significant engineering work.
Other experiments, such as creating C functions to replace the intrinsics, ran into more significant problems.
One of these problems involved storing vectors to the stack.


<!-- ### Adapting vector assembly instructions to CHERI {#addingtochericlang}

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
`int* __capability`) because the macro cannot detect the annotation. -->

<!-- ### Adapting vector intrinsics to CHERI

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
to return them by saving them to the stack, but this had its own issues. -->

### Storing scalable vectors on the stack

If a program uses too much data, or calls a
function which may overwrite register values, the compiler
will save/restore those register values to memory on the stack.
 <!-- Because vector
registers are temporary, and thus may be overwritten by called
functions, they must also be saved/restored from the stack (see
[\[example:saverestore\]](#example:saverestore){reference-type="ref"
reference="example:saverestore"}). -->
This also applies to multiprocessing
systems where a process can be paused, have the state saved, and resume
later. RVV provides whole-register memory access instructions
explicitly to make this process easy[@specification-RVV-v1.0
Section 7.9].

CHERI-Clang contains an LLVM IR pass[^42] which enforces strict bounds
on so-called "stack capabilities" (capabilities pointing to
stack-allocated data), which requires knowing the size of
the data.
This pass requires the size to be known at compile-time, but scalable vectors 
 do not have known sizes until runtime and so cannot currently be stored on the stack.
This can be fixed with engineering effort - on non-CHERI platforms Clang simply finds `VLEN` at runtime.

<!-- This pass assumes all stack-allocated data has a
static size, and crashes when dynamically-sized types e.g. scalable
vectors are allocated. It is therefore impossible (for now) to save
vectors on the stack in CHERI-Clang, although it's clear that it's
theoretically possible. For example, the length of the required vector
allocations could be calculated based on `VLEN` before each stack
allocation is performed, or if performance is a concern stack bounds for
those allocations could potentially be ignored altogether. These
possibilities are investigated further in the next section. -->

## Testing and evaluation {#chap:software:sec:hypotheses}

TODO summarize testing and evaluation


