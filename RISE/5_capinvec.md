# Capabilities-in-vectors

Implementing `memcpy` correctly for CHERI systems requires copying the
tag bits as well as the data. As it stands, any vectorized `memcpy`
on the systems described in previous chapters will not copy the tag bits,
because the vector registers cannot store the tag bits and indeed cannot
store valid capabilities. `memcpy` is very frequently vectorized, so it's vital that CHERI-RVV can
implement it correctly. Manipulating capabilities-in-vectors could also
accelerate CHERI-specific processes, such as revoking capabilities for
freed memory[@xiaCHERIvokeCharacterisingPointer2019].
<!-- 
This chapter examines the changes made to the emulator to support
storing capabilities-in-vectors, and determines the conditions required
for the related hypotheses to be true.
[\[appx:capinvec\]](#appx:capinvec){reference-type="ref"
reference="appx:capinvec"} lists the changes made and all the relevant
properties of the emulator that allow storing capabilities in vectors. -->

## Extending the emulator

We defined three goals for capabilities-in-vectors:

1) Vector registers should be able to hold capabilities.
2) At least one vector memory operation should be able to load/store capabilities from vectors.
    -   Because `memcpy` should copy both integer and capability data,
        vector memory operations should be able to handle both together.
3) Vector instructions should be able to manipulate capabilities.
    -   Clearing tag bits counts as manipulation.

First, we considered the impact on the theoretical vector model. We
decided that any operation with elements smaller than `CLEN` cannot
output valid capabilities under any circumstances[^44], meaning a new
element width equal to `CLEN` must be introduced. We set
`ELEN = VLEN = CLEN = 128`[^45] for our vector unit.

Two new memory access instructions were created to take advantage of
this new element width, and the vector model was adjusted to support
128-bit elements. Similar to the CHERI-RISC-V `LC/SC` instructions we
implemented 128-bit unit-stride vector loads and stores, which took over
officially-reserved encodings[^46] we expected official versions to use.
We have not tested other types of access, but expect them to be
noncontroversial. Indexed accesses require specific scrutiny, as they
may be expected to use 128-bit offsets on 64-bit systems.
<!-- The memory
instructions had to be added to CHERI-Clang manually, and Clang already
has support for setting `SEW=128` in the `vsetvl` family. -->
<!-- These instruction changes
affected inline assembly only, rather than adding vector intrinsics,
because CHERI-Clang only supports inline assembly anyway. -->

The next step was to add capability support to the vector register file.
Our approach to capabilities-in-vectors is similar in concept to CHERI-RISC-V's
Merged scalar register file, in that the same bits of a
register can be accessed in two contexts: an integer context, zeroing
the tag, or a capability context which maintains the current tag. The
only instructions which can access data in a capability context are 128-bit memory accesses[^47].
All other instructions
read out untagged integer data and clear tags when writing data.

A new CHERI-specific vector register file was created, where each
register is a `SafeTaggedCap` i.e. either zero-tagged integer data
or a valid tagged capability. This makes it much harder to accidentally
violate Provenance, and reuses the code path (and related security
properties) for accessing capabilities in memory. Just like scalar
accesses, vectorized capability accesses are atomic and 128-bit aligned.

## Testing and evaluation

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


