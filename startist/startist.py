from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, Response, jsonify, make_response
from flask.ext.pymongo import PyMongo
from flask import send_from_directory
from pymongo import ASCENDING
from validate_email import validate_email
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug import secure_filename
from time import mktime
from time import time
from jinja2 import evalcontextfilter, Markup, escape
import datetime
import tweepy
import json
import bson
import re
import requests
import urlparse
import os
import gridfs


# CONFIGURATION [

DEBUG = False
KEY = 'H\xb8\x8do\x8a\xfc\x80\x18\x06\xaf!i\x028\x1bPs\x85\xe7\x87\x11\xe6j\xb1'
UPLOAD_FOLDER = os.path.realpath('.') + '/static/pics/'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
APP_STATIC = os.path.join(APP_ROOT, 'static')
APP_STATIC_IMG = os.path.join(APP_STATIC, 'img')
APP_STATIC_JS = os.path.join(APP_STATIC, 'js')
APP_STATIC_CSS = os.path.join(APP_STATIC, 'css')
ANONYMOUS = os.path.join(APP_STATIC_IMG, 'anonymous.jpg')
SEARCH_LIMIT = 10
DEFAULT_DESCRIPTION = "Say something nice about yourself."
COMMON_WORDS = ['a', 'able', 'about', 'across', 'after', 'all', 'almost', 'also', 'am', 'among', 'an', 'and', 'any', 'are', 'as', 'at', 'be', 'because', 'been', 'but', 'by', 'can', 'cannot', 'could', 'dear', 'did', 'do', 'does', 'either', 'else', 'ever', 'every', 'for', 'from', 'get', 'got', 'had', 'has', 'have', 'he', 'her', 'hers', 'him', 'his', 'how', 'however', 'i', 'if', 'in', 'into', 'is', 'it', 'its', 'just', 'least', 'let', 'like', 'likely', 'may', 'me', 'might', 'most', 'must', 'my', 'neither', 'no', 'nor', 'not', 'of', 'off', 'often', 'on', 'only', 'or', 'other', 'our', 'own', 'rather', 'said', 'say', 'says', 'she', 'should', 'since', 'so', 'some', 'than', 'that', 'the', 'their', 'them', 'then', 'there', 'these', 'they', 'this', 'tis', 'to', 'too', 'twas', 'us', 'wants', 'was', 'we', 'were', 'what', 'when', 'where', 'which', 'while', 'who', 'whom', 'why', 'will', 'with', 'would', 'yet', 'you', 'your']
WORD_SUFFIX = ['s', 'ed', 'er', 'ing', 'mer', 'ist']


app = Flask(__name__)
app.config.from_object(__name__)
app.config['SECRET_KEY'] = KEY
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
mongo = PyMongo(app)
with app.test_request_context():
    fs = gridfs.GridFS(mongo.db)

if DEBUG:
    FB_SIGNUP_REDIRECT = 'http://localhost:8000/fbsverify'
    FB_LOGIN_REDIRECT = 'http://localhost:8000/fblverify'
    FB_APP_ID = '330274977087606'
    FB_SECRET = 'e9fe610df8d1cbf4ae3dd57226558a29'
    FB_PERMISSIONS = 'user_about_me, email, user_likes, user_interests, user_location'
    FB_STATE = KEY
    TW_SIGNUP_REDIRECT = 'http://localhost:8000/twsverify'
    TW_LOGIN_REDIRECT = 'http://localhost:8000/twlverify'
    TW_CONSUMER_KEY = '9EUuiPXssnwKPwDioQeEyw'
    TW_CONSUMER_SECRET = 'gWXFTi1bDtkbR6Tbu1zRsZ2QHvPkOBh2nsubfA15D8'
else:
    FB_SIGNUP_REDIRECT = 'http://www.startists.com/fbsverify'
    FB_LOGIN_REDIRECT = 'http://www.startists.com/fblverify'
    FB_APP_ID = '471868396209054'
    FB_SECRET = '12d3aa51e0c73758cac9f283fcca23e8'
    FB_PERMISSIONS = 'user_about_me, email, user_likes, user_interests, user_location'
    FB_STATE = KEY
    TW_SIGNUP_REDIRECT = 'http://www.startists.com/twsverify'
    TW_LOGIN_REDIRECT = 'http://www.startists.com/twlverify'
    TW_CONSUMER_KEY = 'QTidL2svjqbtbnDIi3GEg'
    TW_CONSUMER_SECRET = 'GVZ6eApHktuiFJeZRrUQSqc4CwfEfltwi2rC6hTg8'

# ] CONFIGURATION


# PRELAUNCH [

# render the signup page for now until we launch
@app.route('/')
def signup():
    return render_template('launch.html')


# validate email submitted from signup page:
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

# ] PRELAUNCH


# LAUNCH [

# lander page
@app.route('/lander')
def home():
    return render_template('index.html')


# login user
@app.route('/signin', methods = ['POST'])
def signin():
    username = request.json['username']
    password = request.json['password']
    user = mongo.db.users.find_one({"username": username})
    if user:
        username_signal = 1
        salted_password = user["password"]
        if check_password_hash(salted_password, password):
            password_signal = 1
            login_user(username)
        else:
            password_signal = 0
    else:
        username_signal = 0
        password_signal = 2

    data = {"username": username_signal, "password": password_signal}
    data = json.dumps(data)
    return data


