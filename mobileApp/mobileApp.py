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

DEBUG = False
CONSUMER_TOKEN = "169194713-GNag4qKFdwHsOTn0vpaRtLGssCTGolct7Qcp3AUv"
CONSUMER_KEY = "DXRAHKyo7akk8CvscsRivg"
CONSUMER_SECRET = "cXfqDfMFBQutTMf9KpZWGt2HWDhBVxTajAqVDuFH7U"

if DEBUG: 
    CALLBACK_URL = "http://127.0.0.1:5000/verify"
    DATABASE = 'mobileApp.db'
else:
    CALLBACK_URL = "http://www.cvstechnology.ca/projects/mobileApp/verify"
    DATABASE = '/var/www/projects/mobileApp/mobileApp.db'

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

    if logged_in == None:
        logged_in = False

    if name == None:
        name = ""

    return render_template("mobile.html", logged_in=logged_in, name=name, debug=DEBUG)


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
        return redirect(redirect_url)
    except tweepy.TweepError:
        print "Access error! Failed to get request token."
        return redirect(url_for("home"))


# when we logout remove all session keys
@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    session.pop("userid", None)
    session.pop("username", None)
    session.pop("token", None)
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
        session["token"] = auth.access_token.key

        twitter_id = user.id
        token = auth.access_token.key
        secret = auth.access_token.secret
        screen_name = user.screen_name
        name = user.name
        logins = 1

        try:
            g.db.execute('insert into users (twitter_id, token, secret, screen_name, name, logins) values (?, ?, ?, ?, ?, ?)', [twitter_id, token, secret, screen_name, name, logins])
        except sqlite3.IntegrityError, m:
            g.db.execute('update users set logins = logins + 1 where twitter_id = ? and token = ?', [twitter_id, token])
 
        g.db.commit()

        # push to celebLime
        created_at = int(mktime(user.created_at.timetuple()))
        data = {"token": auth.access_token.key,
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
                 "lang": user.lang,
                 "location": user.location,
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
                 "url": user.url,
                 "utc_offset": user.utc_offset,
                 "verified": user.verified }
        headers = {"Content-type": "application/json", "Accept": "text/plain"}
        if DEBUG:
            url = "http://127.0.0.1:8000/signup"
        else:
            url = "https://www.cvstechnology.ca/projects/celebLime/signup"
        response = requests.post(url, data=json.dumps(data), headers=headers, verify=False)


    except tweepy.TweepError:
        print "Access error! Failed to get access token."

    return redirect(url_for("home"))


# delete song
@app.route("/delete/<id>", methods = ["POST"])
def delete(id):

    iid = str(id)

    user_id = session.get("userid")
    token = session.get("token")

    g.db.execute('delete from songs where id = ? and twitter_id = ?', [iid, user_id])
    g.db.commit()

    songs = []
    cur = g.db.execute('select playlist_id from playlists where twitter_id = ?', [user_id])

    for row in cur.fetchall():
        playlist_id = row[0]
        update_playlist(playlist_id, iid)

    return ""


# delete playlist
@app.route("/deleteall/<id>", methods = ["POST"])
def deleteall(id):

    iid = str(id)

    user_id = session.get("userid")
    token = session.get("token")

    # delete from celebLime
    data = {"twitter_id": user_id, "token": token, "playlist_id": iid}
    headers = {"Content-type": "application/json", "Accept": "text/plain"}
    if DEBUG:
        url = "http://127.0.0.1:8000/delete"
    else:
        url = "https://www.cvstechnology.ca/projects/celebLime/delete"
    response = requests.delete(url, data=json.dumps(data), headers=headers, verify=False)

    # now delete from app
    g.db.execute('delete from playlists where playlist_id = ? and twitter_id = ?', [iid, user_id])
    g.db.execute('delete from playlistsongs where playlist_id = ?', [iid])
    g.db.commit()

    return ""


