# FitSync — Adaptive Fitness Companion

A full Python/Flask web application for the SIH fitness solution.

## Included
- Secure registration and login with hashed passwords
- Personalized onboarding: goal, level, available time, equipment and reminder window
- Mood-adaptive workouts
- Time-based workout generation
- Exercise player with demonstration videos, instructions, common mistakes and alternatives
- Workout completion and history
- Daily streak calculation
- Streak Freeze
- SOS Save Workout
- Progress dashboard and achievements
- Real multi-user Streak Buddy using the SQLite user database
- Profile and flexible reminder preferences
- Responsive interface

## Run in GitHub Codespaces

```bash
pip install -r requirements.txt
python app.py
```

Open the **Ports** tab, find port `5000`, and click **Open in Browser**.

## Database

SQLite is created automatically at `instance/fitness.db`.

## Future Scope

AI camera posture/form correction, pose detection and real-time corrective feedback are intentionally excluded from the current build.

## Exercise videos

The prototype uses embedded public demonstration URLs. For production or the final SIH deployment, replace them with demonstration videos you own or are licensed to use.
