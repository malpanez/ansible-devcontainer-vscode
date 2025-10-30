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
   latexmk -pdf resume.tex
   ```
4. **Review output**: the compiled PDF lives under `docs/cv/out/` by default (configured via `devcontainers/latex/devcontainer.json`).
5. **Iterate**: enable auto-build (on save) from the VS Code command palette, commit updates, and push.

## Smoke Test Checklist

- `latexmk -pdf resume.tex` exits successfully with no missing packages.
- Generated PDFs land in `docs/cv/out/` and open locally.
- Optional: switch to TeX Live by editing `devcontainers/latex/devcontainer.json` (`LATEX_DISTRO`/`LATEX_IMAGE`) and rebuilding the container.

## Tips

- Add a GitHub Actions workflow (`latex.yml`) to compile and upload PDFs on push for portfolio automation.
- Use the `latexmkrc` file to customise build options—place it next to your `.tex` sources.
- Add spell checking by enabling the built-in VS Code Code Spell Checker extension (already installed).

> CI exercises these instructions via `scripts/scenarios/run-latex-cv.sh`, which builds the LaTeX devcontainer image and compiles `docs/scenarios/examples/resume.tex` with `latexmk`.
