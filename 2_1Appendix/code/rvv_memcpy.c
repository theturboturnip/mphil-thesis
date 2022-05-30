#include <riscv_vector.h>

void *memcpy_vec(void *dst, void *src, size_t n) {
  void *save = dst;
  // copy data byte by byte
  for (size_t vl; n > 0; n -= vl, src += vl, dst += vl) {
    // Use a vsetvl intrinsic to get the 
    // vector length for this iteration.
    vl = vsetvl_e8m8(n);

    // Allocate vector registers by declaring
    // variables with vector types
    vuint8m8_t vec_src;
    
    // Pass the vector length to intrinsics
    vle8_v_u8m8(src, vl);
    vse8_v_u8m8(dst, vec_src, vl);
  }
  return save;
}

