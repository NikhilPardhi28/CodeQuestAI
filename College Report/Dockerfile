FROM texlive/texlive:latest-small

RUN tlmgr update --self || true && \
    tlmgr update --self || true && \
    tlmgr install \
        tocloft \
        hyperref \
        url \
        cite \
        xltabular \
        tabularx \
        environ \
        trimspaces \
        pgf \
        tikz-cd \
        wrapfig \
        titlesec \
        fancyhdr \
        pdflscape \
        listings \
        tcolorbox \
        sourcesanspro \
        ly1 \
        mptopdf || true

WORKDIR /work
CMD ["pdflatex", "main.tex"]
