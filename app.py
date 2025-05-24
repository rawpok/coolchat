# Updated app.py: no email, admin PIN with time-based logic, full authentication flow
import os, json, hashlib, random, time, re
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
VERIF_CODES = {}
VERIF_TIMES = {}
ADMIN_USERNAME = "admin"
ADMIN_EMAIL = "rawpok@icloud.com"  # still used in variables

SLURS = ["nigger", "faggot", "retard", "tranny", "coon", "chink", "kike"]

PIN_ROTATION = ["72018", "32912", "1763"]

def load_json(file, default):
    if not os.path.exists(file):
        return default
    with open(file, "r") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f)

def hash_password(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

def contains_slur(text):
    return any(re.search(rf"\b{re.escape(word)}\b", text, re.IGNORECASE) for word in SLURS)

def get_current_pin():
    index = int(time.time() / 30) % len(PIN_ROTATION)
    return PIN_ROTATION[index]

users = load_json(USER_FILE, {})
if ADMIN_USERNAME not in users:
    users[ADMIN_USERNAME] = hash_password("admin")
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
    chat = load_json(CHAT_LOG, [])
    bans = load_json(BAN_FILE, {})
    mutes = load_json(MUTE_FILE, [])
    if username in bans:
        return render_template("banned.html", reason=bans[username])
    if request.method == "POST":
        message = request.form["message"].strip()
        if not message or username in mutes or contains_slur(message):
            return "", 204
        chat.append({"user": username, "message": message})
        save_json(CHAT_LOG, chat)
        return "", 204
    return render_template("index.html", username=username)

@app.route("/messages")
def messages():
    if "username" not in session:
        return "", 403
    return json.dumps(load_json(CHAT_LOG, []))

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        users = load_json(USER_FILE, {})
        if username == ADMIN_USERNAME or username in users:
            return "Username not allowed or already exists."
        users[username] = hash_password(password)
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

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        pin = request.form.get("adminpin", "").strip()
        users = load_json(USER_FILE, {})

        if username in users and users[username] == hash_password(password):
            if username == ADMIN_USERNAME:
                if pin != get_current_pin():
                    return redirect("/verify")
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

@app.route("/verify", methods=["GET", "POST"])
def verify():
    correct_pin = get_current_pin()
    if request.method == "POST":
        input_pin = request.form["adminpin"].strip()
        if input_pin == correct_pin:
            session["username"] = "admin"
            token = str(random.randint(10000000, 99999999))
            cookies = load_json(COOKIES_FILE, {})
            cookies[token] = "admin"
            save_json(COOKIES_FILE, cookies)
            resp = make_response(redirect("/"))
            resp.set_cookie("login_token", token, max_age=60*60*24*30)
            return resp
        return "Wrong PIN."
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))
