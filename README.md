# nba_stats
### A repo that retrieves relevant NBA stats using `nba_api`

## Setup
### Runtime environment
This project is configured to run the notebooks with the runtime dependencies declared in `pyproject.toml`.

Recommended install using pip:

```bash
python -m pip install -U pip setuptools wheel
python -m pip install -e .
```

If you prefer conda, you can still create the environment from `environment.yml`:

```bash
conda env create -f environment.yml
```

### Development dependencies
To install development tools for formatting, linting, and testing:

```bash
python -m pip install -e .[dev]
```

### Notes
- The notebooks use `numpy`, `pandas`, `scikit-learn`, `nba-api`, `ipykernel`, and `jupyter`.
- The `dev` extras include `black`, `isort`, `flake8`, `pre-commit`, `pytest`, and `ipython`.

## Preparing model data

Run `python data_retrieve/build_player_season_dataset.py` after updating the regular-season game logs. It writes leakage-safe player-season features and their following-season outcomes to `data/model/`. A feature row for season *t* contains only season-*t* games; its matching label is the player's realized season-*t + 1* production.
