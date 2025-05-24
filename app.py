from flask import Flask, render_template, request, redirect, session
import os, json, hashlib

app = Flask(__name__, static_folder="static")
app.secret_key = "changeme-secret"

CHAT_LOG = "chatlog.json"
USER_FILE = "users.json"
BAN_FILE = "banned.json"
ADMIN_USERNAME = "admin"
ALLOWED_ADMIN_IPS = ["74.75.68.144"]

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

# -- Initialize default admin account --
if not os.path.exists(USER_FILE):
    save_users({ADMIN_USERNAME: hash_password("admin")})

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
        if username == ADMIN_USERNAME:
            user_ip = request.remote_addr
            if user_ip not in ALLOWED_ADMIN_IPS:
                return "Access denied: your IP is not whitelisted for admin."
        if username in users and users[username] == hash_password(password):
            session["username"] = username
            return redirect("/")
        return "Invalid username or password."
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("username", None)
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
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))
