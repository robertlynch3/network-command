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
from wtforms import Form, StringField, validators, IntegerField

import backend


#WT Forms Classes
class setDescription(Form):
    description=StringField('Description', [validators.InputRequired()])
class changeVLAN(Form):
    vlan=IntegerField('VLAN ID', [validators.InputRequired()])

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

app = Flask(__name__, template_folder=directory_root+"/app/html-templates", static_folder='frontend-html_templates/static-template')
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

#Configure Switch
@app.route("/switches/<string:ip>")
@is_logged_in
def conf_switch(ip):
    returnData=backend.getInterfaces(ipAddress=ip, junosUsername=junosUName, junosPassword=junsoPWord)
    if "Error" in returnData:
        return render_template("error.html",error='Connection', message="Error connecting to switch.")
    return render_template("configureSwitch.html", ip=ip, interfaces=returnData, name=backend.getSwitchName(ip))

#Configure Switch
@app.route("/switches/<string:ip>/<string:interface>/<string:script>", methods=['POST','GET'])
@is_logged_in
def configure_interface(ip, interface, script):
    interface=interface.replace('%2F','/')
    if request.method=='POST':
        if script=='setInterfaceDescription':
            response=backend.setDescription(ipAddress=ip, interface=interface, junosUsername=junosUName, junosPassword=junsoPWord, description=request.form['description'])
            if 'Success' in response:
                flash("Successfully set description for {}".format(interface),'success')
            else:
                flash(response['Error'], 'danger')
        elif script=='changeAccessVLAN':
            response=backend.changeAccessVLAN(ipAddress=ip, interface=interface, junosUsername=junosUName, junosPassword=junsoPWord, vlan=request.form['vlan'])
            if 'Success' in response:
                flash("Successfully changed Access VLAN for {}".format(interface),'success')
            else:
                flash(response['Error'], 'danger')
        elif script=='trunkVLANadd':
            response=backend.trunkVLANadd(ipAddress=ip, interface=interface, junosUsername=junosUName, junosPassword=junsoPWord, vlan=request.form['vlan'])
            if 'Success' in response:
                flash("Successfully added Trunked VLAN to {}".format(interface),'success')
            else:
                flash(response['Error'], 'danger')
        elif script=='trunkVLANdelete':
            response=backend.trunkVLANdelete(ipAddress=ip, interface=interface, junosUsername=junosUName, junosPassword=junsoPWord, vlan=request.form['vlan'])
            if 'Success' in response:
                flash("Successfully deleted Trunked VLAN from {}".format(interface),'success')
            else:
                flash(response['Error'], 'danger')


        return redirect(url_for('conf_switch', ip=ip))
    else: #if its a GET method
        config=backend.getInterfaceConfig(ipAddress=ip, interface=interface, junosUsername=junosUName, junosPassword=junsoPWord)
        if script=='setInterfaceDescription':
            form=setDescription(request.form)
            if 'Error' not in config: #the config may come back blank, in which case it should equal {"Error": "..."}
                form.description.data=config['description']
            return render_template("setDescription.html", ip=ip, switch=backend.getSwitchName(ip), interface=interface, form=form)
        elif script=='getInterfaceConfig':
            return render_template("getInterfaceConfig.html", ip=ip, switch=backend.getSwitchName(ip), interface=interface, config=config)
        elif script=='changeAccessVLAN':
            form=changeVLAN(request.form)
            return render_template("changeVLAN.html", ip=ip, switch=backend.getSwitchName(ip), interface=interface, form=form, script='Change Access VLAN')
        elif script=='trunkVLANadd':
            form=changeVLAN(request.form)
            return render_template("changeVLAN.html", ip=ip, switch=backend.getSwitchName(ip), interface=interface, form=form, script='Add Trunk VLAN')
        elif script=='trunkVLANdelete':
            form=changeVLAN(request.form)
            return render_template("changeVLAN.html", ip=ip, switch=backend.getSwitchName(ip), interface=interface, form=form, script='Delete Trunk VLAN')
        elif script=='getMACtable':
            return render_template("getMacTable.html", ip=ip, switch=backend.getSwitchName(ip), interface=interface, mactable=backend.getMACtable(ipAddress=ip, interface=interface, junosUsername=junosUName, junosPassword=junsoPWord))
    return {"Error":404}




if __name__=="__main__":
    app.run(host="0.0.0.0",debug=True, port=3000)