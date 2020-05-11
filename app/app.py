#!/usr/bin/env python3
#
# Robert Lynch (C) 2020
# rob@rlyn.ch
#
#
# app.py

from flask import Flask, render_template, request, session, flash, logging, url_for, redirect
import os, json, sys, hashlib
from functools import wraps

import backend


#finds the directory root and opens config.json
directory_root=os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..'))
try:
    with open(directory_root+"/config.json") as jsonfile:
        configFile=json.load(jsonfile)
except:
    print("Could not open \'config.json\'")
    sys.exit()

#Tries to set the Juniper Username and Password based on the config.json file
try:
    junosUName=configFile['username']
    junsoPWord=configFile['password']
    sessionKey=configFile["sessionKey"]
except:
    print("Could not set the username, password, or sessionKey in the config file.\n\nPlease confirm \'config.json\' matches the \'config.json-example\' format")
    sys.exit()


def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            return redirect(url_for('login'))
    return wrap

app = Flask(__name__, template_folder=directory_root+"/app/html-templates")
app.secret_key=configFile["sessionKey"]

#Route for Login
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        # get form fields
        username = request.form['username']
        password = request.form['password']

        # connects to api and runs the login POST
        response=backend.login(username=username, password=password)
        userIPaddress=request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
        #if it succeeds the login
        if 'Success' in response:
            print("{} logged in from {}".format(username, userIPaddress))
            session['logged_in']=True
            session['username']=response['Success']['username']
            session['name']=response['Success']['name']
            flash("You are now logged in",'success')
            return redirect(url_for('index'))
        #if it fails login
        elif 'Error' in response:
            error=response['Error']
            session['logged_in']=False
            return render_template('login.html',error=error)
    return render_template('login.html')

#Route for Logout
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash("You are now logged out.", "success")
    return redirect(url_for('login'))

#Dashboard home page
@app.route('/')
@is_logged_in
def index():
    if 'logged_in' not in session or not session['logged_in']:
        return redirect(url_for('login'))
    else:
        switches=backend.loadSwitches()
        return render_template('dashboard.html', switches=switches['switches'])




if __name__=="__main__":
    app.run(host="0.0.0.0",debug=True, port=3000)