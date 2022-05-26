
#include <stdint.h>

void test_auto_vector(int64_t* data, int64_t n) {
    for (int i = 0; i < n; i++) {
        data[i] += 1;
    }
}

#include <arm_sve.h>

void test_intrinsics_sve(int64_t* data, int64_t n) {
    int64_t i = 0;
    svbool_t pg = svwhilelt_b64(i, n);
    svint64_t one = svdup_s64(1);
    do {
        svint64_t d_vec = svld1(pg, &data[i]);
        svst1(pg, &data[i], svadd_z(pg, d_vec, one));
        i += svcntd();
        pg = svwhilelt_b64(i, n);
    }
    while (svptest_any(svptrue_b64(), pg)); 
}

void test_asm_sve(int64_t* data, int64_t n) {
    int64_t i = 0;

    asm ("whilelt p0.d, %0, %1" :: "r"(i), "r"(n));
    asm ("mov z0.d, #1");
    asm("loop:");
    {
        // svint64_t d_vec = svld1(pg, &data[i]);
        // Load data[i] -> z1.d, where i = 64-bit index (3 bit shift up from 8-bit)
        asm ("ld1d z1.d, p0/z, [%0, %1, lsl #3]" :: "r"(data), "r"(i));
        // Add z1 + z0, storing the results in z1, where p0/Masks the addition 
        asm ("add z1.d, p0/m, z1.d, z0.d");
        asm ("st1d z1.d, p0, [%0, %1, lsl #3]" :: "r"(data), "r"(i) : "memory");
        // svst1(pg, &data[i], svadd_z(pg, d_vec, one));
        i += svcntd();
        // This sets the Z flag to 1 if nothing is left
        asm ("whilelt p0.d, %0, %1" :: "r"(i), "r"(n));
        // b.ne = Not Equal = (if Z flag is 0)
        // if Z flag is 0 i.e. something is left, jump to loop
        asm ("b.ne loop");
    }
}
