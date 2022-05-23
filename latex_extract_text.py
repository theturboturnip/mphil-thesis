#!/usr/bin/env python3

import argparse
import enum
import re
from dataclasses import dataclass
from pathlib import Path

DOC_START=re.compile(r'\\begin{document}')
DOC_END=re.compile(r'\\end{document}')
INCLUDE=re.compile(r'\\(input|include){([^}]+)}')
BEGIN_END=re.compile(r'\\(begin|end){([^}]+)}')
COMMENTS=re.compile(r'%(?<!\\).*$', flags=re.MULTILINE)

GOOD_MACRO=re.compile(r'\\(cref|ref|cite|todocite|todoref){([^}]+)}')

TOO_MANY_NEWLINES=re.compile(r'\n\n+')

from pylatexenc.latex2text import LatexNodes2Text

@dataclass
class LatexFile:
    path: Path
    data: str

    @staticmethod
    def from_file(path: Path) -> 'LatexFile':
        with open(path, 'r') as f:
            return LatexFile(
                path=path,
                data=f.read()
            )

    def extract_inner(self, require_document_begin: bool = False) -> 'LatexFile':
        doc_start = DOC_START.search(self.data)
        if doc_start:
            doc_end = DOC_END.search(self.data, pos=doc_start.end())
            if not doc_end:
                raise RuntimeError(f"Latex file {self.path} had \\begin{{document}} but no \\end{{document}}")

            return LatexFile(
                path = self.path,
                data = self.data[doc_start.end():doc_end.start()]
            )
        elif require_document_begin:
            raise RuntimeError(f"Latex file {self.path} had no \\begin{{document}} tag, was required.")
        else:
            return self

    def remove_comments(self) -> 'LatexFile':
        return LatexFile(
            path=self.path,
            data=COMMENTS.sub("", self.data)
        )

    def with_includes(self, include_basepath: Path) -> 'LatexFile':
        includes = INCLUDE.finditer(self.data)

        new_data = ""
        old_data_start_pos = 0
        for include in includes:
            # Add data from the end of the last include up to the start of this include.
            new_data += self.data[old_data_start_pos:include.start()]

            # Find the included_file
            include_filepath = include_basepath / f"{include.group(2)}.tex"
            included_file = LatexFile.from_file(include_filepath).remove_comments().extract_inner().with_includes(include_basepath)
            
            # Add the contents of the included file
            new_data += included_file.data
            
            # New "last include" endpoint
            old_data_start_pos = include.end()
        new_data += self.data[old_data_start_pos:]

        return LatexFile(
            path=self.path,
            data=new_data
        )

    def remove_begin_end(self) -> 'LatexFile':
        new_data = ""
        old_data_start_pos = 0
        begin_end_stack = []
        for begin_or_end in BEGIN_END.finditer(self.data):
            if not begin_end_stack:
                new_data += self.data[old_data_start_pos:begin_or_end.start()]

            if begin_or_end.group(1) == 'begin':
                begin_end_stack.append(begin_or_end.group(2))
            elif begin_or_end.group(1) == 'end':
                if begin_end_stack[-1] == begin_or_end.group(2):
                    begin_end_stack.pop()
                else:
                    raise RuntimeError(f"Latex file {self.path} has mismatched begin/end stack: ended {begin_or_end.group(2)} when stack = {begin_end_stack}")
            else:
                raise RuntimeError(f"{self.path} Unexpected hit for begin/end: {begin_or_end.group(0)}")
            old_data_start_pos = begin_or_end.end()

        new_data += self.data[old_data_start_pos:]

        return LatexFile(
            path=self.path,
            data=new_data
        )

    def shorten_newline_chains(self) -> 'LatexFile':
        return LatexFile(
            path=self.path,
            data=TOO_MANY_NEWLINES.sub("\n\n", self.data)
        )

    # def replace_good_macros(self) -> 'LatexFile':
    #     for good_macro in 

if __name__ == '__main__':
    parser = argparse.ArgumentParser("latex_extract_text")
    parser.add_argument("input_file", type=str)
    parser.add_argument("--output_folder", type=str, default=None)

    args = parser.parse_args()
    base_path = Path(args.input_file)
    if not base_path.is_file():
        raise RuntimeError(f"{base_path} is not a file")
    if not str(base_path).endswith(".tex"):
        raise RuntimeError(f"{base_path} is not a TeX file")

    base_file = LatexFile.from_file(base_path)
    base_dir = base_path.parent

    file_with_includes = base_file.remove_comments().extract_inner().with_includes(base_dir)

    # TODO extract captions, footnotes

    # Remove all things inside \begin{}\end{} pairs
    file_without_special = file_with_includes.remove_begin_end().shorten_newline_chains()

    output = LatexNodes2Text().latex_to_text(
        file_without_special.data
            .replace("\\code","")
            .replace("\\shell", "")
            .replace("\\texttt", "")
            .replace("\\must", "must")
            .replace("\\should", "should")
    )
    output = TOO_MANY_NEWLINES.sub("\n\n", output)
    output = output.replace("<cit.>", "[0]")
    output = output.replace("<ref>", "Ref 0")
    output = output.replace("`", "'")
    output = output.replace("''", '"')

    if args.output_folder:
        output_folder = Path(args.output_folder)
        chapters = output.split("CHAPTER: ")

        for i, c in enumerate(chapters):
            with open(output_folder / f"chapter{i:02d}.txt", 'w') as f:
                f.write(c)
    else:
        print(output)
