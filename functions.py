from functools import wraps
from flask import session, request, redirect, url_for
import io
import os

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session["user_id"] is None:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def allowed_file(filename):
    allowed_extensions = {'txt', 'csv', 'xlsx'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def write_file(upload_folder, filename):
    file_return= io.BytesIO()
    with open(upload_folder + "\\" + filename, 'rb') as file:
        file_return.write(file.read())
    file_return.seek(0)
    os.remove(upload_folder + "\\" + filename)
    return file_return