# libraries and imports 
import sqlite3
from flask import Flask, redirect, render_template, flash, request, redirect, url_for, session, send_file, send_from_directory, current_app
from flask_session import Session
import os
import io
import pandas as pd
import pdfkit as pdf
from zipfile import ZipFile
import sys
from functions import login_required, allowed_file, write_file
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash

# Flask up front set-up
app = Flask(__name__)
app.secret_key = os.urandom(24)

## Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

## Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

## folder for upload 
UPLOAD_FOLDER = './upload'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

conn = sqlite3.connect('dictionary.db', check_same_thread=False)
cur = conn.cursor()


# CREATE TABLE USERS(id INTEGER PRIMARY KEY, username TEXT NOT NULL, hash TEXT NOT NULL)
# CREATE TABLE VARIABLES(id INTEGER PRIMARY KEY, user_id TEXT NOT NULL, variable TEXT NOT NULL, definition TEXT NOT NULL)


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=['GET','POST'])
def register():
    
    # Forget previous session
    session.clear()

    username = request.form.get("username")
    password = request.form.get("password")
    confirmation = request.form.get("confirmation")

    if request.method == "POST":
        if not username:
            return render_template("404.html"), 400

        elif not password:
            return render_template("404.html"), 400

        registrants = cur.execute("SELECT * FROM USERS where username IN (?)", [username]).fetchone()

        if registrants is not None:
            return render_template("404.html"), 400

        if password != confirmation:
            return render_template("404.html"), 400

        hash = generate_password_hash(password)

        cur.execute("INSERT INTO USERS (username, hash) VALUES(?, ?)", (username, hash))
        conn.commit()

        return redirect("/")

    else:
        return render_template("register.html")
    
@app.route("/login", methods=['GET','POST'])
def login():
    # Forget any user_id
    session.clear()
    username = request.form.get("username")
    password = request.form.get("password")

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not username:
            return render_template("404.html"), 400

        # Ensure password was submitted
        if not password:
            render_template("404.html"), 400

        # Query database for username
        rows = cur.execute("SELECT username FROM USERS WHERE username = ?", [username]).fetchone()
        password_check = cur.execute("SELECT hash FROM USERS WHERE username = ?", [username]).fetchone()

        # Ensure username exists and password is correct
        if rows is None or password_check is None or not check_password_hash(password_check[0], password):
            return render_template("404.html"), 400

        # Remember which user has logged in
        session["user_id"] = username

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/create",methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']

        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        
        # If the file name is .txt, .csv or .xlsx, upload using pandas
        if file and allowed_file(file.filename):

            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            global data 
            if filename.endswith(".txt") or filename.endswith(".csv"):
                data = pd.read_csv(UPLOAD_FOLDER + "/" + filename, sep=",")
            if filename.endswith(".xlsx"):
                data = pd.read_excel(UPLOAD_FOLDER + "/" + filename)
            
            # Delete the file before redirect 
            os.remove(UPLOAD_FOLDER + "/" + filename)

            return redirect("/uploaded")
    
    return render_template("create.html")

