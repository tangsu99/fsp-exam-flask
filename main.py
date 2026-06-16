from sqlalchemy import func, select

from myapp import create_app, db
from myapp.db_model import User, UserRole, UserStatus

app = create_app()

LEN = 50


def setup():
    print("+" * LEN)
    print("Setting...")
    if db.session.scalar(select(func.count(User.id))) == 0:
        # Please be sure to change the default password!
        user = User(username="root", user_qq="123456789", role=UserRole.ADMIN, status=UserStatus.ACTIVE)
        user.password = "@12345Root"
        db.session.add(user)
        db.session.commit()
        print("Created Admin account!")
    else:
        print("Database is not null!")
    print("+" * LEN)


if __name__ == "__main__":
    app.run(debug=True)
