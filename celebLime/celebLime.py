from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, Response, jsonify
from flask.ext.pymongo import PyMongo
from pymongo import ASCENDING
from pymongo.errors import DuplicateKeyError
import tweepy
import json
import datetime
import pytz
import jinja2

DEBUG = True

CONSUMER_TOKEN = "169194713-GNag4qKFdwHsOTn0vpaRtLGssCTGolct7Qcp3AUv"
CONSUMER_KEY = "DXRAHKyo7akk8CvscsRivg"
CONSUMER_SECRET = "cXfqDfMFBQutTMf9KpZWGt2HWDhBVxTajAqVDuFH7U"

if DEBUG: 
    CALLBACK_URL = "http://127.0.0.1:8000/verify"
else:
    CALLBACK_URL = "http://www.cvstechnology.ca/projects/celebLime/verify"

session = dict()


app = Flask(__name__)
app.config.from_object(__name__)
mongo = PyMongo(app)

# when home page loads
@app.route("/")
def home():

    try:
        logged_in = session["logged_in"]
        name = session["user"].name
    except KeyError:
        logged_in = False
        name = ""

    fans = mongo.db.users.find({"verified": False})
    celebs = mongo.db.users.find({"verified": True})

    fans = fans[0:2]
    celebs = celebs[0:2]
    return render_template("index.html", fans=fans, celebs=celebs, logged_in=logged_in, name=name, debug=DEBUG)


# first half of twitter oauth - go to twitter login page, then redirect to home page
@app.route("/login")
def login():
    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET, CALLBACK_URL)

    try:
        redirect_url = auth.get_authorization_url(True)
        print redirect_url
        session["request_token"] = (auth.request_token.key,auth.request_token.secret)
    except tweepy.TweepError:
        print "Access error! Failed to get request token."

    return redirect(redirect_url)


# when we logout - not sure this is needed with twitter oauth
@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("home"))


# second half of twitter oauth - exchange request token for access token
@app.route("/verify")
def verify():
    verifier = request.args["oauth_verifier"]
    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)

    token = session["request_token"]
    del session["request_token"]
    auth.set_request_token(token[0], token[1])

    try:
        auth.get_access_token(verifier)
        session["logged_in"] = True
        api = tweepy.API(auth)
        user = api.me()
        session["user"] = user

        current_time = datetime.datetime.today()

        user_details = { "added_at": current_time,
                         "access_key": auth.access_token.key,
                         "access_secret": auth.access_token.secret,
                         "contributors_enabled": user.contributors_enabled,
                         "created_at": user.created_at,
                         "description": user.description,
                         "favourites_count": user.favourites_count,
                         "followers_count": user.followers_count,
                         "following": user.following,
                         "friends_count": user.friends_count,
                         "geo_enabled": user.geo_enabled,
                         "id": user.id,
                         "ip": request.access_route[0],
                         "lang": user.lang,
                         "location": user.location,
                         "last_logged_in": current_time,
                         "name": user.name,
                         "notifications": user.notifications,
                         "profile_background_color": user.profile_background_color,
                         "profile_background_image_url": user.profile_background_image_url,
                         "profile_background_tile": user.profile_background_tile,
                         "profile_image_url": user.profile_image_url,
                         "profile_link_color": user.profile_link_color,
                         "profile_sidebar_border_color": user.profile_sidebar_border_color,
                         "profile_sidebar_fill_color": user.profile_sidebar_fill_color,
                         "profile_text_color": user.profile_text_color,
                         "profile_use_background_image": user.profile_use_background_image,
                         "protected": user.protected,
                         "screen_name": user.screen_name,
                         "statuses_count": user.statuses_count,
                         "time_zone": user.time_zone,
                         "total_logins": 1,
                         "url": user.url,
                         "utc_offset": user.utc_offset,
                         "verified": user.verified }

        # if index not there, add a compound index
        mongo.db.users.ensure_index([("access_key",ASCENDING),("access_secret",ASCENDING),("id",ASCENDING),("screen_name",ASCENDING)], unique=True, background=True)

        # found this user in mongo
        already_user = mongo.db.users.find_one({"access_key": auth.access_token.key, "access_secret": auth.access_token.secret, "id": user.id})

        # maintain the original added_at field
        if already_user:
            user_details["added_at"] = already_user["added_at"]
            user_details["total_logins"] = already_user["total_logins"] + 1

        # now update that user
        try:
            mongo.db.users.update({"access_key": auth.access_token.key, "access_secret": auth.access_token.secret, "id": user.id}, user_details, upsert=True)
        except DuplicateKeyError:
            print "Duplicate error! User inserted already."

    except tweepy.TweepError:
        print "Access error! Failed to get access token."

    return redirect(url_for("home"))


