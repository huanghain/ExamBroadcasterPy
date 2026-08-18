"""数据库引擎与会话管理"""
import shutil
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from config import DB_PATH, APP_DATA_DIR
from utils.logger import get_logger

logger = get_logger("database")

BACKUP_DIR = APP_DATA_DIR / "backups"


def backup_database() -> str | None:
    """备份当前数据库到 backups 目录，返回备份文件路径

    每次启动时执行，保留最近 30 天的备份。
    """
    try:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)

        if not DB_PATH.exists():
            logger.warning("数据库文件不存在，跳过备份")
            return None

        today = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUP_DIR / f"exam_broadcaster_{today}.db"
        shutil.copy2(str(DB_PATH), str(backup_path))
        logger.info("数据库已备份: %s", backup_path)

        # 清理 30 天前的旧备份
        _cleanup_old_backups(30)

        return str(backup_path)
    except Exception as e:
        logger.warning("数据库备份失败: %s", e)
        return None


def _cleanup_old_backups(days: int = 30):
    """清理超过指定天数的旧备份"""
    try:
        cutoff = datetime.now().timestamp() - days * 86400
        for f in sorted(BACKUP_DIR.glob("exam_broadcaster_*.db")):
            if f.stat().st_mtime < cutoff:
                f.unlink()
                logger.info("已清理旧备份: %s", f.name)
    except Exception as e:
        logger.warning("清理旧备份失败: %s", e)


class Base(DeclarativeBase):
    pass


_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(
            f"sqlite:///{DB_PATH}",
            echo=False,
            connect_args={"check_same_thread": False}
        )
    return _engine


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        # expire_on_commit=False: commit 后属性不过期，避免 detached 对象访问报错
        _SessionLocal = sessionmaker(
            bind=get_engine(),
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    return _SessionLocal


def get_session():
    """获取新的数据库会话"""
    factory = get_session_factory()
    return factory()


@contextmanager
def session_scope():
    """
    数据库会话上下文管理器

    自动管理 session 的创建、提交/回滚和关闭。
    用法：
        with session_scope() as session:
            result = session.query(Exam).all()
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _run_migrations():
    """执行数据库迁移（为已有表添加新列、创建新表）"""
    engine = get_engine()
    inspector = inspect(engine)

    # 检查 exams 表是否存在
    if "exams" not in inspector.get_table_names():
        return  # 表尚未创建，create_all 会处理

    existing_columns = {col["name"] for col in inspector.get_columns("exams")}

    migrations = [
        ("reminder_enabled", "BOOLEAN DEFAULT 1"),
        ("reminder_minutes_before", "INTEGER DEFAULT 30"),
        ("reminder_end_enabled", "BOOLEAN DEFAULT 0"),
        ("reminder_end_minutes_before", "INTEGER DEFAULT 15"),
    ]

    with engine.connect() as conn:
        for col_name, col_def in migrations:
            if col_name not in existing_columns:
                conn.execute(
                    text(f"ALTER TABLE exams ADD COLUMN {col_name} {col_def}")
                )
        conn.commit()

    # 迁移 exam_reminders 表的 custom_audio_path 列
    _migrate_reminder_audio_column(engine, inspector)

    # 迁移旧提醒数据到 exam_reminders 表
    _migrate_legacy_reminders(engine, inspector)


def _migrate_reminder_audio_column(engine, inspector):
    """为 exam_reminders 表添加 custom_audio_path 和 custom_tts_text 列"""
    if "exam_reminders" not in inspector.get_table_names():
        return  # 表尚未创建，create_all 会处理

    existing_columns = {col["name"] for col in inspector.get_columns("exam_reminders")}
    if "custom_audio_path" not in existing_columns:
        with engine.connect() as conn:
            conn.execute(
                text("ALTER TABLE exam_reminders ADD COLUMN custom_audio_path VARCHAR(500)")
            )
            conn.commit()

    if "custom_tts_text" not in existing_columns:
        with engine.connect() as conn:
            conn.execute(
                text("ALTER TABLE exam_reminders ADD COLUMN custom_tts_text VARCHAR(2000)")
            )
            conn.commit()


def _migrate_legacy_reminders(engine, inspector):
    """将旧的单提醒字段迁移到 exam_reminders 表"""
    if "exam_reminders" not in inspector.get_table_names():
        return  # 新表尚未创建，create_all 会处理

    with engine.connect() as conn:
        # 检查是否已有迁移数据
        result = conn.execute(text("SELECT COUNT(*) FROM exam_reminders"))
        if result.scalar() > 0:
            return  # 已有数据，不重复迁移

        # 查询所有有旧提醒设置的考试
        rows = conn.execute(text(
            "SELECT id, reminder_enabled, reminder_minutes_before, "
            "reminder_end_enabled, reminder_end_minutes_before FROM exams"
        )).fetchall()

        for row in rows:
            exam_id = row[0]
            r_enabled = row[1]
            r_mins = row[2] or 30
            r_end_enabled = row[3]
            r_end_mins = row[4] or 15

            if r_enabled:
                conn.execute(text(
                    "INSERT INTO exam_reminders (exam_id, reminder_type, minutes_before, is_enabled, created_at) "
                    "VALUES (:eid, 'start', :mins, 1, datetime('now'))"
                ), {"eid": exam_id, "mins": r_mins})

            if r_end_enabled:
                conn.execute(text(
                    "INSERT INTO exam_reminders (exam_id, reminder_type, minutes_before, is_enabled, created_at) "
                    "VALUES (:eid, 'end', :mins, 1, datetime('now'))"
                ), {"eid": exam_id, "mins": r_end_mins})

        conn.commit()


def init_db():
    """初始化数据库（创建所有表）"""
    # 确保模型已导入
    import models.exam
    import models.exam_reminder
    import models.template
    import models.schedule_task

    Base.metadata.create_all(bind=get_engine())

    # 执行增量迁移
    _run_migrations()