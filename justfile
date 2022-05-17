alias b := build-thesis
alias c := count 
alias rb := rebuild
alias ba := build-all

clean:
    latexmk -lualatex ./thesis.tex -outdir=./output/ -c

build-results:
    #!/usr/bin/env sh
    (cd ./1_50Evaluation/data && python3 ./generate_latex.py)

build-thesis:
    @# Run latexmk on just this thesis
    latexmk -shell-escape -interaction=nonstopmode -lualatex ./thesis.tex -outdir=./output/

build-all: build-results build-thesis

rebuild: clean build-all

count:
    #!/usr/bin/env sh
    # for each content file in the main body
    # run "texcount -1 -sum -merge -q $FILE"
    # and print each command before you run it
    echo 1_*/content.tex chapters.tex | xargs -n1 -t texcount -1 -sum -merge -q


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