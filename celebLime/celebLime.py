from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, Response, jsonify
from flask.ext.pymongo import PyMongo
from pymongo import ASCENDING
from pymongo.errors import DuplicateKeyError
from bson import json_util
from time import time
from time import mktime
from celery import Celery
from collections import defaultdict
import itunes
import tweepy
import json
import bson
import datetime
import pytz
import jinja2
import urllib2
import urlparse
import requests

## CONFIG SETTINGS ##

DEBUG = False
CONSUMER_TOKEN = "169194713-GNag4qKFdwHsOTn0vpaRtLGssCTGolct7Qcp3AUv"
CONSUMER_KEY = "DXRAHKyo7akk8CvscsRivg"
CONSUMER_SECRET = "cXfqDfMFBQutTMf9KpZWGt2HWDhBVxTajAqVDuFH7U"

if DEBUG:
    CALLBACK_URL = "http://127.0.0.1:8000/verify"
else:
    CALLBACK_URL = "http://www.cvstechnology.ca/projects/celebLime/verify"

app = Flask(__name__)
app.debug = True
app.config.from_object(__name__)
app.config['SECRET_KEY'] = "\x89\x06\xc4\xf0\xc8&\x91\x01\x01\x8d^:\xb4b$\xa5u\x0b\xa8\xd7\x15\xa3\xd0\xab"
mongo = PyMongo(app)

celery = Celery('celebLime', backend='mongodb://localhost', broker='mongodb://localhost')

celery.config_from_object('celeryconfig')

## CELERY TASKS ##

@celery.task
def getiTunesTrack(song_id, search):
    with app.test_request_context():

        results = itunes.search_track(query=search, limit=1)
        # convert the string song_id to a bson ObjectID for mongo
        song_oid = bson.objectid.ObjectId(song_id)

        if results:
            # assume the first result is the best match
            data = results[0].json
        else:
            data = json.loads("{}")

        # update original song_id record to keep all data in one place
        mongo.db.songs.update({"_id": song_oid },{"$set": {"itunes": data}})


@celery.task
def getSpotifyTrack(song_id, search):
    with app.test_request_context():

        # preprocess search terms, replace space with + for a direct API call
        query_url ="http://ws.spotify.com/search/1/track.json"
        query_params = {'q': search}
        results = requests.get(query_url, params=query_params).json()
        # convert the string song_id to a bson ObjectID for mongo
        song_oid = bson.objectid.ObjectId(song_id)

        if results["tracks"]:
            # assume ths first result is the best match
            data = results["tracks"][0]
        else:
            data = json.loads("{}")

        # update original song_id record to keep all data in one place
        mongo.db.songs.update({"_id": song_oid },{"$set": {"spotify": data}})


@celery.task
def getYouTubeVideo(song_id, search):
    with app.test_request_context():

        query_url = "https://gdata.youtube.com/feeds/api/videos"
        query_params = {'alt': 'json', 'max-results': '1', 'orderby': 'relevance', 'q': search, 'v': '2'}
        results = requests.get(query_url, params=query_params).json()

        # convert the string song_id to a bson ObjectID for mongo
        song_oid = bson.objectid.ObjectId(song_id)
        data = {}

        if (results.get('feed').get('entry')) != None:
            # assume the first result is the best match
            video = results.get('feed').get('entry')[0]
            data["title"] = video.get('title').get('$t')
            data["link"] = video.get('link')[0].get('href')
            data["videoid"] = find_between(data["link"], "=", "&")
        else:
            data = json.loads("{}")

        # update original song_id record to keep all data in one place
        mongo.db.songs.update({"_id": song_oid },{"$set": {"youtube": data}})


## CELEBLIME APP ##

