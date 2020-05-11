#!/usr/bin/env python3
#
# Robert Lynch (C) 2020
# rob@rlyn.ch
#
#
# backend.py


import os, json, sys, hashlib

directory_root=os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..'))

def login(username, password):
    #Tries to open the users file
    try:
        with open(directory_root+"/users.json") as jsonfile:
            usersFile=json.load(jsonfile)
    except:
        print("Could not open \'users.json\'")
        sys.exit()
    
    #Looks to confirm the username is in the file, then sees if the md5 has of the file is equal to the entry in the usersfile
    if username in usersFile and hashlib.md5(password.encode()).hexdigest()==usersFile[username]['password']:
        response={"Success":{"username":username, 
                            "name":usersFile[username]['name']
                            }
                }
        return response #md5 has equals the password
    else:
        return {"Error":"Invalid credentials"} #either the username is not in the users file or the password is not the same value




def loadSwitches():
    try:
        with open(directory_root+"/switches.json") as jsonfile:
            return json.load(jsonfile)
    except:
        print("Could not open \'switches.json\'")
        sys.exit()

