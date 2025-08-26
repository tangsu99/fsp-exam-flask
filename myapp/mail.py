from threading import Thread

from flask import render_template, current_app
from flask_mail import Message

from myapp import mail


def send_async_mail(app, mail_msg):
    with app.app_context():
        mail.send(mail_msg)


def send_mail(app, mail_msg):
    return Thread(target=send_async_mail, args=[app, mail_msg]).start()


def reset_password_mail(recipients: list[str], token: str) -> Message:
    reset_password_url = current_app.config["RESET_PASSWORD_URL"]
    mail_msg = Message('重置密码', recipients=recipients)
    mail_msg.html = render_template('mail_reset_password.html', url=reset_password_url + token)
    return mail_msg


def activation_mail(recipients: list[str], token: str) -> Message:
    activation_url = current_app.config["ACTIVATION_URL"]
    mail_msg = Message('账户激活', recipients=recipients)
    mail_msg.html = render_template('mail_activation.html', url=activation_url + token)
    return mail_msg

def survey_complete_mail(recipients: list[str], username: str, response_time: str, id_: int) -> Message:
    url = current_app.config["FRONT_END_BASE_URL"] + '/admin/response?id=' + str(id_)
    mail_msg = Message('答卷完成', recipients=recipients)
    mail_msg.html = render_template('mail_survey_complete.html', username = username, response_time = response_time, url=url)
    return mail_msg

def guarantee_result_mail(recipients: list[str], guarantor: str, result: bool) -> Message:
    mail_msg = Message('担保结果', recipients=recipients)
    mail_msg.html = render_template('mail_guarantee_result.html', guarantor = guarantor, result = result)
    return mail_msg

def survey_result_mail(recipients: list[str], score: str) -> Message:
    url = current_app.config["FRONT_END_BASE_URL"] + '/Query/Examination'
    mail_msg = Message('考试结果', recipients=recipients)
    mail_msg.html = render_template('mail_survey_result.html', score = score, url = url)
    return mail_msg
