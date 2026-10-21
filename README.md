# Real or Fake? – Deepfake awareness survey (Flask + single-page front end)

## Run locally
    pip install -r requirements.txt
    ADMIN_KEY=yourSecret python app.py      # PowerShell: $env:ADMIN_KEY="yourSecret"; python app.py
Open http://localhost:5000 (same Wi-Fi: http://<your-ip>:5000 on a phone).

## Get your data (CSV, UTF-8 with BOM so Excel shows Chinese correctly)
- Wide, 1 row per participant: /admin/export/wide.csv?key=yourSecret
- Long, 1 row per participant x stimulus (for R/SPSS/mixed models): /admin/export/trials.csv?key=yourSecret
- Progress: /admin/count?key=yourSecret
Data live in survey.db (SQLite) – back it up. Answers are saved after each section/round, so drop-outs are kept (completed=0).

## Deploy for real participants
Any Python host (Render, Railway, Fly.io, PythonAnywhere). Start command: `gunicorn app:app`.
Env vars: ADMIN_KEY (required), DB_PATH (point to a persistent disk). Use HTTPS so video sound/autoplay works.

## Edit
- Questions / wording: static/index.html (DEMO, AWARE, FEATURES arrays)
- Stimuli and ground truth: stimuli.json + static/stimuli/ (truth stays on the server until the participant finishes)
- Display time: images 6 s, GIFs 8 s, videos play once (see stim())
- Replace the consent and debrief placeholder text in index.html with your ethics-approved wording.

## Columns
D1..D11 (+_group for D3, +_other for "please specify"), SA1..SI5, then per stimulus sNN_: truth, order, q1 (real/fake), correct, q1_rt_ms, q2_confidence, q3_authenticity, q4_share, q5_feature, view_ms.
Key: s01 GIF real, s02 GIF fake, s03 video real, s04 video fake, s05/s06 image real, s07/s08 image fake, s09 video real, s10 video fake.
