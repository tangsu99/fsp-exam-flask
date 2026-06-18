# FSP-exam-Flask

This is the back-end part of the Minecraft server website that integrates whitelist qualification acquisition and resource center

[Front-end](https://github.com/tangsu99/fsp-exam-vue)

## Project Setup

- The initial administrator user and password are written in `main.py`. Please be sure to change the default password!

### Environment Configuration

```
uv sync
cp .env.example .env
```

.env:

```
# DATABASE_URL=mysql+pymysql://<user>:<password>@<host>:<port>/<database>

# example
DATABASE_URL=mysql+pymysql://root:123456@localhost:3306/fsp_exam
```

### Database

- Initial

```
flask --app main.py db init
flask --app main.py db migrate -m "Initial migration."
```

- Migration Database

```
flask --app main.py db migrate -m "xxx update."
flask --app main.py db upgrade
```

### Test

```shell
uv run pytest
```

## Run

- Before running the Flask application, please ensure that the MySQL service is started!
- Windows system development environment:
    - default url：http://127.0.0.1:5000
    - startup command：`uv run ./main.py`
    - startup command(virtual environment)：`python ./main.py`

- Linux system development environment:
    - install uv
        ```bash
        curl -LsSf https://astral.sh/uv/install.sh | sh
        source ~/.bashrc
        ```
    - install gunicorn: `pip install gunicorn`
    - systemd config：

        ```text
        [Unit]
        Description=Fsp Exam Application
        After=network.target

        [Service]
        User=root
        Group=root
        WorkingDirectory=/opt/web/fsp_exam
        Environment="PATH=/opt/web/fsp_exam/venv/bin"
        ExecStart=/root/.local/bin/uv run gunicorn --config=config.py main:app

        [Install]
        WantedBy=multi-user.target
        ```

    - first：`systemctl daemon-reload`
    - start：`systemctl start myflaskapp`
