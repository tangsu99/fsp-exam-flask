from functools import wraps
from typing import Callable, Optional, TypeVar, cast
from flask import request, jsonify

# 定义类型变量 F，表示函数类型
F = TypeVar("F", bound=Callable)


def validate_json(required_fields: Optional[list[str]] = None) -> Callable[[F], F]:
    """
    装饰器：验证请求中的 JSON 数据是否有效，并检查必需字段是否存在。
    """

    def decorator(f: F) -> F:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.json:
                return jsonify({"code": 1, "desc": "Invalid JSON data"}), 400

            # 将 request.json 的类型缩小为 dict
            req_data = cast(dict, request.json)

            if required_fields:
                missing_fields = [field for field in required_fields if field not in req_data]
                if missing_fields:
                    return jsonify({"code": 1, "desc": f"Missing fields: {', '.join(missing_fields)}"}), 400

            return f(*args, **kwargs)

        return cast(F, decorated_function)

    return decorator