# when we visit a user profile page
@app.route("/user/<userid>", methods = ["GET"])
def user(userid):

    try:
        logged_in = session["logged_in"]
        name = session["user"].name
    except KeyError:
        logged_in = False
        name = ""

    # must cast unicode to int
    userid = int(userid)
    user = mongo.db.users.find_one({"id": userid})

    playlists = []

    playlists_cursor = mongo.db.playlists.find({"id": userid})

    for playlist in playlists_cursor:

        songs = []
        songids = playlist["songs"]
        
        for songid in songids:

            songinfo = mongo.db.songs.find_one(songid)
            songs.append(songinfo)

        playlist["songs"] = songs

        playlists.append(playlist)

    streaming = []

    # sort in descending order by date
    streaming_cursor = mongo.db.streaming.find({"id": userid}).limit(25).sort([("played_at", -1)])

    for song in streaming_cursor:

        songid = song["songid"]

        songinfo = mongo.db.songs.find_one({"songid": songid})

        songinfo["played_at"] = song["played_at"]

        streaming.append(songinfo)

    top = []

    # sort in descending order by number of times played
    top_cursor = mongo.db.streaming.find({"id": userid}).limit(10).sort([("number", -1)])

    for song in top_cursor:

        songid = song["songid"]

        songinfo = mongo.db.songs.find_one({"songid": songid})

        top.append(songinfo)

    return render_template("user.html", user=user, playlists=playlists, streaming=streaming, top=top, logged_in=logged_in, name=name, debug=DEBUG)


# ajax query to determine if the more recent listened song is being played
@app.route("/poll/<userid>", methods = ["POST"])
def poll(userid):

    userid = int(userid)

    # sort in descending order by date and return most recent song
    recent_songs_cursor = mongo.db.streaming.find({"id": userid}).limit(25).sort([("played_at", -1)])

    if recent_songs_cursor.count() > 0:

        most_recent_song = recent_songs_cursor[0]

        songid = most_recent_song["songid"]

        songinfo = mongo.db.songs.find_one({"songid": songid})

        songinfo["played_at"] = most_recent_song["played_at"]

        song_start = most_recent_song["played_at"]
        song_duration = songinfo["duration"]

        if ((song_start + datetime.timedelta(seconds=song_duration)) >= datetime.datetime.today().replace(tzinfo=pytz.utc)):
            return '<now>Now Playing</now>'
        else:
            return '<div class="listen">Listened</div><div class="date">' + str(format_date(songinfo["played_at"])) + '</div>'

    else:
            return ''


## API ##
# create a playlist from JSON object
@app.route("/create", methods = ["POST"])
def api_create_playlist():

    if request.headers["Content-Type"] == "application/json":

        mongo.db.playlists.ensure_index([("access_key",ASCENDING),("access_secret",ASCENDING),("id",ASCENDING),("screen_name",ASCENDING)], unique=True, background=True)

        # found this user in mongo
        already_user = mongo.db.playlists.find_one({"access_key": auth.access_token.key, "access_secret": auth.access_token.secret, "id": user.id})


        print "JSON Message: " + json.dumps(request.json)
        data = {"playlist_id"  : 1}
        js = json.dumps(data)
        resp = Response(js, status=201, mimetype="application/json")
        return resp
    else:
        return not_found()


@app.route("/add", methods = ["POST"])
def api_add_song():

    if request.headers["Content-Type"] == "application/json":
        print "JSON Message: " + json.dumps(request.json)
        data = {"playlist_id"  : 1}
        js = json.dumps(data)
        resp = Response(js, status=201, mimetype="application/json")
        return resp
    else:
        return not_found()


@app.errorhandler(404)
def not_found(error=None):
    message = {
            "status": 404,
            "message": "Not Found: " + request.url,
    }
    resp = jsonify(message)
    resp.status_code = 404

    return resp


# format return string according to day
def format_date(date_time):

    if date_time.date() == datetime.datetime.today().date():
 
        return date_time.strftime('Today at ' + '%I:%M:%S %p')

    if date_time.date() + datetime.timedelta(1) == datetime.datetime.today().date():

        return date_time.strftime('Yesterday at ' + '%I:%M:%S %p')

    else:

        return date_time.strftime('%a %d %b %Y at %I:%M:%S %p')


# now apply this jinja2 template
app.jinja_env.globals.update(format_date=format_date)


if __name__ == "__main__":

    if DEBUG:
        app.run(port=8000)
    else:
        app.run()
