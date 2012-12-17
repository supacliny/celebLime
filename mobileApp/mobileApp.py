from __future__ import with_statement
from contextlib import closing
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, Response, jsonify
from time import time
from time import mktime
import tweepy
import json
import datetime
import pytz
import jinja2
import urllib2
import urlparse
import requests
import sqlite3
import itunes

DEBUG = True
DATABASE = 'mobileApp.db'
CONSUMER_TOKEN = "169194713-GNag4qKFdwHsOTn0vpaRtLGssCTGolct7Qcp3AUv"
CONSUMER_KEY = "DXRAHKyo7akk8CvscsRivg"
CONSUMER_SECRET = "cXfqDfMFBQutTMf9KpZWGt2HWDhBVxTajAqVDuFH7U"

if DEBUG: 
    CALLBACK_URL = "http://127.0.0.1:5000/verify"
else:
    CALLBACK_URL = "http://www.cvstechnology.ca/projects/mobileApp/verify"

app = Flask(__name__)
app.config.from_object(__name__)
app.config['SECRET_KEY'] = "\x89\x06\xc4\xf0\xc8&\x91\x01\x01\x8d^:\xb4b$\xa5u\x0b\xa8\xd7\x15\xa3\xd0\xab"


## MOBILE APP ##

# DATABASE
def connect_db():
    return sqlite3.connect(app.config['DATABASE'])

def init_db():
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql') as f:
            db.cursor().executescript(f.read())
        db.commit()

@app.before_request
def before_request():
    g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
    g.db.close()


# APP #
# when home page loads
@app.route("/", methods=["GET", "POST"])
def home():

    # check for logged in session
    logged_in = session.get("logged_in")

    name = session.get("username")

    userid = session.get("userid")

    if logged_in == None:
        logged_in = False

    if name == None:
        name = ""

    if userid == None:
        userid = 0

    if request.method == "POST":
        title = request.form['title']
        artist = request.form['artist']
        album = request.form['album']

        if title and artist and album:
            search = title + " " + artist
            track = getiTunesTrack(search)

            print track
            song_title = track.get("trackName")
            song_artist = track.get("artistName")
            song_album = track.get("collectionName")

            if song_title != None and song_artist != None and song_album != None:
                cur = g.db.execute('select song_id, song_title, song_artist, song_album, twitter_id from songs where song_title = ? and song_artist = ? and song_album = ? and twitter_id = ?', [song_title, song_artist, song_album, userid])

                results = cur.fetchall()

                # song is already in there!
                if results:
                    song_id = results[0][0]
                else:
                    # has not been inserted
                    g.db.execute('insert into songs (song_title, song_artist, song_album, twitter_id) values (?, ?, ?, ?)', [song_title, song_artist, song_album, userid])
                    g.db.commit()


    cur = g.db.execute('select song_id, song_title, song_artist, song_album from songs where twitter_id = ?', [userid])
    tracks = [dict(id=row[0], title=row[1], artist=row[2], album=row[3]) for row in cur.fetchall()]

    return render_template("mobile.html", logged_in=logged_in, name=name, tracks=tracks, debug=DEBUG)


# get track
def getiTunesTrack(search):

    results = itunes.search_track(query=search, limit=1)

    if results:
        # assume the first result is the best match
        data = results[0].json
    else:
        data = json.loads("{}")

    return data


# first half of twitter oauth - go to twitter login page, then redirect to home page
@app.route("/login")
def login():
    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET, CALLBACK_URL)

    try:
        redirect_url = auth.get_authorization_url(True)
        session["request_token"] = (auth.request_token.key,auth.request_token.secret)
    except tweepy.TweepError:
        print "Access error! Failed to get request token."

    return redirect(redirect_url)


# when we logout remove all session keys
@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    session.pop("userid", None)
    session.pop("username", None)
    session.pop("request_token", None)
    return redirect(url_for("home"))


# second half of twitter oauth - exchange request token for access token
@app.route("/verify")
def verify():

    # check to see if we were denied by twitter
    denied = "denied"
    if denied in request.args:
        return redirect(url_for("home"))

    # otherwise we are clear
    verifier = request.args["oauth_verifier"]

    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)

    token = session.get("request_token")
    session.pop("request_token", None)

    # die gracefully
    if token == None:
        return redirect(url_for("home"))

    auth.set_request_token(token[0], token[1])

    try:
        auth.get_access_token(verifier)
        session["logged_in"] = True
        api = tweepy.API(auth)
        user = api.me()
        session["userid"] = user.id
        session["username"] = user.name

        twitter_id = user.id
        token = auth.access_token.key
        secret = auth.access_token.secret
        screen_name = user.screen_name
        name = user.name
        logins = 1

        try:
            g.db.execute('insert into users (twitter_id, token, secret, screen_name, name, logins) values (?, ?, ?, ?, ?, ?)', [twitter_id, token, secret, screen_name, name, logins])
        except sqlite3.IntegrityError, m:
            g.db.execute('update users set logins = logins + 1')
 
        g.db.commit()

    except tweepy.TweepError:
        print "Access error! Failed to get access token."

    return redirect(url_for("home"))


# delete added track
@app.route("/delete/<id>", methods = ["POST"])
def store(id):

    song_id = int(id)
    user_id = session.get("userid")

    # delete song - it must exist
    g.db.execute('delete from songs where song_id = ? and twitter_id = ?', [song_id, user_id])
    g.db.commit()
 
    cur = g.db.execute('select song_id, song_title, song_artist, song_album from songs where twitter_id = ?', [user_id])
    tracks = [dict(id=row[0], title=row[1], artist=row[2], album=row[3]) for row in cur.fetchall()]

    return render_template("streaming.html", tracks=tracks)


@app.errorhandler(404)
def not_found(error=None):
    message = {
            "status": 404,
            "message": "Not Found: " + request.url,
    }
    resp = jsonify(message)
    resp.status_code = 404

    return resp


## HELPER FUNCTIONS ##

def not_json(error=None):
    message = {
        "status": 400,
        "message": "Bad Request (not JSON): " + request.url,
    }
    resp = jsonify(message)
    resp.status_code = 400

    return resp


def not_authorized(error=None):
    message = {
        "status": 401,
        "message": "Not Authorized: " + request.url,
    }
    resp = jsonify(message)
    resp.status_code = 401

    return resp


def bad_request(error=None):
    message = {
        "status": 400,
        "message": "Bad Request (missing required JSON fields): " + request.url,
    }
    resp = jsonify(message)
    resp.status_code = 400

    return resp


# used to extract the youtube video ID
def find_between(s, first, last):
    try:
        start = s.index( first ) + len( first )
        end = s.index( last, start )
        return s[start:end]
    except ValueError:
        return ""


# for now, simply check that the access token is present in mongodb
# later on we would use it in conjunction with the secret to sign a request for twitter
def is_authorized(access_token):

    #result = mongo.db.users.find_one({"access_key": access_token})
    if result:
        return True
    else:
        return False


if __name__ == "__main__":

    if DEBUG:
        app.run(port=5000)
    else:
        app.run()
