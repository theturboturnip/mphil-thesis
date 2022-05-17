set -e
git clone https://github.com/riscv-collab/riscv-gnu-toolchain.git /scratch/gccs/riscv-gnu-toolchain-rvv-next/
cd /scratch/gccs/riscv-gnu-toolchain-rvv-next/
git switch rvv-next
git submodule update --init --recursive --progress --force ./riscv-gcc
./configure --prefix=/scratch/gccs/outputs/rvv-next/ --with-arch=rv64gcv --with-abi=lp64d --target=riscv64-unknown-elf
make newlib -j16


# NOTE: rvv-next doesn't support intrinsics, but it does support the arch string.
# NOTE: GCC Vector support isn't a focus as of december 2021 https://github.com/riscv-collab/riscv-gcc/issues/320
# NOTE: 