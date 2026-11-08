# paper_softwarex: SoftwareX paper of pyssms (separate from `paper/`)

Rebuild everything (from the repository root, `.venv`; do not use `-I`, the scripts import their neighbours):

```
python paper_softwarex/make_numbers.py     # results.json from docs/*.json, the shipped bank and the test suite
python paper_softwarex/make_figures.py     # figures/*.pdf and *.png
python paper_softwarex/build_en.py         # official Elsevier OSP template -> manuscript_softwarex.pdf (+ LaTeX zip, highlights)
python paper_softwarex/build_fa.py         # Persian right-to-left version -> manuscript_softwarex_fa.pdf
python paper_softwarex/check_pdf_numbers.py   # the numbers written in both bodies must be identical
```

`content.py` holds the text of both languages with number tokens only; `common.py`, `check_parallel.py` are the shared helpers and the gate
between the two texts. `listing_test.py` runs the code listing of the paper on real NGSIM data
(needs `data_raw/ngsim`, not in git).