# login page
@app.route('/login')
def login():
    return render_template('login.html')


# logout user
@app.route('/logout')
def logout():
    session.pop("logged_in", None)
    session.pop("username", None)
    session.pop("name", None)
    return redirect(url_for('home'))


# join page
@app.route('/join')
def join():
    return render_template('join.html')


# signup page
@app.route('/signup')
def email_signup():
    return render_template('signup.html')


# partners/users
@app.route('/profile/<username>', methods = ['GET'])
def user(username):
    user = get_user(username)
    if user:
        return render_template("profile.html", user=user)
    abort(404)


# projects
@app.route('/profile/<username>/<project_id>', methods = ['GET'])
def project(username, project_id):
    user = get_user(username)
    project = get_project(username, project_id)
    if user and project:
        return render_template("project.html", user=user, project=project)
    abort(404)


# create project
@app.route('/profile/<username>/create', methods = ['GET'])
def create_project(username):
    user = get_user(username)
    if user:
        return render_template("create-project.html", user=user)
    abort(404)


# portfolios
@app.route('/profile/<username>/portfolio', methods = ['GET'])
def portfolio(username):
    user = get_user(username)
    if user:
        return render_template("portfolio.html", user=user)
    abort(404)


# messages
@app.route('/profile/<username>/messages', methods = ['GET'])
def messages(username):
    username_session = session.get("username", "")
    if username_session == username:
        user = get_user(username)
        if user:
            messages_cursor = mongo.db.messages.find({"$or": [{ "from": username }, { "to": username}]}).sort([("time", -1)])
            messages = update_message_data(messages_cursor)
            return render_template("messages.html", user=user, messages=messages)
    abort(404)


# user not found
@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404


# register new user
@app.route('/register', methods = ['POST'])
def register():

    group = request.json['group']
    name = request.json['name']
    username = request.json['username']
    email = request.json['email']
    password = request.json['password']
    pic = request.json['pic']
    country = request.json['country']
    country_code = request.json['code']
    city = request.json['city']
    field = request.json['field']

    try:
        is_email_valid = validate_email(email)
    except Exception:
        is_email_valid = True

    if len(name) > 0:
        name_signal = 1
    else:
        name_signal = 0

    if (len(username) > 0) and (' ' not in username):
        username_signal = 1
        already_username = mongo.db.users.find_one({"username": username})
        if already_username:
            username_signal = 2
    else:
        username_signal = 0

    if is_email_valid:
        email_signal = 1
        already_email = mongo.db.users.find_one({"email": email})
        if already_email:
            email_signal = 2
    else:
        email_signal = 0

    password_signal = validate_password(password)

    if (name_signal == 1) and (username_signal == 1) and (email_signal == 1) and (password_signal == 1):
        salted_password = generate_password_hash(password)

        facebook = session.get("facebook")
        if facebook == None:
            facebook = {}
        else:
            session.pop("facebook", None)

        twitter = session.get("twitter")
        if twitter == None:
            twitter = {}
        else:
            session.pop("twitter", None)

        current_time = int(time())
        ip = request.access_route[0]
        description_default = DEFAULT_DESCRIPTION
        skills = []
        projects = []
        keywords = convert_string_to_list(name) + convert_string_to_list(country) + convert_string_to_list(city) + convert_string_to_list(username) + convert_string_to_list(field) + convert_string_to_list(country_code)
        followers = {"profiles": []}
        following = {"profiles": [], "projects": []}
        portfolio = {}

        user = {"group": group, "name": name, "username": username, "email": email, "password": salted_password, "logins": 0, "facebook": facebook, "twitter": twitter, "added_at": current_time, "last_login_at": current_time, "ip": ip, "pic": pic, "country": country, "country_code": country_code, "city": city, "field": field, "description": description_default, "skills": skills, "projects": projects, "followers": followers, "following": following, "keywords": keywords, "portfolio": portfolio}

        mongo.db.users.ensure_index([("username", ASCENDING)], unique=True, background=True)
        mongo.db.users.ensure_index([("facebook.username", ASCENDING)], sparse=True, background=True)
        mongo.db.users.ensure_index([("twitter.screen_name", ASCENDING)], sparse=True, background=True)

        user_id = mongo.db.users.insert(user)
        # maintain a list of all users for autocompletion
        mongo.db.globals.update({},{"$push": {"users": username}}, upsert=True)
        login_user(username)

    data = {"name": name_signal, "username": username_signal, "email": email_signal, "password": password_signal}
    data = json.dumps(data)
    return data


