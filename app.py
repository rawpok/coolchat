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

def send_verification_code(code):
    msg = MIMEText(f"Your admin verification code is: {code}")
    msg["Subject"] = "Admin Login Code"
    msg["From"] = "destynp329@gmail.com"
    msg["To"] = ADMIN_EMAIL
    try:
        with smtpllib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login("destynp329@gmail.com", "YOUR_APP_PASSWORD")  # Replace with actual App Password
            server.sendmail(msg["From"], [msg["To"]], msg.as_string())
    except Exception as e:
        print("Failed to send email:", e)

# -- Default Admin Setup --

users = load_json(USER_FILE, {})
if ADMIN_USERNAME not in users:
    users[ADMIN_USERNAME] = hash_password("admin")
    save_json(USER_FILE, users)

# -- Routes --

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

        # Commands
        if message.startswith(":"):
            parts = message.split()
            cmd = parts[0].lower()
            args = parts[1:]

            if is_admin:
                if cmd == ":ban" and len(args) >= 2:
                    bans[args[0]] = " ".join(args[1:])
                    send_system(f"{args[0]} was banned: {' '.join(args[1:])}")
                    save_json(BAN_FILE, bans)

                elif cmd == ":unban" and len(args) == 1:
                    bans.pop(args[0], None)
                    send_system(f"{args[0]} was unbanned.")
                    save_json(BAN_FILE, bans)

                elif cmd == ":clear":
                    save_json(CHAT_LOG, [])
                    return "", 204

                elif cmd == ":mod" and len(args) == 1:
                    if args[0] not in mods:
                        mods.append(args[0])
                        save_json(MOD_FILE, mods)
                        send_system(f"{args[0]} is now a mod.")

                elif cmd == ":unmod" and len(args) == 1:
                    if args[0] in mods:
                        mods.remove(args[0])
                        save_json(MOD_FILE, mods)
                        send_system(f"{args[0]} is no longer a mod.")

                elif cmd == ":bans":
                    send_system(f"Banned users: {', '.join(bans.keys()) or 'None'}")

                elif cmd == ":logs":
                    for msg in chat[-10:]:
                        send_system(f"{msg['user']}: {msg['message']}")

                elif cmd == ":lockchat":
                    locked["status"] = True
                    save_json(LOCKED_FILE, locked)
                    send_system("Chat locked.")

                elif cmd == ":unlockchat":
                    locked["status"] = False
                    save_json(LOCKED_FILE, locked)
                    send_system("Chat unlocked.")

                elif cmd == ":slowmode" and len(args) == 1:
                    try:
                        seconds = int(args[0])
                        slow["seconds"] = seconds
                        save_json(SLOWMODE_FILE, slow)
                        send_system(f"Slowmode set to {seconds}s.")
                    except:
                        send_system("Invalid slowmode.")

            if is_privileged():
                if cmd == ":mute" and len(args) == 1:
                    if args[0] not in mutes:
                        mutes.append(args[0])
                        save_json(MUTE_FILE, mutes)
                        send_system(f"{args[0]} was muted.")

                elif cmd == ":unmute" and len(args) == 1:
                    if args[0] in mutes:
                        mutes.remove(args[0])
                        save_json(MUTE_FILE, mutes)
                        send_system(f"{args[0]} was unmuted.")

                elif cmd == ":kick" and len(args) == 1:
                    bans[args[0]] = "(Kicked)"
                    save_json(BAN_FILE, bans)
                    send_system(f"{args[0]} was kicked.")

            # Fun
            if cmd == ":roll":
                send_system(f"{username} rolled {random.randint(1, 100)}")
            elif cmd == ":flip":
                send_system(f"{username} flipped {'Heads' if random.randint(0,1)==1 else 'Tails'}")
            elif cmd == ":8ball":
                ball = random.choice(["Yes", "No", "Maybe", "Definitely", "Absolutely not", "Try again later"])
                send_system(f"🎱 {ball}")
            elif cmd == ":say" and args:
                send_system(" ".join(args))

            save_json(CHAT_LOG, chat)
            return "", 204

        if username in mutes:
            return "", 204  # muted users can't speak

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
