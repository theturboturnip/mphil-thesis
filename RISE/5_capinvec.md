# Capabilities-in-vectors

Implementing `memcpy` correctly for CHERI systems requires copying the
tag bits as well as the data, which means the vector registers must store the tag bits and thus store valid capabilities.
`memcpy` is frequently vectorized, so it's vital that CHERI-RVV can
implement it correctly. Manipulating capabilities-in-vectors could also
accelerate CHERI-specific processes, such as revoking capabilities for
freed memory[@xiaCHERIvokeCharacterisingPointer2019].

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
this new element width. Similar to CHERI-RISC-V's `LC/SC` instructions, we
implemented 128-bit unit-stride vector loads and stores, which took over
officially-reserved encodings[^46] for 128-bit accesses.
We have not tested other types of access, but expect them to be
noncontroversial.
<!-- Indexed accesses require extra scrutiny, as they
may be expected to use 128-bit offsets on 64-bit systems. -->

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

## The Hypothesis

*It is possible for a vector architecture to load, store, and manipulate capabilities in vector registers without violating CHERI security principles.*

We considered this from three perspectives, checking they each fulfil Provenance, Monotonicity, and Integrity.

### Holding capabilities in vector registers
As long as `VLEN = CLEN`, and a tag bit is stored alongside each one, a single vector register can hold a capability and differentiate it from integer data.
One could also hold multiple capabilities in a register if `VLEN` was an integer multiple of `CLEN`, but this was not tested.
We decided that only `CLEN`-width operations could produce capabilities, thus we had to ensure `ELEN = CLEN`.
Our implementation sets `VLEN = ELEN = CLEN = 128bits`.

To ensure Provenance and Monotonicity were upheld, we decided that the tag bit for a register would only be set when loading a valid capability from memory, and cleared in all other circumstances.
Integrity is not affected by how a capability is stored.

### Moving capabilities between vector registers and memory

Memory access instructions must follow the same rules as scalar capability accesses.
To maintain Provenance they must be `CLEN`-aligned, or at least only load
valid capabilities from aligned addresses, because tag bits only apply
to `CLEN`-aligned regions; and they must be atomic[@TR-951 Section 11.3].

This atomicity requirement applies to the individual element accesses within each vector access too.
If multiple elements within a vector access try to write to the same 128-bit region, TODO

Monotonicity is not affected by simply loading/storing capabilities from memory.
Integrity requires that the accesses themselves are checked against a valid base capability, just like normal scalar and vector accesses.

### Manipulating capabilities in vector registers

The emulator limits all manipulation to clearing the tag bit, achieved
by writing data to the register in an integer context. 
This preserves Provenance and Monotonicity, because it's impossible to create or change capabilities, and doesn't affect Integrity.

In theory it's possible to do more complex transformations, but there aren't many scalar transformations which would benefit from vectorization.
If more transformations are added they
should be considered carefully, rather than creating vector equivalents
for all scalar manipulations. For example, revocation as described
in [@xiaCHERIvokeCharacterisingPointer2019] may benefit from a vector
equivalent to `CLoadTags`.
