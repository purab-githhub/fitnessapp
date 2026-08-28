# FitSync — Adaptive Fitness Companion

FitSync is the Python/Flask implementation of our SIH fitness solution. It focuses on helping users stay consistent by adapting workouts to their goal, fitness level, available time, and current mood.

## Current solution features

- Registration, login and logout with hashed passwords
- SQLite database created automatically
- Personalized onboarding: goal, level, available time, equipment and reminder window
- Mood-adaptive workout generation
- Goal-prioritized workout generation
- Time-based 5, 10, 20 and 30 minute workout options
- Exercise player with demonstration videos, instructions, common mistakes and alternatives
- Workout timer and completion flow
- Workout history and 7-day progress view
- Daily streak calculation
- Streak Freeze
- SOS Save Workout
- Achievement badges
- Multi-user Streak Buddy lookup using registered accounts
- Profile and flexible reminder preferences
- Browser notification permission control
- Responsive Flask templates and static assets

## Run in GitHub Codespaces

```bash
pip install -r requirements.txt
python app.py
```

Then open the **PORTS** tab, locate port **5000**, and choose **Open in Browser**.

For automatic reload while developing:

```bash
FLASK_DEBUG=1 python app.py
```

## Fresh test database

The SQLite database is created at `instance/fitness.db`.

If you want to reset all test users and data, stop the app and run:

```bash
rm -f instance/fitness.db
python app.py
```

## Important limitation of the current MVP

Reminder windows and browser notification permission are implemented, but reliable background push notifications require deployment plus a push-notification service. Exercise videos are embedded prototype demonstrations and should be replaced with videos that the project owns or is licensed to use before final deployment.

## Future Scope

The following advanced AI module is intentionally outside the current build:

- Camera integration
- Pose detection
- Exercise detection
- Form/posture analysis
- Real-time corrective feedback