# when home page loads
@app.route("/")
def home():

    # check for logged in session
    logged_in = session.get("logged_in")
    name = session.get("username")
    active = session.get("tab")

    if logged_in == None:
        logged_in = False

    if name == None:
        name = ""

    # possibly new session, so set active to Celebrities tab
    if active == None:
        active = True

    # get list of celebs
    celebs_cursor = mongo.db.users.find({"verified": True})

    celebs = []

    for celeb in celebs_cursor:

        celebid = celeb["twitter_id"]
        most_recent_songs = mongo.db.streaming.find({"twitter_id": celebid, "visible": True}).limit(25).sort([("played_at", -1)])

        if most_recent_songs.count() > 0:
            most_recent_song = most_recent_songs[0]
            song_id = most_recent_song["song_id"]
            songinfo = mongo.db.songs.find_one({"_id": song_id})

            if songinfo:
                songinfo["played_at"] = most_recent_song["played_at"]

                if ((int(songinfo["played_at"]) + int(songinfo["duration"])) >= int(time())):
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
        most_recent_songs = mongo.db.streaming.find({"twitter_id": fanid, "visible": True}).limit(25).sort([("played_at", -1)])

        if most_recent_songs.count() > 0:
            most_recent_song = most_recent_songs[0]
            song_id = most_recent_song["song_id"]
            songinfo = mongo.db.songs.find_one({"_id": song_id})

            if songinfo:
                songinfo["played_at"] = most_recent_song["played_at"]

                if ((int(songinfo["played_at"]) + int(songinfo["duration"])) >= int(time())):
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

    tfans = fans
    fans = []
    celebs = []

    for i in tfans:
        if i["screen_name"] in ["fanlimeDRose", "fanlimeBolt"]:
            # replace normal size image to big size                                                                                                                                                        
            celeb_image = i["profile_image_url"]
            i["profile_image_url"] = celeb_image.replace('_normal', '')
            celebs.append(i)
        else:
            fans.append(i)

    return render_template("old/index.html", fans=fans, celebs=celebs, logged_in=logged_in, name=name, active=active, debug=DEBUG)


# first half of twitter oauth - go to twitter login page, then redirect to home page
@app.route("/login")
def login():
    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET, CALLBACK_URL, secure=True)

    try:
        redirect_url = auth.get_authorization_url(True)
        session["request_token"] = (auth.request_token.key,auth.request_token.secret)
        return redirect(redirect_url)
    except tweepy.TweepError, e:
        print e
        print "Access error! Failed to get request token."
        return redirect(url_for("home"))


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

    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET, secure=True)

    token = session.get("request_token")
    session.pop("request_token", None)

    # die gracefully and redirect to login
    if token == None:
        return redirect(url_for("login"))

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
                         "token": auth.access_token.key,
                         "secret": auth.access_token.secret,
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
        mongo.db.users.ensure_index([("token",ASCENDING),("twitter_id",ASCENDING)], unique=True, background=True)

        # found this user in mongo
        already_user = mongo.db.users.find_one({"token": auth.access_token.key, "twitter_id": user.id})

        # maintain the original added_at field
        if already_user:
            user_details["added_at"] = already_user["added_at"]
            user_details["total_logins"] = already_user["total_logins"] + 1

        # now update that user
        try:
            mongo.db.users.update({"token": auth.access_token.key, "twitter_id": user.id}, user_details, upsert=True)
        except DuplicateKeyError:
            print "User error! User can not be updated."

    except tweepy.TweepError, e:
        print e
        print "Access error! Failed to get access token."

    return redirect(url_for("home"))


# when we visit a user profile page

@app.route("/user/<screen_name>/old", methods = ["GET"])
def user_view_depr(screen_name):
    return user(screen_name, "old/user.html")

@app.route("/user/<screen_name>", methods = ["GET"])
def user_view(screen_name):
    return user(screen_name)


