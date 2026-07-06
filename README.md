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

## Database Schema Sync

Compare the DDL differences between two databases (e.g., development vs. production) and generate synchronization SQL.

### Prerequisites

- `mysqldump` installed and accessible via PATH
- Database connection credentials

### Usage

```shell
# Option 1: Compare two live databases directly
python scripts/sync_db_schema.py \
    --source root:pass@localhost:3306/dev_db \
    --target root:pass@prod_host:3306/prod_db

# Option 2: Compare from existing DDL dump files
mysqldump -u root -p --no-data dev_db > dev_ddl.sql
mysqldump -u root -p --no-data prod_db > prod_ddl.sql
python scripts/sync_db_schema.py \
    --source-dump dev_ddl.sql \
    --target-dump prod_ddl.sql

# Option 3: Only dump DDL for a single database
python scripts/sync_db_schema.py --dump-only root:pass@localhost:3306/mydb

# Save output to a file
python scripts/sync_db_schema.py \
    --source root:pass@localhost:3306/dev_db \
    --target root:pass@prod_host:3306/prod_db \
    -o sync.sql
```

The script will generate:

1. `CREATE TABLE` statements for tables missing in the target
2. `ALTER TABLE` statements for column definition differences
3. `ALTER TABLE` / `CREATE INDEX` statements for missing indexes and constraints
4. Warnings for tables that exist only in the target database

> ⚠️ Always review the generated SQL before executing it against a production database.

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
