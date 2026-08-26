import logging
import os
import secrets

from attr.converters import to_bool
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import select

from myapp.db_model import ConfigModel
from myapp.default_config import DEFAULT_CONFIG

logger = logging.getLogger(__name__)


class Config:
    app: Flask = None  # type: ignore
    db: SQLAlchemy = None  # type: ignore

    def __init__(self, app: Flask, db_: SQLAlchemy) -> None:
        self.app = app
        self.db = db_
        self.accepted_types = ["str", "int", "bool", "list"]
        self.__init_default_config()
        self.__resync_flask_config()

    def __init_default_config(self) -> None:
        """
        Config 实例化的时候遍历 DEFAULT_CONFIG，如果 DB 里没有对应的键值对，那么写入默认配置，
        这样后续无论如何都能查到这个参数，不存在 None 的可能，最多是 value 为空字符串
        以确保所有配置项都存在于 DB 中
        """

        with self.app.app_context():
            # SECRET_KEY 完全由环境变量/随机生成提供，不落库，清除数据库中遗留的记录
            self.__purge_secret_key_from_db()

            for default_config_item in DEFAULT_CONFIG:
                stmt = select(ConfigModel).where(ConfigModel.key == default_config_item.get("key"))
                conf: ConfigModel | None = self.db.session.execute(stmt).scalar_one_or_none()

                if conf is None:
                    self.db.session.add(
                        ConfigModel(
                            key=default_config_item["key"],
                            value=default_config_item["value"],
                            type=default_config_item["type"],
                            description=default_config_item["description"],
                        )
                    )

            self.db.session.commit()

    def __resync_flask_config(self) -> None:
        """
        当配置发生变化时需要执行此方法
        """
        with self.app.app_context():
            stmt = select(ConfigModel.key, ConfigModel.value, ConfigModel.type)
            rows = self.db.session.execute(stmt).all()

            for key, value, type_ in rows:
                self.app.config[key] = self.type_conversion(value, type_)

        # 敏感密钥优先从环境变量注入，不落数据库
        self.__apply_secret_key()

    def __purge_secret_key_from_db(self) -> None:
        """清除数据库中遗留的 SECRET_KEY 配置记录（SECRET_KEY 由环境变量/随机生成提供，不落库）"""
        stmt = select(ConfigModel).where(ConfigModel.key == "SECRET_KEY")
        legacy_records = self.db.session.execute(stmt).scalars().all()
        if legacy_records:
            for record in legacy_records:
                self.db.session.delete(record)
            self.db.session.commit()
            logger.warning("已清除数据库中遗留的 SECRET_KEY 配置记录，SECRET_KEY 改为环境变量注入")

    def __apply_secret_key(self) -> None:
        """
        SECRET_KEY 解析策略：
        1. 优先从环境变量 SECRET_KEY 注入（稳定持久，推荐）
        2. 未设置时，每次启动随机生成临时 key（重启后所有登录态失效），
           绝不复用默认/弱值，也不写入数据库
        """
        env_secret = os.environ.get("SECRET_KEY", "").strip()
        if env_secret:
            self.app.config["SECRET_KEY"] = env_secret
            return

        temp_secret = secrets.token_hex(32)
        self.app.config["SECRET_KEY"] = temp_secret
        logger.warning(
            "未检测到环境变量 SECRET_KEY，已生成临时随机密钥（进程重启后所有登录态失效）。"
            "生产环境请通过环境变量 SECRET_KEY 提供固定密钥。"
        )

    def get_item(self, key: str) -> dict[str, str] | None:
        stmt = select(ConfigModel).where(ConfigModel.key == key)
        conf: ConfigModel | None = self.db.session.execute(stmt).scalar_one_or_none()
        return (
            None
            if conf is None
            else {"key": conf.key, "value": conf.value, "type": conf.type, "description": conf.description}
        )

    def get_all_item(self) -> list[dict[str, str]]:
        stmt = select(ConfigModel.key, ConfigModel.value, ConfigModel.type, ConfigModel.description)
        rows = self.db.session.execute(stmt).all()

        res: list[dict[str, str]] = []
        for item in rows:
            res.append({"key": item.key, "value": item.value, "type": item.type, "description": item.description})

        return res

    def set_item(self, item_key: str, item_value: str, item_type: str, item_description: str) -> bool:
        stmt = select(ConfigModel).where(ConfigModel.key == item_key)
        conf: ConfigModel | None = self.db.session.execute(stmt).scalar_one_or_none()

        if item_type not in self.accepted_types:
            return False

        if conf is None:
            self.db.session.add(
                ConfigModel(key=item_key, value=item_value, type=item_type, description=item_description)
            )
        else:
            conf.value = item_value
            conf.type = item_type
            conf.description = item_description

        self.db.session.commit()
        self.__resync_flask_config()
        return True

    def delete_item(self, item_key: str) -> bool:
        stmt = select(ConfigModel).where(ConfigModel.key == item_key)
        conf: ConfigModel | None = self.db.session.execute(stmt).scalar_one_or_none()

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
        if item_type == "str":
            return str(item_value)
        elif item_type == "int":
            return int(item_value)
        elif item_type == "bool":
            return to_bool(item_value)
        elif item_type == "list":
            return item_value.split(",")
        else:
            raise ValueError("无法处理的类型")