def user(screen_name, template="userpage.html"):

    # check for logged in session
    logged_in = session.get("logged_in")
    name = session.get("username")

    if logged_in == None:
        logged_in = False

    if name == None:
        name = ""

    # cast to string just in case
    screen_name = str(screen_name)
    user = mongo.db.users.find_one({"screen_name": screen_name})

    # get the bigger profile image url
    user_image = user["profile_image_url"]
    user["profile_image_url"] = user_image.replace('_normal', '')

    # behind the scenes use twitter id
    user_id = user["twitter_id"]

    playlists = []

    # get all visible playlists for this userid and sort by descending updated date!
    playlists_cursor = mongo.db.playlists.find({"twitter_id": user_id, "visible": True}).sort([("updated_at", -1)])

    for playlist in playlists_cursor:

        songs = []
        song_ids = playlist["songs"]

        for song_id in song_ids:
            # song_id is a dict string, convert to ObjectID
            song_id = song_id["song_id"]
            song_id = bson.objectid.ObjectId(song_id)
            songinfo = mongo.db.songs.find_one(song_id)
            if songinfo:
                songs.append(songinfo)
                playlist["songs"] = songs

        # corner case fix: there are song_ids but no mapped songs!
        if not songs:
            playlist["songs"] = songs

        make_song_playlists(playlist["songs"])
        jsonify_playlist(playlist)

        playlists.append(playlist)

    streaming = []

    # sort recently played songs in descending order by date
    streaming_cursor = mongo.db.streaming.find({"twitter_id": user_id, "visible": True}).limit(25).sort([("played_at", -1)])

    for song in streaming_cursor:
        song_id = song["song_id"]
        songinfo = mongo.db.songs.find_one({"_id": song_id})
        if songinfo:
            songinfo["played_at"] = song["played_at"]
            songinfo["played_count"] = song["played_count"]
            streaming.append(songinfo)

    # added to make recent songs like a playlist
    streaming_playlist = {}
    streaming_playlist["songs"] = streaming
    make_song_playlists(streaming_playlist["songs"])
    jsonify_playlist(streaming_playlist)

    top_songs = []

    # sort in descending order by number of times played
    top_songs_cursor = mongo.db.streaming.find({"twitter_id": user_id, "visible": True}).limit(10).sort([("played_count", -1)])

    for song in top_songs_cursor:
        song_id = song["song_id"]
        songinfo = mongo.db.songs.find_one({"_id": song_id})
        top_songs.append(songinfo)

    # added to make top songs like a playlist
    top_songs_playlist = {}
    top_songs_playlist["songs"] = top_songs
    make_song_playlists(top_songs_playlist["songs"])
    jsonify_playlist(top_songs_playlist)

    artists = []

    # get all streamed songs of this user
    top_artists_cursor = mongo.db.streaming.find({"twitter_id": user_id, "visible": True})

    # now get the song info for each song_id
    for song in top_artists_cursor:
        song_id = song["song_id"]
        songinfo = mongo.db.songs.find_one({"_id": song_id})
        if songinfo:
            artists.append(songinfo)

    # default dict to the rescue!
    counter = defaultdict(int)

    for song in artists:
        artist = song["artist"]
        counter[artist] += 1

    # now reverse sort
    top_artists = sorted(counter, key=counter.get, reverse=True)
    top_artists = top_artists[:6]

    return render_template(template, user=user, playlists=playlists, streaming=streaming_playlist, top_songs=top_songs_playlist, top_artists=top_artists, logged_in=logged_in, name=name, debug=DEBUG)


def make_song_playlists(plist, inplace=True):
    playlist = []
    yt = []
    for song in plist:
        if inplace:
            try:
                song["itunes"]["artworkUrl600"] = song["itunes"].get('artworkUrl100', "").replace("100x100","600x600")
            except:
                pass
        spotify_link = song.get("spotify",[]).get("href", "")
        if spotify_link:
            spotify_link = spotify_link.split(":")
            spotify_id = spotify_link[2]
            playlist.append(spotify_id)
        vidid = song.get("youtube", []).get("videoid", "")
        if vidid:
            yt.append(vidid)
    if inplace:
        for index, song in enumerate(plist):
            string_list = ','.join(map(str, playlist[index:]))
            song["playlists"] = string_list
            song["youtube_playlist"] = json.dumps(yt[index:])
    else:
        string_list = ','.join(map(str, playlist))
        pls = string_list
        ytpls = json.dumps(yt)
        return (pls, ytpls)

def jsonify_playlist(p):
    # { _id, songs: [{title, song}], spotify, youtube, played}
    def es(x):
        #return x
        x = x.replace("'", "&#39;")
        x = x.replace("\"", "&#34;")
        return x
    pl = {}
    #pl["_id"] = p["_id"]
    pl["songs"] = []
    for s in p["songs"]:
        ss = {"title":es(s["title"]), "artist":es(s["artist"])}
        pl["songs"].append(ss)
    t = make_song_playlists(p["songs"], False)
    pl["spotify"] = t[0]
    pl["youtube"] = json.loads(t[1])

    try:
        pl["played"] = p["songs"][0].get("played_at", 0)
    except Exception, e:
        print e

    pl = json.dumps(pl)
    p['js'] = pl


