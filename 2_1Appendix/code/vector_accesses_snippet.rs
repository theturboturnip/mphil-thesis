/// Converts a decoded memory operation to the list of accesses it performs.
fn get_load_store_accesses(&mut self, rd: u8, addr_p: (u64, Provenance), rs2: u8, vm: bool, op: DecodedMemOp) -> Result<Vec<(VectorElem, u64)>> {
    // Vector of (VectorElem, Address)
    let mut map = vec![];

    let (base_addr, _) = addr_p;

    use DecodedMemOp::*;
    match op {
        Strided{stride, evl, nf, eew, emul, ..} => {
            // For each segment
            for i_segment in self.vstart..evl {
                let seg_addr = base_addr + (i_segment as u64 * stride);

                // If we aren't masked out...
                if !self.vreg.seg_masked_out(vm, i_segment) {
                    // For each field
                    let mut field_addr = seg_addr;
                    for i_field in 0..nf {
                        // ... perform the access
                        let vec_elem = VectorElem::check_with_lmul(
                            // Register group start
                            // For field 0, = rd
                            // For field 1, = rd + (number of registers/group)
                            // etc.
                            rd + (i_field * emul.num_registers_consumed()),
                            eew, emul,
                            // Element index within register group
                            i_segment
                        );
                        map.push((vec_elem, field_addr));
                        // and increment the address
                        field_addr += eew.width_in_bytes();
                    }
                }
            }
        }
        FaultOnlyFirst{evl, nf, eew, emul} => {
            // We don't handle the exceptions here
            // This just lists the accesses that will be attempted
            // This is exactly the same code as for Strided, but it calculates the stride
            let stride = eew.width_in_bytes() * (nf as u64);

            // For each segment
            for i_segment in self.vstart..evl {
                let seg_addr = base_addr + (i_segment as u64 * stride);

                // If we aren't masked out...
                if !self.vreg.seg_masked_out(vm, i_segment) {
                    // For each field
                    let mut field_addr = seg_addr;
                    for i_field in 0..nf {
                        // ... perform the access
                        let vec_elem = VectorElem::check_with_lmul(
                            rd + (i_field * emul.num_registers_consumed()),
                            eew, emul,
                            i_segment
                        );
                        map.push((vec_elem, field_addr));
                        // and increment the address
                        field_addr += eew.width_in_bytes();
                    }
                }
            }
        }
        Indexed{index_ew, evl, nf, eew, emul, ..} => {
            // i = element index in logical vector (which includes groups)
            for i_segment in self.vstart..evl {
                // Get our index
                let seg_offset = self.vreg.load_vreg_elem_int(index_ew, rs2, i_segment)?;
                let seg_addr = base_addr + seg_offset as u64;

                // If we aren't masked out...
                if !self.vreg.seg_masked_out(vm, i_segment) {
                    // For each field
                    let mut field_addr = seg_addr;
                    for i_field in 0..nf {
                        // ... perform the access
                        let vec_elem = VectorElem::check_with_lmul(
                            rd + (i_field * emul.num_registers_consumed()),
                            eew, emul,
                            i_segment
                        );
                        map.push((vec_elem, field_addr));
                        // and increment the address
                        field_addr += eew.width_in_bytes();
                    }
                }
            }
        }
        WholeRegister{num_regs, eew, ..} => {
            if vm == false {
                // There are no masked variants of this instruction
                bail!("WholeRegister operations cannot be masked")
            }

            let mut addr = base_addr;
            let vl = op.evl();
            // For element in register set...
            for i in self.vstart..vl {
                // ...perform the access
                let vec_elem = VectorElem::check_with_num_regs(
                    rd, 
                    eew, num_regs,
                    i as u32
                );
                map.push((vec_elem, addr));
                addr += eew.width_in_bytes();
            }
        }
        ByteMask{evl, ..} => {
            if vm == false {
                // vlm, vsm cannot be masked out
                bail!("ByteMask operations cannot be masked")
            }

            let mut addr = base_addr;
            // evl = number of 8-bit elements required for the mask
            // self.vstart = in terms of bytes
            for i in self.vstart..evl {
                let vec_elem = VectorElem::check_with_lmul(
                    rd,
                    Sew::e8, Lmul::e1,
                    i
                );
                map.push((vec_elem, addr));
                addr += 1;
            }
        }
    };

    Ok(map)
}