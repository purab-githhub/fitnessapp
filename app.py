from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3, os
from datetime import date, datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-me-in-production')
app.config['DATABASE'] = os.path.join(app.instance_path, 'fitness.db')
os.makedirs(app.instance_path, exist_ok=True)

EXERCISES = {
 'jumping_jacks': {'name':'Jumping Jacks','category':'cardio','level':'beginner','minutes':3,'video':'https://www.youtube.com/embed/c4DAnQ6DtF8','instructions':'Stand tall, jump feet apart while raising arms, then return.','mistakes':'Avoid landing with locked knees.','alternative':'March in place'},
 'squat': {'name':'Bodyweight Squats','category':'strength','level':'beginner','minutes':4,'video':'https://www.youtube.com/embed/aclHkVaku9U','instructions':'Feet shoulder-width apart, sit hips back, keep chest lifted, then stand.','mistakes':'Do not let knees collapse inward.','alternative':'Chair squats'},
 'pushup': {'name':'Push-ups','category':'strength','level':'intermediate','minutes':4,'video':'https://www.youtube.com/embed/IODxDxX7oi4','instructions':'Keep body in one line, lower chest with control and press back up.','mistakes':'Do not sag hips.','alternative':'Knee or wall push-ups'},
 'plank': {'name':'Plank','category':'core','level':'beginner','minutes':3,'video':'https://www.youtube.com/embed/ASdvN_XEl_c','instructions':'Support yourself on forearms and toes, keeping a neutral spine.','mistakes':'Avoid raising or dropping hips.','alternative':'Knee plank'},
 'lunges': {'name':'Reverse Lunges','category':'strength','level':'beginner','minutes':4,'video':'https://www.youtube.com/embed/9L3D9Q8J6vQ','instructions':'Step back, lower with control, and push through the front foot.','mistakes':'Keep front knee aligned with toes.','alternative':'Split squat hold'},
 'stretch': {'name':'Full Body Stretch','category':'mobility','level':'beginner','minutes':5,'video':'https://www.youtube.com/embed/g_tea8ZNk5A','instructions':'Move slowly through gentle stretches and breathe normally.','mistakes':'Never force a painful range.','alternative':'Seated stretching'},
 'breathing': {'name':'Breathing Reset','category':'recovery','level':'beginner','minutes':5,'video':'https://www.youtube.com/embed/aXItOY0sLRY','instructions':'Sit comfortably and take slow, controlled breaths.','mistakes':'Do not hold your breath forcefully.','alternative':'Short guided relaxation'},
 'march': {'name':'Brisk March','category':'cardio','level':'beginner','minutes':5,'video':'https://www.youtube.com/embed/enYITYwvPAQ','instructions':'March with an upright posture and comfortable pace.','mistakes':'Do not overstride.','alternative':'Easy walk'}
}

MOOD_RULES = {
 'energetic':['jumping_jacks','squat','pushup','lunges','plank'],
 'normal':['jumping_jacks','squat','plank','stretch'],
 'tired':['march','stretch','plank'],
 'stressed':['stretch','breathing','march'],
 'unwell':['breathing','stretch']
}

def db():
    con = sqlite3.connect(app.config['DATABASE']); con.row_factory = sqlite3.Row; return con

def init_db():
    con=db(); con.executescript('''
    CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, password TEXT NOT NULL, goal TEXT DEFAULT 'stay_active', level TEXT DEFAULT 'beginner', available_time INTEGER DEFAULT 20, equipment TEXT DEFAULT 'none', reminder_start TEXT DEFAULT '18:00', reminder_end TEXT DEFAULT '21:00', freeze_tokens INTEGER DEFAULT 1, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS workouts (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, workout_date TEXT NOT NULL, mood TEXT, duration INTEGER DEFAULT 0, exercises TEXT, completed INTEGER DEFAULT 0, is_sos INTEGER DEFAULT 0, UNIQUE(user_id, workout_date, is_sos));
    CREATE TABLE IF NOT EXISTS freezes (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, freeze_date TEXT, reason TEXT);
    CREATE TABLE IF NOT EXISTS buddies (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, buddy_email TEXT, status TEXT DEFAULT 'pending', created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS achievements (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, code TEXT, unlocked_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, code));
    '''); con.commit(); con.close()

@app.before_request
def ensure_db(): init_db()