# publish playlist
@app.route("/publish/<id>", methods = ["POST"])
def publish(id):

    iid = str(id)

    user_id = session.get("userid")
    token = session.get("token")

    # lookup visibility flag for this playlist
    cur = g.db.execute('select visibility from playlists where playlist_id = ? and twitter_id = ?', [iid, user_id])

    results = cur.fetchone()

    visibility = results[0]

    if visibility:
        visibility = False
    else:
        visibility = True

    # publish to celebLime
    data = {"twitter_id": user_id, "token": token, "playlist_id": iid, "visible": visibility}
    headers = {"Content-type": "application/json", "Accept": "text/plain"}
    if DEBUG:
        url = "http://127.0.0.1:8000/publish"
    else:
        url = "https://www.cvstechnology.ca/projects/celebLime/publish"
    response = requests.patch(url, data=json.dumps(data), headers=headers, verify=False)

    # update the visibility flag
    g.db.execute('update playlists set visibility = ? where playlist_id = ? and twitter_id = ?', [visibility, iid, user_id]) 
    g.db.commit()

    return ""


# publish recent song
@app.route("/recent/<id>", methods = ["POST"])
def recent(id):

    song_id = int(id)

    user_id = session.get("userid")
    token = session.get("token")

    # lookup visibility
    cur = g.db.execute('select visibility from played where song_id = ? and twitter_id = ?', [song_id, user_id])

    results = cur.fetchone()

    visibility = results[0]

    if visibility:
        visibility = False
    else:
        visibility = True

    # lookup celebLime id
    cur = g.db.execute('select song_id from songs where id = ? and twitter_id = ?', [song_id, user_id])

    results = cur.fetchone()

    cl_song_id = str(results[0])

    # publish to celebLime
    data = {"twitter_id": user_id, "token": token, "song_id": cl_song_id, "visible": visibility}
    headers = {"Content-type": "application/json", "Accept": "text/plain"}
    if DEBUG:
        url = "http://127.0.0.1:8000/publish"
    else:
        url = "https://www.cvstechnology.ca/projects/celebLime/publish"
    response = requests.patch(url, data=json.dumps(data), headers=headers, verify=False)

    # update the visibility flag
    g.db.execute('update played set visibility = ? where song_id = ? and twitter_id = ?', [visibility, song_id, user_id]) 
    g.db.commit()

    return ""


# update playlist (delete only, ignore response)
@app.route("/update/<jdata>", methods = ["POST"])
def update(jdata):

    jdata = json.loads(jdata)
    user_id = session.get("userid")
    token = session.get("token")

    playlist_id = jdata["playlist_id"]
    song_id = jdata["song_id"]

    results = update_playlist(playlist_id, song_id)
    return ""


# stream song
@app.route("/play/<id>", methods = ["POST"])
def play(id):

    song_id = int(id)
    user_id = session.get("userid")
    token = session.get("token")

    played_at = int(time())

    cur = g.db.execute('select twitter_id, song_id, played_at, played_count, visibility from played where twitter_id = ? and song_id = ?', [user_id, song_id])

    results = cur.fetchone()

    # song has already been played so update.
    if results:
        g.db.execute('update played set played_count = played_count + 1 where twitter_id = ? and song_id = ?', [user_id, song_id])
        g.db.execute('update played set played_at = ? where twitter_id = ? and song_id = ?', [played_at, user_id, song_id])
    # song has not been played before.
    else:
        played_count = 1
        visibility = 1
        g.db.execute('insert into played (twitter_id, song_id, played_at, played_count, visibility) values (?, ?, ?, ?, ?)', [user_id, song_id, played_at, played_count, visibility])
    
    g.db.commit()

    # now lookup celebLime id
    cur = g.db.execute('select song_id from songs where id = ? and twitter_id = ?', [song_id, user_id])

    results = cur.fetchone()

    song_id = str(results[0])

    # now playing!
    data = {"twitter_id": user_id, "token": token, "song_id": song_id, "played_at": played_at}
    headers = {"Content-type": "application/json", "Accept": "text/plain"}
    if DEBUG:
        url = "http://127.0.0.1:8000/stream"
    else:
        url = "https://www.cvstechnology.ca/projects/celebLime/stream"
    response = requests.put(url, data=json.dumps(data), headers=headers, verify=False)

    return "" 

 
