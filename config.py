# 这个配置文件是给 Linux 生产环境的 Gunicorn 用的，Windows 系统不用管
# import multiprocessing
# workers = multiprocessing.cpu_count() * 2 + 1
bind = "127.0.0.1:5000"

workers = 1
backlog = 2048
# 默认是sync，同步模式，eventlet 是异步模式，要通过pip安装eventlet>=0.24.1
# worker_class = "eventlet"
worker_connections = 1000
daemon = False  # False 代表前台运行，后台运行会导致 systemd 识别问题
pidfile = "log/gunicorn.pid"
accesslog = "log/access.log"
errorlog = "log/gunicorn.log"
