from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user

from myapp import db

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


@user.route('/getWhitelist')
@login_required
def get_whitelist():
    temp = current_user.whitelist
    res = {
        'code': 0,
        'list': [],
    }
    for item in temp:
        res['list'].append({
            'id': item.id,
            'name': item.player_name,
            'uuid': item.player_uuid,
        })
    return jsonify(res)


@user.route('/setAvatar', methods=['POST'])
@login_required
def set_avatar():
    # 获取请求数据
    req_data = request.json

    # 检查是否提供了头像 URL
    if not req_data or 'avatarUrl' not in req_data:
        return jsonify({
            'code': 1,
            'desc': '缺少头像 URL 参数！'
        }), 400

    avatar_url = req_data['avatarUrl']

    # 修改用户头像
    try:
        current_user.avatar = avatar_url
        db.session.commit()
        return jsonify({
            'code': 0,
            'desc': '头像修改成功！'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'code': 3,
            'desc': f'头像修改失败：{str(e)}'
        }), 500

