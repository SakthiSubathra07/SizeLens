import os

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

# Database
DATABASE = os.environ.get(
    'DATABASE_PATH',
    os.path.join(BASE_DIR, 'sizelens.db'),
)

# Recommendation algorithm thresholds
MARGIN = 1.0
MAX_SCORE = 4.0

# Confidence cutoffs
# high if best score == 0 and runner-up - best >= 1.5; medium if best <= 2; else low.
CONFIDENCE_HIGH_DIFF = 1.5
CONFIDENCE_MED_MAX_SCORE = 2.0

SECRET_KEY = os.environ.get('SECRET_KEY')
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
