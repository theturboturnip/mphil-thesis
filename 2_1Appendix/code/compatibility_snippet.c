#define ASM_PREG(val) "r"(val)
// GCC doesn't like __has_feature(capabilities), so define a convenience value
// which is only 1 when in LLVM with __has_feature(capabilities)
#define HAS_CAPABILITIES 0

// Patch over differences between GCC, clang, and CHERI-clang
#if defined(__llvm__)
// Clang intrinsics are correct for segmented loads,
// and supports fractional LMUL.
// Clang 14+ has the correct intrinsics for bytemask loads,
// and Clang has been tested with wholereg ASM

    // Use intrinsics for BYTEMASK in newer Clangs,
    // otherwise the intrinsics don't exist
    #if __clang_major__ >= 14
        #define ENABLE_BYTEMASK 1
        #define USE_ASM_FOR_BYTEMASK 0
    #else
        // LLVM 13 does not support bytemask
        #define ENABLE_BYTEMASK 0
    #endif

    #if __has_feature(capabilities)
        #undef HAS_CAPABILITIES
        #define HAS_CAPABILITIES 1

        #if __has_feature(pure_capabilities)
            #undef ASM_PREG
            #define ASM_PREG(val) "C"(val)
        #endif

        // Enable everything
        #define ENABLE_UNIT 1
        #define ENABLE_STRIDED 1
        #define ENABLE_INDEXED 1
        #define ENABLE_MASKED 1
        #define ENABLE_SEGMENTED 1
        #define ENABLE_FRAC_LMUL 1
        #define ENABLE_ASM_WHOLEREG 1
        #define ENABLE_FAULTONLYFIRST 1
        // BYTEMASK is disabled above

        // Use ASM for everything
        #define USE_ASM_FOR_UNIT 1
        #define USE_ASM_FOR_STRIDED 1
        #define USE_ASM_FOR_INDEXED 1
        #define USE_ASM_FOR_MASKED 1
        #define USE_ASM_FOR_SEGMENTED 1
        // Wholereg has no intrinsics, always ASM
        #define USE_ASM_FOR_FAULTONLYFIRST 1
    #else
        // Enable everything
        #define ENABLE_UNIT 1
        #define ENABLE_STRIDED 1
        #define ENABLE_INDEXED 1
        #define ENABLE_MASKED 1
        #define ENABLE_SEGMENTED 1
        #define ENABLE_FRAC_LMUL 1
        #define ENABLE_ASM_WHOLEREG 1
        #define ENABLE_FAULTONLYFIRST 1

        // Use intrinsics for everything
        #define USE_ASM_FOR_UNIT 0
        #define USE_ASM_FOR_STRIDED 0
        #define USE_ASM_FOR_INDEXED 0
        #define USE_ASM_FOR_MASKED 0
        #define USE_ASM_FOR_SEGMENTED 0
        // Wholereg has no intrinsics, always ASM
        #define USE_ASM_FOR_FAULTONLYFIRST 0
    #endif
#elif defined(__GNUC__) && !defined(__INTEL_COMPILER)
// GNU exts enabled, not in LLVM or Intel, => in GCC

// GCC from RISC-V toolchain rvv-intrinsics branch
// has incorrect names for segmented intrinsics,
// doesn't support fractional LMUL,
// doesn't support byte-mask,
// emits incorrect code for fault-only-first intrinsics
//   (it seems to emit a vsetvli instruction).

    // Enable everything except fractional LMUL and bytemask
    #define ENABLE_UNIT 1
    #define ENABLE_STRIDED 1
    #define ENABLE_INDEXED 1
    #define ENABLE_MASKED 1
    #define ENABLE_SEGMENTED 1
    #define ENABLE_FRAC_LMUL 0
    #define ENABLE_BYTEMASK 0
    #define ENABLE_ASM_WHOLEREG 1
    #define ENABLE_FAULTONLYFIRST 1

    // Use intrinsics for all except segmented loads
    #define USE_ASM_FOR_UNIT 0
    #define USE_ASM_FOR_STRIDED 0
    #define USE_ASM_FOR_INDEXED 0
    #define USE_ASM_FOR_MASKED 0
    #define USE_ASM_FOR_SEGMENTED 1
    // bytemask is disabled
    #define USE_ASM_FOR_BYTEMASK 0
    // Wholereg is always ASM
    // fault-only-first intrinsics emit the wrong instruction
    #define USE_ASM_FOR_FAULTONLYFIRST 1
#endif