# ajax query to update the recently listened playlist
@app.route("/old/poll/<screen_name>", methods = ["POST"])
def poll_view_depr(screen_name):
    return poll(screen_name, "old/streaming.html")

@app.route("/poll/<screen_name>", methods = ["POST"])
def poll_view(screen_name):
    return poll(screen_name)


def poll(screen_name, template="streaming.html"):

    # cast to string just in case
    screen_name = str(screen_name)
    user = mongo.db.users.find_one({"screen_name": screen_name})

    # behind the scenes use twitter id
    user_id = user["twitter_id"]

    # sort in descending order by date and return most recent song
    recent_songs_cursor = mongo.db.streaming.find({"twitter_id": user_id, "visible": True}).limit(25).sort([("played_at", -1)])

    recent_songs = []

    for recent_song in recent_songs_cursor:
        song_id = recent_song["song_id"]
        songinfo = mongo.db.songs.find_one({"_id": song_id})
        if songinfo:
            songinfo["played_at"] = recent_song["played_at"]
            songinfo["played_count"] = recent_song["played_count"]
            recent_songs.append(songinfo)

    now = False

    # compute if a song is streaming now!
    if recent_songs:
        most_recent_song_start = recent_songs[0]["played_at"]
        most_recent_song_duration = recent_songs[0]["duration"]

        if ((int(most_recent_song_start) + int(most_recent_song_duration)) >= int(time())):
            now = True

    # added to make recent songs like a playlist
    streaming_playlist = {}
    streaming_playlist["songs"] = recent_songs
    make_song_playlists(streaming_playlist["songs"])
    jsonify_playlist(streaming_playlist)

    return render_template(template, streaming=streaming_playlist, now=now, debug=DEBUG)


# store session preferences - right place or use g?
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

# create a new user
@app.route("/signup", methods = ["POST"])
def api_create_user():

    if request.headers["Content-Type"] == "application/json":

        incoming = request.json

        # partially validate JSON fields
        try:
            user_id = incoming["twitter_id"]
            token = incoming["token"]
            name = incoming["name"]
            screen_name = incoming["screen_name"]
            verified = incoming["verified"]
        except KeyError:
            return bad_request()

        # work in unix time
        current_time = int(time())
        incoming["added_at"] = current_time
        incoming["last_logged_in"] = current_time
        incoming["total_logins"] = 1
        incoming["ip"] = request.access_route[0]

        # check if already registered
        already_user = mongo.db.users.find_one({"twitter_id": user_id})

        # then return no content, already in mongo
        if already_user:
            incoming["added_at"] = already_user["added_at"]
            incoming["total_logins"] = already_user["total_logins"] + 1
            mongo.db.users.update({"twitter_id": user_id}, incoming, upsert=True)
            data = {}
            data = json.dumps(data)
            resp = Response(data, status=204, mimetype="application/json")
            return resp
        # else register new user
        else:
            mongo.db.users.insert(incoming)
            data = {}
            data = json.dumps(data)
            resp = Response(data, status=201, mimetype="application/json")
            return resp
    else:
        return not_json()


# create a playlist from JSON object
@app.route("/create", methods = ["POST"])
def api_create_playlist():

    if request.headers["Content-Type"] == "application/json":

        incoming = request.json

        # partially validate JSON fields
        try:
            user_id = incoming["twitter_id"]
            token = incoming["token"]
            songs = incoming["songs"]
        except KeyError:
            return bad_request()

        # check for authorization
        if not is_authorized(user_id):
            return not_authorized()

        # get celebLime ids for these songs
        tracks = []
        for song in songs:
            tracks.append(add_song(song))

        # add timestamps and replace songs/local ids with all celebLime ids
        incoming["added_at"] = int(time())
        incoming["updated_at"] = int(time())
        incoming["songs"] = tracks
        incoming["visible"] = True

        #  then insert
        mongo.db.playlists.ensure_index([("name",ASCENDING),("twitter_id",ASCENDING)], unique=True, background=True)
        try:
            playlist_id = mongo.db.playlists.insert(incoming)
        except DuplicateKeyError:
            return already_exists()

        data = {"twitter_id": user_id, "playlist_id": str(playlist_id), "songs": tracks}

        data = json.dumps(data)

        resp = Response(data, status=201, mimetype="application/json")
        return resp
    else:
        return not_json()


