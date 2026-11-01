# LaTeX: Résumé Authoring Scenario

Showcase the LaTeX devcontainer by compiling your résumé/CV with `latex-workshop` and Git-driven workflows.

## Prerequisites

- Select the LaTeX stack via `./scripts/use-devcontainer.sh latex` and reopen in the container.
- Place your `.tex` sources under `docs/cv/` (or clone an existing template into that directory).

## Workflow

1. **Open the project in VS Code** inside the LaTeX container. The `latex-workshop` extension is already installed.
2. **Create a new document**:
   ```bash
   mkdir -p docs/cv
   tee docs/cv/resume.tex <<'TEX' >/dev/null
   \documentclass{article}
   \begin{document}
   Hello, world!
   \end{document}
   TEX
   ```
3. **Build the PDF** using the VS Code command *LaTeX Workshop: Build LaTeX project*, or run:
   ```bash
   cd docs/cv
   tectonic resume.tex
   ```
4. **Review output**: the LaTeX Workshop build writes the PDF under `docs/cv/out/` (`latex-workshop.latex.outDir` in `devcontainers/latex/devcontainer.json`); the manual `tectonic resume.tex` writes `resume.pdf` next to the source.
5. **Iterate**: enable auto-build (on save) from the VS Code command palette, commit updates, and push.

## Smoke Test Checklist

- `tectonic resume.tex` exits successfully with no missing packages.
- Generated PDFs land in `docs/cv/out/` (LaTeX Workshop) or next to the source (manual command) and open locally.
- The image has Tectonic only (no `latexmk`, no TeX Live or MiKTeX switch); to use another distribution build your own image.

## Tips

- Add a GitHub Actions workflow (`latex.yml`) to compile and upload PDFs on push for portfolio automation.
- Add spell checking by enabling the built-in VS Code Code Spell Checker extension (already installed).

> CI exercises these instructions via `scripts/scenarios/run-latex-cv.sh`, which builds the LaTeX devcontainer image and compiles `docs/scenarios/examples/resume.tex` with `tectonic`.
