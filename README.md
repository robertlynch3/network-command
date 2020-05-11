# juniper-ex-sdn-controller
This project is a Flask based SDN controller for Juniper EX series switches.

### Background
This controller was built as a final project for Marist College MSIS603 - Network Virtualization, Spring 2020.

This controller is built on Python using Flask as a frontend and Juniper's PyEZ as the backend connections to switches.

***NOTE***: This app is not secure. It requires a file called `users.json` and `switch.json` so all the info in it is in plaintext. A full implementation of this should use a secure database, not plain text files.

## Install
Before using this controller, you must have `Python3` installed along with `Python Pip`.<br>
Clone the repo and change into the directory.
```bash
pip install -R requirements.txt
```

## Using
