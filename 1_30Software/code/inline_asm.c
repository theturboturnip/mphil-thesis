// Godbolt https://godbolt.org/z/rW9orr66a

#include <riscv_vector.h>

void inline_asm_memory(void) {
    int* ptr; int val; vint32m1_t vec_val;
    // "ld a0, 0(a0)" - valid
    asm ("ld %0, %1"
            : "=r"(val)
            : "m"(*ptr));
}


#define CAN_VEC_LOAD_FROM_MEM 0
#if CAN_VEC_LOAD_FROM_MEM
void inline_asm_vector_memory(void) {
    vsetvlmax_e32m1();
    int* ptr;
    vint32m1_t vec_val;
    // "vle32.v v8, 0(a0)" - invalid
    asm ("vle32.v %0, %1"
            : "=vr"(vec_val)
            : "m"(*ptr));
    return 0;
}
#endif // CAN_VEC_LOAD_FROM_MEM

void inline_asm_vector_ptr_reg(void) {
    vsetvlmax_e32m1();
    int* ptr;
    vint32m1_t vec_val;
    // "vle32.v v8, (a0)" - valid
    asm ("vle32.v %0, (%1)"
            : "=vr"(vec_val)
            : "r"(ptr));
}

#if __has_feature(capabilities)
void inline_asm_vector_cap_reg(void) {
    vsetvlmax_e32m1();
    int* ptr;
    vint32m1_t vec_val;
    // "vle32.v v8, (ca0)" - valid
    asm ("vle32.v %0, (%1)"
            : "=vr"(vec_val)
            : "C"(ptr));
}
#endif


void test_both(void) {
    vsetvlmax_e32m1();

    int* ptr;
    vint32m1_t vec_val;

    #if __has_feature(pure_capabilities)
    #define PTR_REG "C"
    #else
    #define PTR_REG "r"
    #endif

    // Produces "vle32.v v8, (ca0)"
    // or "vle32.v v8, (a0)"
    asm ("vle32.v %0, (%1)"
            : "=vr"(vec_val)
            : PTR_REG(ptr));
}