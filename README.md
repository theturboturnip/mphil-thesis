# Samuel Stark MPhil Thesis

## Build System

This is the LuaTeX source code for my MPhil thesis.

It's based on the "Clean Sample" from [https://github.com/cambridge/thesis].
This folder is not included as a submodule (Overleaf doesn't like them), but the pertinent files are copied into the `./thesis-class/` directory.
If you clone this repository, `./thesis-class/` will be a regular directory.
If you want to upgrade the thesis class to a newer version, running `just upgrade-thesis-class` will clone the full Git repository under `./thesis-class/`, fetch, and pull.

It uses `latexmk` as a build tool, which uses an Overleaf-compatible [latexmkrc](latexmkrc) file.
Differences from the [Overleaf default latexmkrc](https://www.overleaf.com/learn/how-to/How_does_Overleaf_compile_my_project%3F) are marked with comments like so:

```# TURBOTURNIP SPECIFIC```

It also uses the [`just` command runner](https://github.com/casey/just) to simplify remembering build commands.
To build the thesis, run `just b` or `just build-thesis`.
If you don't have `just`, look in the [justfile](justfile) to find the relevant `latexmk` command.

The output file is stored in [`output/thesis.pdf`](output/thesis.pdf).