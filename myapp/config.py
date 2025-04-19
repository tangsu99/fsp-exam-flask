from attr.converters import to_bool
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from myapp import db
from myapp.db_model import ConfigModel

DEFAULT_CONFIG = [
    {
        'key': 'SECRET_KEY',
        'value': 'c4329f5e3bc9daf6cd2b82bf9355a5d2',
        'type': 'str',
    },
    {
        'key': 'API_TOKEN',
        'value': '5d0f1a51226e42a8b35908823eadfcab',
        'type': 'str',
    },
    {
        'key': 'ALLOWED_ORIGINS',
        'value': 'http://localhost:5173,http://127.0.0.1:5173',
        'type': 'str',
    },
    {
        'key': 'RESET_PASSWORD_URL',
        'value': 'http://localhost:5173/#/reset_password?token=',
        'type': 'str',
    },
    {
        'key': 'MAIL_SERVER',
        'value': 'smtp.qq.com',
        'type': 'str',
    },
    {
        'key': 'MAIL_PORT',
        'value': '465',
        'type': 'int',
    },
    {
        'key': 'MAIL_USE_SSL',
        'value': 'True',
        'type': 'bool',
    },
    {
        'key': 'MAIL_USERNAME',
        'value': 'your_email@qq.com',
        'type': 'str',
    },
    {
        'key': 'MAIL_PASSWORD',
        'value': 'your_auth_password',
        'type': 'str',
    },
    {
        'key': 'MAIL_DEFAULT_SENDER',
        'value': 'your_email@qq.com',
        'type': 'str',
    },
]


class Config:
    __config = []
    app: Flask = None
    db: SQLAlchemy = None

    def init_app(self, app: Flask, db_: SQLAlchemy):
        self.app = app
        self.db = db_
        self.__resync_config()

    def __resync_config(self):
        with self.app.app_context():
            for i in ConfigModel.query.all():
                self.__config.append({
                    'key': i.key,
                    'value': i.value,
                    'type': i.type,
                })

    def get(self, key: str):
        val = self.type(self.__get_item(key, self.__config))
        if val is not None:
            return val
        return self.type(self.__get_default(key))

    def get_all(self):
        if self.__config == 0:
            self.__resync_config()
        result = []
        for i in self.__config:
            result.append({
                'key': i.key,
                'value': i.value,
                'type': i.type,
            })
        return result

    def set(self, key, value, type_):
        return self.app

    def __get_default(self, key: str):
        return self.__get_item(key, DEFAULT_CONFIG)

    @staticmethod
    def __get_item(key: str, config):
        for item in config:
            if item.get('key') == key:
                return item
        return None

    @staticmethod
    def type(item):
        type_ = item.get('type')
        if type_ == 'str':
            return item.get('value')
        if type_ == 'int':
            return int(item.get('value'))
        if type_ == 'bool':
            return to_bool(item.get('value'))
        return item.get('value')


def init_config():
    for item in DEFAULT_CONFIG:
        db.session.add(ConfigModel(item.get('key'), item.get('value'), item.get('type')))
    db.session.commit()
