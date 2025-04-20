# FSP-exam-Flask

[前端地址](https://github.com/tangsu99/fsp-exam-vue)

## 初始配置

- 初始管理员用户和密码写在 main.py 里，请务必修改默认密码！

## 环境配置

- Windows

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

## Run

- Windows

```
python main.py
```
