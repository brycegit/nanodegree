# IMPORTS
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify

from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, Item, User

#OAuth imports
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError

import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']

APPLICATION_NAME = "Catalog App"

# DB CONNECT
# Connect to Database and create database session
engine = create_engine('sqlite:///catalogapp.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

# ROUTES
# Routes and logic for the various page URLs
@app.route('/')
def homepage():
    loggedIn = checkLogIn()
    items = session.query(Item).order_by(desc('id'))
    return render_template('homepage.html', loggedIn=loggedIn, items = items)

@app.route('/login')
def login():
    loggedIn = checkLogIn()
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state, loggedIn=loggedIn)     

@app.route('/gconnect', methods=['GET', 'POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s' % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['provider'] = 'google'
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    # CHECK FOR/CREATE USER
    # See if user already exists in user table; if not make a new one
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("Woo hoo! You're logged in as %s" % login_session['username'])
    print login_session
    return output

@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session['credentials']
    
    #check is user is connected
    print 'In gdisconnect access token is %s', access_token
    print 'User name is: ' 
    print login_session['username']
    if access_token is None:
        print 'Access Token is None'
        response = make_response(json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    
    #if connected, delete login_session data and return to homepage
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print 'result is '
    print result
    if result['status'] == '200':
        del login_session['credentials']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        flash('Bye bye. You are logged out.')
        return redirect(url_for('homepage'))
    else:
    
        response = make_response(json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return redirect(url_for('clearSession'))             

# USE LATER IF >1 oAUTH
# @app.route('/disconnect')
# def disconnect():
#     if 'provider' in login_session:
#         if login_session['provider'] == 'google':
#             gdisconnect()
#             del login_session['gplus_id']
#             del login_session['credentials']
#         if login_session['provider'] == 'facebook':
#             fbdisconnect()
#             del login_session['facebook_id']
#         del login_session['username']
#         del login_session['email']
#         del login_session['picture']
#         del login_session['user_id']
#         del login_session['provider']
#         flash("You have successfully been logged out.")
#         return redirect(url_for('showRestaurants'))
#     else:
#         flash("You were not logged in")
#         return redirect(url_for('showRestaurants'))  

@app.route('/clearSession')
def clearSession():
    login_session.clear()
    return redirect(url_for('homepage'))      

@app.route('/category/<string:cat_id>')
def category(cat_id):
    loggedIn = checkLogIn()
    
    #display all categories
    if cat_id == 'all':
        categories = session.query(Category).all()
        return render_template('categoryPage.html', cat_id=cat_id, categories=categories, loggedIn=loggedIn)
    else:
        # display one category
        category = session.query(Category).filter_by(id = cat_id).one()
        if category != []:
            return render_template('categoryPage.html', cat_id=cat_id, category=category, loggedIn=loggedIn)
        else:
            return redirect(url_for('homepage'))


@app.route('/item/<string:item_id>')
def item(item_id):
    loggedIn = checkLogIn()
    #display all items
    if item_id == 'all':
        items = session.query(Item).all()
        return render_template('itemPage.html', item_id=item_id, items=items, loggedIn=loggedIn)
    else:
        #display one item
        item = session.query(Item).filter_by(id = item_id).one()
        if item != []:
            return render_template('itemPage.html', item_id=item_id, item=item, loggedIn=loggedIn)
        else:
            return redirect(url_for('homepage'))   

@app.route('/category/<string:action>/<int:id>', methods=['GET', 'POST'])
def categoryForm(action, id):
    loggedIn = checkLogIn()
    print loggedIn
    if loggedIn == 'false':
        return redirect(url_for('homepage'))
    if request.method == 'POST':
        #process data from add form
        if action == "add":
            newCategory = Category(name = request.form['name'], description = request.form['description'])
            session.add(newCategory)
            session.commit()
            flash('%s category is alive!!' % newCategory.name)
            return redirect(url_for('category', cat_id = 'all'))
        else:
            #process data from edit form
            if action =="edit":
                updatedCategory = session.query(Category).filter_by(id = id).one()
                if request.form['name']:
                    updatedCategory.name = request.form['name']
                if request.form['description']:
                    updatedCategory.description = request.form['description']
                session.add(updatedCategory)
                session.commit()
                flash("You've updated %s!" % updatedCategory.name)
                return redirect(url_for('category', cat_id = id))
            else:
                #process data from delete form
                if action =="delete":
                    deleteCategory = session.query(Category).filter_by(id = id).one()
                    if deleteCategory != []:
                        session.delete(deleteCategory)
                        session.commit()
                        flash("You demolished %s!" % deleteCategory.name)
                        return redirect(url_for('category', cat_id='all'))
                else:
                    return redirect(url_for('homepage'))
    else:
        if action == "add":
            return render_template('categoryForm.html', action=action, id=id, loggedIn=loggedIn)
        else:
            if action =="edit":
                categoryData = session.query(Category).filter_by(id = id).one()
                if categoryData != []:
                    return render_template('categoryForm.html', action=action, id=id, categoryData=categoryData, loggedIn=loggedIn)
                else:
                    return redirect(url_for('homepage'))
            else:
                if action =="delete":
                    categoryData = session.query(Category).filter_by(id = id).one()
                    if categoryData != []:
                        return render_template('categoryForm.html', action=action, id=id, categoryData=categoryData, loggedIn=loggedIn)
                    else:
                        return redirect(url_for('homepage'))
                else:
                    return redirect(url_for('homepage'))

@app.route('/item/<string:action>/<int:id>', methods=['GET', 'POST'])
def itemForm(action, id):
    loggedIn = checkLogIn()
    if loggedIn == 'false':
        return redirect(url_for('homepage'))
    if request.method == 'POST':
        #process data from add form
        if action == "add":
            newItem = Item(name = request.form['name'], description = request.form['description'], category_id = request.form['category'])
            session.add(newItem)
            session.commit()
            flash('%s is alive!!' % newItem.name)
            return redirect(url_for('item', item_id='all'))
        else:
            #process data from edit form
            if action =="edit":
                updatedItem = session.query(Item).filter_by(id = id).one()
                if request.form['name']:
                    updatedItem.name = request.form['name']
                if request.form['description']:
                    updatedItem.description = request.form['description']
                if request.form['category']:
                    updatedItem.category_id = request.form['category']
                session.add(updatedItem)
                session.commit()
                flash("You've updated %s!" % updatedItem.name)
                return redirect(url_for('item', item_id = id))
            else:
                #process data from delete form
                if action =="delete":
                    deleteItem = session.query(Item).filter_by(id = id).one()
                    if deleteItem != []:
                        session.delete(deleteItem)
                        session.commit()
                        flash("You demolished %s!" % deleteItem.name)
                        return redirect(url_for('item', item_id='all'))
                else:
                    return redirect(url_for('homepage'))
    else:
        allCategories = session.query(Category).all()
        if action == "add":
            return render_template('itemForm.html', action=action, id=id, allCategories=allCategories, loggedIn=loggedIn)
        else:
            if action =="edit":
                itemData = session.query(Item).filter_by(id = id).one()
                if itemData != []:
                    return render_template('itemForm.html', action=action, id=id, itemData=itemData, allCategories=allCategories, loggedIn=loggedIn)
                else:
                    return redirect(url_for('homepage'))
            else:
                if action =="delete":
                    itemData = session.query(Item).filter_by(id = id).one()
                    if itemData != []:
                        return render_template('itemForm.html', action=action, id=id, itemData=itemData, loggedIn=loggedIn)
                    else:
                        return redirect(url_for('homepage'))
                else:
                    return redirect(url_for('homepage'))


@app.route('/itemsjson')
def itemsjson():
    items = session.query(Item).all()
    # items = session.query(MenuItem).filter_by(restaurant_id=restaurant_id).all()
    return jsonify(Items=[i.serialize for i in items])

# oAUTH FUNCTIONS
def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id

def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user

def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None

def checkLogIn():
    if 'username' in login_session:
        if login_session['user_id'] == getUserID(login_session['email']):
            return 'true'
    else:
        return 'false'        

if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)

