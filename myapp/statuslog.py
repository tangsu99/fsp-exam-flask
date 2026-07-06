from datetime import UTC, datetime
from typing import cast

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user
from sqlalchemy import desc, select

from myapp import db
from myapp.db_model import StatusLog
from myapp.utils import parse_dt_to_iso_utc

statuslog = Blueprint("statuslog", __name__)

# 未登录用户最大查询条数
ANONYMOUS_MAX = 100


@statuslog.route("/log", methods=["GET"])
def online_stats():
    """在线人数统计接口

    默认查询今天的数据，今天数据不满50条则查询最新的100条记录。
    指定 start_time / end_time 参数则返回该时间段的数据。
    未登录用户最多只能查询最新 500 条数据。
    """
    start_time_str = request.args.get("start_time", type=str)
    end_time_str = request.args.get("end_time", type=str)
    is_anonymous = not current_user.is_authenticated
    SERVER_LAUNCH_DATE = cast(str, current_app.config["SERVER_LAUNCH_DATE"])

    # 指定了时间段参数：直接按时间段查询
    if start_time_str or end_time_str:
        stmt = select(StatusLog).order_by(StatusLog.create_time.asc())

        if start_time_str:
            start_time = datetime.fromisoformat(start_time_str)
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=UTC)
            stmt = stmt.where(StatusLog.create_time >= start_time)

        if end_time_str:
            end_time = datetime.fromisoformat(end_time_str)
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=UTC)
            stmt = stmt.where(StatusLog.create_time <= end_time)

        if is_anonymous:
            stmt = stmt.limit(ANONYMOUS_MAX)

        records = db.session.execute(stmt).scalars().all()
    else:
        # 默认：今天的数据
        now = datetime.now(UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        stmt = (
            select(StatusLog)
            .where(StatusLog.create_time.between(today_start, today_end))
            .order_by(StatusLog.create_time.asc())
        )
        if is_anonymous:
            stmt = stmt.limit(ANONYMOUS_MAX)

        today_records = db.session.execute(stmt).scalars().all()

        if len(today_records) >= 50:
            records = today_records
        else:
            # 今天不满足50条，查询最新100条（未登录时最多500）
            fallback_limit = min(100, ANONYMOUS_MAX) if is_anonymous else 100
            stmt = select(StatusLog).order_by(desc(StatusLog.create_time)).limit(fallback_limit)
            records = list(db.session.execute(stmt).scalars().all())
            records.reverse()  # 正序返回

    count = [r.player_count for r in records]
    date = [parse_dt_to_iso_utc(r.create_time) for r in records]

    return jsonify(
        {
            "code": 0,
            "data": {"total": len(records), "count": count, "date": date, "serverLaunchDate": SERVER_LAUNCH_DATE},
        }
    )
