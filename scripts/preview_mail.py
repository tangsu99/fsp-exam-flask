"""Render mail templates for preview (approved / rejected), inline the QR image."""

import base64
from pathlib import Path

from flask import Flask, render_template

ROOT = Path(__file__).resolve().parent.parent
app = Flask(__name__, template_folder=str(ROOT / "templates"))

QR = ROOT / "static" / "images" / "qrcode_fsp.jpg"


def inline_qr(html: str) -> str:
    data = base64.b64encode(QR.read_bytes()).decode()
    return html.replace("cid:qrcode", f"data:image/jpeg;base64,{data}")


with app.app_context():
    html_ok = render_template(
        "mail_survey_result.html",
        heading="像素仙缘-考试结果",
        score="85",
        url="https://exam.fsp.ink/Query/Examination",
        reason=None,
        review_time="2026-08-22 14:30",
    )
    (ROOT / "preview_result_ok.html").write_text(inline_qr(html_ok), encoding="utf-8")

    html_rejected = render_template(
        "mail_survey_result.html",
        heading="像素仙缘-考试结果",
        score="60",
        url="https://exam.fsp.ink/Query/Examination",
        reason="答题不符合要求，请重新作答。",
        review_time="2026-08-22 14:30",
    )
    (ROOT / "preview_result_rejected.html").write_text(html_rejected, encoding="utf-8")

    html_guarantee_ok = render_template(
        "mail_guarantee_result.html",
        heading="像素仙缘-担保结果",
        guarantor="Admin",
        result=True,
        handle_time="2026-08-22 15:00",
    )
    (ROOT / "preview_guarantee_ok.html").write_text(inline_qr(html_guarantee_ok), encoding="utf-8")

    html_guarantee_rejected = render_template(
        "mail_guarantee_result.html",
        heading="像素仙缘-担保结果",
        guarantor="Admin",
        result=False,
        handle_time="2026-08-22 15:00",
    )
    (ROOT / "preview_guarantee_rejected.html").write_text(html_guarantee_rejected, encoding="utf-8")

print("done")
