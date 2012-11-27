from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, Response, jsonify
from flask.ext.pymongo import PyMongo
from pymongo import ASCENDING
from pymongo.errors import DuplicateKeyError
import tweepy
import json
import datetime

CONSUMER_TOKEN = "169194713-GNag4qKFdwHsOTn0vpaRtLGssCTGolct7Qcp3AUv"
CONSUMER_KEY = "DXRAHKyo7akk8CvscsRivg"
CONSUMER_SECRET = "cXfqDfMFBQutTMf9KpZWGt2HWDhBVxTajAqVDuFH7U"
CALLBACK_URL = "http://127.0.0.1:8000/verify"
session = dict()

DEBUG = True

app = Flask(__name__)
app.config.from_object(__name__)
mongo = PyMongo(app)


@app.route('/')
def home():
    try:
        logged_in = session['logged_in']
    except KeyError:
        logged_in = False

    celebs = []
    return render_template('index.html', celebs=celebs, logged_in=logged_in)


@app.route('/login')
def login():
    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET, CALLBACK_URL)

    try:
        redirect_url = auth.get_authorization_url(True)
        print redirect_url
        session['request_token'] = (auth.request_token.key,auth.request_token.secret)
    except tweepy.TweepError:
        print 'Access error! Failed to get request token.'

    return redirect(redirect_url)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('home'))


@app.route('/verify')
def verify():
    verifier = request.args['oauth_verifier']
    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)

    token = session['request_token']
    del session['request_token']
    auth.set_request_token(token[0], token[1])

    try:
        auth.get_access_token(verifier)
        session['logged_in'] = True
        api = tweepy.API(auth)
        user = api.me()

        user_details = { 'added_at': datetime.datetime.utcnow(),
                         'access_key': auth.access_token.key,
                         'access_secret': auth.access_token.secret,
                         'contributors_enabled': user.contributors_enabled,
                         'created_at': user.created_at,
                         'description': user.description,
                         'favourites_count': user.favourites_count,
                         'followers_count': user.followers_count,
                         'following': user.following,
                         'friends_count': user.friends_count,
                         'geo_enabled': user.geo_enabled,
                         'id': user.id,
                         'ip': request.access_route[0],
                         'lang': user.lang,
                         'location': user.location,
                         'last_logged_in': datetime.datetime.utcnow(),
                         'name': user.name,
                         'notifications': user.notifications,
                         'profile_background_color': user.profile_background_color,
                         'profile_background_image_url': user.profile_background_image_url,
                         'profile_background_tile': user.profile_background_tile,
                         'profile_image_url': user.profile_image_url,
                         'profile_link_color': user.profile_link_color,
                         'profile_sidebar_border_color': user.profile_sidebar_border_color,
                         'profile_sidebar_fill_color': user.profile_sidebar_fill_color,
                         'profile_text_color': user.profile_text_color,
                         'profile_use_background_image': user.profile_use_background_image,
                         'protected': user.protected,
                         'screen_name': user.screen_name,
                         'statuses_count': user.statuses_count,
                         'time_zone': user.time_zone,
                         'total_logins': 1,
                         'url': user.url,
                         'utc_offset': user.utc_offset,
                         'verified': user.verified }

        # if index not there, add a compound index
        mongo.db.users.ensure_index([('access_key',ASCENDING),('access_secret',ASCENDING),('id',ASCENDING),('screen_name',ASCENDING)], unique=True, background=True)

        # found this user in mongo
        already_user = mongo.db.users.find_one({'access_key': auth.access_token.key, 'access_secret': auth.access_token.secret, 'id': user.id})

        # maintain the original added_at field
        if already_user:
            user_details['added_at'] = already_user['added_at']
            user_details['total_logins'] = already_user['total_logins'] + 1

        # now update that user
        try:
            mongo.db.users.update({'access_key': auth.access_token.key, 'access_secret': auth.access_token.secret, 'id': user.id}, user_details, upsert=True)
        except DuplicateKeyError:
            print 'Duplicate error! User inserted already.'

    except tweepy.TweepError:
        print 'Access error! Failed to get access token.'

    return redirect(url_for('home'))


@app.route('/create', methods = ['POST'])
def api_create_playlist():

    if request.headers['Content-Type'] == 'application/json':

        mongo.db.users.ensure_index([('access_key',ASCENDING),('access_secret',ASCENDING),('id',ASCENDING),('screen_name',ASCENDING)], unique=True, background=True)


        print "JSON Message: " + json.dumps(request.json)
        data = {'playlist_id'  : 1}
        js = json.dumps(data)
        resp = Response(js, status=201, mimetype='application/json')
        return resp
    else:
        return not_found()


@app.route('/add', methods = ['POST'])
def api_add_song():

    if request.headers['Content-Type'] == 'application/json':
        print "JSON Message: " + json.dumps(request.json)
        data = {'playlist_id'  : 1}
        js = json.dumps(data)
        resp = Response(js, status=201, mimetype='application/json')
        return resp
    else:
        return not_found()


@app.errorhandler(404)
def not_found(error=None):
    message = {
            'status': 404,
            'message': 'Not Found: ' + request.url,
    }
    resp = jsonify(message)
    resp.status_code = 404

    return resp


if __name__ == '__main__':
    app.run(port=8000)

