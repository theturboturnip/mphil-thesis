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

rise:
    @mkdir -p ./output_RISE/
    cat RISE/1_intro.md RISE/2_bg.md RISE/3_hw.md RISE/4_sw.md RISE/5_capinvec.md RISE/6_concl.md > output_RISE/RISE_cutdown.md
    pandoc --wrap=none -N --citeproc output_RISE/RISE_cutdown.md -o output_RISE/content.html
    pandoc --wrap=none -t plain output_RISE/content.html -o output_RISE/content.txt
    wc -c -w output_RISE/content.txt | tee output_RISE/bytecount.txt
    head -c 30200 output_RISE/content.txt > output_RISE/content_30k.txt

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

build-book:
    @mkdir -p ./output_book/
    latexmk -shell-escape -interaction=nonstopmode -lualatex ./thesis_book.tex -outdir=./output_book/

build-submission: build-results build-thesis build-thesis-anon

build-all: build-submission build-book

final: build-submission
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

rcount:
    wc -w RISE/1_intro.md RISE/2_bg.md RISE/3_hw.md RISE/4_sw.md RISE/5_capinvec.md RISE/6_concl.md
    wc -w RISE/RISE_abstract.md

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