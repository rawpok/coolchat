from flask import Flask, render_template, request, redirect, session, make_response, jsonify
import os, json, hashlib, smtplib, random, time

app = Flask(__name__, static_folder="static")
app.secret_key = "changeme-secret"

CHAT_LOG = "chatlog.json"
USER_FILE = "users.json"
BAN_FILE = "banned.json"
VERIF_CODES = {}
VERIF_TIMES = {}
ADMIN_USERNAME = "admin"
ADMIN_EMAIL = "rawpok@icloud.com"

# -- Data Loading --
def load_chat():
    if not os.path.exists(CHAT_LOG):
        return []
    with open(CHAT_LOG, "r") as f:
        return json.load(f)

def save_chat(chat):
    with open(CHAT_LOG, "w") as f:
        json.dump(chat[-100:], f)

def load_users():
    if not os.path.exists(USER_FILE):
        return {}
    with open(USER_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USER_FILE, "w") as f:
        json.dump(users, f)

def load_bans():
    if not os.path.exists(BAN_FILE):
        return {}
    with open(BAN_FILE, "r") as f:
        return json.load(f)

def save_bans(bans):
    with open(BAN_FILE, "w") as f:
        json.dump(bans, f)

def hash_password(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

def send_verification_code(code):
    print(f"Verification code sent to {ADMIN_EMAIL}: {code}")  # Simulated email

# -- Ensure default admin account always exists --
users = load_users()
if ADMIN_USERNAME not in users:
    users[ADMIN_USERNAME] = hash_password("admin")
    save_users(users)

# -- Routes --
@app.route("/", methods=["GET", "POST"])
def index():
    if "username" not in session:
        return redirect("/login")

    bans = load_bans()
    if session["username"] in bans:
        return render_template("banned.html", reason=bans[session["username"]])

    if request.method == "POST":
        message = request.form["message"].strip()
        if message:
            if session["username"] == ADMIN_USERNAME and message.startswith(":ban"):
                parts = message.split()
                if len(parts) >= 3:
                    target = parts[1]
                    reason = " ".join(parts[2:])
                    bans[target] = reason
                    save_bans(bans)
                    chat = load_chat()
                    chat.append({"user": "System", "message": f"{target} has been banned by admin. Reason: {reason}"})
                    save_chat(chat)
                    return "", 204
            chat = load_chat()
            chat.append({"user": session["username"], "message": message})
            save_chat(chat)
        return "", 204
    return render_template("index.html", username=session["username"])

@app.route("/messages")
def messages():
    if "username" not in session:
        return "", 403
    return json.dumps(load_chat())

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"].strip()
        if username == ADMIN_USERNAME:
            return "You cannot create an admin account."
        password = request.form["password"]
        users = load_users()
        if username in users:
            return "Username already exists."
        users[username] = hash_password(password)
        save_users(users)
        session["username"] = username
        return redirect("/")
    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        users = load_users()
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

@app.route("/clear", methods=["POST"])
def clear_chat():
    if session.get("username") == ADMIN_USERNAME:
        save_chat([])
        return "Chat cleared", 200
    return "Unauthorized", 403

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))
