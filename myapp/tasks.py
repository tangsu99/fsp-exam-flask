from mcstatus import JavaServer

from myapp import APP, db, scheduler
from myapp.db_model import StatusLog


@scheduler.task("interval", id="mcstatus", seconds=600, misfire_grace_time=900)  # type: ignore[reportUnknownMemberType]
def job1():
    """定时采集 MC 服务器在线人数，保存到 StatusLog 表"""
    with APP.app_context():
        server_address: str = APP.config.get("MC_SERVER_ADDRESS", "")  # type: ignore
        if not server_address or server_address == "example.com":
            APP.logger.info("未配置 MC_SERVER_ADDRESS，跳过采集。")
            return

        try:
            server = JavaServer.lookup(server_address)  # type: ignore
            status = server.status()
            log = StatusLog(
                server_address=server_address,  # type: ignore
                player_count=status.players.online,
            )
            db.session.add(log)
            db.session.commit()
            APP.logger.info(f"[mcstatus] 采集指定的服务器在线: {status.players.online} 名玩家。")
        except Exception:
            db.session.rollback()
            APP.logger.info("[mcstatus] 采集失败！")
