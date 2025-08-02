from flask import render_template, current_app
from flask_mail import Message


def reset_password_mail(recipients: list[str], token: str) -> Message:
    reset_password_url = current_app.config["RESET_PASSWORD_URL"]
    msg = Message('重置密码', recipients=recipients)
    msg.html = render_template('mail_reset_password.html', url=reset_password_url + token)
    return msg


def activation_mail(recipients: list[str], token: str) -> Message:
    activation_url = current_app.config["ACTIVATION_URL"]
    msg = Message('账户激活', recipients=recipients)
    msg.html = render_template('mail_activation.html', url=activation_url + token)
    return msg

def survey_complete_mail(recipients: list[str], username: str, response_time: str, id_: int) -> Message:
    url = current_app.config["FRONT_END_BASE_URL"] + '/admin/response?id=' + str(id_)
    msg = Message('答卷完成', recipients=recipients)
    msg.html = render_template('mail_survey_complete.html', username = username, response_time = response_time, url=url)
    return msg
