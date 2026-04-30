# Template instructions

## Set up a new Python project

Clone the `lang-tools` repo.

```bash
git clone git@github.com:Pitrified/lang-tools.git
```

Enter the repo folder:

```bash
cd lang-tools
```

Install the dependencies (including the ones needed for the renaming script):

```bash
uv sync --group dev
```

Run the [rename_project.py](meta/rename_project.py) script to rename the project.
This will create a new folder next to the current one (sibling directory).

```bash
# Syntax: uv run rename-project <lang_tools> [--repo-name <repo-name>] [--github-username <username>]
uv run rename-project my_new_project --github-username Pitrified
```

By this point, the project is already set up with the new name.
This README file will be copied in `README_POST_CREATE.md`,
with the name of the project updated.

Go to the new folder:

```bash
cd ../lang-tools
```

Install the project:

```bash
uv sync --all-extras --all-groups
```

## First-time git setup

Initialise a git repository and push to GitHub.
If you supplied `--github-username` when running `rename-project`, the URLs below
are already correct. Otherwise replace `Pitrified` with your GitHub username.

```bash
git init
git add . && git add **/.gitkeep -f
git config user.name "Your Name"
git config user.email "your.email@example.com"
git commit -m "bootstrap project"
git branch -M main
# HTTPS
git remote add origin https://github.com/Pitrified/lang-tools.git
# or SSH
# git remote add origin git@github.com:Pitrified/lang-tools.git
git push -u origin main
```

## First tasks

Open the
[copilot post rename cleanup](scratch_space/vibes/01-post-rename-cleanup.md)
and follow the checklist there.
It guides you through updating the Copilot instructions, deciding which optional
features to keep, and verifying the project is working correctly.


<!-- Install the optional dependencies with the following command: -->
<!-- {{optional_dependencies}} -->
<!-- TODO automagically generate the optional dependencies list -->

Install the required dependencies:
(already done by the `uv sync` command, as the existing dependencies of the template project are kept in the `pyproject.toml` file)
To bump the versions of dependencies, use:

```bash
uv add loguru
uv add --group dev pytest
```

You can update dependencies with:

```bash
uv add loguru --upgrade-package loguru
```

Initialize the git repository, set the identity, and make the first commit:

```bash
git init
git add .
git add **/.gitkeep -f
# gitid ...
git commit -m "Initial commit"
```

## Set up github pages

Visit the
[github pages settings](https://github.com/Pitrified/lang-tools/settings/pages)
and enable github pages, setting deploy from action.

## Install additional dependencies

Install the dependencies you want with the following commands


Log and formatting dependencies

```bash
uv add loguru rich tqdm
```

LLM dependencies

```bash
uv add transformers accelerate
uv add torch
uv add \
    chromadb \
    langchain \
    langchain-chroma \
    langchain-community \
    langchain-huggingface \
    langchain-ollama ollama \
    langchain-openai \
    langgraph \
    sentence_transformers
```

Data dependencies

```bash
uv add \
    pandas numpy matplotlib seaborn scikit-learn \
    plotly altair bokeh
    kaleido==0.2.1
```

Web dependencies

```bash
uv add fastapi uvicorn
uv add streamlit
```

Notebook dependencies

```bash
uv add ipykernel ipywidgets nbformat
```

Scraping dependencies

```bash
uv add \
    beautifulsoup4 lxml \
    httpx \
    requests \
    scrapy \
    aiohttp
```

Test dependencies

```bash
uv add --group dev pytest
uv add --group dev pytest-cov
```
