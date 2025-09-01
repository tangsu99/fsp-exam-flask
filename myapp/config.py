from attr.converters import to_bool
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from myapp.db_model import ConfigModel
from myapp.default_config import DEFAULT_CONFIG


class Config:

    app: Flask = None # type: ignore
    db: SQLAlchemy = None # type: ignore

    def __init__(self, app: Flask, db_: SQLAlchemy) -> None:
        self.app = app
        self.db = db_
        self.__init_default_config()
        self.__resync_flask_config()

    def __init_default_config(self) -> None:
        """
        Config 实例化的时候遍历 DEFAULT_CONFIG，如果 DB 里没有对应的键值对，那么写入默认配置，
        这样后续无论如何都能查到这个参数，不存在 None 的可能，最多是 value 为空字符串
        以确保所有配置项都存在于 DB 中
        """

        with self.app.app_context():
            for default_config_item in DEFAULT_CONFIG:
                conf: ConfigModel | None = ConfigModel.query.filter(ConfigModel.key == default_config_item.get('key')).first()
                if conf is None:
                    self.db.session.add(ConfigModel(
                        default_config_item['key'],
                        default_config_item['value'],
                        default_config_item['type']
                    ))

            self.db.session.commit()

    def __resync_flask_config(self)-> None:
        """
        当配置发生变化时需要执行此方法
        """
        with self.app.app_context():
            config_list = ConfigModel.query.all()
            for db_config_item in config_list:
                # print(db_config_item.key)
                self.app.config[db_config_item.key] = self.type_conversion(db_config_item.value, db_config_item.type)

    def get_item(self, key: str) -> dict | None:
        item: ConfigModel | None = ConfigModel.query.filter(ConfigModel.key == key).first()
        if item is None:
            return None

        return { 'key': item.key, 'value': item.value, 'type': item.type}

    def get_all_item(self) -> list:
        config_list = ConfigModel.query.all()
        res = []
        for item in config_list:
            res.append({ 'key': item.key, 'value': item.value, 'type': item.type})

        return res

    def set_item(self, item_key: str, item_value: str, item_type:str) -> None:
        item_value = str(item_value) # 保险起见
        conf: ConfigModel | None = ConfigModel.query.filter(ConfigModel.key == item_key).first()
        if conf is None:
            self.db.session.add(ConfigModel(item_key, item_value, item_type))
        else:
            conf.value = item_value
            conf.type = item_type

        self.db.session.commit()
        self.__resync_flask_config()

    def delete_item(self, item_key: str) -> bool:
        conf: ConfigModel | None = ConfigModel.query.filter(ConfigModel.key == item_key).first()
        if conf:
            self.db.session.delete(conf)
            self.db.session.commit()
            self.__resync_flask_config()
            return True
        return False

    @staticmethod
    def type_conversion(item_value: str, item_type: str):
        """
        数据存到 app.config 的时候需要正确的类型，在 DB 里统一存的是 str
        """
        if item_type == 'str':
            return str(item_value)
        elif item_type == 'int':
            return int(item_value)
        elif item_type == 'bool':
            return to_bool(item_value)
        elif item_type == 'list':
            return item_value.split(',')
        else:
            raise ValueError("无法处理的类型")