def current_user():
    if 'user_id' not in session: return None
    con=db(); u=con.execute('SELECT * FROM users WHERE id=?',(session['user_id'],)).fetchone(); con.close(); return u

def login_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapped(*a,**k):
        if not current_user(): return redirect(url_for('login'))
        return fn(*a,**k)
    return wrapped

def day_completed(uid, d=None):
    d=d or date.today().isoformat(); con=db(); r=con.execute('SELECT 1 FROM workouts WHERE user_id=? AND workout_date=? AND completed=1',(uid,d)).fetchone(); f=con.execute('SELECT 1 FROM freezes WHERE user_id=? AND freeze_date=?',(uid,d)).fetchone(); con.close(); return bool(r or f)

def streak(uid):
    count=0; d=date.today()
    if not day_completed(uid,d.isoformat()): d-=timedelta(days=1)
    while day_completed(uid,d.isoformat()): count+=1; d-=timedelta(days=1)
    return count

def unlock(uid):
    con=db(); total=con.execute('SELECT COUNT(*) c FROM workouts WHERE user_id=? AND completed=1',(uid,)).fetchone()['c']; s=streak(uid); codes=[]
    if total>=1: codes.append('first_workout')
    if total>=10: codes.append('ten_workouts')
    if s>=7: codes.append('seven_day_streak')
    if s>=30: codes.append('thirty_day_streak')
    for code in codes: con.execute('INSERT OR IGNORE INTO achievements(user_id,code) VALUES (?,?)',(uid,code))
    con.commit(); con.close()

def build_workout(user,mood,minutes,sos=False):
    keys=['jumping_jacks','squat','pushup','plank'] if sos else MOOD_RULES.get(mood,MOOD_RULES['normal'])
    if user['level']=='beginner': keys=[k for k in keys if EXERCISES[k]['level']=='beginner'] or keys
    chosen=[]; total=0
    for k in keys:
        if total>=minutes: break
        chosen.append(k); total+=EXERCISES[k]['minutes']
    if not chosen: chosen=['stretch']
    return chosen

@app.route('/')
def home(): return redirect(url_for('dashboard')) if current_user() else render_template('welcome.html')

@app.route('/register',methods=['GET','POST'])
def register():
    if request.method=='POST':
        name=request.form['name'].strip(); email=request.form['email'].lower().strip(); password=request.form['password']
        try:
            con=db(); con.execute('INSERT INTO users(name,email,password) VALUES (?,?,?)',(name,email,generate_password_hash(password))); con.commit(); uid=con.execute('SELECT id FROM users WHERE email=?',(email,)).fetchone()['id']; con.close(); session['user_id']=uid; return redirect(url_for('onboarding'))
        except sqlite3.IntegrityError: flash('Email already registered.'); return redirect(url_for('register'))
    return render_template('register.html')

@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        con=db(); u=con.execute('SELECT * FROM users WHERE email=?',(request.form['email'].lower().strip(),)).fetchone(); con.close()
        if u and check_password_hash(u['password'],request.form['password']): session['user_id']=u['id']; return redirect(url_for('dashboard'))
        flash('Invalid email or password.')
    return render_template('login.html')

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('home'))

@app.route('/onboarding',methods=['GET','POST'])
@login_required
def onboarding():
    u=current_user()
    if request.method=='POST':
        con=db(); con.execute('UPDATE users SET goal=?,level=?,available_time=?,equipment=?,reminder_start=?,reminder_end=? WHERE id=?',(request.form['goal'],request.form['level'],int(request.form['available_time']),request.form['equipment'],request.form['reminder_start'],request.form['reminder_end'],u['id'])); con.commit(); con.close(); flash('Your fitness plan is ready!'); return redirect(url_for('dashboard'))
    return render_template('onboarding.html',user=u)

@app.route('/dashboard')
@login_required
def dashboard():
    u=current_user(); con=db(); total=con.execute('SELECT COUNT(*) c FROM workouts WHERE user_id=? AND completed=1',(u['id'],)).fetchone()['c']; con.close(); return render_template('dashboard.html',user=u,streak=streak(u['id']),total=total,today=day_completed(u['id']))

@app.route('/workout',methods=['GET','POST'])
@login_required
def workout():
    u=current_user()
    if request.method=='POST':
        mood=request.form['mood']; minutes=int(request.form['minutes']); keys=build_workout(u,mood,minutes); return render_template('workout.html',user=u,mood=mood,minutes=minutes,keys=keys,exercises=EXERCISES,sos=False)
    return render_template('workout_setup.html',user=u)

