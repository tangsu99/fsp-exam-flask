from flask import render_template, current_app
from flask_mail import Message


def reset_password_mail(recipients: list[str], token: str) -> Message:
    reset_password_url = current_app.config["RESET_PASSWORD_URL"]
    msg = Message('重置密码', recipients=recipients)
    msg.html = render_template('mail_reset_password.html', url=reset_password_url + token)
    return msg
