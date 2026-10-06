# Exascale AI Assignment Submission

This workspace contains two complete Data Developer Intern assignment prototypes for Exascale Deeptech & AI.

The actual submission code is inside `project/`. The original assignment brief PDF is kept at the root only as reference material.

## Contents

```text
.
├── Assignment - IIIT NR.pdf
└── project/
    ├── README.md
    ├── TESTING.md
    ├── assignment 1/
    └── assignment 2/
```

## Assignments

| Folder | Assignment | Summary |
| --- | --- | --- |
| `project/assignment 1` | Intelligent Power Demand Forecasting | ML pipeline, Jupyter notebook, FastAPI inference API, and Chart.js dashboard for 24-hour half-hourly power demand forecasting in Dhanbad, Jharkhand. |
| `project/assignment 2` | Carbon Emissions Reporting Platform | GHG Protocol Scope 1 and Scope 2 emissions platform with historical factor selection, override audit trail, analytics APIs, and ESG dashboard. |

## Cleanup Status

- Virtual environments were removed.
- Python caches and pytest caches were removed.
- Planning notes and generated helper scripts were removed.
- Local secrets and local SQLite runtime database were removed.
- Raw assignment data was moved into the relevant assignment folder.

## Recommended Submission Path

Use the `project/` folder as the repository root when pushing to GitHub/GitLab.

```bash
cd project
git init
git add .
git commit -m "Complete Exascale AI assignments"
```

Docker was not available in the current environment, so container build verification should be run on a machine with Docker installed before final submission.

## Deployment Note

Deployment config is included for both layouts:

- If you push this whole folder, Render can use the root `render.yaml`.
- If you push only `project/`, Render can use `project/render.yaml`.

For Vercel, deploy each frontend separately and set the root directory to either `project/assignment 1/frontend` and `project/assignment 2/frontend` from this whole-folder repo, or `assignment 1/frontend` and `assignment 2/frontend` from a `project/`-root repo.

Render's current default Python version is newer than some pinned dependencies support, so Python is pinned to `3.11.9` with `.python-version` files in the repo and backend service roots.
