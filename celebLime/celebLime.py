from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, Response, jsonify
from flask.ext.pymongo import PyMongo
from pymongo import ASCENDING
from pymongo.errors import DuplicateKeyError
from bson import json_util
from time import time
from time import mktime
import tweepy
import json
import bson
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

app = Flask(__name__)
app.config.from_object(__name__)
app.config['SECRET_KEY'] = "\x89\x06\xc4\xf0\xc8&\x91\x01\x01\x8d^:\xb4b$\xa5u\x0b\xa8\xd7\x15\xa3\xd0\xab"
mongo = PyMongo(app)


# when home page loads
@app.route("/")
def home():

    # check for logged in session
    try:
        logged_in = session.get("logged_in")
        name = session.get("username")
    except KeyError:
        logged_in = False
        name = ""

    # check for active tab
    active = session.get("tab")

    # possibly new session, so set active    
    if active == None:
        active = True

    # get list of celebs
    celebs_cursor = mongo.db.users.find({"verified": True})

    celebs = []

    for celeb in celebs_cursor:

        celebid = celeb["twitter_id"]
        most_recent_songs = mongo.db.streaming.find({"twitter_id": celebid}).limit(25).sort([("played_at", -1)])

        if most_recent_songs.count() > 0:
            most_recent_song = most_recent_songs[0]
            songid = most_recent_song["songid"]
            songinfo = mongo.db.songs.find_one({"songid": songid})

            if songinfo:
                songinfo["played_at"] = most_recent_song["played_at"]

                if ((songinfo["played_at"]+ songinfo["duration"])) >= int(time()):
                    celeb["now"] = True
                else:
                    celeb["now"] = False

                celeb["mr_song_title"] = songinfo["title"] 
                celeb["mr_song_artist"] = songinfo["artist"]

                celebs.append(celeb)
        else:
            celeb["now"] = False
            celeb["mr_song_title"] = ""
            celeb["mr_song_artist"] = ""
            celebs.append(celeb)


    # get list of fans
    fans_cursor = mongo.db.users.find({"verified": False})

    fans = []

    for fan in fans_cursor:

        fanid = fan["twitter_id"]
        most_recent_songs = mongo.db.streaming.find({"twitter_id": fanid}).limit(25).sort([("played_at", -1)])

        if most_recent_songs.count() > 0:
            most_recent_song = most_recent_songs[0]
            songid = most_recent_song["songid"]
            songinfo = mongo.db.songs.find_one({"songid": songid})

            if songinfo:
                songinfo["played_at"] = most_recent_song["played_at"]

                if ((songinfo["played_at"] + songinfo["duration"]) >= int(time())):
                    fan["now"] = True
                else:
                    fan["now"] = False

                fan["mr_song_title"] = songinfo["title"] 
                fan["mr_song_artist"] = songinfo["artist"]

                fans.append(fan)
        else:
            fan["now"] = False
            fan["mr_song_title"] = ""
            fan["mr_song_artist"] = ""
            fans.append(fan)

    return render_template("index.html", fans=fans, celebs=celebs, logged_in=logged_in, name=name, active=active, debug=DEBUG)


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

        # work in unix time
        current_time = int(time())
        created_at = int(mktime(user.created_at.timetuple()))

        user_details = { "added_at": current_time,
                         "access_key": auth.access_token.key,
                         "access_secret": auth.access_token.secret,
                         "contributors_enabled": user.contributors_enabled,
                         "created_at": created_at,
                         "description": user.description,
                         "favourites_count": user.favourites_count,
                         "followers_count": user.followers_count,
                         "following": user.following,
                         "friends_count": user.friends_count,
                         "geo_enabled": user.geo_enabled,
                         "twitter_id": user.id,
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
        mongo.db.users.ensure_index([("access_key",ASCENDING),("access_secret",ASCENDING),("twitter_id",ASCENDING),("screen_name",ASCENDING)], unique=True, background=True)

        # found this user in mongo
        already_user = mongo.db.users.find_one({"access_key": auth.access_token.key, "access_secret": auth.access_token.secret, "twitter_id": user.id})

        # maintain the original added_at field
        if already_user:
            user_details["added_at"] = already_user["added_at"]
            user_details["total_logins"] = already_user["total_logins"] + 1

        # now update that user
        try:
            mongo.db.users.update({"access_key": auth.access_token.key, "access_secret": auth.access_token.secret, "twitter_id": user.id}, user_details, upsert=True)
        except DuplicateKeyError:
            print "User error! User can not be updated."

    except tweepy.TweepError:
        print "Access error! Failed to get access token."

    return redirect(url_for("home"))


# when we visit a user profile page
@app.route("/user/<screen_name>", methods = ["GET"])
def user(screen_name):

    try:
        logged_in = session.get("logged_in")
        name = session.get("username")
    except KeyError:
        logged_in = False
        name = ""

    # cast to string just in case
    screen_name = str(screen_name)
    user = mongo.db.users.find_one({"screen_name": screen_name})

    # behind the scenes use twitter id
    userid = user["twitter_id"]

    playlists = []

    # get all playlists for this userid
    playlists_cursor = mongo.db.playlists.find({"twitter_id": userid})

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
    streaming_cursor = mongo.db.streaming.find({"twitter_id": userid}).limit(25).sort([("played_at", -1)])

    for song in streaming_cursor:
        songid = song["songid"]
        songinfo = mongo.db.songs.find_one({"songid": songid})
        songinfo["played_at"] = song["played_at"]
        streaming.append(songinfo)

    top = []

    # todo mongodb groupby?
    # sort in descending order by number of times played
    # top_cursor = mongo.db.streaming.find({"twitter_id": userid}).limit(10).sort([("number", -1)])

    # for song in top_cursor:
    #     songid = song["songid"]
    #     songinfo = mongo.db.songs.find_one({"songid": songid})
    #     top.append(songinfo)

    return render_template("user.html", user=user, playlists=playlists, streaming=streaming, top=top, logged_in=logged_in, name=name, debug=DEBUG)


# ajax query to update the recently listened playlist
@app.route("/poll/<screen_name>", methods = ["POST"])
def poll(screen_name):

    # cast to string just in case
    screen_name = str(screen_name)
    user = mongo.db.users.find_one({"screen_name": screen_name})

    # behind the scenes use twitter id
    userid = user["twitter_id"]

    # sort in descending order by date and return most recent song
    recent_songs_cursor = mongo.db.streaming.find({"twitter_id": userid}).limit(25).sort([("played_at", -1)])

    recent_songs = []

    for recent_song in recent_songs_cursor:
        songid = recent_song["songid"]
        songinfo = mongo.db.songs.find_one({"songid": songid})
        songinfo["played_at"] = recent_song["played_at"]
        recent_songs.append(songinfo)

    now = False

    if recent_songs:
        most_recent_song_start = recent_songs[0]["played_at"]
        most_recent_song_duration = recent_songs[0]["duration"]

        if ((most_recent_song_start + most_recent_song_duration) >= int(time())):
            now = True

    return render_template("streaming.html", streaming=recent_songs, now=now)


# store preference to secure session
@app.route("/store/<pref>", methods = ["POST"])
def store(pref):

    pref = str(pref)

    # which active tab
    if pref == "celeb":
        session["tab"] = True
    else:
        session["tab"] = False

    resp = Response(None, status=200, mimetype="application/json")

    return resp


## API ##

# create a playlist from JSON object
@app.route("/create", methods = ["POST"])
def api_create_playlist():

    if request.headers["Content-Type"] == "application/json":

        incoming = request.json
        userid = incoming["twitter_id"]
        key = incoming["access_key"]
        secret = incoming["access_secret"]
        incoming["added_at"] = int(time())
        incoming["updated_at"] = int(time())

        # does this playlist exist already?
        # authenticate user?

        # insert into mongo
        playlist_id = mongo.db.playlists.insert(incoming)

        data = {"playlist_id": str(playlist_id)}

        data = json.dumps(data)

        resp = Response(data, status=201, mimetype="application/json")
        return resp
    else:
        return not_json()


# delete a playlist
@app.route("/delete", methods = ["DELETE"])
def api_delete_playlist():

    if request.headers["Content-Type"] == "application/json":

        incoming = request.json
        userid = incoming["twitter_id"]
        key = incoming["access_key"]
        secret = incoming["access_secret"]
        playlist_id = incoming["playlist_id"]

        # incoming playlist_id is a string, convert to ObjectID
        playlist_oid = bson.objectid.ObjectId(playlist_id)

        # authenticate user?

        # remove from mongo
        mongo.db.playlists.remove({"_id": playlist_oid})

        data = {}

        data = json.dumps(data)

        resp = Response(data, status=204, mimetype="application/json")
        return resp
    else:
        return not_json()


# update a playlist
@app.route("/update", methods = ["PATCH"])
def api_update_playlist():

    if request.headers["Content-Type"] == "application/json":

        incoming = request.json
        userid = incoming["twitter_id"]
        key = incoming["access_key"]
        secret = incoming["access_secret"]
        playlist_id = incoming["playlist_id"]

        # incoming playlist_id is a string, convert to ObjectID
        playlist_oid = bson.objectid.ObjectId(playlist_id)

        # authenticate user?

        # find the playlist in mongo
        playlist = mongo.db.playlists.find_one({"_id": playlist_oid})

        # maintain the original added_at field but update the updated_at field
        if playlist:
            incoming["added_at"] = playlist["added_at"]
            incoming["updated_at"] = int(time())

            # now update that playlist
            try:
                mongo.db.playlists.update({"_id": playlist_oid}, incoming, upsert=True)
            except DuplicateKeyError:
                print "Playlist error! Playlist can not be updated."

        else:
            print "Playlist error! Playlist not found."

        data = {}

        data = json.dumps(data)

        resp = Response(data, status=204, mimetype="application/json")
        return resp
    else:
        return not_json()


# stream a song
@app.route("/stream", methods = ["PUT"])
def api_stream_song():

    if request.headers["Content-Type"] == "application/json":

        incoming = request.json
        user_id = incoming["twitter_id"]
        key = incoming["access_key"]
        secret = incoming["access_secret"]
        song_id = incoming["songid"]

        # incoming playlist_id is a string, convert to ObjectID
        # playlist_oid = bson.objectid.ObjectId(playlist_id)

        # authenticate user?

        # find the song in mongo streamed by that user
        song = mongo.db.streaming.find_one({"twitter_id": user_id, "songid": song_id})

        # update the number of times played, if this key does not exist then song never streamed before
        try:
            incoming["played_count"] = song["played_count"] + 1
        except TypeError:
            incoming["played_count"] = 1

        # now update
        try:
            mongo.db.streaming.update({"twitter_id": user_id, "songid": song_id}, incoming, upsert=True)
        except DuplicateKeyError:
            print "Streaming error! Streaming song can not be updated."

        data = {}

        data = json.dumps(data)

        resp = Response(data, status=204, mimetype="application/json")
        return resp
    else:
        return not_json()


# add a song
@app.route("/add", methods = ["POST"])
def api_add_song():

    if request.headers["Content-Type"] == "application/json":

        incoming = request.json

        # authenticate user?

        # if index not there, add a compound index
        mongo.db.songs.ensure_index([("title",ASCENDING),("artist",ASCENDING)], unique=True, background=True)

        # does this song already exist in the db?
        song = mongo.db.songs.find_one({"title": incoming["title"], "artist": incoming["artist"]})

        # then return that id else return a new id after inserting
        if song:
            song_id = song["_id"]
            data = {"song_id": str(song_id)}
        else:
            song_id = mongo.db.songs.insert(incoming)
            data = {"song_id": str(song_id)}

        data = json.dumps(data)

        resp = Response(data, status=201, mimetype="application/json")
        return resp
    else:
        return not_json()


@app.errorhandler(404)
def not_found(error=None):
    message = {
            "status": 404,
            "message": "Not Found: " + request.url,
    }
    resp = jsonify(message)
    resp.status_code = 404

    return resp


def not_json(error=None):
    message = {
            "status": 404,
            "message": "Not JSON: " + request.url,
    }
    resp = jsonify(message)
    resp.status_code = 404

    return resp


# format return string according to day
def format_date(time):

    # convert from unix time to datetime
    date_time = datetime.datetime.fromtimestamp(time)
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