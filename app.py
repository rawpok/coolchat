from flask import Flask, render_template, request, redirect, session
import os, json, hashlib

app = Flask(__name__, static_folder="static")
app.secret_key = "changeme-secret"

CHAT_LOG = "chatlog.json"
USER_FILE = "users.json"
ADMIN_USERNAME = "admin"

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
    if request.method == "POST":
        message = request.form["message"].strip()
        if message:
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
