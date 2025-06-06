import os, json, hashlib, random, time, re, threading
from flask import Flask, render_template, request, redirect, session, make_response, jsonify

app = Flask(__name__, static_folder="static")
app.secret_key = "changeme-secret"

# File paths
CHAT_LOG = "chatlog.json"
USER_FILE = "users.json"
BAN_FILE = "banned.json"
MOD_FILE = "mods.json"
MUTE_FILE = "mutes.json"
SLOWMODE_FILE = "slowmode.json"
LOCKED_FILE = "locked.json"
COOKIES_FILE = "cookies.json"

ADMIN_USERNAME = "admin"
ALT_ADMIN = "doodiebutthole3"
ADMIN_EMAIL = "rawpok@icloud.com"

VERIF_CODES = {}
VERIF_TIMES = {}

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
    if not os.path.exists(file):
        return default
    try:
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

# Ensure admin and doodie always exist
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
    if "username" not in session:
        return redirect("/login")
    username = session["username"]
    bans = load_json(BAN_FILE, {})
    if username in bans:
        return render_template("banned.html", reason=bans[username])
    chat = load_json(CHAT_LOG, [])
    mutes = load_json(MUTE_FILE, [])
    if request.method == "POST":
        message = request.form.get("message", "").strip()
        if is_perma_ban_trigger(message):
            bans[username] = "Triggered IP trap."
            save_json(BAN_FILE, bans)
            return "", 204
        if username in mutes:
            return "", 204
        if username == ADMIN_USERNAME and message.startswith(":404"):
            return redirect("/trigger404")
        message = clean_message(message)
        display = "rawpok" if username == ALT_ADMIN else username
        chat.append({"user": display, "message": message})
        save_json(CHAT_LOG, chat)
        return "", 204
    return render_template("index.html", username=username)

@app.route("/messages")
def messages():
    if "username" not in session:
        return "", 403
    chat = load_json(CHAT_LOG, [])
    return jsonify(chat)

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if should_auto_ban(username):
            bans = load_json(BAN_FILE, {})
            bans[username] = "Banned for impersonating admin"
            save_json(BAN_FILE, bans)
            return "Banned."
        users = load_json(USER_FILE, {})
        if username in users:
            return "Username exists."
        users[username] = hash_password(password)
        save_json(USER_FILE, users)
        if username.lower() == "toby":
            mods = load_json(MOD_FILE, {})
            mods[username] = True
            save_json(MOD_FILE, mods)
        session["username"] = username
        token = str(random.randint(10000000, 99999999))
        cookies = load_json(COOKIES_FILE, {})
        cookies[token] = username
        save_json(COOKIES_FILE, cookies)
        resp = make_response(redirect("/"))
        resp.set_cookie("login_token", token, max_age=60 * 60 * 24 * 30)
        return resp
    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        users = load_json(USER_FILE, {})
        if username in users and users[username] == hash_password(password):
            session["username"] = username
            token = str(random.randint(10000000, 99999999))
            cookies = load_json(COOKIES_FILE, {})
            cookies[token] = username
            save_json(COOKIES_FILE, cookies)
            resp = make_response(redirect("/"))
            resp.set_cookie("login_token", token, max_age=60 * 60 * 24 * 30)
            return resp
        return "Invalid login."
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    resp = make_response(redirect("/login"))
    resp.set_cookie("login_token", "", expires=0)
    return resp

@app.route("/trigger404")
def trigger404():
    if "username" not in session:
        return redirect("/login")
    if session["username"] not in [ADMIN_USERNAME, ALT_ADMIN]:
        return "Unauthorized", 403
    return render_template("404.html"), 404

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

# Auto restart every hour
def hourly_restart():
    while True:
        time.sleep(3600)
        os._exit(0)

threading.Thread(target=hourly_restart, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))
