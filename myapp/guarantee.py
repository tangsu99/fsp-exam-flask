from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user

from mj_api import get_player_uuid
from myapp.db_model import Whitelist, Guarantee, User
from myapp import db

guarantee = Blueprint('guarantee', __name__)


def get_ago_time():
    return datetime.utcnow() - timedelta(minutes=10)


@guarantee.route('/request', methods=['POST'])
@login_required
async def _request():
    data = request.get_json()
    response_data = {'code': 0, 'desc': '担保请求提交成功', 'state': 'success'}
    wl_result = Whitelist.query.filter_by(player_uuid=data['playerUUID']).first()
    # 在白名单中
    if wl_result is not None:
        response_data['desc'] = '已存在白名单'
        response_data['state'] = 'alreadyExists'
        return jsonify(response_data)
    ten_minutes_ago = get_ago_time()
    g_result = Guarantee.query.filter(
        Guarantee.player_uuid == data['playerUUID'],
        Guarantee.create_time >= ten_minutes_ago
    ).all()
    if len(g_result) != 0:
        response_data['desc'] = '担保请求未过期'
        response_data['state'] = 'requestExists'
        response_data['guaranteeId'] = g_result[0].id
        return jsonify(response_data)
    _res = get_player_uuid(data['playerName'])
    if _res is None:
        response_data['desc'] = '未找到此玩家'
        response_data['state'] = 'inconsistentInfo'
        return jsonify(response_data)
    name: str = _res[0]
    uuid: str = _res[1]
    # 验证
    if name.lower() != data['playerName'].lower() or uuid != data['playerUUID'].replace('-', ''):
        response_data['desc'] = '未找到此玩家'
        response_data['state'] = 'inconsistentInfo'
        return jsonify(response_data)
    g_wl_result: User = User.query.filter(User.user_qq == data['guaranteeQQ']).first()
    if g_wl_result is None:
        response_data['desc'] = '未找到此担保人'
        response_data['state'] = 'unknownGuarantor'
        return jsonify(response_data)
    elif g_wl_result.status != 1:
        response_data['desc'] = '担保人白名单异常'
        response_data['state'] = 'unknownGuarantor'
        return jsonify(response_data)

    # 存
    _guarantee = Guarantee(g_wl_result.id, current_user.get_id(), data['playerName'], data['playerUUID'])
    db.session.add(_guarantee)
    db.session.commit()
    return jsonify(response_data)


@guarantee.route('/query', methods=['GET'])
@login_required
def query():
    response_data = {'code': 0, 'desc': 'yes', 'data': {
        'guarantee': [],
        'applicant': []
    }}
    g_result = current_user.guarantees
    if len(g_result) != 0:
        for i in g_result:
            response_data['data']['guarantee'].append({
                'id': i.guarantor.id,
                'username': i.guarantor.username,
                'userQQ': i.guarantor.user_qq,
                'avatar': i.guarantor.avatar,
                'playerName': i.player_name,
                'playerUUID': i.player_uuid,
                'createTime': i.create_time,
                'status': i.status
            })
    a_result = current_user.applicant
    if len(a_result) != 0:
        for i in a_result:
            response_data['data']['applicant'].append({
                'id': i.applicant.id,
                'username': i.applicant.username,
                'userQQ': i.applicant.user_qq,
                'avatar': i.applicant.avatar,
                'playerName': i.player_name,
                'playerUUID': i.player_uuid,
                'createTime': i.create_time,
                'status': i.status
            })
    return jsonify(response_data)