# update user information
@app.route('/update', methods = ['POST'])
def update():

    username_session = session.get("username", "")
    username_client = request.json['username']
    parameters = request.json['parameters']
    origin = request.json['origin']
    command = request.json['command']

    # check authentication
    if username_client == username_session:

        user = get_user(username_client)
        user_keywords = user.get("keywords", "")

        if command == 'follow-profile' and origin == 'profile':
            profile = parameters.get("following", "")
            # add profile to username: username is following that profile
            mongo.db.users.update({"username": username_client, "following.profiles": {"$ne": profile}},{"$push": {"following.profiles": profile}}, upsert=False)

            # now add username to profile: username is a follower of that profile
            mongo.db.users.update({"username": profile, "followers.profiles": {"$ne": username_client}},{"$push": {"followers.profiles": username_client}}, upsert=False)

        if command == 'unfollow-profile' and origin == 'profile':
            profile = parameters.get("following", "")
            # remove profile from username: username is now not following that profile
            mongo.db.users.update({"username": username_client} ,{"$pull": {"following.profiles": profile}}, upsert=False)

            # remove username from profile: username is now not a follower of that profile
            mongo.db.users.update({"username": profile}, {"$pull": {"followers.profiles": username_client}}, upsert=False)

        if command == 'update-skills' and origin == 'profile':
            old_skills = user.get("skills", [])
            new_skills = parameters.get("skills", [])
            new_keywords = update_keywords(user_keywords, new_skills, old_skills)
            mongo.db.users.update({"username": username_client}, {"$set": {"skills": new_skills}})
            mongo.db.users.update({"username": username_client}, {"$set": {"keywords": new_keywords}})

        if command == 'update-description' and origin == 'profile':
            description = parameters.get("description", "")
            mongo.db.users.update({"username": username_client}, {"$set": {"description": description}})

        if command == 'follow-project' and origin == 'project':
            profile = parameters.get("following", "")
            project_id = parameters.get("project", "")

            # add profile and project to username_client following
            mongo.db.users.update({"username": username_client},{"$push": {"following.projects": {"username": profile, "project": project_id}}})

            # add profile to project followers: username is a follower of that project
            mongo.db.users.update({"username": profile, "projects.id": project_id}, {"$push": {"projects.$.followers": username_client}})

        if command == 'unfollow-project' and origin == 'project':
            profile = parameters.get("following", "")
            project_id = parameters.get("project", "")

            # remove profile and project from username_client following
            mongo.db.users.update({"username": username_client},{"$pull": {"following.projects": {"username": profile, "project": project_id}}})

            # remove profile from project followers
            mongo.db.users.update({"username": profile, "projects.id": project_id}, {"$pull": {"projects.$.followers": username_client}})

        if command == 'update-name' and origin == 'project':
            project_id = parameters.get("project", "")
            new_name = parameters.get("name", "")
            project = get_project(username_client, project_id)
            project_keywords = project.get("keywords", [])
            old_name = project.get("name", "")
            new_name_keywords = convert_string_to_list(new_name)
            old_name_keywords = convert_string_to_list(old_name)
            new_keywords = update_keywords(project_keywords, new_name_keywords, old_name_keywords)
            mongo.db.users.update({"username": username_client, "projects.id": project_id}, {"$set": {"projects.$.name": new_name}})
            mongo.db.users.update({"username": username_client, "projects.id": project_id}, {"$set": {"projects.$.keywords": new_keywords}})

        if command == 'update-description' and origin == 'project':
            project = parameters.get("project", "")
            description = parameters.get("description", "")
            mongo.db.users.update({"username": username_client, "projects.id": project}, {"$set": {"projects.$.description": description}})

        if command == 'update-skills' and origin == 'project':
            project_id = parameters.get("project", "")
            project = get_project(username_client, project_id)
            project_keywords = project.get("keywords", [])
            old_skills = project.get("skills", [])
            old_skills_keywords = [entry['skill'] for entry in old_skills]
            new_skills_keywords = parameters.get("skills", [])
            new_keywords = update_keywords(project_keywords, new_skills_keywords, old_skills_keywords)
            new_skills = update_project_skills(new_skills_keywords, old_skills)
            mongo.db.users.update({"username": username_client, "projects.id": project_id}, {"$set": {"projects.$.skills": new_skills}})
            mongo.db.users.update({"username": username_client, "projects.id": project_id}, {"$set": {"projects.$.keywords": new_keywords}})
            data = update_candidate_data(new_skills)
            data = json.dumps(data)
            return data

        if command == 'add-candidate' and origin == 'project':
            project_owner = parameters.get("owner", "")
            project_id = parameters.get("project", "")
            skill = parameters.get("skill", "")
            project = get_project(project_owner, project_id)
            old_skills = project.get("skills", [])
            new_skills = update_project_candidates(skill, username_client, old_skills, True)
            mongo.db.users.update({"username": project_owner, "projects.id": project_id, "projects.skills.skill": skill}, {"$set": {"projects.$.skills": new_skills}})
            data = update_candidate_data(new_skills)
            data = json.dumps(data)
            return data

        if command == 'remove-candidate' and origin == 'project':
            project_owner = parameters.get("owner", "")
            project_id = parameters.get("project", "")
            skill = parameters.get("skill", "")
            project = get_project(project_owner, project_id)
            old_skills = project.get("skills", [])
            new_skills = update_project_candidates(skill, username_client, old_skills, False)
            mongo.db.users.update({"username": project_owner, "projects.id": project_id, "projects.skills.skill": skill}, {"$set": {"projects.$.skills": new_skills}})                  
            data = update_candidate_data(new_skills)
            data = json.dumps(data)
            return data
        
        if command == 'approve-candidate' and origin == 'project':
            candidate = parameters.get("candidate", "")
            project_id = parameters.get("project", "")
            skill = parameters.get("skill", "")
            project = get_project(username_client, project_id)
            old_skills = project.get("skills", [])
            new_skills = remove_project_skill(skill, old_skills)
            mongo.db.users.update({"username": username_client, "projects.id": project_id, "projects.skills.skill": skill}, {"$set": {"projects.$.skills": new_skills}})
            mongo.db.users.update({"username": username_client, "projects.id": project_id}, {"$addToSet": {"projects.$.partners": {"skill": skill, "partner":candidate}}}) 
            data = update_candidate_data(new_skills)
            candidate_user = get_user(candidate)
            candidate_user_details = {}
            if candidate_user:
                pic = process_image(candidate_user["pic"])
                candidate_user_details = {"name": candidate_user["name"], "username": candidate_user["username"], "pic": pic, "skill": skill}
            appended_data = {"skills": data, "partner": candidate_user_details}
            appended_data = json.dumps(appended_data)
            return appended_data

        if command == 'reject-candidate' and origin == 'project':
            candidate = parameters.get("candidate", "")
            project_id = parameters.get("project", "")
            skill = parameters.get("skill", "")
            project = get_project(username_client, project_id)
            old_skills = project.get("skills", [])
            new_skills = update_project_candidates(skill, candidate, old_skills, False)
            mongo.db.users.update({"username": username_client, "projects.id": project_id, "projects.skills.skill": skill}, {"$set": {"projects.$.skills": new_skills}})
            data = update_candidate_data(new_skills)
            data = json.dumps(data)
            return data

        if command == 'delete-project' and origin == 'project':
            project_id = parameters.get("project", "")
            project = get_project(username_client, project_id)
            project_file = project.get("file", "")
            mongo.db.users.update({"username": username_client},{"$pull": {"projects": {"id": project_id}}})
            delete_file(project_file)
            data = {}
            data = json.dumps(data)
            return data

        if command == 'change-status' and origin == 'messages':
            message_id = parameters.get("message_id", "")
            message_oid = bson.objectid.ObjectId(message_id)
            mongo.db.messages.update({"_id": message_oid}, {"$set": {"status": 0}})
            
        if command == 'update-caption' and origin == 'portfolio':
            media_id = parameters.get("media", "")
            media = get_portfolio_media(username_client, media_id)
            old_caption = media.get("caption", "")
            new_caption = parameters.get("caption", "")
            old_caption_keywords = convert_string_to_list(old_caption)
            new_caption_keywords = convert_string_to_list(new_caption)
            media_keywords = media.get("keywords", [])
            new_keywords = update_keywords(media_keywords, new_caption_keywords, old_caption_keywords)
            mongo.db.users.update({"username": username_client, "portfolio.media.id": media_id}, {"$set": {"portfolio.media.$.caption": new_caption}})
            mongo.db.users.update({"username": username_client, "portfolio.media.id": media_id}, {"$set": {"portfolio.media.$.keywords": new_keywords}})

        if command == 'update-labels' and origin == 'portfolio':
            media_id = parameters.get("media", "")
            media = get_portfolio_media(username_client, media_id)
            new_labels = parameters.get("labels", [])
            old_labels = media.get("labels", [])
            media_keywords = media.get("keywords", [])
            new_keywords = update_keywords(media_keywords, new_labels, old_labels)
            mongo.db.users.update({"username": username_client, "portfolio.media.id": media_id}, {"$set": {"portfolio.media.$.labels": new_labels}})
            mongo.db.users.update({"username": username_client, "portfolio.media.id": media_id}, {"$set": {"portfolio.media.$.keywords": new_keywords}})

        if command == 'delete-box' and origin == 'portfolio':
            media_id = parameters.get("media", "")
            mongo.db.users.update({"username": username_client}, {"$pull": {"portfolio.media": {"id": media_id}}})
            delete_file(media)

        if command == 'submit-link' and origin == 'portfolio':
            link = parameters.get("link", "")
            try:
                if 'youtube' in link:
                    url_data = urlparse.urlparse(link)
                    query = urlparse.parse_qs(url_data.query)
                    file_id = query["v"][0]
                    pic_link = "http://img.youtube.com/vi/" + file_id + "/0.jpg"
                    mongo.db.users.update({"username": username_client},{"$push": {"portfolio.media": {"file": pic_link, "class": "videos", "id": str(file_id)}}})
                    data = {"link": "youtube", "id": str(file_id), "class": "videos", "file": pic_link}
                    data = json.dumps(data)
                    return data

                if 'soundcloud' in link:
                    path = urlparse.urlparse(link).path
                    response = requests.get('http://soundcloud.com/oembed?format=json&url=https://soundcloud.com' + str(path) + '&iframe=true&callback=')
                    result = response.json()
                    html = result.get("html", "")
                    pic_link = result.get("thumbnail_url", "")
                    mongo.db.users.update({"username": username_client},{"$push": {"portfolio.media": {"file": pic_link, "class": "soundcloud", "id": str(path), "iframe": html}}})
                    data = {"link": "soundcloud", "id": str(path), "class": "soundcloud", "file": pic_link, "iframe": html}
                    data = json.dumps(data)
                    return data

            except Exception, e:
                print e
 
    data = {}
    data = json.dumps(data)
    return data


