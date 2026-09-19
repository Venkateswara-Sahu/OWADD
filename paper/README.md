# Paper: Vigil — arXiv Preprint

## Files

```
paper/
  main.tex              ← Full paper (IEEE two-column, ~8 pages)
  vigil_paper.bib       ← BibTeX references (13 citations)
  figures/
    fig1_top_features.pdf/png   ← Top-5 drifted features bar chart
    fig2_comparison.pdf/png     ← Vigil vs. baselines comparison
    fig3_per_class.pdf/png      ← Per-attack-class detection rates
    generate_figures.py         ← Re-generate figures from scratch
  baselines/
    run_baselines.py    ← ADWIN/KSWIN/PageHinkley comparison script
```

---

## Step 1 — Compile on Overleaf (Recommended)

1. Go to [https://overleaf.com](https://overleaf.com) → New Project → Upload Project
2. Zip the `paper/` folder contents:
   - `main.tex`
   - `vigil_paper.bib`
   - `figures/fig1_top_features.pdf`
   - `figures/fig2_comparison.pdf`
   - `figures/fig3_per_class.pdf`
3. Upload the zip
4. Overleaf will detect IEEEtran automatically (it's built in)
5. Set compiler to **pdfLaTeX**
6. Click **Recompile** → Download PDF

---

## Step 2 — Create arXiv Account

1. Go to [https://arxiv.org/register](https://arxiv.org/register)
2. Register with your email
3. You need an endorsement for `cs.LG` — request one from the submission form, or ask a professor to endorse you (one-time process, free)

---

## Step 3 — Submit to arXiv

1. Go to [https://arxiv.org/submit](https://arxiv.org/submit)
2. Select category: **cs.LG** (Machine Learning)
3. Cross-list: **cs.CR** (Cryptography and Security)
4. Upload files:
   - `main.tex`
   - `vigil_paper.bib`
   - All 3 figure PDFs
5. Fill metadata:
   - **Title**: `Vigil: Explainable Concept Drift Detection in Network Traffic Streams via Feature-Level Reconstruction Error Attribution`
   - **Authors**: `Venkateswara Sahu`
   - **Abstract**: (copy from paper)
   - **Comments**: `8 pages, 3 figures, 3 tables. Code: https://github.com/Venkateswara-Sahu/OWADD`
   - **Report-no**: leave blank
6. Submit → you get `arXiv:XXXX.XXXXX` within 1-2 business days

---

## Step 4 — Add to Portfolio and Resume

Once you have the arXiv ID:
- Add to portfolio: `[arXiv:XXXX.XXXXX]` next to Vigil project
- Add to resume: under Publications section
  - `Sahu, V. (2026). Vigil: Explainable Concept Drift Detection... arXiv:XXXX.XXXXX`
- Add to GitHub README badge:
  ```markdown
  [![arXiv](https://img.shields.io/badge/arXiv-XXXX.XXXXX-b31b1b)](https://arxiv.org/abs/XXXX.XXXXX)
  ```

---

## Re-generating Figures

```bash
python paper/figures/generate_figures.py
```

## Re-running Baselines

```bash
python paper/baselines/run_baselines.py
```
