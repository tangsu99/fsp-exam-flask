from myapp import create_app, db
from myapp.db_model import User, ConfigModel

app = create_app()

LEN = 50

def setup():
    print('+' * LEN)
    print('Setting...')
    if User.query.count() == 0:
        username: str = 'root'
        password: str = '@12345Root'
        user = User(username, '123456789', 'admin').set_password(password)
        user.status = 1
        db.session.add(user)
        db.session.commit()
        print('Created Admin account!')
        if ConfigModel.query.count() == 0:
            from myapp.config import init_config
            init_config()
            print('Created config!')
    else:
        print('Database is not null!')
    print('+' * LEN)

if __name__ == "__main__":
    app.run(debug=True)
