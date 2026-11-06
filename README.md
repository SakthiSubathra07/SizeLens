# SizeLens

## What SizeLens does

SizeLens is a Flask app that recommends a clothing size from body measurements
and a brand-specific size chart. It includes T-shirt and jeans charts, a
measurement guide, optional user accounts, saved measurement profiles, and
recommendation history for logged-in users.

## Screenshots

The image paths below are placeholders. Replace them with screenshots of the
running application:

- Home: ![SizeLens home page](docs/home.png)
- Recommendation result: ![Size recommendation result](docs/result.png)
- No-good-match result: ![No good match result](docs/no-match.png)
- Profile: ![Saved measurement profile](docs/profile.png)

## How the algorithm works

The implementation is in `app/recommend.py`; its thresholds are defined in
`app/config.py`.

1. For each size and measurement, the deviation is zero when the value is
   within the inclusive chart range. Otherwise, it is the distance to the
   nearest range boundary.
2. The engine multiplies each deviation by its category weight and sums them.
   Missing measurements are skipped, and the remaining weights are
   renormalized. A lower score is a closer fit.
3. **Body and garment charts:** body measurements are compared directly with
   body-chart ranges. For garment charts, the configured `ease_cm` is added to
   the body measurement before comparison. Body charts do not apply ease.
4. **Fit preference:** `regular` keeps the lowest-scoring size. If the two
   lowest scores differ by less than `MARGIN` (`1.0`), `slim` chooses the
   smaller of those two sizes and `loose` chooses the larger.
5. **No good match:** if the best score is greater than `MAX_SCORE` (`4.0`),
   the engine returns no match rather than a recommended size.
6. **Confidence:** confidence is high when the best score is `0` and the gap
   between the best and runner-up scores is at least
   `CONFIDENCE_HIGH_DIFF` (`1.5`). Otherwise it is medium when the best score
   is at most `CONFIDENCE_MED_MAX_SCORE` (`2.0`); otherwise it is low.

## Run locally on Windows PowerShell

From the project directory:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:SECRET_KEY = "set-a-private-random-secret"
python seed.py
python run.py
```

Open `http://127.0.0.1:5000` in a browser. The app creates its database
automatically at `sizelens.db` in the project directory by default. To use a
different file, set `DATABASE_PATH` before starting the app:

```powershell
$env:DATABASE_PATH = "C:\path\to\data\sizelens.db"
```

Running `python seed.py` resets and reseeds the database. Do not run it against
a database containing data you want to keep. The deployment Procfile uses
`python seed.py --if-empty` instead.

## Run tests

With the project environment active, run:

```powershell
python -m pytest -q
```

## Data privacy

Saving body measurements is optional; the form only saves them to a profile
when the user selects the save checkbox. Passwords are stored as Werkzeug
password hashes. Logged-in users can use **Delete my data** to remove their
account, profile, and recommendation history.

## Brand data

All brand names and size-chart data in SizeLens are fictional.

## Deployment

The included `Procfile` runs `seed.py --if-empty` and then starts the Flask
application with Gunicorn. It initializes size-chart data for a new database
and preserves existing records on subsequent starts. Configure `SECRET_KEY`
and, if needed, `DATABASE_PATH` in the deployment environment.

SQLite's filesystem is not persistent on Render's free tier. The database and
registered users stored there are lost when the service restarts. Options are
to use a persistent disk on a paid plan, use a hosted database, or keep the
deployment demo-only and avoid relying on retained data.
