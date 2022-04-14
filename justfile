alias b := build-thesis
build-thesis:
    @# Run latexmk on just this thesis
    latexmk -lualatex ./thesis.tex -outdir=./output/

open: build-thesis
    xdg-open ./output/thesis.pdf