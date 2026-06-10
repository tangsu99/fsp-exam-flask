# This configuration file is for Gunicorn in a Linux production environment. For Windows systems, please disregard it#
# import multiprocessing
# workers = multiprocessing.cpu_count() * 2 + 1
bind = "127.0.0.1:5000"

workers = 1
backlog = 2048
# worker_class = "eventlet"
worker_connections = 1000
daemon = False
pidfile = "log/gunicorn.pid"
accesslog = "log/access.log"
errorlog = "log/gunicorn.log"