# delete a playlist or song
@app.route("/delete", methods = ["DELETE"])
def api_delete():

    if request.headers["Content-Type"] == "application/json":

        incoming = request.json

        playlist_id = 0
        song_id = 0

        # partially validate JSON fields
        try:
            user_id = incoming["twitter_id"]
            token = incoming["token"]
            if "playlist_id" in incoming:
                playlist_id = incoming["playlist_id"]
            if "song_id" in incoming:
                song_id = incoming["song_id"]
        except KeyError:
            return bad_request()

        # check for authorization
        if not is_authorized(user_id):
            return not_authorized()

        if playlist_id:
            # incoming playlist_id is a string, convert to ObjectID
            playlist_oid = bson.objectid.ObjectId(playlist_id)

            # remove from mongo
            mongo.db.playlists.remove({"_id": playlist_oid})

        if song_id:
            # incoming song_id is a string, convert to ObjectID
            song_oid = bson.objectid.ObjectId(song_id)

            # remove all from mongo
            mongo.db.songs.remove({"_id": song_oid})
            mongo.db.streaming.remove({"_id": song_oid})
            mongo.db.playlists.update({"twitter_id": user_id}, {"$pull": {"songs": {"song_id": song_id}}}, multi=True)


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

        # partially validate JSON fields
        try:
            user_id = incoming["twitter_id"]
            token = incoming["token"]
            playlist_id = incoming["playlist_id"]
            songs = incoming["songs"]
        except KeyError:
            return bad_request()

        # check for authorization
        if not is_authorized(user_id):
            return not_authorized()

        # get celebLime ids for these songs
        tracks = []
        for song in songs:
            tracks.append(add_song(song))

        # incoming playlist_id is a string, convert to ObjectID
        playlist_oid = bson.objectid.ObjectId(playlist_id)

        # find the playlist in mongo
        playlist = mongo.db.playlists.find_one({"_id": playlist_oid})

        # maintain the original added_at field but update the updated_at field
        if playlist:
            incoming["added_at"] = playlist["added_at"]
            incoming["visible"] = playlist["visible"]
            incoming["updated_at"] = int(time())
            incoming["songs"] = tracks
            incoming["name"] = playlist["name"]

            # now update that playlist
            try:
                mongo.db.playlists.update({"_id": playlist_oid}, incoming, upsert=True)
            except DuplicateKeyError:
                print "Playlist error! Playlist can not be updated."

        else:
            print "Playlist error! Playlist not found."

        data = {"twitter_id": user_id, "playlist_id": str(playlist_id), "songs": tracks}

        data = json.dumps(data)

        resp = Response(data, status=200, mimetype="application/json")
        return resp
    else:
        return not_json()


# stream a song
@app.route("/stream", methods = ["PUT"])
def api_stream_song():

    if request.headers["Content-Type"] == "application/json":

        incoming = request.json

        # partially validate JSON fields
        try:
            user_id = incoming["twitter_id"]
            token = incoming["token"]
            song_id = incoming["song_id"]
            played_at = incoming["played_at"]
        except KeyError:
            return bad_request()

        # check for authorization
        if not is_authorized(user_id):
            return not_authorized()

        # incoming song_id is a string, convert to ObjectID
        song_oid = bson.objectid.ObjectId(song_id)

        # if index not there, add a compound index
        mongo.db.streaming.ensure_index([("twitter_id",ASCENDING),("song_id",ASCENDING)], unique=True, background=True)

        # find the song in mongo streamed by that user
        song = mongo.db.streaming.find_one({"twitter_id": user_id, "song_id": song_oid})

        # by default, a streaming song has to be visible
        incoming["visible"] = True

        # update the number of times played, if this key does not exist then song never streamed before
        try:
            incoming["played_count"] = song["played_count"] + 1
            incoming["song_id"] = song_oid
            mongo.db.streaming.update({"twitter_id": user_id, "song_id": song_oid}, incoming, upsert=True)
        except TypeError:
            incoming["played_count"] = 1
            incoming["song_id"] = song_oid
            mongo.db.streaming.insert(incoming)

        data = {}

        data = json.dumps(data)

        resp = Response(data, status=204, mimetype="application/json")
        return resp
    else:
        return not_json()


