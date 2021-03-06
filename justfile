alias b := build-thesis
alias c := count 
alias rb := rebuild
alias ba := build-all

both: build-thesis build-thesis-anon

clean:
    @mkdir -p ./output/
    rm -rf ./output/*
    @mkdir -p ./output_anon/
    rm -rf ./output_anon/*
    @mkdir -p ./submission/
    rm -rf ./submission/*

text:
    @mkdir -p ./output_RISE/
    pandoc -N --citeproc RISE/RISE_cutdown.md -o output_RISE/content.html
    pandoc -t plain output_RISE/content.html -o output_RISE/content.txt
    wc -c output_RISE/content.txt

build-results:
    #!/usr/bin/env sh
    (cd ./1_50Evaluation/data && python3 ./generate_latex.py)

build-thesis: savecount
    @mkdir -p ./output/
    @# Run latexmk on just this thesis
    latexmk -shell-escape -interaction=nonstopmode -lualatex ./thesis.tex -outdir=./output/

build-thesis-anon: savecount
    @mkdir -p ./output_anon/
    latexmk -shell-escape -interaction=nonstopmode -lualatex -pretex="\def\turnipanon{1}" -usepretex ./thesis.tex -outdir=./output_anon/

build-all: build-results build-thesis build-thesis-anon

final: build-all
    #!/usr/bin/env sh
    mkdir -p ./submission/
    cp ./output/thesis.pdf ./submission/sws35-project.pdf
    cp ./output_anon/thesis.pdf ./submission/2095J.pdf
    cp ./code_docs_tested.zip ./submission/2095J-sourcecode.zip


rebuild: clean build-all

count:
    #!/usr/bin/env sh
    # for each content file in the main body
    # run "texcount -1 -sum -merge -q $FILE"
    # and print each command before you run it
    echo 1_*/content.tex chapters.tex | xargs -n1 -t ./texcount.pl -1 -sum -merge -q

opencount:
    xdg-open ./output/wordcount.html

savecount:
    #!/usr/bin/env sh
    mkdir -p ./output/
    ./texcount.pl -sum -merge chapters.tex > ./output/wordcount.txt
    ./texcount.pl -sum -merge chapters.tex -v -html > ./output/wordcount.html

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