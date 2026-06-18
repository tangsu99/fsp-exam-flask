"""pytest 全局配置：为测试设置必要的环境变量"""

import os

# 在导入 myapp 之前设置测试数据库，避免 myapp/__init__.py 因缺少 DATABASE_URL 而报错
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
