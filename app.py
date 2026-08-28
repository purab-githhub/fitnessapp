import os
import sqlite3
from datetime import date, timedelta
from functools import wraps

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-this-secret")
app.config["DATABASE"] = os.path.join(app.instance_path, "fitness.db")
os.makedirs(app.instance_path, exist_ok=True)

EXERCISES = {
    "jumping_jacks": {"name": "Jumping Jacks", "category": "cardio", "level": "beginner", "minutes": 3, "video": "https://www.youtube.com/embed/c4DAnQ6DtF8", "instructions": "Stand tall, jump feet apart while raising your arms, then return with control.", "mistakes": "Avoid landing with locked knees.", "alternative": "March in place"},
    "squat": {"name": "Bodyweight Squats", "category": "strength", "level": "beginner", "minutes": 4, "video": "https://www.youtube.com/embed/aclHkVaku9U", "instructions": "Keep feet shoulder-width apart, sit hips back, keep chest lifted, then stand.", "mistakes": "Do not let knees collapse inward.", "alternative": "Chair squats"},
    "pushup": {"name": "Push-ups", "category": "strength", "level": "intermediate", "minutes": 4, "video": "https://www.youtube.com/embed/IODxDxX7oi4", "instructions": "Keep your body in one line, lower with control, then press back up.", "mistakes": "Do not sag your hips.", "alternative": "Knee or wall push-ups"},
    "plank": {"name": "Plank", "category": "core", "level": "beginner", "minutes": 3, "video": "https://www.youtube.com/embed/ASdvN_XEl_c", "instructions": "Support yourself on forearms and toes while keeping a neutral spine.", "mistakes": "Avoid raising or dropping your hips.", "alternative": "Knee plank"},
    "lunges": {"name": "Reverse Lunges", "category": "strength", "level": "beginner", "minutes": 4, "video": "https://www.youtube.com/embed/9L3D9Q8J6vQ", "instructions": "Step back, lower with control, and push through the front foot.", "mistakes": "Keep the front knee aligned with the toes.", "alternative": "Split squat hold"},
    "stretch": {"name": "Full Body Stretch", "category": "mobility", "level": "beginner", "minutes": 5, "video": "https://www.youtube.com/embed/g_tea8ZNk5A", "instructions": "Move slowly through gentle stretches and breathe normally.", "mistakes": "Never force a painful range.", "alternative": "Seated stretching"},
    "breathing": {"name": "Breathing Reset", "category": "recovery", "level": "beginner", "minutes": 5, "video": "https://www.youtube.com/embed/aXItOY0sLRY", "instructions": "Sit comfortably and take slow, controlled breaths.", "mistakes": "Do not hold your breath forcefully.", "alternative": "Short guided relaxation"},
    "march": {"name": "Brisk March", "category": "cardio", "level": "beginner", "minutes": 5, "video": "https://www.youtube.com/embed/enYITYwvPAQ", "instructions": "March with an upright posture at a comfortable pace.", "mistakes": "Do not overstride.", "alternative": "Easy walk"},
}

MOOD_RULES = {
    "energetic": ["jumping_jacks", "squat", "pushup", "lunges", "plank"],
    "normal": ["jumping_jacks", "squat", "plank", "stretch"],
    "tired": ["march", "stretch", "plank"],
    "stressed": ["stretch", "breathing", "march"],
    "unwell": ["breathing", "stretch"],
}
GOAL_RULES = {
    "stay_active": [],
    "weight_loss": ["jumping_jacks", "march", "lunges", "squat"],
    "strength": ["squat", "pushup", "lunges", "plank"],
    "flexibility": ["stretch", "breathing"],
}
VALID_MOODS = set(MOOD_RULES)
VALID_MINUTES = {5, 10, 20, 30}


def db():
    con = sqlite3.connect(app.config["DATABASE"])
    con.row_factory = sqlite3.Row
    return con