@app.route("/uploaded", methods=['GET','POST'])
@login_required
def uploaded():
    
    def_values = {}
    existing_vars = []
    var_type_dict = {}
    column_names = []
    col_len = len(data.columns)
    all_types = ['Character','Numeric(Integer)','Numeric(Float)', 'Boolean', 'Date/Time', 'Time delta', 'Category']

    # Create a standardized class name 
    for i in range(col_len):
        column_names.append(data.columns[i])
        if data.dtypes[i].name == "object":
            var_type_dict[data.columns[i]] = "Character"
        elif "int" in data.dtypes[i].name:
            var_type_dict[data.columns[i]] = "Numeric(Integer)"
        elif "float" in data.dtypes[i].name:
            var_type_dict[data.columns[i]] = "Numeric(Float)"
        elif "bool" in data.dtypes[i].name:
            var_type_dict[data.columns[i]] = "Boolean"
        elif "datetime" in data.dtypes[i].name:
            var_type_dict[data.columns[i]] = "Date/Time"
        elif "timedelta" in data.dtypes[i].name:
            var_type_dict[data.columns[i]] = "Time delta"
        else:
            var_type_dict[data.columns[i]] = data.dtypes[i].name.capitalize()

        # if the word "date" is in the column names, change to date
        if "date" in data.columns[i].lower():
            var_type_dict[data.columns[i]] = "Date/Time"
    
    get_def = cur.execute("SELECT variable, definition FROM VARIABLES WHERE user_id = ?",[session["user_id"]])

    for variable, definition in get_def.fetchall():
        if get_def.fetchall() is not None:
            def_values[variable] = definition
            existing_vars.append(variable)
    
    for col in column_names:
        if col not in def_values:
            def_values[col] = ""

    if request.method == "POST":

        var_def_dict = {}
        var_def_dict["variable"] = []
        var_def_dict["type"] =[]
        var_def_dict["definition"] = []
   
        for col in column_names:
            var_def_dict["variable"].append(col)
            var_def_dict["type"].append(request.form.get("type_name_" + col))
            var_def_dict["definition"].append(request.form.get("def_name_" + col))

            if col not in existing_vars:
                cur.execute("INSERT INTO VARIABLES (user_id, variable, definition) VALUES(?, ?, ?)", [session["user_id"], col, request.form.get("def_name_" + col)])
                conn.commit()
    
                
        
        dataset_to_export = pd.DataFrame.from_dict(var_def_dict)
        dataset_to_export.to_excel(os.path.join(os.getcwd(), app.config['UPLOAD_FOLDER'],"final.xlsx"))
        dataset_to_export.to_html(os.path.join(os.getcwd(), app.config['UPLOAD_FOLDER'],"final.html"))
        pdf.from_file(os.path.join(os.getcwd(), app.config['UPLOAD_FOLDER'],"final.html"), os.path.join(os.getcwd(), app.config['UPLOAD_FOLDER'],"final.pdf"))
        return redirect("/exported")
        

    return render_template("uploaded.html", column_names = column_names, var_type_dict = var_type_dict, all_types = all_types, def_values = def_values)

@app.route("/exported", methods=['GET','POST'])
@login_required
def exported():
    return render_template("exported.html")

# with help from https://stackoverflow.com/questions/24612366/delete-an-uploaded-file-after-downloading-it-from-flask
@app.route('/<file_type>/download', methods=['GET'])
def download(file_type):
        if file_type == "xlsx":
            file_return = write_file(app.config['UPLOAD_FOLDER'],"final.xlsx")
            return send_file(file_return, mimetype = 'application/xlsx', as_attachment=True, download_name = 'final.xlsx')
        if file_type == "pdf":
            file_return = write_file(app.config['UPLOAD_FOLDER'],"final.pdf")
            return send_file(file_return, mimetype = 'application/pdf', as_attachment=True, download_name = 'final.pdf')

@app.route("/build", methods=["GET","POST"])   
@login_required
def build():
    variable_dictionary = cur.execute("SELECT variable,definition FROM VARIABLES WHERE user_id = ?", [session["user_id"]]).fetchall()
    
    
    if request.method == "POST":
        
        for tuple in variable_dictionary:
            if request.form.get("modify_name_" + tuple[0]) is None:
                definition = ""
            else:
                definition = request.form.get("modify_name_" + tuple[0])
            cur.execute("UPDATE VARIABLES SET definition = ? WHERE user_id = ? AND variable = ?", [definition,session["user_id"], tuple[0]])
            conn.commit()
            
        return redirect("/build")
        
    return render_template("build.html", variable_dictionary=variable_dictionary)     

@app.route("/deleted", methods=["POST"])
@login_required
def deleted():
    if request.method == "POST":
        cur.execute("DELETE FROM VARIABLES WHERE variable = ? AND user_id = ?", [request.form["delete"], session["user_id"]])
        conn.commit()
        return redirect("/build")

