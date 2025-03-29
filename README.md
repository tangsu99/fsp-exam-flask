# FSP-exam-Flask
[前端地址](https://github.com/tangsu99/fsp-exam-vue)

## 环境配置
 * Windows
 ```
 pip install -r requirement.txt
 cp .env.example .env
 ```

## Database
* Initial
```
flask --app main.py db init
flask --app main.py db migrate -m "Initial migration."
```
* Migration Database
```
flask --app main.py db migrate -m "xxx update."
flask --app main.py db upgrade
```

## Run
 * Windows
 ```
 python main.py
 ```
