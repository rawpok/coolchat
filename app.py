# Final full app.py logic block for required censorship and auto-ban features

import os, json, hashlib, smtplib, random, time, re, threading
from flask import Flask, render_template, request, redirect, session, make_response, jsonify
from email.mime.text import MIMEText

app = Flask(__name__, static_folder="static")
app.secret_key = "changeme-secret"

# File paths
CHAT_LOG = "chatlog.json"
USER_FILE = "users.json"
BAN_FILE = "banned.json"
MOD_FILE = "mods.json"
MUTE_FILE = "mutes.json"
COOKIES_FILE = "cookies.json"
VERIF_CODES = {}
VERIF_TIMES = {}
ADMIN_USERNAME = "admin"
ALT_ADMIN = "doodiebutthole3"
ADMIN_EMAIL = "rawpok@icloud.com"
EMAIL_FROM = "coolchat.noreply@gmail.com"
EMAIL_PASS = "jjievghapfvxout"

# Filtering
SWEAR_WORDS = [
    "fuck", "shit", "bitch", "asshole", "cunt", "fag", "faggot", "nigger",
    "retard", "tranny", "dick", "cock", "pussy", "bastard", "slut", "whore",
    "kike", "coon", "chink", "nigga", "fgt", "a55", "sh1t", "f@ck", "f*ck"
]

def clean_message(text):
    for word in SWEAR_WORDS:
        text = re.sub(rf"\b{re.escape(word)}\b", "#" * len(word), text, flags=re.IGNORECASE)
    return text

def is_perma_ban_trigger(text):
    return text.strip() == "fe80::9087:8f45:8e77:8fc9%12"

def should_auto_ban(username):
    return re.match(r".*admin.*", username, re.IGNORECASE)

def load_json(file, default):
    try:
        if not os.path.exists(file):
            return default
        with open(file, "r") as f:
            return json.load(f)
    except:
        return default

def save_json(file, data):
    try:
        with open(file, "w") as f:
            json.dump(data, f)
    except:
        pass

def hash_password(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

def send_verification_code(code):
    try:
        msg = MIMEText(f"Your admin verification code is: {code}")
        msg["Subject"] = "Admin Login Code"
        msg["From"] = EMAIL_FROM
        msg["To"] = ADMIN_EMAIL
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_FROM, EMAIL_PASS)
            server.sendmail(msg["From"], [msg["To"]], msg.as_string())
    except Exception as e:
        print("EMAIL ERROR:", type(e).__name__, str(e))

# Ensure admin and alt account exist
users = load_json(USER_FILE, {})
if ADMIN_USERNAME not in users:
    users[ADMIN_USERNAME] = hash_password("admin")
if ALT_ADMIN not in users:
    users[ALT_ADMIN] = hash_password("admin")
if "rawpok" in users:
    del users["rawpok"]
save_json(USER_FILE, users)

@app.before_request
def cookie_login():
    if "username" not in session:
        cookies = load_json(COOKIES_FILE, {})
        token = request.cookies.get("login_token")
        if token in cookies:
            session["username"] = cookies[token]

@app.route("/", methods=["GET", "POST"])
def index():
    try:
        if "username" not in session:
            return redirect("/login")
        username = session["username"]
        bans = load_json(BAN_FILE, {})
        if username in bans:
            return render_template("banned.html", reason=bans[username])
        chat = load_json(CHAT_LOG, [])
        if request.method == "POST":
            message = request.form.get("message", "").strip()
            if is_perma_ban_trigger(message):
                bans[username] = "Triggered IP trap."
                save_json(BAN_FILE, bans)
                return "", 204
            message = clean_message(message)
            display = "rawpok" if username == ALT_ADMIN else username
            chat.append({"user": display, "message": message})
            save_json(CHAT_LOG, chat)
            return "", 204
        return render_template("index.html", username=username)
    except Exception as e:
        return f"Internal error: {e}", 500

@app.route("/signup", methods=["GET", "POST"])
def signup():
    try:
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            bans = load_json(BAN_FILE, {})
            mods = load_json(MOD_FILE, [])
            if should_auto_ban(username):
                bans[username] = "Banned for impersonating admin"
                save_json(BAN_FILE, bans)
                return "Banned."
            users = load_json(USER_FILE, {})
            if username in users:
                return "Username exists."
            users[username] = hash_password(password)
            if username.lower() == "toby":
                mods.append(username)
                save_json(MOD_FILE, mods)
            save_json(USER_FILE, users)
            session["username"] = username
            token = str(random.randint(10000000, 99999999))
            cookies = load_json(COOKIES_FILE, {})
            cookies[token] = username
            save_json(COOKIES_FILE, cookies)
            resp = make_response(redirect("/"))
            resp.set_cookie("login_token", token, max_age=60*60*24*30)
            return resp
        return render_template("signup.html")
    except Exception as e:
        return f"Signup failed: {e}", 500

@app.route("/login", methods=["GET", "POST"])
def login():
    try:
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            users = load_json(USER_FILE, {})
            if username in users and users[username] == hash_password(password):
                if username == ADMIN_USERNAME:
                    code = str(random.randint(100000, 999999))
                    VERIF_CODES[username] = code
                    VERIF_TIMES[username] = time.time()
                    send_verification_code(code)
                    session["pending"] = username
                    return redirect("/verify")
                else:
                    session["username"] = username
                    token = str(random.randint(10000000, 99999999))
                    cookies = load_json(COOKIES_FILE, {})
                    cookies[token] = username
                    save_json(COOKIES_FILE, cookies)
                    resp = make_response(redirect("/"))
                    resp.set_cookie("login_token", token, max_age=60*60*24*30)
                    return resp
            return "Invalid login."
        return render_template("login.html")
    except Exception as e:
        return f"Login error: {e}", 500

@app.route("/verify", methods=["GET", "POST"])
def verify():
    if "pending" not in session:
        return redirect("/login")
    if request.method == "POST":
        code = request.form.get("code", "").strip()
        if VERIF_CODES.get(session["pending"]) == code:
            username = session.pop("pending")
            session["username"] = username
            token = str(random.randint(10000000, 99999999))
            cookies = load_json(COOKIES_FILE, {})
            cookies[token] = username
            save_json(COOKIES_FILE, cookies)
            resp = make_response(redirect("/"))
            resp.set_cookie("login_token", token, max_age=60*60*24*30)
            return resp
        return "Incorrect code."
    return render_template("verify.html")

@app.route("/logout")
def logout():
    session.clear()
    resp = make_response(redirect("/login"))
    resp.set_cookie("login_token", "", expires=0)
    return resp

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

def hourly_restart():
    while True:
        time.sleep(3600)
        print("Restarting Flask process.")
        os._exit(0)

threading.Thread(target=hourly_restart, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))