# search for profiles, projects and portfolios
@app.route('/search/<search>', methods = ['GET', 'POST'])
def search(search):

    users = []
    projects = []
    portfolios = []

    query = request.args

    # there is a query term
    if query:
        query = query['search']
        mongo.db.users.ensure_index([("keywords",ASCENDING)], sparse=True, background=True)
        mongo.db.users.ensure_index([("projects.keywords",ASCENDING)], sparse=True, background=True)
        mongo.db.users.ensure_index([("portfolio.media.keywords",ASCENDING)], sparse=True, background=True)
        query = query.split(' ')
        for word in query:
            word = stem_search_query(word)
            if word:
                regex_word = word + '.*'

                users_cursor = mongo.db.users.find({"keywords": {'$regex': regex_word}}).limit(SEARCH_LIMIT)
                for user in users_cursor:
                    user.pop("_id", None)
                    users.append(user)
            
                users_cursor = mongo.db.users.find({"projects.keywords": {'$regex': regex_word}}).limit(SEARCH_LIMIT)
                for user in users_cursor:
                    projects_array = user.get("projects", [])
                    for project in projects_array:
                        keywords = project.get("keywords", [])
                        if (any(word in item for item in keywords)):
                            project["username"] = user.get("username", "")
                            projects.append(project)

                users_cursor = mongo.db.users.find({"portfolio.media.keywords": {'$regex': regex_word}}).limit(SEARCH_LIMIT)
                for user in users_cursor:
                    portfolio = user.get("portfolio", {}).get("media", [])
                    for media in portfolio:
                         keywords = media.get("keywords", [])
                         if (any(word in item for item in keywords)):
                            media["username"] = user.get("username", "")
                            portfolios.append(media)


        # get unique list of users, projects, portofolio
        users = {user['username']:user for user in users}.values()
        projects = {project['id']:project for project in projects}.values()
        portfolios = {media['id']:media for media in portfolios}.values()

    # there is no query term
    else:
        if search == 'projects':
            query = ''
            users_cursor = mongo.db.users.find().limit(SEARCH_LIMIT)
            for user in users_cursor:
                user.pop("_id", None)
                users.append(user)
                projects_array = user.get("projects", [])
                for project in projects_array:
                    project["username"] = user.get("username", "")
                    projects.append(project)
                portfolio = user.get("portfolio", {}).get("media", [])
                if portfolio:
                    media = portfolio[0]
                    media["username"] = user.get("username", "")
                    portfolios.append(media)
            users = []
            portfolios = []        

    return render_template("search.html", users=users, projects=projects, portfolios=portfolios, search=search)


