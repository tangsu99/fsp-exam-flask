# FSP-exam-Flask

[前端地址](https://github.com/tangsu99/fsp-exam-vue)

## 初始配置

-   初始管理员用户和密码写在 main.py 里，请务必修改默认密码！

## 环境配置

-   Windows

```
pip install -r requirement.txt
cp .env.example .env
```

数据库使用`MySQL`，驱动采用`PyMySQL`，编辑`.env`配置数据库连接地址

```
# DATABASE_URL=mysql+pymysql://<user>:<password>@<host>:<port>/<database>
# <user>:       用户名
# <password>:   密码
# <host>:       地址
# <port>:       端口
# <database>:   数据库名

# 示例
DATABASE_URL=mysql+pymysql://root:123456@localhost:3306/fsp_exam
```

## Database

-   Initial

```
flask --app main.py db init
flask --app main.py db migrate -m "Initial migration."
```

-   Migration Database

```
flask --app main.py db migrate -m "xxx update."
flask --app main.py db upgrade
```

## 运行

-   在运行 Flask 应用前，请先确保 Mysql 服务已启动！
-   Windows 系统开发环境：

    -   默认地址：http://127.0.0.1:5000
    -   启动命令：`python ./main.py`

-   Linux 系统生产环境：

    -   systemd 配置：

        ```text
        [Unit]
        Description=Fsp Exam Application
        After=network.target

        [Service]
        User=root
        Group=root
        WorkingDirectory=/opt/web/fsp_exam
        Environment="PATH=/opt/web/fsp_exam/venv/bin"
        ExecStart=/opt/web/fsp_exam/venv/bin/gunicorn --config=config.py main:app

        [Install]
        WantedBy=multi-user.target

        ```

    -   首次：`systemctl daemon-reload`
    -   启动：`systemctl start myflaskapp`
