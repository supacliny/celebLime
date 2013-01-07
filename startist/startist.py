from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, Response, jsonify

DEBUG = False

app = Flask(__name__)
app.config.from_object(__name__)
app.config['SECRET_KEY'] = "H\xb8\x8do\x8a\xfc\x80\x18\x06\xaf!i\x028\x1bPs\x85\xe7\x87\x11\xe6j\xb1"

@app.route('/')
def signup():
    return render_template('signup.html')

if __name__ == "__main__":
    if DEBUG:
        app.run(debug=True, port=8000)
    else:
        app.run()