# autocomplete usernames
@app.route('/autocomplete', methods = ['GET'])
def autocomplete():
    data = mongo.db.globals.find()[0]
    data = data.get("users", [])
    data = json.dumps(data)
    return data


# launch a project
@app.route('/create', methods=['GET', 'POST'])
def launch_project():
    username = session["username"]
    name = request.form["project-name"]
    description = request.form["project-description"]
    skills = request.form["project-skills"]
    followers = []
    partners = []
    keywords_name = convert_string_to_list(name)
    keywords_skills = convert_string_to_list(skills, ",")
    keywords = keywords_name + keywords_skills
    id = scrub_project_id_string(name)
    id = id.replace (" ", "-").lower()
    project = get_project(username, id)
    if project:
        id = id + "-a"
    skills = skills.split(',') 
    skills = initialize_project_skills(skills)
    if request.method == 'POST':
        file = request.files['file']
        file_id = ""
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_id = fs.put(file, filename=filename)

        mongo.db.users.update({"username": username},{"$push": {"projects": {"id": id, "name": name, "description": description, "skills": skills, "file": str(file_id), "keywords": keywords, "followers": followers, "partners": partners}}}, upsert=True)

    return redirect(url_for('project', username=username, project_id=id))


# send internal messages
@app.route('/send', methods = ['POST'])
def send():
    username = session["username"]
    sender = request.json['from']
    recipient = request.json['to']
    message = request.json['message']

    recipient_list = recipient.split(',')
    if len(recipient_list) > 1:
        data = {"error": "Only one recipient allowed."}
        data = json.dumps(data)
        return data

    recipient_user = get_user(recipient)
    if not recipient_user:
        data = {"error": "User " + recipient + " does not exist."}
        data = json.dumps(data)
        return data

    if username == sender:
        current_time = int(time())
        entry = {"from": sender, "to": recipient, "time": current_time, "message": message, "status": 1}
        message_id = mongo.db.messages.insert(entry)
        new_entry = update_message_entry(entry, message_id)
        data = json.dumps(new_entry)
        return data

    data = {}
    data = json.dumps(data)
    return data


# serve only image files stored in gridfs
@app.route('/image/')
@app.route('/image/<path:id>')
def get_image(id=None):
    if id == None:
        file = open(ANONYMOUS, "rb")
        response = make_response(file.read())
        response.headers['Content-Type'] = 'image/jpeg'
        return response
    id = str(id)
    file_oid = bson.objectid.ObjectId(id)
    file = fs.get(file_oid).read()
    response = make_response(file)
    response.headers['Content-Type'] = 'image/jpeg'
    return response


# SOCIAL MEDIA LOGIN [

