from datetime import datetime, timedelta

import jwt
from flask import Blueprint, jsonify, render_template, request, current_app
from flask_login import login_user

from myapp.db_model import User, Token
from myapp import db

auth = Blueprint('auth', __name__)


@auth.route('/login', methods=['GET'])
def login_index():
    return render_template('login.html')


@auth.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    # req_data = request.json
    user: User = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        # login_user(user)
        token = create_token(user)
        return jsonify(
            {
                'code': 0,
                'token': token,
                'username': user.username
            }
        )
    else:
        return jsonify(
            {
                'code': 1,
                'desc': 'User not found'
            }
        ), 404


@auth.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    password = request.form['password']
    user: User = User(username).set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify({'code': 0, 'desc': '成功'})


def generate_token(user, expires_in=3600):
    payload = {
        'user_id': user.id,
        'exp': datetime.utcnow() + timedelta(hours=expires_in * 24)
    }
    secret_key = current_app.config['SECRET_KEY']
    token = jwt.encode(payload, secret_key, algorithm='HS256')
    return token


def create_token(user, expires_in=3600):
    token = generate_token(user, expires_in)
    new_token = Token(user_id=user.id, token=token, expires_in=expires_in)
    db.session.add(new_token)
    db.session.commit()
    return token


def revoke_token(token):
    token_record = Token.query.filter_by(token=token).first()
    if token_record:
        token_record.is_revoked = True
        db.session.commit()


def is_token_revoked(token):
    token_record = Token.query.filter_by(token=token).first()
    if token_record and token_record.is_revoked:
        return True
    return False


def verify_token(token, secret_key) -> int:
    try:
        payload = jwt.decode(token, secret_key, algorithm='HS256')
        user_id = payload['user_id']
        return user_id
    except jwt.ExpiredSignatureError:
        return -1  # Token 过期
    except jwt.InvalidTokenError:
        return 0  # 无效 Token
