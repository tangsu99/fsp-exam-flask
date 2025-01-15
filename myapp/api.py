from flask import Blueprint, jsonify, request
from flask_login import login_required

from myapp.db_model import Whitelist
from myapp import db

api = Blueprint('api', __name__)


@api.route('/whitelist/<player>', methods=['GET'])
def whitelist(player: str):
    if len(player) > 16:
        result = Whitelist.query.filter_by(player_uuid=player).first()
        if result is not None:
            return jsonify({'code': 0, 'desc': '在白名单中', 'uuid': result.player_uuid, 'name': result.player_name})
    else:
        result = Whitelist.query.filter_by(player_name=player).first()
        if result is not None:
            return jsonify({'code': 0, 'desc': '在白名单中', 'uuid': result.player_uuid, 'name': result.player_name})
    return jsonify({'code': 1, 'desc': 'not fond'})


@api.route('/whitelists', methods=['GET'])
def whitelists():
    result = Whitelist.query.all()
    response_data = {'code': 0, 'desc': 'yes', 'list': []}
    for i in result:
        response_data['list'].append({'name': i.player_name, 'uuid': i.player_uuid})
    return jsonify(response_data)


@api.route('/whitelistAdd', methods=['POST'])
@login_required
def add_whitelist():
    data = request.get_json()
    db.session.add(Whitelist(data['name'], data['uuid']))
    db.session.commit()
    return jsonify({'code': 0, 'desc': '成功'})


@api.route('/guarantee', methods=['POST'])
def guarantee():
    data = request.get_json()
    response_data = {'code': 0, 'desc': 'yes', 'state': 'success'}
    # 验证
    # 添加
    result = Whitelist.query.filter_by(player_uuid=data['uuid']).first()
    if result is not None:
        db.session.add()
        db.session.commit()
    return jsonify(response_data)

