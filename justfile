alias b := build-thesis
build-thesis:
    @# Run latexmk on just this thesis
    latexmk -shell-escape -interaction=nonstopmode -lualatex ./thesis.tex -outdir=./output/

count:
    texcount -1 -sum -merge -q chapters.tex

clean:
    latexmk -lualatex ./thesis.tex -outdir=./output/ -c

open: build-thesis
    xdg-open ./output/thesis.pdf

upgrade-thesis-class:
    #!/usr/bin/env sh
    # if thesis-class is a git repo, fetch+pull
    if [ -d ./thesis-class/.git/ ]; then
        cd ./thesis-class/ && git fetch && git pull
    else
        # if it is not a git repo, then delete and re-clone 
        rm -r ./thesis-class/
        git clone https://github.com/theturboturnip/thesis ./thesis-class/
    fi