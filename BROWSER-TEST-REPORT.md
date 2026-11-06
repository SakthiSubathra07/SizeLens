# Browser Journey Test Report

**Date:** 2026-11-06  
**App:** `http://127.0.0.1:5000`  
**Result:** All requested user-facing checks passed.

## Checks

| Journey | Expected | Observed | Result |
|---|---|---|---|
| UrbanThread T-shirt, chest 90 / shoulder 40 / waist 74, regular | M | M | Pass |
| NorthLoom, same measurements, regular | S | S | Pass |
| PrimeWeave, same measurements, regular | S | S | Pass |
| Invalid chest input (49 cm) | Validation error | Stayed on form and reported the allowed 50–200 cm range | Pass |
| NorthLoom, chest 92 / shoulder 41 / waist 77, slim | S | S | Pass |
| Same NorthLoom measurements, loose | M | M | Pass |
| UrbanThread chest 130 cm | No good match | No-match state and closest-size comparison shown | Pass |
| Register | Account created and signed in | Redirected to the size form while signed in | Pass |
| Log out, then log in | Existing credentials accepted | Redirected back to the size form | Pass |
| Save measurements | Profile saved only when checkbox selected | Saved measurements and recommendation shown in history | Pass |
| Reuse saved profile | Form prefilled | Height 175, chest 90, shoulder 40, waist 74 cm prefilled | Pass |
| Delete my data | Account, profile, and history removed | Session ended; database had no test account, profile, or recommendation rows; old credentials were rejected | Pass |

## Failures and notes

- No requested user journey failed.
- Invalid input returned HTTP 400 as designed and displayed the validation message.
- A direct browser automation click on the visually hidden fit radio input was intercepted by its visible label. Clicking the visible Slim/Loose option worked and both preference results passed.

## Screenshots

Screenshots captured in the accompanying chat: PrimeWeave recommendation, invalid-input message, loose-fit result, no-match result, prefilled profile form, profile with saved measurements and delete action, and post-deletion login rejection.