@app.route('/facebook_login')
def facebook_login():
    try:
        fb_app_info = {'client_id': FB_APP_ID, 'redirect_uri': FB_LOGIN_REDIRECT, 'scope': FB_PERMISSIONS, 'state': FB_STATE}
        fb_oAuthRedirect = facebook_connect(fb_app_info)
        return redirect(fb_oAuthRedirect)
    except Exception, e:
        print e
        return redirect(url_for('login'))


@app.route('/fblverify')
def fblverify():
    try:
        code = request.args['code']
        fb_app_info = {'client_id': FB_APP_ID, 'redirect_uri': FB_LOGIN_REDIRECT, 'client_secret': FB_SECRET, 'code': code}
        user_details = facebook_verify(fb_app_info)
        fb_name = user_details['name']
        fb_username = user_details['username']
        fb_email = user_details['email']
        fb_id = user_details['id']
        fb_pic = 'http://graph.facebook.com/' + fb_id + '/picture?type=large'
        user = get_user(fb_username, "facebook")
        if user:
            username = user["username"]
            login_user(username)
            update_fb_info(username, user_details)
            return redirect(url_for('user', username=username))
        else:
            session["facebook"] = user_details
            return render_template('signup.html', name=fb_name, username=fb_username, email=fb_email, pic=fb_pic)
    except Exception, e:
        print e
        return redirect(url_for('login'))


@app.route('/twitter_login')
def twitter_login():
    try:
        tw_auth_request = tweepy.OAuthHandler(TW_CONSUMER_KEY, TW_CONSUMER_SECRET, TW_LOGIN_REDIRECT)
        tw_oAuthRedirect = twitter_connect(tw_auth_request)
        return redirect(tw_oAuthRedirect)
    except Exception, e:
        print e
        return redirect(url_for('login'))


@app.route('/twlverify')
def twlverify():
    try: 
        verifier = request.args["oauth_verifier"]
        user_details = twitter_verify(verifier)
        tw_name = user_details['name']
        tw_username = user_details["screen_name"]
        user = get_user(tw_username, "twitter")
        tw_pic = 'https://api.twitter.com/1/users/profile_image?screen_name=' + tw_username + '&size=reasonably_small'
        if user:
            username = user["username"]
            login_user(username)
            update_tw_info(username, user_details)
            return redirect(url_for('user', username=username))
        else:
            session["twitter"] = user_details        
            return render_template('signup.html', name=tw_name, username=tw_username, pic=tw_pic)
    except Exception, e:
        print e
        return redirect(url_for('login'))

# ] SOCIAL MEDIA LOGIN


# SOCIAL MEDIA SIGNUP [
@app.route('/facebook_signup')
def facebook_signup():
    try:
        fb_app_info = {'client_id': FB_APP_ID, 'redirect_uri': FB_SIGNUP_REDIRECT, 'scope': FB_PERMISSIONS, 'state': FB_STATE}
        fb_oAuthRedirect = facebook_connect(fb_app_info)
        return redirect(fb_oAuthRedirect)
    except Exception, e:
        print e
        return redirect(url_for('join'))


@app.route('/fbsverify')
def fbsverify():
    try:
        code = request.args['code']
        fb_app_info = {'client_id': FB_APP_ID, 'redirect_uri': FB_SIGNUP_REDIRECT, 'client_secret': FB_SECRET, 'code': code}
        user_details = facebook_verify(fb_app_info)
        fb_name = user_details['name']
        fb_username = user_details['username']
        fb_email = user_details['email']
        fb_id = user_details['id']
        fb_pic = 'http://graph.facebook.com/' + fb_id + '/picture?type=large'
        user = get_user(fb_username, "facebook")
        if user:
            username = user["username"]
            login_user(username)
            update_fb_info(username, user_details)
            return redirect(url_for('user', username=username))
        else:
            session["facebook"] = user_details
            return render_template('signup.html', name=fb_name, username=fb_username, email=fb_email, pic=fb_pic)
    except Exception, e:
        print e
        return redirect(url_for('join'))


@app.route('/twitter_signup')
def twitter_signup():
    try:
        tw_auth_request = tweepy.OAuthHandler(TW_CONSUMER_KEY, TW_CONSUMER_SECRET, TW_SIGNUP_REDIRECT)
        tw_oAuthRedirect = twitter_connect(tw_auth_request)
        return redirect(tw_oAuthRedirect)
    except Exception, e:
        print e
        return redirect(url_for('join'))


@app.route('/twsverify')
def twsverify():
    try: 
        verifier = request.args["oauth_verifier"]
        user_details = twitter_verify(verifier)
        tw_name = user_details['name']
        tw_username = user_details['screen_name']
        user = get_user(tw_username, "twitter")
        tw_pic = 'https://api.twitter.com/1/users/profile_image?screen_name=' + tw_username + '&size=reasonably_small'
        if user:
            username = user["username"]
            login_user(username)
            update_tw_info(username, user_details)
            return redirect(url_for('user', username=username))
        else:
            session["twitter"] = user_details        
            return render_template('signup.html', name=tw_name, username=tw_username, pic=tw_pic)
    except Exception, e:
        print e
        return redirect(url_for('join'))

# ] SOCIAL MEDIA SIGNUP 


