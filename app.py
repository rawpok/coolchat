# Updated app.py logic to include :cmds command to open /commands.html
# and a basic slur filter
import re
from flask import Flask, render_template, request, redirect, session, make_response, jsonify
import os, json, hashlib, smtplib, random, time
from email.mime.text import MIMEText

app = Flask(__name__, static_folder="static")
app.secret_key = "changeme-secret"

CHAT_LOG = "chatlog.json"
USER_FILE = "users.json"
BAN_FILE = "banned.json"
MOD_FILE = "mods.json"
MUTE_FILE = "mutes.json"
SLOWMODE_FILE = "slowmode.json"
LOCKED_FILE = "locked.json"
VERIF_CODES = {}
VERIF_TIMES = {}
ADMIN_USERNAME = "admin"
ADMIN_EMAIL = "rawpok@icloud.com"

SLURS = ["nigger", "faggot", "retard", "tranny", "coon", "chink", "kike"]  # You may customize this list

# -- Utility Functions --

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

def send_verification_code(code):
    msg = MIMEText(f"Your admin verification code is: {code}")
    msg["Subject"] = "Admin Login Code"
    msg["From"] = "destynp329@gmail.com"
    msg["To"] = ADMIN_EMAIL
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login("destynp329@gmail.com", "YOUR_APP_PASSWORD")
            server.sendmail(msg["From"], [msg["To"]], msg.as_string())
    except Exception as e:
        print("Failed to send email:", e)

# -- Default Admin Setup --

users = load_json(USER_FILE, {})
if ADMIN_USERNAME not in users:
    users[ADMIN_USERNAME] = hash_password("admin")
    save_json(USER_FILE, users)

@app.route("/", methods=["GET", "POST"])
def index():
    if "username" not in session:
        return redirect("/login")

    username = session["username"]
    chat = load_json(CHAT_LOG, [])
    users = load_json(USER_FILE, {})
    mods = load_json(MOD_FILE, [])
    bans = load_json(BAN_FILE, {})
    mutes = load_json(MUTE_FILE, [])
    slow = load_json(SLOWMODE_FILE, {})
    locked = load_json(LOCKED_FILE, {"status": False})

    if username in bans:
        return render_template("banned.html", reason=bans[username])

    if request.method == "POST":
        now = time.time()
        if locked.get("status") and username not in [ADMIN_USERNAME] + mods:
            return "Chat is locked.", 403
        if slow.get("seconds") and username != ADMIN_USERNAME:
            last = slow.get(username, 0)
            if now - last < slow["seconds"]:
                return "You're typing too fast.", 429
            slow[username] = now
            save_json(SLOWMODE_FILE, slow)

        message = request.form["message"].strip()
        if not message:
            return "", 204

        def send_system(msg): chat.append({"user": "System", "message": msg})

        is_admin = username == ADMIN_USERNAME
        is_mod = username in mods
        def is_privileged(): return is_admin or is_mod

        # Slur filter
        if contains_slur(message):
            send_system(f"{username} tried to send a blocked message.")
            save_json(CHAT_LOG, chat)
            return "", 204

        # Command parsing
        if message.startswith(":"):
            parts = message.split()
            cmd = parts[0].lower()
            args = parts[1:]

            if cmd == ":cmds" and is_privileged():
                chat.append({"user": "System", "message": '<a href="/commands" target="_blank">Open Commands</a>'})
                save_json(CHAT_LOG, chat)
                return "", 204

            # (You would continue with all previous admin/mod/fun commands here...)

        if username in mutes:
            return "", 204

        chat.append({"user": username, "message": message})
        save_json(CHAT_LOG, chat)
        return "", 204

    return render_template("index.html", username=username)

@app.route("/commands")
def command_page():
    return render_template("commands.html")

@app.route("/messages")
def messages():
    if "username" not in session:
        return "", 403
    return json.dumps(load_json(CHAT_LOG, []))

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"].strip()
        if username == ADMIN_USERNAME:
            return "You cannot create an admin account."
        password = request.form["password"]
        users = load_json(USER_FILE, {})
        if username in users:
            return "Username already exists."
        users[username] = hash_password(password)
        save_json(USER_FILE, users)
        session["username"] = username
        return redirect("/")
    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        users = load_json(USER_FILE, {})
        if username in users and users[username] == hash_password(password):
            if username == ADMIN_USERNAME:
                code = str(random.randint(100000, 999999))
                VERIF_CODES[username] = code
                VERIF_TIMES[username] = time.time()
                send_verification_code(code)
                session["pending"] = username
                return redirect("/verify")
            session["username"] = username
            return redirect("/")
        return "Invalid username or password."
    return render_template("login.html")

@app.route("/verify", methods=["GET", "POST"])
def verify():
    if "pending" not in session:
        return redirect("/login")
    if request.method == "POST":
        code = request.form["code"].strip()
        if VERIF_CODES.get(session["pending"]) == code:
            session["username"] = session.pop("pending")
            return redirect("/")
        return "Incorrect verification code."
    return render_template("verify.html")

@app.route("/resend", methods=["POST"])
def resend():
    user = session.get("pending")
    if user != ADMIN_USERNAME:
        return jsonify({"error": "Not allowed"}), 403
    now = time.time()
    if user in VERIF_TIMES and now - VERIF_TIMES[user] < 30:
        return jsonify({"error": "Please wait before resending."}), 429
    code = str(random.randint(100000, 999999))
    VERIF_CODES[user] = code
    VERIF_TIMES[user] = now
    send_verification_code(code)
    return jsonify({"success": True})

@app.route("/logout")
def logout():
    session.pop("username", None)
    session.pop("pending", None)
    return render_template("logout.html")

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))
