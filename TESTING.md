# Version 1 verification

Run:

```powershell
python -m pytest -q
python -m streamlit run app.py
```

Upload `sample_data/sample_sales.csv`, then verify:

1. The dataset persists when moving to Prepare.
2. Readiness metrics appear.
3. Cleaning recommendations appear when issues are detected.
4. Apply a recipe and confirm raw data remains unchanged.
5. Before/after metrics update.
6. Transformation history lists each applied operation.
7. Prepared CSV, recipe JSON, package JSON, and log downloads work.
8. Reset preparation restores the raw-only state.