# FILE UPLOAD [

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    # check for authentication
    username = session["username"]
    user = get_user(username)
    if request.method == 'POST':
        origin = request.form['origin']
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_id = fs.put(file, filename=filename)
            if origin == "profile":
                mongo.db.users.update({"username": username},{"$set": {"pic": str(file_id)}}, upsert=True)
                if user["pic"]:
                    delete_file(user["pic"])
                data = {}
                data = json.dumps(data)
                return data

            if origin == "portfolio":
                mongo.db.users.update({"username": username},{"$push": {"portfolio.media": {"file": str(file_id), "class": "pictures", "id": str(file_id)}}}, upsert=True)
                data = {"id": str(file_id), "class": "pictures", "file": str(file_id)}
                data = json.dumps(data)
                return data

            if origin == "project":
                project_id = request.form['id']
                mongo.db.users.update({"username": username, "projects.id": project_id},{"$set": {"projects.$.file": str(file_id)}}, upsert=True)
                projects = user["projects"]
                if projects:
                    project = next((item for item in projects if item["id"] == project_id), None)
                    if project:
                        delete_file(project["file"])
                data = {}
                data = json.dumps(data)
                return data

    return redirect(url_for('portfolio', username=username))

# ] FILE UPLOAD

# AUXILLARY FUNCTIONS [

# validate password
def validate_password(password):
    if re.match(r'[A-Za-z0-9@#$%^&+=]{7,}', password):
        return 1
    else:
        return 0


def facebook_connect(fb_app_info):
    fb_auth_request = requests.get('https://www.facebook.com/dialog/oauth', params=fb_app_info, allow_redirects=True)
    fb_oAuthRedirect = fb_auth_request.url
    return fb_oAuthRedirect


def facebook_verify(fb_app_info):
    token_request = requests.get('https://graph.facebook.com/oauth/access_token', params=fb_app_info)
    response = token_request.text
    access_token = urlparse.parse_qs(response)['access_token'][0]
    expires = urlparse.parse_qs(response)['expires'][0]
    graph_params = {'access_token': access_token}
    user_details = requests.get('https://graph.facebook.com/me/', params=graph_params)
    user_details = user_details.json()
    user_details["access_token"] = access_token
    user_details["access_token_expires"] = expires    
    return user_details


def twitter_connect(tw_auth_request):
    tw_oAuthRedirect = tw_auth_request.get_authorization_url(True)
    session["tw_request_token"] = (tw_auth_request.request_token.key,tw_auth_request.request_token.secret)
    return tw_oAuthRedirect