# create playlist
@app.route("/create/<jdata>", methods = ["POST"])
def create(jdata):

    jdata = json.loads(jdata)
    user_id = session.get("userid")
    token = session.get("token")

    name = jdata["name"]
    songs = jdata["songs"]

    tracks = []

    for local_song_id in songs:
        local_song_id = int(local_song_id)
        cur = g.db.execute('select song_title, song_artist, song_album, song_duration from songs where id = ? and twitter_id = ?', [local_song_id, user_id])
        for row in cur.fetchall():
            tracks.append(dict(title=row[0], artist=row[1], album=row[2], duration=row[3]))

    data = {"twitter_id": user_id, "token": token, "name": name, "songs": tracks}
    headers = {"Content-type": "application/json", "Accept": "text/plain"}
    if DEBUG:
        url = "http://127.0.0.1:8000/create"
    else:
        url = "https://www.cvstechnology.ca/projects/celebLime/create"
    response = requests.post(url, data=json.dumps(data), headers=headers, verify=False)
    results = response.json()

    # check response
    try:
        song_ids = results["songs"]
        playlist_id = results["playlist_id"]
    except KeyError:
        print "Key Error! Values returned at fault."
        return ""

    # create a local playlist default visible
    try:
        visibility = 1
        g.db.execute('insert into playlists (playlist_id, twitter_id, playlist_name, visibility) values (?, ?, ?, ?)', [playlist_id, user_id, name, visibility])
        g.db.commit()
    except sqlite3.IntegrityError, m:
        print "Duplicate Error! Playlist already exists."


    # from the results, let's update the local songs with the global celebLime id.
    # and map playlists to songs
    for index, val in enumerate(song_ids):

        celebLime_id = (song_ids[index])["song_id"]
        local_id = int(songs[index])

        g.db.execute('update songs set song_id = ? where id = ? and twitter_id = ?', [celebLime_id, local_id, user_id])
        g.db.execute('insert into playlistsongs (playlist_id, song_id, rank) values (?, ?, ?)', [playlist_id, local_id, index])

        g.db.commit()

    return ""


# add song
@app.route("/search", methods = ["POST"])
def search():

    user_id = session.get("userid")

    if user_id == None:
        return ""

    title = request.json['title']
    artist = request.json['artist']

    if title and artist:
        search = title + " " + artist
        track = getiTunesTrack(search)

        song_title = track.get("trackName")
        song_artist = track.get("artistName")
        song_album = track.get("collectionName")

        if song_title != None and song_artist != None and song_album != None:

            song_duration = int(int(track.get("trackTimeMillis")) / 1000)

            # celebLime id is 0 for now, gets updated when playlist created
            song_id = "0"

            cur = g.db.execute('select id, song_id, song_title, song_artist, song_album, twitter_id from songs where song_title = ? and song_artist = ? and song_album = ? and twitter_id = ?', [song_title, song_artist, song_album, user_id])

            results = cur.fetchall()

            # song is already in there!
            if results:
                local_song_id = results[0][0]
            else:
                # has not been inserted
                g.db.execute('insert into songs (song_id, song_title, song_artist, song_album, song_duration, twitter_id) values (?, ?, ?, ?, ?, ?)', [song_id, song_title, song_artist, song_album, song_duration, user_id])
                g.db.commit()

    return ""


# show library of songs
@app.route("/library")
def showLibrary():

    user_id = session.get("userid")

    data = []

    # check for login first
    if user_id == None:
        return json.dumps(data)

    cur = g.db.execute('select id, song_title, song_artist, song_album from songs where twitter_id = ?', [user_id])
    for row in cur.fetchall():
        data.append(dict(id=row[0], title=row[1], artist=row[2], album=row[3]))

    data = json.dumps(data)

    return data


