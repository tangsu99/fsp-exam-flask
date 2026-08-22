from collections.abc import Mapping
from datetime import UTC, datetime, timedelta, timezone
from threading import Thread
from typing import BinaryIO, cast

from flask import Flask, current_app, render_template
from flask_mail import Message

from myapp import mail as flask_mail_app


def attach_image(msg: Message, image_path: str, cid: str):
    fp = cast(BinaryIO, current_app.open_resource(image_path))
    with fp:
        data: bytes = fp.read()
        msg.attach(cid, "image/jpeg", data, headers={"Content-ID": cid})


def send_async_mail(app: Flask, mail_msg: Message):
    with app.app_context():
        flask_mail_app.send(mail_msg)


def _is_mail_configured(app: Flask) -> bool:
    """
    邮件是否具备发送条件：
    - MAIL_ENABLED 显式关闭时返回 False
    - 账号/密码为空，或仍是默认占位符（your_*）时视为未配置，返回 False
    """
    config = cast("Mapping[str, object]", app.config)
    if not cast(bool, config.get("MAIL_ENABLED", True)):
        return False
    username: str = str(config.get("MAIL_USERNAME", "") or "")
    password: str = str(config.get("MAIL_PASSWORD", "") or "")
    if not username or not password:
        return False
    if username.startswith("your_") or password.startswith("your_"):
        return False
    return True


def send_mail(app: Flask, mail_msg: Message):
    if not _is_mail_configured(app):
        app.logger.info("邮件未启用或未配置真实账号，跳过发送: %s", mail_msg.subject)
        return
    return Thread(target=send_async_mail, args=[app, mail_msg]).start()


def _recipients_list(recipients: list[str]) -> "list[str | tuple[str, str]]":
    """转换收件人列表类型以匹配 flask_mail Message 的签名"""
    return cast("list[str | tuple[str, str]]", recipients)


def _format_cn_datetime(iso_str: str) -> str:
    """将 ISO 时间字符串格式化为东八区时间，例如 2026-08-22 14:51 (UTC + 8 )"""
    dt = datetime.fromisoformat(iso_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    cn_tz = timezone(timedelta(hours=8))
    return dt.astimezone(cn_tz).strftime("%Y-%m-%d %H:%M (UTC + 8 )")


def reset_password_mail(recipients: list[str], token: str) -> Message:
    subject = "像素仙缘-密码重置"
    reset_password_url: str = current_app.config["RESET_PASSWORD_URL"]  # type: ignore[reportUnknownMemberType]
    mail_msg = Message(subject, recipients=_recipients_list(recipients))
    mail_msg.html = render_template("mail_reset_password.html", heading=subject, url=reset_password_url + token)
    return mail_msg


def activation_mail(recipients: list[str], token: str) -> Message:
    subject = "像素仙缘-账户激活"
    activation_url = current_app.config["ACTIVATION_URL"]  # type: ignore[reportUnknownMemberType]
    mail_msg = Message(subject, recipients=_recipients_list(recipients))
    mail_msg.html = render_template("mail_activation.html", heading=subject, url=activation_url + token)
    return mail_msg


def survey_complete_mail(recipients: list[str], username: str, response_time: str, id_: int) -> Message:
    subject = "像素仙缘-新的待批改答卷"
    url: str = current_app.config["FRONT_END_BASE_URL"] + "/admin/response?id=" + str(id_)  # type: ignore[reportUnknownMemberType]
    mail_msg = Message(subject, recipients=_recipients_list(recipients))
    mail_msg.html = render_template(
        "mail_survey_complete.html",
        heading=subject,
        username=username,
        response_time=_format_cn_datetime(response_time),
        url=url,
    )
    return mail_msg


def guarantee_result_mail(
    recipients: list[str], guarantor: str, result: bool, handle_time: str | None = None
) -> Message:
    subject = "像素仙缘-担保结果"
    mail_msg = Message(subject, recipients=_recipients_list(recipients))
    html_content = render_template(
        "mail_guarantee_result.html",
        heading=subject,
        guarantor=guarantor,
        result=result,
        handle_time=_format_cn_datetime(handle_time) if handle_time else None,
    )
    # 附加图片
    try:
        attach_image(mail_msg, "../static/images/qrcode_fsp.jpg", "qrcode")
    except Exception as e:
        current_app.logger.warning(f"无法附加图片: {e}")
        # 如果图片附加失败，使用备选文本
        html_content = html_content.replace("cid:qrcode", "qrcode")

    mail_msg.html = html_content
    return mail_msg


def survey_result_mail(
    recipients: list[str], score: str, reason: str | None = None, review_time: str | None = None
) -> Message:
    subject = "像素仙缘-考试结果"
    url = current_app.config["FRONT_END_BASE_URL"] + "/Query/Examination"  # type: ignore[reportUnknownMemberType]
    mail_msg = Message(subject, recipients=_recipients_list(recipients))
    mail_msg.html = render_template(
        "mail_survey_result.html",
        heading=subject,
        score=score,
        url=url,
        reason=reason,
        review_time=_format_cn_datetime(review_time) if review_time else None,
    )
    return mail_msg
