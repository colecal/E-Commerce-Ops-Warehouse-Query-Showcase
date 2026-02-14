# Screenshots / GIF

This repo is designed to be easy to screenshot for portfolio use.

## Option A (manual)

1. `docker compose up --build`
2. Open http://localhost:8000
3. Click a few queries (AOV Trend, Cohort Retention, Shipping SLA)
4. Take screenshots and place them in `docs/assets/`:
   - `docs/assets/ui-home.png`
   - `docs/assets/ui-results.png`

## Option B (automated via Playwright)

If you have Python + Playwright installed locally:

```bash
pip install playwright
playwright install chromium
python scripts/capture_screenshots.py
```

This will start a browser, load the UI, run a couple queries, and save PNGs into `docs/assets/`.
