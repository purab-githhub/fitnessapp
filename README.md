# FitSync — Adaptive Fitness Companion

A working browser-based MVP for the SIH fitness solution.

## Included now
- Personalized onboarding: goal, level, time and workout window
- Mood-adaptive workout generation
- Time-based workout sizing
- Exercise player with embedded demonstration-video support, instructions and common mistakes
- Exercise alternatives
- Workout completion and persistent local history
- Daily streak calculation
- Streak Freeze
- SOS Save workout
- Progress dashboard and achievements
- Flexible reminder preference using the browser Notification API while the app is open
- Streak Buddy simulation UI
- Responsive mobile-friendly interface

## Future scope
AI camera posture/form correction, pose detection and real-time corrective feedback are intentionally not part of this build.

## Run locally
No build step is required. Serve this folder with any static server, for example:

```bash
python -m http.server 8080
```

Then open `http://localhost:8080`.

## Data
The current MVP uses `localStorage` under `fitsync_v1`, so workouts, streaks, freezes, profile settings and demo buddy state persist in the browser.

For production, replace the storage functions in `app.js` with a backend such as Firebase or Supabase. Suggested collections/tables: users, workouts, buddy_connections, reminders and achievements.

## Exercise videos
The catalogue supports embeddable video URLs. Before a production release, verify ownership, licensing and availability of every exercise demonstration, or host your own properly licensed videos.