def init_db():
    con = db()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, password TEXT NOT NULL, goal TEXT DEFAULT 'stay_active', level TEXT DEFAULT 'beginner', available_time INTEGER DEFAULT 20, equipment TEXT DEFAULT 'none', reminder_start TEXT DEFAULT '18:00', reminder_end TEXT DEFAULT '21:00', freeze_tokens INTEGER DEFAULT 1, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS workouts (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, workout_date TEXT NOT NULL, mood TEXT, duration INTEGER DEFAULT 0, exercises TEXT, completed INTEGER DEFAULT 0, is_sos INTEGER DEFAULT 0, UNIQUE(user_id, workout_date, is_sos));
    CREATE TABLE IF NOT EXISTS freezes (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, freeze_date TEXT NOT NULL, reason TEXT, UNIQUE(user_id, freeze_date));
    CREATE TABLE IF NOT EXISTS buddies (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, buddy_email TEXT NOT NULL, status TEXT DEFAULT 'connected', created_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, buddy_email));
    CREATE TABLE IF NOT EXISTS achievements (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, code TEXT NOT NULL, unlocked_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, code));
    """)
    con.commit(); con.close()

@app.before_request
def ensure_db(): init_db()

def current_user():
    user_id = session.get("user_id")
    if not user_id: return None
    con = db(); user = con.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone(); con.close(); return user

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            flash("Please log in to continue.")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped

def day_completed(user_id, day_value=None):
    day_value = day_value or date.today().isoformat()
    con = db()
    workout = con.execute("SELECT 1 FROM workouts WHERE user_id=? AND workout_date=? AND completed=1", (user_id, day_value)).fetchone()
    frozen = con.execute("SELECT 1 FROM freezes WHERE user_id=? AND freeze_date=?", (user_id, day_value)).fetchone()
    con.close(); return bool(workout or frozen)

def streak(user_id):
    count = 0; day_value = date.today()
    if not day_completed(user_id, day_value.isoformat()): day_value -= timedelta(days=1)
    while day_completed(user_id, day_value.isoformat()):
        count += 1; day_value -= timedelta(days=1)
    return count

def unlock_achievements(user_id):
    con = db(); total = con.execute("SELECT COUNT(*) AS c FROM workouts WHERE user_id=? AND completed=1", (user_id,)).fetchone()["c"]; current_streak = streak(user_id)
    codes = []
    if total >= 1: codes.append("first_workout")
    if total >= 10: codes.append("ten_workouts")
    if current_streak >= 7: codes.append("seven_day_streak")
    if current_streak >= 30: codes.append("thirty_day_streak")
    for code in codes: con.execute("INSERT OR IGNORE INTO achievements(user_id, code) VALUES (?, ?)", (user_id, code))
    con.commit(); con.close()

def build_workout(user, mood, minutes, sos=False):
    if sos:
        pool = ["jumping_jacks", "squat", "plank", "stretch"]
    else:
        pool = list(MOOD_RULES.get(mood, MOOD_RULES["normal"]))
        for key in reversed(GOAL_RULES.get(user["goal"], [])):
            if key in pool: pool.remove(key)
            pool.insert(0, key)
    if user["level"] == "beginner":
        beginner_pool = [key for key in pool if EXERCISES[key]["level"] == "beginner"]
        pool = beginner_pool or pool
    chosen, total = [], 0
    for key in pool:
        exercise_minutes = EXERCISES[key]["minutes"]
        if chosen and total + exercise_minutes > minutes: continue
        chosen.append(key); total += exercise_minutes
        if total >= minutes: break
    return chosen or ["stretch"]

def safe_minutes(value):
    try: minutes = int(value)
    except (TypeError, ValueError): return None
    return minutes if minutes in VALID_MINUTES else None

@app.route("/")
def home(): return redirect(url_for("dashboard")) if current_user() else render_template("welcome.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip(); email = request.form.get("email", "").lower().strip(); password = request.form.get("password", "")
        if not name or not email or len(password) < 6:
            flash("Enter a name, valid email, and a password of at least 6 characters."); return redirect(url_for("register"))
        try:
            con = db(); con.execute("INSERT INTO users(name, email, password) VALUES (?, ?, ?)", (name, email, generate_password_hash(password))); con.commit(); user_id = con.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()["id"]; con.close(); session["user_id"] = user_id; return redirect(url_for("onboarding"))
        except sqlite3.IntegrityError:
            flash("Email already registered."); return redirect(url_for("register"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").lower().strip(); password = request.form.get("password", "")
        con = db(); user = con.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone(); con.close()
        if user and check_password_hash(user["password"], password): session["user_id"] = user["id"]; return redirect(url_for("dashboard"))
        flash("Invalid email or password.")
    return render_template("login.html")

@app.route("/logout")
def logout(): session.clear(); return redirect(url_for("home"))

@app.route("/onboarding", methods=["GET", "POST"])
@login_required
def onboarding():
    user = current_user()
    if request.method == "POST":
        minutes = safe_minutes(request.form.get("available_time"))
        if not minutes: flash("Choose a valid workout duration."); return redirect(url_for("onboarding"))
        con = db(); con.execute("UPDATE users SET goal=?, level=?, available_time=?, equipment=?, reminder_start=?, reminder_end=? WHERE id=?", (request.form.get("goal", "stay_active"), request.form.get("level", "beginner"), minutes, request.form.get("equipment", "none"), request.form.get("reminder_start", "18:00"), request.form.get("reminder_end", "21:00"), user["id"])); con.commit(); con.close(); flash("Your personalized fitness plan is ready!"); return redirect(url_for("dashboard"))
    return render_template("onboarding.html", user=user)

@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user(); con = db(); total = con.execute("SELECT COUNT(*) AS c FROM workouts WHERE user_id=? AND completed=1", (user["id"],)).fetchone()["c"]; con.close()
    return render_template("dashboard.html", user=user, streak=streak(user["id"]), total=total, today=day_completed(user["id"]))

@app.route("/workout", methods=["GET", "POST"])
@login_required
def workout():
    user = current_user()
    if request.method == "POST":
        mood = request.form.get("mood", "normal"); minutes = safe_minutes(request.form.get("minutes"))
        if mood not in VALID_MOODS or not minutes: flash("Choose a valid mood and workout duration."); return redirect(url_for("workout"))
        keys = build_workout(user, mood, minutes)
        return render_template("workout.html", user=user, mood=mood, minutes=minutes, keys=keys, exercises=EXERCISES, sos=False)
    return render_template("workout_setup.html", user=user)

@app.route("/complete", methods=["POST"])
@login_required
def complete():
    user = current_user(); mood = request.form.get("mood", "normal"); minutes = safe_minutes(request.form.get("minutes")) or 10; keys = [key for key in request.form.get("keys", "").split(",") if key in EXERCISES]; is_sos = 1 if request.form.get("sos") == "1" else 0
    if not keys: flash("Workout data was invalid. Please start the workout again."); return redirect(url_for("workout"))
    con = db()
    try:
        con.execute("INSERT INTO workouts(user_id, workout_date, mood, duration, exercises, completed, is_sos) VALUES (?, ?, ?, ?, ?, 1, ?)", (user["id"], date.today().isoformat(), mood, minutes, ",".join(keys), is_sos)); con.commit(); message = "Workout completed — great job! 🔥"
    except sqlite3.IntegrityError: message = "You already completed this type of workout today. Your streak is unchanged."
    finally: con.close()
    unlock_achievements(user["id"]); flash(message); return redirect(url_for("dashboard"))

@app.route("/sos")
@login_required
def sos():
    user = current_user(); keys = build_workout(user, "energetic", 5, sos=True)
    return render_template("workout.html", user=user, mood="sos", minutes=5, keys=keys, exercises=EXERCISES, sos=True)

@app.route("/freeze", methods=["POST"])
@login_required
def freeze():
    user = current_user(); today = date.today().isoformat()
    if day_completed(user["id"], today): flash("Today is already protected or completed."); return redirect(url_for("dashboard"))
    if user["freeze_tokens"] < 1: flash("No Streak Freeze is available. Try the SOS workout!"); return redirect(url_for("dashboard"))
    con = db(); con.execute("INSERT OR IGNORE INTO freezes(user_id, freeze_date, reason) VALUES (?, ?, ?)", (user["id"], today, request.form.get("reason", "Personal day"))); con.execute("UPDATE users SET freeze_tokens=freeze_tokens-1 WHERE id=?", (user["id"],)); con.commit(); con.close(); flash("Streak Freeze used. Your consistency is protected. ❄️"); return redirect(url_for("dashboard"))

@app.route("/progress")
@login_required
def progress():
    user = current_user(); con = db(); rows = con.execute("SELECT * FROM workouts WHERE user_id=? AND completed=1 ORDER BY workout_date DESC, id DESC", (user["id"],)).fetchall(); achievements = con.execute("SELECT code FROM achievements WHERE user_id=?", (user["id"],)).fetchall(); con.close(); week = []
    for offset in range(6, -1, -1):
        day_value = (date.today() - timedelta(days=offset)).isoformat(); week.append({"date": day_value, "done": day_completed(user["id"], day_value)})
    return render_template("progress.html", user=user, rows=rows, week=week, ach=[item["code"] for item in achievements], streak=streak(user["id"]))

@app.route("/buddy", methods=["GET", "POST"])
@login_required
def buddy():
    user = current_user()
    if request.method == "POST":
        email = request.form.get("email", "").lower().strip()
        if not email: flash("Enter your buddy's registered email.")
        elif email == user["email"]: flash("Choose another user as your buddy.")
        else:
            con = db(); other = con.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
            if other: con.execute("INSERT OR IGNORE INTO buddies(user_id, buddy_email, status) VALUES (?, ?, 'connected')", (user["id"], email)); con.commit(); flash("Buddy connected!")
            else: flash("No registered user found with that email.")
            con.close()
    con = db(); buddy_rows = con.execute("SELECT * FROM buddies WHERE user_id=?", (user["id"],)).fetchall(); data = []
    for buddy_row in buddy_rows:
        other = con.execute("SELECT id, name, email FROM users WHERE email=?", (buddy_row["buddy_email"],)).fetchone()
        if other: data.append({"name": other["name"], "email": other["email"], "streak": streak(other["id"]), "today": day_completed(other["id"])})
    con.close(); return render_template("buddy.html", user=user, buddies=data)

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = current_user()
    if request.method == "POST":
        minutes = safe_minutes(request.form.get("available_time"))
        if not minutes: flash("Choose a valid workout duration."); return redirect(url_for("profile"))
        con = db(); con.execute("UPDATE users SET name=?, goal=?, level=?, available_time=?, equipment=?, reminder_start=?, reminder_end=? WHERE id=?", (request.form.get("name", user["name"]).strip() or user["name"], request.form.get("goal", user["goal"]), request.form.get("level", user["level"]), minutes, request.form.get("equipment", user["equipment"]), request.form.get("reminder_start", user["reminder_start"]), request.form.get("reminder_end", user["reminder_end"]), user["id"])); con.commit(); con.close(); flash("Profile and reminder preferences updated."); return redirect(url_for("profile"))
    return render_template("profile.html", user=user)

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=os.environ.get("FLASK_DEBUG", "0") == "1")
