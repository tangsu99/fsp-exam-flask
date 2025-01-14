from flask import Blueprint, jsonify, request
from flask_login import login_required
from myapp.db_model import Guarantee
from myapp import db

admin = Blueprint('admin', __name__)

@admin.route('/')
@login_required
def admin_index():
    return '<h1>Welcome admin page!</h1>'