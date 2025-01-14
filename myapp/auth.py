from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import login_user
from myapp.db_model import User
from myapp import db

auth = Blueprint('login', __name__)

@auth.route('/')
def login_index():
    return render_template('login.html')

@auth.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    user = User.query.filter_by(username=username).first()
    if user and user.password == password:
        login_user(user)
        return redirect(url_for('/admin'))
    else:
        return 'Invalid username or password'
    return jsonify({'code': 0, 'desc': '成功'})
    
@auth.route('/register', methods=['POST'])
def register():
    return jsonify({'code': 0, 'desc': '成功'})
