from myapp import db
from myapp.db_model import SurveySlot
from sqlalchemy import select, exists

def is_survey_mounted(survey_id: int) -> bool:
    """问卷是否被挂载，或者说问卷是否允许被用户作答"""
    stmt = exists().where(SurveySlot.mounted_survey_id == survey_id)
    return True if db.session.scalar(select(stmt)) else False