# get the most recent songs by number and visibility
@app.route("/recent", methods = ["GET", "POST"])
def api_recent_list():

    if request.headers["Content-Type"] == "application/json":

        incoming = request.json

        # partially validate JSON fields
        try:
            user_id = incoming["twitter_id"]
            token = incoming["token"]
        except KeyError:
            return bad_request()

        # check for authorization
        if not is_authorized(user_id):
            return not_authorized()

        try:
            limit = incoming["limit"]
        except KeyError:
            limit = None

        try:
            visible = incoming["visible"]
        except KeyError:
            visible = None

        if limit == None and visible == None:
            most_recent_songs_cursor = mongo.db.streaming.find({"twitter_id": user_id}).sort([("played_at", -1)])

        if limit != None and visible == None:
            most_recent_songs_cursor = mongo.db.streaming.find({"twitter_id": user_id}).limit(limit).sort([("played_at", -1)])

        if limit == None and visible != None:
            most_recent_songs_cursor = mongo.db.streaming.find({"twitter_id": user_id, "visible": visible}).sort([("played_at", -1)])

        if limit != None and visible != None:
            most_recent_songs_cursor = mongo.db.streaming.find({"twitter_id": user_id, "visible": visible}).limit(limit).sort([("played_at", -1)])

        mru = []

        for song in most_recent_songs_cursor:
            song_id = str(song["song_id"])
            mru.append(song_id)

        data = {"recent": mru}

        data = json.dumps(data)

        resp = Response(data, status=200, mimetype="application/json")
        return resp
    else:
        return not_json()


# get all the playlists for a user
@app.route("/playlists", methods = ["GET", "POST"])
def api_playlists():

    if request.headers["Content-Type"] == "application/json":

        incoming = request.json

        # partially validate JSON fields
        try:
            user_id = incoming["twitter_id"]
            token = incoming["token"]
        except KeyError:
            return bad_request()

        # check for authorization
        if not is_authorized(user_id):
            return not_authorized()

        try:
            visible = incoming["visible"]
            playlists_cursor = mongo.db.playlists.find({"twitter_id": user_id, "visible": visible})
        except KeyError:
            playlists_cursor = mongo.db.playlists.find({"twitter_id": user_id})

        playlists = []

        for playlist in playlists_cursor:
            playlist["playlist_id"] = str(playlist["_id"])
            playlist.pop("_id", None)
            playlists.append(playlist)

        data = {"playlists": playlists}

        data = json.dumps(data)

        resp = Response(data, status=200, mimetype="application/json")
        return resp
    else:
        return not_json()


# publish/unpublish a playlist or streamed song
@app.route("/publish", methods = ["PATCH"])
def api_publish_playlist():

    if request.headers["Content-Type"] == "application/json":

        incoming = request.json

        playlist_id = 0
        song_id = 0

        # partially validate JSON fields
        try:
            user_id = incoming["twitter_id"]
            token = incoming["token"]
            if "playlist_id" in incoming:
                playlist_id = incoming["playlist_id"]
            if "song_id" in incoming:
                song_id = incoming["song_id"]
            visibility = incoming["visible"]
        except KeyError:
            return bad_request()

        # check for authorization
        if not is_authorized(user_id):
            return not_authorized()

        if playlist_id:
            # incoming playlist_id is a string, convert to ObjectID
            playlist_oid = bson.objectid.ObjectId(playlist_id)
            # make the playlist visible or not
            mongo.db.playlists.update({"_id": playlist_oid},{"$set": {"visible": visibility}})

        if song_id:
            # incoming song_id is a string, convert to ObjectID
            song_oid = bson.objectid.ObjectId(song_id)

            # make the streamed song visible or not
            mongo.db.streaming.update({"twitter_id": user_id, "song_id": song_oid}, {"$set": {"visible": visibility}})

        data = {}

        data = json.dumps(data)

        resp = Response(data, status=204, mimetype="application/json")
        return resp
    else:
        return not_json()


