# Django Web App for The City Tutors

## Setup

run `git clone https://github.com/The-City-Tutors/ct.git` to copy down the project

run `cd ct` to navigate into the project

run `python3 -m venv venv`

run `source venv/bin/activate` (You have to run this every time you start a new terminal)

> If running windows run `venv\Scripts\activate` (You have to run this every time you start a new terminal)

run `python3 -m venv venv`

run `source venv/bin/activate` (You have to run this every time you start a new terminal)

> If running windows run `venv\Scripts\activate` (You have to run this every time you start a new terminal)

run `python3 -m pip install -r requirements.txt` to install dependencies

> If running windows you may run into an issue which can be solved by [these instructions](https://docs.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation?tabs=powershell#enable-long-paths-in-windows-10-version-1607-and-later)

run `python3 manage.py migrate` to create the database

run `python3 manage.py runserver` to start the server

Go to http://127.0.0.1:8000/tutor/ to check that it works!

## Troubleshooting
Cygwin users may run into an issue where several modules cannot be installed because they cannot be found. In this case, users should run the cygwin installation file and install the following packages: libxml2, libxml2-devel, libxslt, libxslt-devel, python-libxslt, python39-libxml2 before installing the required modules.

Cygwin user may run into another issue where the regex module fails to install. Users should run the cygwin installation file and install the python39-devel package.

An error may occur involving the Twilio module. In that case, comment out all lines including Twilio in ct/settings.py.

Windows Users may come across another error involving incorrect string format. In that case, change line 17 in tutor/models.py from

```sh
times = [datetime.datetime.strptime(str(h), "%H").strftime("%-I%p") for h in range(24)]
```
to

```#!/bin/sh
times = [datetime.datetime.strptime(str(h), "%H").strftime("%I%p") for h in range(24)]
```

## More Documentation
https://docs.google.com/document/d/1rFCbQordAB7qiwnElPntNmq-vUnc4TWlST0cFq_MNys/edit#
