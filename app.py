import os, json, hashlib, smtplib, random, time
from email.mime.text import MIMEText
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
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login("coolchat.noreply@gmail.com", "psuq ysvb gafa jlii")  # Replace with real password
            server.sendmail(msg["From"], [msg["To"]], msg.as_string())
    except Exception as e:
        print("Email failed:", e)

# Ensure admin account exists
users = load_json(USER_FILE, {})
if ADMIN_USERNAME not in users:
    users[ADMIN_USERNAME] = hash_password("admin")
    save_json(USER_FILE, users)

@app.before_request
def check_cookie_login():
    if "username" not in session:
        cookies = load_json(COOKIES_FILE, {})
        user_cookie = request.cookies.get("login_token")
        if user_cookie in cookies:
            session["username"] = cookies[user_cookie]

@app.route("/", methods=["GET", "POST"])
def index():
    if "username" not in session:
        return redirect("/login")
    return render_template("index.html", username=session["username"])

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        users = load_json(USER_FILE, {})
        if username == ADMIN_USERNAME or username in users:
            return "Invalid or existing username."
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
    if "pending" not in session:
        return redirect("/login")
    if request.method == "POST":
        code = request.form["code"].strip()
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
    session.pop("username", None)
    session.pop("pending", None)
    resp = make_response(redirect("/login"))
    resp.set_cookie("login_token", "", expires=0)
    return resp

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))