@app.route('/complete',methods=['POST'])
@login_required
def complete():
    u=current_user(); mood=request.form.get('mood','normal'); minutes=int(request.form.get('minutes',10)); keys=request.form.get('keys','').split(','); sos=int(request.form.get('sos','0')); con=db();
    try: con.execute('INSERT INTO workouts(user_id,workout_date,mood,duration,exercises,completed,is_sos) VALUES (?,?,?,?,?,?,?)',(u['id'],date.today().isoformat(),mood,minutes,','.join(keys),1,sos)); con.commit()
    except sqlite3.IntegrityError: pass
    con.close(); unlock(u['id']); flash('Workout completed — great job! 🔥'); return redirect(url_for('dashboard'))

@app.route('/sos')
@login_required
def sos():
    u=current_user(); keys=build_workout(u,'energetic',5,True); return render_template('workout.html',user=u,mood='sos',minutes=5,keys=keys,exercises=EXERCISES,sos=True)

@app.route('/freeze',methods=['POST'])
@login_required
def freeze():
    u=current_user(); today=date.today().isoformat()
    if day_completed(u['id'],today): flash('Today is already protected or completed.'); return redirect(url_for('dashboard'))
    if u['freeze_tokens']<1: flash('No Streak Freeze available. Try the SOS workout!'); return redirect(url_for('dashboard'))
    con=db(); con.execute('INSERT INTO freezes(user_id,freeze_date,reason) VALUES (?,?,?)',(u['id'],today,request.form.get('reason','Personal day'))); con.execute('UPDATE users SET freeze_tokens=freeze_tokens-1 WHERE id=?',(u['id'],)); con.commit(); con.close(); flash('Streak Freeze used. Your consistency is protected. ❄️'); return redirect(url_for('dashboard'))

@app.route('/progress')
@login_required
def progress():
    u=current_user(); con=db(); rows=con.execute('SELECT * FROM workouts WHERE user_id=? AND completed=1 ORDER BY workout_date DESC',(u['id'],)).fetchall(); ach=con.execute('SELECT code FROM achievements WHERE user_id=?',(u['id'],)).fetchall(); con.close(); week=[]
    for i in range(6,-1,-1):
        d=(date.today()-timedelta(days=i)).isoformat(); week.append({'date':d,'done':day_completed(u['id'],d)})
    return render_template('progress.html',user=u,rows=rows,week=week,ach=[x['code'] for x in ach],streak=streak(u['id']))

@app.route('/buddy',methods=['GET','POST'])
@login_required
def buddy():
    u=current_user()
    if request.method=='POST':
        email=request.form['email'].lower().strip()
        if email==u['email']: flash('Choose another user as your buddy.')
        else:
            con=db(); exists=con.execute('SELECT id FROM users WHERE email=?',(email,)).fetchone()
            if exists: con.execute('INSERT INTO buddies(user_id,buddy_email,status) VALUES (?,?,?)',(u['id'],email,'connected')); con.commit(); flash('Buddy connected!')
            else: flash('No registered user found with that email.')
            con.close()
    con=db(); buddies=con.execute('SELECT * FROM buddies WHERE user_id=?',(u['id'],)).fetchall(); data=[]
    for b in buddies:
        other=con.execute('SELECT id,name,email FROM users WHERE email=?',(b['buddy_email'],)).fetchone()
        if other: data.append({'name':other['name'],'email':other['email'],'streak':streak(other['id']),'today':day_completed(other['id'])})
    con.close(); return render_template('buddy.html',user=u,buddies=data)

@app.route('/profile',methods=['GET','POST'])
@login_required
def profile():
    u=current_user()
    if request.method=='POST':
        con=db(); con.execute('UPDATE users SET name=?,goal=?,level=?,available_time=?,equipment=?,reminder_start=?,reminder_end=? WHERE id=?',(request.form['name'],request.form['goal'],request.form['level'],int(request.form['available_time']),request.form['equipment'],request.form['reminder_start'],request.form['reminder_end'],u['id'])); con.commit(); con.close(); flash('Profile updated.'); return redirect(url_for('profile'))
    return render_template('profile.html',user=u)

if __name__=='__main__':
    init_db(); app.run(host='0.0.0.0',port=int(os.environ.get('PORT',5000)),debug=True)
