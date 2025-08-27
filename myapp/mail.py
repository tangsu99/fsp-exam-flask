from threading import Thread

from flask import render_template, current_app
from flask_mail import Message

from myapp import mail as flask_mail_app


def attach_image(msg, image_path, cid):
    with current_app.open_resource(image_path) as fp:
        msg.attach(cid, 'image/jpeg', fp.read(), headers={'Content-ID': cid})


def send_async_mail(app, mail_msg):
    with app.app_context():
        flask_mail_app.send(mail_msg)


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
    html_content = render_template('mail_guarantee_result.html', guarantor = guarantor, result = result)
    # 附加图片
    try:
        attach_image(mail_msg, '../static/images/qrcode_fsp.jpg', 'qrcode')
    except Exception as e:
        current_app.logger.warning(f"无法附加图片: {e}")
        # 如果图片附加失败，使用备选文本
        html_content = html_content.replace('cid:qrcode', 'qrcode')

    mail_msg.html = html_content
    return mail_msg

def survey_result_mail(recipients: list[str], score: str) -> Message:
    url = current_app.config["FRONT_END_BASE_URL"] + '/Query/Examination'
    mail_msg = Message('考试结果', recipients=recipients)
    mail_msg.html = render_template('mail_survey_result.html', score = score, url = url)
    return mail_msg
