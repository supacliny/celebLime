from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, Response, jsonify
from flask.ext.pymongo import PyMongo
from pymongo import ASCENDING
from validate_email import validate_email
import json

DEBUG = False

app = Flask(__name__)
app.config.from_object(__name__)
app.config['SECRET_KEY'] = "H\xb8\x8do\x8a\xfc\x80\x18\x06\xaf!i\x028\x1bPs\x85\xe7\x87\x11\xe6j\xb1"
mongo = PyMongo(app)


@app.route('/')
def signup():
    return render_template('signup.html')

@app.route('/email', methods = ['POST'])
def email():
    email = request.json['email']
    is_valid = validate_email(email,verify=True)

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


if __name__ == "__main__":
    if DEBUG:
        app.run(debug=True, port=8000)
    else:
        app.run()