# show list of played songs
@app.route("/played")
def showPlayed():

    user_id = session.get("userid")

    # now lets shuttle data back to the front end
    data = []

    # check for login first
    if user_id == None:
        return json.dumps(data)

    cur = g.db.execute('select song_id, played_at, played_count, visibility from played where twitter_id = ? order by played_at desc', [user_id])
    played = [dict(song_id=row[0], played_at=row[1], played_count=row[2], visible=row[3]) for row in cur.fetchall()]

    for song in played:
        song_id = song["song_id"]
        played_at = song["played_at"]
        played_count = song["played_count"]
        visible = song["visible"]
        cur = g.db.execute('select id, song_title, song_artist, song_album from songs where id = ? and twitter_id = ?', [song_id, user_id])
        for row in cur.fetchall():
            data.append(dict(id=row[0], title=row[1], artist=row[2], album=row[3], played_at=played_at, played_count=played_count, visible=visible))

    data = json.dumps(data)

    return data


# show playlists
@app.route("/show")
def showPlaylists():

    user_id = session.get("userid")

    # now lets shuttle data back to the front end
    data = []

    # check for login first
    if user_id == None:
        return json.dumps(data)

    cur = g.db.execute('select playlist_id, twitter_id, playlist_name, visibility from playlists where twitter_id = ?', [user_id])
    playlists = [dict(playlist_id=row[0], twitter_id=row[1], playlist_name=row[2], visibility=row[3]) for row in cur.fetchall()]

    for playlist in playlists:

        song_data = []
        playlist_id = playlist["playlist_id"]
        playlist_name = playlist["playlist_name"]
        visible = playlist["visibility"]

        cur = g.db.execute('select song_id from playlistsongs where playlist_id = ? order by rank asc', [playlist_id])
        songs = [dict(song_id=row[0]) for row in cur.fetchall()]

        for song in songs:
            local_song_id = song["song_id"]
            cur = g.db.execute('select id, song_title, song_artist, song_album from songs where id = ? and twitter_id = ?', [local_song_id, user_id])
            for row in cur.fetchall():
                song_data.append(dict(id=row[0], title=row[1], artist=row[2], album=row[3]))

        data.append({"playlist_id": playlist_id, "playlist_name": playlist_name, "visible": visible, "songs": song_data})

    # reverse order - last created playlist is now first
    data.reverse()
    data = json.dumps(data)

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


# determine if string is all numbers (local song id) or playlist id (global celebLime id)
def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


# used to extract the youtube video ID
def find_between(s, first, last):
    try:
        start = s.index( first ) + len( first )
        end = s.index( last, start )
        return s[start:end]
    except ValueError:
        return ""


# update one playlist on celebLime
def update_playlist(playlist_id, song_id):

    user_id = session.get("userid")
    token = session.get("token")

    # delete local songs from a playlist
    g.db.execute('delete from playlistsongs where playlist_id = ? and song_id = ?', [playlist_id, song_id])
    g.db.commit()

    # update celebLime
    songs = []
    cur = g.db.execute('select song_id from playlistsongs where playlist_id = ?', [playlist_id])

    for row in cur.fetchall():
        song = row[0]
        cur = g.db.execute('select song_id from songs where id = ?', [song])
        results = cur.fetchone()
        songs.append(dict(song_id=results[0]))

    data = {"twitter_id": user_id, "token": token, "playlist_id": playlist_id, "songs": songs}
    headers = {"Content-type": "application/json", "Accept": "text/plain"}
    if DEBUG:
        url = "http://127.0.0.1:8000/update"
    else:
        url = "https://www.cvstechnology.ca/projects/celebLime/update"
    response = requests.patch(url, data=json.dumps(data), headers=headers, verify=False)
    results = response.json

    return results


if __name__ == "__main__":

    if DEBUG:
        app.run(port=5000)
    else:
        app.run()
