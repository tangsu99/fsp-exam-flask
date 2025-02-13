from flask import Blueprint, jsonify
from flask_login import login_required, current_user

user = Blueprint('user', __name__)


@user.route('/getInfo')
@login_required
def getUserInfo():
    return jsonify({
        'code': 0,
        'data': {
            'id': current_user.id,
            'username': current_user.username,
            'user_qq': current_user.user_qq,
            'role': current_user.role,
            'addtime': current_user.addtime,
            'avatar': current_user.avatar,
            'status': current_user.status
        }
    })