# add a song via the api and return a celebLime id
@app.route("/add", methods = ["POST"])
def api_add_song():

    if request.headers["Content-Type"] == "application/json":

        incoming = request.json

        data = json.dumps(add_song(incoming))

        resp = Response(data, status=201, mimetype="application/json")
        return resp
    else:
        return not_json()


# get a song via the api and return its metadata
@app.route("/get", methods = ["GET", "POST"])
def api_get_song():

    if request.headers["Content-Type"] == "application/json":

        try:
            song_id = request.json["song_id"]
        except KeyError:
            return bad_request()

        song_oid = bson.objectid.ObjectId(song_id)

        song = mongo.db.songs.find_one({"_id": song_oid})

        if song:
            song["song_id"] = str(song["_id"])
            song.pop("_id", None)
        else:
            song = {}

        data = json.dumps(song)

        resp = Response(data, status=200, mimetype="application/json")
        return resp
    else:
        return not_json()


def add_song(song):

    # determine if full song or just id
    # if just song_id, then this song is already in our database with a proper celebLime id
    try:
        title = song["title"]
        artist = song["artist"]
        album = song["album"]
        duration = song["duration"]
    except KeyError:
        return {"song_id": song["song_id"]}

    # if index not there, add a compound index
    mongo.db.songs.ensure_index([("title",ASCENDING),("artist",ASCENDING), ("album", ASCENDING)], unique=True, background=True)

    # does this song already exist in the db?
    already_song = mongo.db.songs.find_one({"title": title, "artist": artist, "album": album})

    # then return that id else return a new id after inserting
    if already_song:
        song_id = already_song["_id"]
        data = {"song_id": str(song_id)}
    else:
        song["itunes"] = {}
        song["spotify"] = {}
        song["youtube"] = {}
        song_id = mongo.db.songs.insert(song)
        data = {"song_id": str(song_id)}

        # dispatch to celery to update in the background!
        search = title + " " + artist
        asynciTunes = getiTunesTrack.delay(str(song_id), search)
        asyncSpotify = getSpotifyTrack.delay(str(song_id), search)
        asyncYouTube = getYouTubeVideo.delay(str(song_id), search)

    return data


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


def already_exists(error=None):
    message = {
            "status": 400,
            "message": "Bad Request (resource already exists): " + request.url,
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


# for now, simply check that the twitter_id is present in mongodb
# later on we would use it in conjunction with the secret and key to sign a request for twitter
def is_authorized(user_id):

    result = mongo.db.users.find_one({"twitter_id": user_id})
    if result:
        return True
    else:
        return False


# format return string according to day
def format_date(time):

    # convert from unix time to datetime
    date_time = datetime.datetime.fromtimestamp(time)
    if date_time.date() == datetime.datetime.today().date():
        return date_time.strftime('Today at ' + '%H:%M:%S')
    if date_time.date() + datetime.timedelta(1) == datetime.datetime.today().date():
        return date_time.strftime('Yesterday at ' + '%H:%M:%S')
    else:
        return date_time.strftime('%a %d %b %Y at %H:%M:%S')



#rest get playlist data

@app.route("/rest/playlist/<pid>", methods = ["GET"])
def user_view_pid(pid):
    playlist = []

    # get all visible playlists for this userid and sort by descending updated date!
    try:
        p_id = bson.objectid.ObjectId(pid)
        playlist = mongo.db.playlists.find_one(p_id)
    except:
        playlist = {}

    songs = []
    if playlist:
        del playlist["_id"]
        del playlist["token"]
        song_ids = playlist.get("songs", [])
    else :
        song_ids = []


    for song_id in song_ids:
        # song_id is a dict string, convert to ObjectID
        song_id = song_id["song_id"]
        song_id = bson.objectid.ObjectId(song_id)
        songinfo = mongo.db.songs.find_one(song_id)
        if songinfo:
            del songinfo["_id"]
            songs.append(songinfo)
            playlist["songs"] = songs

    return Response(json.dumps(playlist), status=200, mimetype="application/json")

# now apply this jinja2 template
app.jinja_env.globals.update(format_date=format_date)
app.debug = True

if __name__ == "__main__":
    if DEBUG:
        app.run(host="0.0.0.0", port=8000)
    else:
        app.run()
