from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, Response, jsonify
from flask.ext.pymongo import PyMongo
from pymongo import ASCENDING
from validate_email import validate_email
from werkzeug.security import generate_password_hash, check_password_hash
import json
import re

DEBUG = False

app = Flask(__name__)
app.config.from_object(__name__)
app.config['SECRET_KEY'] = "H\xb8\x8do\x8a\xfc\x80\x18\x06\xaf!i\x028\x1bPs\x85\xe7\x87\x11\xe6j\xb1"
mongo = PyMongo(app)

# PRELAUNCH [
# render the signup page for now until we launch
@app.route('/')
def signup():
    return render_template('signup.html')


@app.route('/launch')
def launch():
    return render_template('launch.html')


# validate email submitted from signup page:
# if the email is invalid, then return 0
# if the email is valid, then return 1 
# if the email is valid but already in mongo, then return 2
@app.route('/email', methods = ['POST'])
def email():
    email = request.json['email']
    try:
        is_valid = validate_email(email)
    except Exception:
        is_valid = True
    signal = 0
    if is_valid:
        mongo.db.emails.ensure_index([("email",ASCENDING)], unique=True, background=True)
        already = mongo.db.emails.find_one(request.json)
        if already:
            signal = 2
        else:
            signal = 1
            mongo.db.emails.insert(request.json)
    else:
        signal = 0
    data = {"valid": signal}
    data = json.dumps(data)
    return data


@app.route('/jobs')
def jobs():
    return render_template('jobs.html')

# ]


# LAUNCH [
# lander page
@app.route('/lander')
def home():
    return render_template('index.html')

# login user
@app.route('/login', methods = ['POST'])
def login():
    email = request.json['email']
    password = request.json['password']
    name = ''
    user = mongo.db.users.find_one({"email": email})
    if user:
        email_signal = 1
        salted_password = user["password"]
        if check_password_hash(salted_password, password):
            password_signal = 1
            session["logged_in"] = True
            session["name"] = user["name"]
            name = user["name"]
            session["user_id"] = str(user["_id"])
            logins = user["logins"] + 1
            mongo.db.users.update({"email": email}, {"$set": {"logins": logins}})
        else:
            password_signal = 0
    else:
        email_signal = 0
        password_signal = 2

    data = {"name": name, "email": email_signal, "password": password_signal}
    data = json.dumps(data)
    return data

# logout user
@app.route('/logout')
def logout():
    session.pop("logged_in", None)
    session.pop("name", None)
    session.pop("user_id", None)
    return redirect(url_for('home'))

# join page
@app.route('/join', methods = ['POST'])
def join():
    name = request.json['name']
    email = request.json['email']
    password = request.json['password']
    confirm = request.json['confirm']
    try:
        is_email_valid = validate_email(email,verify=True)
    except Exception:
        is_email_valid = True

    if len(name) > 0:
        name_signal = 1
    else:
        name_signal = 0

    if is_email_valid:
        email_signal = 1
    else:
        email_signal = 0

    password_signal = validate_password(password, confirm)

    if name_signal and email_signal and (password_signal == 1):

        mongo.db.users.ensure_index([("email",ASCENDING)], unique=True, background=True)
        already = mongo.db.users.find_one({"email": email})
        if already:
            email_signal = 2
        else:
            salted_password = generate_password_hash(password)
            user = {"name": name, "email": email, "password": salted_password, "logins": 1}
            user_id = mongo.db.users.insert(user)
            session["logged_in"] = True
            session["name"] = name
            session["user_id"] = str(user_id)        

    data = {"name": name_signal, "email": email_signal, "password": password_signal}
    data = json.dumps(data)
    return data

# ]

# AUXILLARY FUNCTIONS [

# validate password
def validate_password(password, confirm):
    if password != confirm:
        return 0
    if re.match(r'[A-Za-z0-9@#$%^&+=]{7,}', password):
        return 1
    else:
        return 2
# ]

if __name__ == "__main__":
    if DEBUG:
        app.run(debug=True, port=8000)
    else:
        app.run()

