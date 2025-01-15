from flask import Blueprint, jsonify, request
from myapp.db_model import Guarantee
from myapp import db

guarantee = Blueprint('guarantee', __name__)


@guarantee.route('/addGuarantee', methods=['POST'])
def add_guarantee():
    guarantee_: Guarantee = Guarantee(request.json['name'], request.json['description'])
    db.session.add(guarantee_)
    db.session.commit()
    return jsonify({'code': 0, 'desc': '成功'})
