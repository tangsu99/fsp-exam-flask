DEFAULT_CONFIG = [
    {
        'key': 'SECRET_KEY',
        'value': 'c4329f5e3bc9daf6cd2b82bf9355a5d2',
        'type': 'str',
        'desc': '',
    },
    {
        'key': 'API_TOKEN',
        'value': '5d0f1a51226e42a8b35908823eadfcab',
        'type': 'str',
        'desc': '',
    },
    {
        'key': 'ALLOWED_ORIGINS',
        'value': 'http://localhost:5173,http://127.0.0.1:5173',
        'type': 'list',
        'desc': '如果有多个值使用逗号隔开',
    },
    {
        'key': 'RESET_PASSWORD_URL',
        'value': 'http://localhost:5173/reset_password?token=',
        'type': 'str',
        'desc': '输入 URL',
    },
    {
        'key': 'ACTIVATION_URL',
        'value': 'http://localhost:5173/activation?token=',
        'type': 'str',
        'desc': '',
    },
    {
        'key': 'FRONT_END_BASE_URL',
        'value': 'http://localhost:5173',
        'type': 'str',
        'desc': '',
    },
    {
        'key': 'MAIL_SERVER',
        'value': 'smtp.qq.com',
        'type': 'str',
        'desc': '',
    },
    {
        'key': 'MAIL_PORT',
        'value': '465',
        'type': 'int',
        'desc': '',
    },
    {
        'key': 'MAIL_USE_SSL',
        'value': 'True',
        'type': 'bool',
        'desc': 'True 或者 False',
    },
    {
        'key': 'MAIL_USERNAME',
        'value': 'your_email@qq.com',
        'type': 'str',
        'desc': '',
    },
    {
        'key': 'MAIL_PASSWORD',
        'value': 'your_auth_password',
        'type': 'str',
        'desc': '',
    },
    {
        'key': 'MAIL_DEFAULT_SENDER',
        'value': 'your_email@qq.com',
        'type': 'str',
        'desc': '',
    },
    {
        'key': 'GUARANTEE_EXPIRATION',
        'value': '1',
        'type': 'int',
        'desc': '单位：小时',
    },
    {
        'key': 'RESPONSE_VALIDITY_PERIOD',
        'value': '24',
        'type': 'int',
        'desc': '单位：小时',
    },
]

