from myapp import db
from myapp.db_model import SurveySlot, Survey, QuestionCategory, Question

from sqlalchemy import select, exists

from dataclasses import dataclass, field


@dataclass
class DCOption:
    text: str
    is_correct: bool
    question_id: int | None = None


@dataclass
class DCImage:
    data: str
    alt: str = ''
    question_id: int | None = None


@dataclass
class DCQuestion:
    survey_id: int
    title: str
    type: QuestionCategory
    _score: float
    options: list[DCOption] = field(default_factory=list)
    images: list[DCImage] = field(default_factory=list)
    display_order: int | None = None # None 或者 0 都代表插入到末尾

    def __post_init__(self):
        if self.display_order == 0:
            self.display_order = None
        if len(self.options) == 0:
            raise ValueError(f"标题为{self.title[:8]}...的题目至少需要一个选项")

        if self.type == QuestionCategory.FILL_IN_THE_BLANKS or self.type == QuestionCategory.SUBJECTIVE:
            if len(self.options) > 1:
                raise ValueError(f"标题为{self.title[:8]}...的题目只能有一个选项")

            self.options[0].is_correct = True

        self.score = self._score

    @property
    def score(self) -> float:
        return self._score

    @score.setter
    def score(self, value: float):
        if not (0 <= value <= 100):
            raise ValueError(f"标题为{self.title[:8]}...的题目分数必须在 0 到 100 之间，当前值为: {value}")

        self._score = value


def is_survey_mounted(survey_id: int) -> bool:
    """问卷是否被挂载，或者说问卷是否允许被用户作答"""
    stmt = exists().where(SurveySlot.mounted_survey_id == survey_id)
    return True if db.session.scalar(select(stmt)) else False


def is_survey_exist(survey_id: int) -> bool:
    stmt = select(exists().where(Survey.id == survey_id))
    return db.session.scalar(stmt)


def is_question_exist(question_id: int) -> bool:
    stmt = select(exists().where(Question.id == question_id))
    return db.session.scalar(stmt)


def build_dc_questions(survey_id: int, questions: list) -> tuple[bool, str | list[DCQuestion]]:
    if not is_survey_exist(survey_id):
        return False, "问卷不存在"

    dc_questions = []
    errors = []

    for idx, question in enumerate(questions):
        try:
            raw_options = question.get("options", [])
            raw_images = question.get("images", [])

            dc_question = DCQuestion(
                survey_id=survey_id,
                display_order=question.get("displayOrder", None),
                title=question.get("title", "未知题目"),
                type=question.get("type"),
                _score=question.get("score", 5),

                options=[
                    DCOption(text=item.get("text", ""), is_correct=item.get("isCorrect", False))
                    for item in raw_options
                ],
                images=[
                    DCImage(data=item.get("data", ""), alt=item.get("alt", ""))
                    for item in raw_images
                ]
            )

            dc_questions.append(dc_question)

        except Exception as e:
            errors.append(f"第 {idx + 1} 题构建失败: {str(e)}")
            continue

    if errors:
        return False, "; ".join(errors)

    return True, dc_questions
