from flask import Blueprint, jsonify

api = Blueprint('api', __name__)


@api.route('/whitelist/<uuid>')
def whitelist(uuid: str):
    if len(uuid) > 16:
        return jsonify({'code': 0, 'desc': '在白名单中', 'uuid': uuid, 'playerName': 'tangsu99'})
    return jsonify({'code': 1, 'desc': 'not fond'})


@api.route('/whitelists')
def whitelists():
    return jsonify({'code': 0, 'desc': 'yes', 'list': []})