def twitter_verify(verifier):
    auth = tweepy.OAuthHandler(TW_CONSUMER_KEY, TW_CONSUMER_SECRET) 
    token = session.get("tw_request_token")
    session.pop("tw_request_token", None)
    auth.set_request_token(token[0], token[1])        
    auth.get_access_token(verifier)
    api = tweepy.API(auth)
    user = api.me()
    created_at = int(mktime(user.created_at.timetuple()))

    user_details = { "access_token_key": token[0],
                     "access_token_secret": token[1],
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

    return user_details


def login_user(username):
    session["logged_in"] = True
    session["username"] = username
    current_time = int(time())
    ip = request.access_route[0]
    user = mongo.db.users.find_one({"username": username})
    session["name"] = user["name"]
    logins = user["logins"] + 1
    mongo.db.users.update({"username": username}, {"$set": {"logins": logins, "last_login_at": current_time, "ip": ip}})


def get_user(username, ext=None):
    if ext == None:
        return mongo.db.users.find_one({"username": username})
    if ext == "twitter":
        return mongo.db.users.find_one({"twitter.screen_name": username})
    if ext == "facebook":
        return mongo.db.users.find_one({"facebook.username": username})
    else:
        return {}


def get_project(username, project_id):
    user = mongo.db.users.find_one({"username": username})
    try:
        projects = user['projects']
        if projects:
            project = next((item for item in projects if item["id"] == project_id), None)
            if project:
                return project
            else:
                return {}
    except Exception:
        return {}


def get_portfolio_media(username, media_id):
    user = mongo.db.users.find_one({"username": username})
    try:
        portfolio = user.get("portfolio", {}).get("media", [])
        if portfolio:
            media = next((item for item in portfolio if item["id"] == media_id), None)
            if media:
                return media
            else:
                return {}
    except Exception:
        return {}


def update_fb_info(username, user_details):
    mongo.db.users.update({"username": username},{"$set": {"facebook": user_details}})


def update_tw_info(username, user_details):
    mongo.db.users.update({"username": username},{"$set": {"twitter": user_details}})


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


# delete file from gridfs
def delete_file(file_id):
    try:
        file_id = bson.objectid.ObjectId(file_id)
        fs.delete(file_id)
    except Exception, e:
        print e


def update_keywords(keywords, new, old):
    keywords = list(set(keywords) - set(old))
    keywords = keywords + new
    keywords = [word.lower() for word in keywords]
    return keywords


# convert a 'splitter'-separated string into a list: default split by white space, and then make it unique
def convert_string_to_list(string, splitter=" "):
    string_list = string.split(splitter)
    string_list = [x.lower() for x in string_list]
    keywords = list(set(string_list) - set(COMMON_WORDS))
    return keywords


# remove characters from string as well leading and trailing whitespace
def scrub_project_id_string(string):
    scrubbed_string = re.sub('[^0-9a-zA-Z ]+', '', string)
    scrubbed_string = scrubbed_string.strip()
    return scrubbed_string


# a basic way of extracting the root stem of a word
def stem_search_query(word):
    word = word.lower()
    word_temp = word
    word_suffix_one = word[-1:]
    word_suffix_two = word[-2:]
    word_suffix_three = word[-3:]
    if word_suffix_one in WORD_SUFFIX:
        word_temp = word[:-1]
    if word_suffix_two in WORD_SUFFIX:
        word_temp = word[:-2]
    if word_suffix_three in WORD_SUFFIX:
        word_temp = word[:-3]
    if word in WORD_SUFFIX:
        word_temp = word
    return word_temp


# on creation add an empty candidate list for each skill
def initialize_project_skills(skills):
    skills_with_empty_candidates = []
    for skill in skills:
        entry = {"skill": skill, "candidates": []}
        skills_with_empty_candidates.append(entry)
    return skills_with_empty_candidates


# new_skills is the new list of skills, old_skills is pulled from mongo
def update_project_skills(new_skills, old_skills):
    updated_skills = []
    for skill in new_skills:
        entry = next((item for item in old_skills if item["skill"] == skill), None)
        if entry:
            updated_skills.append(entry)
        else:
            updated_skills.append({"skill": skill, "candidates": []})
    return updated_skills


# a helper function to update the entire skills field of a project
# this is an attempt to work around mongo's inability to deal with multiple positional operators ($)
def update_project_candidates(skill, candidate, old_skills, command):
    updated_skills = []
    for entry in old_skills:
        old_skill = entry["skill"]
        candidates = entry["candidates"]
        if (old_skill == skill):
            if command:
                candidates.append(candidate)
            else:
                try:
                    candidates.remove(candidate)
                except Exception, e:
                    print e
            updated_skills.append(entry)
        else:
            updated_skills.append({"skill": old_skill, "candidates": candidates})
    return updated_skills


# remove a skill from the skills array
def remove_project_skill(skill, old_skills):
    new_skills = [x["skill"] for x in old_skills]
    try:
        new_skills.remove(skill)
        return update_project_skills(new_skills, old_skills)
    except Exception, e:
        print e 
        return old_skills
    

# send any data concerning the user back to the client when updating project skills.
# for now we'll send the name, username and pic
def update_candidate_data(skills):
    for entry in skills:
        candidates = entry.get("candidates", [])
        updated = []
        for candidate in candidates:
            user = get_user(candidate)
            if user:
                pic = process_image(user["pic"])
                new_entry = {"name": user["name"], "username": user["username"], "pic": pic}
                updated.append(new_entry)
        entry["candidates"] = updated
    return skills


# repackage message data for front-end
def update_message_data(messages_cursor):
    updated = []
    for entry in messages_cursor:
        message_id = entry.get("_id", "")
        new_entry = update_message_entry(entry, message_id)
        updated.append(new_entry)
    return updated


# get the actual to and from user data for a message
def update_message_entry(entry, message_oid):
    message_id = str(message_oid)
    entry.pop("_id", None)
    entry["id"] = message_id
    from_username = entry.get("from", "")
    to_username = entry.get("to", "")
    from_user = get_user(from_username)
    if from_user:
        entry.pop("from", None)
        from_pic = process_image(from_user["pic"])
        new_entry = {"name": from_user["name"], "username": from_user["username"], "pic": from_pic}
        entry["from"] = new_entry
    else:
        entry.pop("from", None)
        from_pic = process_image()
        new_entry = {"name": "", "username": from_username, "pic": from_pic}
        entry["from"] = new_entry
    to_user = get_user(to_username)
    if to_user:
        entry.pop("to", None)
        to_pic = process_image(to_user["pic"])
        new_entry = {"name": to_user["name"], "username": to_user["username"], "pic": to_pic}
        entry["to"] = new_entry
    else:
        entry.pop("to", None)
        from_pic = process_image()
        new_entry = {"name": "", "username": to_username, "pic": from_pic}
        entry["to"] = new_entry
    return entry

# ] AUXILARY FUNCTIONS

# TEMPLATE FUNCTIONS [

# convert newlines to breaks for html display
_paragraph_re = re.compile(r'(?:\r\n|\r|\n){2,}')

@app.template_filter()
@evalcontextfilter
def nl2br(eval_ctx, value):
    result = u'\n\n'.join(u'<p>%s</p>' % p.replace('\n', '<br>\n')
                          for p in _paragraph_re.split(escape(value)))
    if eval_ctx.autoescape:
        result = Markup(result)

    result = re.sub('\&lt;br\&gt;', '', result)
    return result


# format unix epoch time for day number, month, year
def format_date(time):
    # convert from unix time to datetime
    date_time = datetime.datetime.fromtimestamp(time)
    return date_time.strftime('%d %b %Y')


# a pic can be an external http or local file
def process_image(image=None):
    image = str(image)
    if "http" in image:
        return image

    return url_for('get_image', id=image)


# register extra template functions
app.jinja_env.globals.update(format_date=format_date)
app.jinja_env.globals.update(get_user=get_user)
app.jinja_env.globals.update(process_image=process_image)
app.debug = True

# ] TEMPLATE FUNCTIONS

if __name__ == "__main__":
    if DEBUG:
        app.run(debug=True, port=8000)
    else:
        app.run()

# ] LAUNCH