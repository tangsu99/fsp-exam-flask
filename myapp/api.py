from flask import Blueprint, jsonify, request
from flask_login import login_required

from myapp.db_model import Whitelist
from myapp import db

api = Blueprint('api', __name__)


@api.route('/whitelist/<player>', methods=['GET'])
def whitelist(player: str):
    response_data = {'code': 1, 'desc': 'not fond'}
    result = None
    if len(player) > 16:
        result = Whitelist.query.filter_by(player_uuid=player).first()
    else:
        result = Whitelist.query.filter_by(player_name=player).first()
    if result is not None:
        response_data['code'] = 0
        response_data['desc'] = '在白名单中'
        response_data['uuid'] = result.player_uuid
        response_data['name'] = result.player_name
    return jsonify(response_data)


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
    db.session.add(Whitelist(data['name'], data['uuid'], data['qq']))
    db.session.commit()
    return jsonify({'code': 0, 'desc': '成功'})
