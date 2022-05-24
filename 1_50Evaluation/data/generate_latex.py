#!/usr/bin/env python3.8

import pandas as pd
from typing import Optional, Dict
from dataclasses import dataclass
import sys, os

test_prefix_rename = {
    "hello_world": {
        "factorial_test": "\\code{factorial(10)}",
        "fibonacci_test_recursive": "\\code{fib(10)} (recursive)",
        "fibonacci_test_memoized": "\\code{fib(33)} (memoized)",
    },
    "vector_memcpy": {
        "vector_memcpy_unit_stride_e": "Unit Stride e",
        "vector_memcpy_strided_": "Strided ",
        "vector_memcpy_indexed_": "Indexed ",
        "vector_memcpy_masked_e": "Unit Stride Masked e",
        "vector_memcpy_masked_bytemask_load_": "Bytemask Load ",
        "vector_memcpy_segmented_": "Unit Stride Segmented ",
        "vector_memcpy_wholereg_": "Whole-Register ",
        "vector_memcpy_unit_stride_faultonlyfirst_": "FoF Memcpy ",
        "vector_memcpy_boundary_faultonlyfirst_": "FoF Boundary "
    },
    "vector_memcpy_pointers": {
        "base_memcpy_capability_test": "Copy",
        "base_memcpy_capability_invalidate_test": "Copy + Invalidate",
    }
}

def rename_test(test_program: str, test: str) -> Optional[str]:
    for prefix, new_prefix in test_prefix_rename[test_program].items():
        if test.startswith(prefix):
            return test.replace(prefix, new_prefix)
    return None

def get_status(test_row) -> str:
    if not test_row["Ran"]:
        return "-"
    if str(test_row["Successful"]) == "True":
        return "Y"
    else:
        return "N"

def generate_table_data(test_program: str, df: pd.DataFrame) -> Dict[str, Dict[str, str]]:
    df = df.loc[df["Test Program"] == test_program]

    tests = df["Test"].unique()

    table_data = {}
    for test in tests:
        test_renamed = rename_test(test_program, test)
        if not test_renamed:
            continue

        test_data = df.loc[df["Test"] == test]

        table_data[test_renamed] = {
            row["Compiler"] + "-" + row["Architecture"]: row["status"]
            for _, row in test_data.iterrows()
        }

    return table_data


def generate_table(test_program: str, df: pd.DataFrame, file, longtable=False):
    table_data = generate_table_data(test_program, df)

    compiler_arch_order = [
        "llvm-13-rv32imv",
        "llvm-13-rv64imv",
        "llvm-trunk-rv64imv",
        "gcc-rv64imv",
        "llvm-13-rv64imvxcheri",
        "llvm-13-rv64imvxcheri-int",
    ]

    print("\\toprule", file=file)
    print("& RV32 & \\multicolumn{5}{c}{RV-64} \\\\", file=file)
    print("\\cmidrule(lr){2-2} \\cmidrule(lr){3-7}", file=file)
    print("& \\code{llvm-13} & \\code{llvm-13} & \\code{llvm-15} & \\code{gcc} & CHERI & CHERI (Int) \\\\", file=file)
    print("\\midrule", file=file)
    if longtable:
        print("\\endhead", file=file)
        print("\\bottomrule", file=file)
        print("\\endfoot", file=file)
        print("\\endlastfoot", file=file)
    for test, status in table_data.items():
        row = f"{test} & "
        row += " & ".join([
            status[compiler_arch]
            for compiler_arch in compiler_arch_order
        ])
        row += "\\\\"
        print(row, file=file)
    print("\\bottomrule", file=file)


def main():
    df = pd.read_csv("results-20220517-193435.tsv", sep="\t", names=["Compiler", "Architecture", "Test Program", "Test", "Ran", "Successful"])
    df["status"] = df.apply(get_status, axis=1)
    print(df)

    # Split into a table for each test program:
    # Program: vector_memcpy
    #  rv32imv            rv64imv         rv64imvxcheri  rv64imvxcheri-int 
    #  -------  ------------------------  -------------  -----------------
    #  llvm-13  gcc  llvm-13  llvm-trunk    CHERI-Clang    CHERI-clang     

    # program_grouped = df.groupby("Test Program")

    tables = ["hello_world", "vector_memcpy_pointers"]

    for table in tables:
        with open(f"{table}_rows.tex", "w") as f:
            generate_table(table, df, file=f)

    with open(f"vector_memcpy_full.tex", "w") as f:
        print("\\begin{longtable}{rcccccc}", file=f)
        print("\\caption{Results --- Vectorized memcpy}\\\\", file=f)
        generate_table("vector_memcpy", df, file=f, longtable=True)
        print("\\end{longtable}", file=f)

if __name__ == '__main__':
    main()