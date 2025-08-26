from attr.converters import to_bool
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

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
        'value': 'http://localhost:5173/reset_password?token=',
        'type': 'str',
    },
    {
        'key': 'ACTIVATION_URL',
        'value': 'http://localhost:5173/activation?token=',
        'type': 'str',
    },
    {
        'key': 'FRONT_END_BASE_URL',
        'value': 'http://localhost:5173',
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
    {
        'key': 'GUARANTEE_EXPIRATION',
        'value': 1, # 小时
        'type': int,
    },
    {
        'key': 'RESPONSE_VALIDITY_PERIOD',
        'value': 24, # 小时
        'type': int,
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

    def resync_flask_config(self):
        # TODO 待优化实现
        self.app.config["SECRET_KEY"] = self.get("SECRET_KEY")  # 用于安全签名session
        self.app.config["SESSION_PROTECTION"] = None  # 禁用会话保护
        self.app.config["API_TOKEN"] = self.get("API_TOKEN")
        # cors
        self.app.config["ALLOWED_ORIGINS"] = self.get('ALLOWED_ORIGINS').split(',')
        # mail
        self.app.config['MAIL_SERVER'] = self.get('MAIL_SERVER')  # 邮件服务器地址
        self.app.config['MAIL_PORT'] = self.get('MAIL_PORT')  # 邮件服务器端口
        self.app.config['MAIL_USE_SSL'] = self.get('MAIL_USE_SSL')  # 启用SSL
        self.app.config['MAIL_USERNAME'] = self.get('MAIL_USERNAME')  # 发件人邮箱
        self.app.config['MAIL_PASSWORD'] = self.get('MAIL_PASSWORD')  # 邮箱授权码/密码？？
        self.app.config['MAIL_DEFAULT_SENDER'] = self.get('MAIL_DEFAULT_SENDER')  # 默认发件人

        # 重置密码页面
        self.app.config['RESET_PASSWORD_URL'] = self.get('RESET_PASSWORD_URL')
        # 激活页面
        self.app.config['ACTIVATION_URL'] = self.get('ACTIVATION_URL')

        self.app.config['FRONT_END_BASE_URL'] = self.get('FRONT_END_BASE_URL')

        # 过期配置
        self.app.config['GUARANTEE_EXPIRATION'] = self.get('GUARANTEE_EXPIRATION') # 小时
        self.app.config['RESPONSE_VALIDITY_PERIOD'] = self.get('RESPONSE_VALIDITY_PERIOD') # 小时

    def get(self, key: str, default='None', type_='str'):
        res = self.__get_item(key, self.__config)
        if res is None:
            self.set(key, default, type_)
            return default
        return self.type(res)

    def get_item(self, key: str):
        return self.__get_item(key, self.__config)

    def get_all(self):
        if self.__config == 0:
            self.__resync_config()
        return self.__config

    def set(self, key, value, type_):
        if self.get(key) is None:
            self.__config.append({
                'key': key,
                'value': value,
                'type': type_,
            })
            self.db.session.add(ConfigModel(key, value, type_))
        else:
            self.set__(key, value, type_)
            conf: ConfigModel = ConfigModel.query.filter(ConfigModel.key == key).first()
            conf.value = value
            conf.type = type_
        self.db.session.commit()
        self.resync_flask_config()
        return 0

    def set__(self, key, value, type_):
        for i in self.__config:
            if i['key'] == key:
                i['value'] = value
                i['type'] = type_
                return

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
    from myapp import db
    for item in DEFAULT_CONFIG:
        db.session.add(ConfigModel(item.get('key'), item.get('value'), item.get('type')))
    db.session.commit()
