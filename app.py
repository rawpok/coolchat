# Now write the full updated app.py with safe JSON loading logic applied

full_app_code = """
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
SLOWMODE_FILE = "slowmode.json"
LOCKED_FILE = "locked.json"
COOKIES_FILE = "cookies.json"
VERIF_CODES = {}
VERIF_TIMES = {}
ADMIN_USERNAME = "admin"
ALT_ADMIN = "doodiebutthole3"
ADMIN_EMAIL = "rawpok@icloud.com"
EMAIL_FROM = "coolchat.noreply@gmail.com"
EMAIL_PASS = "jjievghapfvxout"

SWEAR_WORDS = [
    "fuck", "shit", "bitch", "asshole", "cunt", "fag", "faggot", "nigger",
    "retard", "tranny", "dick", "cock", "pussy", "bastard", "slut", "whore",
    "kike", "coon", "chink", "nigga", "fgt", "a55", "sh1t", "f@ck", "f*ck"
]
IMAGE_EXTS = [".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"]

def load_json_safe(file, expected_type):
    try:
        if not os.path.exists(file):
            return expected_type()
        with open(file, "r") as f:
            data = json.load(f)
            return data if isinstance(data, expected_type) else expected_type()
    except:
        return expected_type()

def save_json(file, data):
    try:
        with open(file, "w") as f:
            json.dump(data, f)
    except:
        pass

def clean_message(text):
    for word in SWEAR_WORDS:
        text = re.sub(rf"\\b{re.escape(word)}\\b", "#" * len(word), text, flags=re.IGNORECASE)
    return text.replace("<", "&lt;").replace(">", "&gt;")

def is_image_url(url):
    return url.startswith("http") and any(url.lower().endswith(ext) for ext in IMAGE_EXTS)

def is_perma_ban_trigger(text):
    return text.strip() == "fe80::9087:8f45:8e77:8fc9%12"

def should_auto_ban(username):
    return re.match(r".*admin.*", username, re.IGNORECASE)

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

@app.before_request
def cookie_login():
    if "username" not in session:
        cookies = load_json_safe(COOKIES_FILE, list)
        token = request.cookies.get("login_token")
        for entry in cookies:
            if isinstance(entry, dict) and entry.get("token") == token:
                session["username"] = entry.get("username")

@app.route("/", methods=["GET", "POST"])
def index():
    if "username" not in session:
        return redirect("/login")
    username = session["username"]
    bans = load_json_safe(BAN_FILE, dict)
    if username in bans:
        return render_template("banned.html", reason=bans[username])
    chat = load_json_safe(CHAT_LOG, list)
    mutes = load_json_safe(MUTE_FILE, list)
    if request.method == "POST":
        message = request.form.get("message", "").strip()
        if is_perma_ban_trigger(message):
            bans[username] = "Triggered IP trap."
            save_json(BAN_FILE, bans)
            return "", 204
        if username in mutes:
            return "", 204
        display = "rawpok" if username == ALT_ADMIN else username
        if username in [ADMIN_USERNAME, ALT_ADMIN]:
            msg_final = message
        elif is_image_url(message):
            msg_final = f"<img src='{message}' style='max-width:200px;border-radius:8px;'>"
        else:
            msg_final = clean_message(message)
        chat.append({"user": display, "message": msg_final})
        save_json(CHAT_LOG, chat)
        return "", 204
    return render_template("index.html", username=username)

@app.route("/messages")
def messages():
    if "username" not in session:
        return "", 403
    return jsonify(load_json_safe(CHAT_LOG, list))

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        if should_auto_ban(username):
            bans = load_json_safe(BAN_FILE, dict)
            bans[username] = "Banned for impersonating admin"
            save_json(BAN_FILE, bans)
            return "Banned."
        users = load_json_safe(USER_FILE, dict)
        if username in users:
            return "Username exists."
        users[username] = hash_password(password)
        save_json(USER_FILE, users)
        if username.lower() == "toby":
            mods = load_json_safe(MOD_FILE, dict)
            mods[username] = True
            save_json(MOD_FILE, mods)
        session["username"] = username
        token = str(random.randint(10000000, 99999999))
        cookies = load_json_safe(COOKIES_FILE, list)
        cookies.append({"token": token, "username": username})
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
        users = load_json_safe(USER_FILE, dict)
        if username in users and users[username] == hash_password(password):
            if username == ADMIN_USERNAME:
                code = str(random.randint(100000, 999999))
                VERIF_CODES[username] = code
                VERIF_TIMES[username] = time.time()
                send_verification_code(code)
                session["pending"] = username
                return redirect("/verify")
            session["username"] = username
            token = str(random.randint(10000000, 99999999))
            cookies = load_json_safe(COOKIES_FILE, list)
            cookies.append({"token": token, "username": username})
            save_json(COOKIES_FILE, cookies)
            resp = make_response(redirect("/"))
            resp.set_cookie("login_token", token, max_age=60*60*24*30)
            return resp
        return "Invalid login."
    return render_template("login.html")

@app.route("/verify", methods=["GET", "POST"])
def verify():
    if "pending" not in session:
        return redirect("/login")
    if request.method == "POST":
        code = request.form["code"].strip()
        if VERIF_CODES.get(session["pending"]) == code:
            username = session.pop("pending")
            session["username"] = username
            token = str(random.randint(10000000, 99999999))
            cookies = load_json_safe(COOKIES_FILE, list)
            cookies.append({"token": token, "username": username})
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

@app.route("/trigger404")
def trigger404():
    if "username" not in session or session["username"] != ALT_ADMIN:
        return "Unauthorized", 403
    return render_template("404.html"), 404

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

def hourly_restart():
    while True:
        time.sleep(3600)
        os._exit(0)

threading.Thread(target=hourly_restart, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))
"""

with open("/mnt/data/app.py", "w") as f:
    f.write(full_app_code)

"/mnt/data/app.py is now fully updated with correct initial file states and safe fallbacks."
