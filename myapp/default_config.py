DEFAULT_CONFIG = [
    {
        "key": "API_TOKEN",
        "value": "5d0f1a51226e42a8b35908823eadfcab",
        "type": "str",
        "description": (
            "用于对外 API 接口鉴权的访问令牌，客户端需在请求头中携带此 Token 以通过身份验证，相当于接口的“钥匙”。"
            "如果你的后端接口需要被第三方或特定客户端调用，通常会校验这个 Token，防止接口被随意滥用。"
        ),
    },
    {
        "key": "ALLOWED_ORIGINS",
        "value": "http://localhost:5173,http://127.0.0.1:5173",
        "type": "list",
        "description": "前端地址，如果有多个值使用逗号隔开",
    },
    {
        "key": "RESET_PASSWORD_URL",
        "value": "http://localhost:5173/reset_password?token=",
        "type": "str",
        "description": "重置密码链接，输入 URL",
    },
    {
        "key": "ACTIVATION_URL",
        "value": "http://localhost:5173/activation?token=",
        "type": "str",
        "description": "",
    },
    {
        "key": "FRONT_END_BASE_URL",
        "value": "http://localhost:5173",
        "type": "str",
        "description": "前端地址",
    },
    {
        "key": "MAIL_ENABLED",
        "value": "True",
        "type": "bool",
        "description": (
            "是否启用邮件发送。测试/开发环境可设为 False 屏蔽所有邮件；"
            "即使为 True，若账号仍是默认占位符配置也会自动跳过发送。"
        ),
    },
    {
        "key": "MAIL_SERVER",
        "value": "smtp.qq.com",
        "type": "str",
        "description": "邮件服务器地址",
    },
    {
        "key": "MAIL_PORT",
        "value": "465",
        "type": "int",
        "description": "邮件发送端口",
    },
    {
        "key": "MAIL_USE_SSL",
        "value": "True",
        "type": "bool",
        "description": "邮件是否启用 SSL，填入 True 或者 False",
    },
    {
        "key": "MAIL_USERNAME",
        "value": "your_email@qq.com",
        "type": "str",
        "description": "邮件用户名",
    },
    {
        "key": "MAIL_PASSWORD",
        "value": "your_auth_password",
        "type": "str",
        "description": "邮件账户密码",
    },
    {
        "key": "MAIL_DEFAULT_SENDER",
        "value": "your_email@qq.com",
        "type": "str",
        "description": "邮件默认发送者",
    },
    {
        "key": "GUARANTEE_EXPIRATION",
        "value": "1",
        "type": "int",
        "description": "担保申请过期时间，单位：小时",
    },
    {
        "key": "RESPONSE_VALIDITY_PERIOD",
        "value": "24",
        "type": "int",
        "description": "单位：小时",
    },
    {
        "key": "MC_SERVER_ADDRESS",
        "value": "example.com",
        "type": "str",
        "description": "被采集的mc服务器地址",
    },
    {
        "key": "MC_PLAYER_COLLECT_INTERVAL_MINUTES",
        "value": "10",
        "type": "int",
        "description": "MC 服务器在线人数采集间隔，单位：分钟",
    },
    {
        "key": "SERVER_LAUNCH_DATE",
        "value": "",
        "type": "str",
        "description": "开服日期，格式：2024-07-05",
    },
]
