from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from sqlalchemy import exists, func, select

from myapp import db
from myapp.db_model import (
    Option,
    Question,
    QuestionImgURL,
    QuestionType,
    Response,
    ResponseDetail,
    ResponseScore,
    Survey,
    SurveySlot,
)


@dataclass
class DCOption:
    text: str
    is_correct: bool
    question_id: int | None = None


@dataclass
class DCImage:
    data: str
    alt: str = ""
    question_id: int | None = None


@dataclass
class DCQuestion:
    survey_id: int
    title: str
    type: QuestionType
    _score: float
    options: list[DCOption] = field(default_factory=list[DCOption])
    images: list[DCImage] = field(default_factory=list[DCImage])
    display_order: int | None = None  # None 或者 0 都代表插入到末尾
    id: int | None = None

    def __post_init__(self):
        if self.display_order == 0:
            self.display_order = None
        if len(self.options) == 0:
            raise ValueError(f"标题为{self.title[:8]}...的题目至少需要一个选项")

        if self.type == QuestionType.FILL_IN_THE_BLANKS or self.type == QuestionType.SUBJECTIVE:
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


def is_survey_exist(survey_id: int) -> bool | None:
    stmt = select(exists().where(Survey.id == survey_id))
    return db.session.scalar(stmt)


def is_question_exist(question_id: int) -> bool | None:
    stmt = select(exists().where(Question.id == question_id, Question.logical_deletion.is_(False)))
    return db.session.scalar(stmt)


def build_dc_questions(
    questions: list[dict[str, Any]], survey_id: int | None = None
) -> tuple[bool, str | list[DCQuestion]]:
    if (not survey_id) or (not is_survey_exist(survey_id)):
        return False, "问卷不存在"

    dc_questions: list[DCQuestion] = []
    errors: list[str] = []

    for idx, question in enumerate(questions):
        try:
            raw_options = question.get("options", [])
            raw_images = question.get("images", [])

            dc_question = DCQuestion(
                survey_id=survey_id,
                title=question.get("title", "未知题目"),
                type=question.get("type", 0),
                _score=question.get("score", 5),
                options=[
                    DCOption(text=item.get("text", ""), is_correct=item.get("isCorrect", False)) for item in raw_options
                ],
                images=[DCImage(data=item.get("data", ""), alt=item.get("alt", "")) for item in raw_images],
                display_order=question.get("display_order", None),
                id=question.get("id", None),
            )

            dc_questions.append(dc_question)

        except Exception as e:
            errors.append(f"第 {idx + 1} 题构建失败: {str(e)}")
            continue

    if errors:
        return False, "; ".join(errors)

    return True, dc_questions


def is_survey_response_expired(survey_response: Response) -> bool:
    """
    判断答卷是否过期
    """
    if survey_response.end_time is None:
        return False

    expired_datetime = survey_response.end_time.replace(tzinfo=UTC)
    current_datetime = datetime.now(UTC)
    return True if current_datetime > expired_datetime else False


def get_response_total_score(response_id: int) -> float:
    """
    获取答卷总分
    """
    stmt = select(func.sum(ResponseScore.score)).where(ResponseScore.response_id == response_id)
    return db.session.scalar(stmt) or 0.0


def get_survey_total_score(survey_id: int) -> float:
    """
    获取问卷满分分数
    """
    stmt = select(func.sum(Question.score)).where(Question.survey_id == survey_id)
    return db.session.scalar(stmt) or 0.0


def get_response_objective_question_score(user_response: list[str], question: Question) -> float:
    """
    获取答卷客观题的分数
    """
    # 获取问题的正确选项,列表元素的值为正确选项的ID
    correct_options: list[int] = [option.id for option in question.options if option.is_correct]

    if question.question_type == QuestionType.SINGLE_CHOICE.value:
        if int(user_response[0]) in correct_options:
            return question.score

    elif question.question_type == QuestionType.MULTIPLE_CHOICE.value:
        user_response_int: list[int] = [int(option) for option in user_response]
        if set(user_response_int) == set(correct_options):
            return question.score

    elif question.question_type == QuestionType.FILL_IN_THE_BLANKS.value:
        new_user_response: str = user_response[0]
        correct_answer_id: int = correct_options[0]
        option: Option | None = db.session.get(Option, correct_answer_id)
        if option is not None:
            correct_answer: str = option.option_text
            if new_user_response == correct_answer:
                return question.score

    return 0.0


def make_answer_details(
    user_response: list[str], question: Question, response_id: int, question_id: int
) -> list[ResponseDetail]:
    if question.question_type == QuestionType.MULTIPLE_CHOICE.value:
        return [
            ResponseDetail(
                response_id=response_id,
                question_id=question_id,
                answer=answer,
            )
            for answer in user_response
        ]
    else:
        return [
            ResponseDetail(
                response_id=response_id,
                question_id=question_id,
                answer=user_response[0],
            )
        ]


def user_answered_question(details: Sequence[ResponseDetail]) -> bool:
    return False if len(details) == 0 else True


def build_dict_image(img: QuestionImgURL) -> dict[str, Any]:
    return {"id": img.id, "alt": img.img_alt, "data": img.img_data}


type QuestionViewType = Literal["answer", "admin-view", "admin-review"]


def build_dict_option(
    type: QuestionViewType,
    question_type: QuestionType,
    option: Option,
    answer_list: Sequence[ResponseDetail] | None = None,
) -> dict[str, Any]:
    """
    answer_list: 这道题的答题列表
    当题目为单选题或多选题时，指一道题里所有选择了的选项的ID
    当题目为填空题或简答题时，列表的第一个元素是用户作答的内容
    """
    result: dict[str, Any] = {
        "id": option.id,
        "text": option.option_text,
    }

    if type == "answer" and question_type in (QuestionType.FILL_IN_THE_BLANKS, QuestionType.SUBJECTIVE):
        result["text"] = "此处作答"

    if type in ("admin-view", "admin-review"):
        result["isCorrect"] = option.is_correct
        result["referenceAnswer"] = (
            option.option_text if question_type in (QuestionType.FILL_IN_THE_BLANKS, QuestionType.SUBJECTIVE) else ""
        )

    if type == "admin-review":
        if answer_list is None:
            raise ValueError("admin-review 模式必须提供 answer_list 参数")

        user_selected_option: list[int] = []
        if question_type in (QuestionType.SINGLE_CHOICE, QuestionType.MULTIPLE_CHOICE):
            for detail in answer_list:
                user_selected_option.append(int(detail.answer))

        result["isSelected"] = True if option.id in user_selected_option else False
        result["userAnsweredText"] = (
            answer_list[0].answer
            if question_type in (QuestionType.FILL_IN_THE_BLANKS, QuestionType.SUBJECTIVE)
            and user_answered_question(answer_list)
            else ""
        )

    return result


def build_dict_question(
    type: QuestionViewType,
    question: Question,
    details: Sequence[ResponseDetail] | None = None,
    response_score: ResponseScore | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": question.id,
        "display_order": question.display_order,
        "title": question.question_text,
        "type": question.question_type,
        "score": question.score,
        "images": [build_dict_image(img) for img in question.img_list],
    }

    if type in ("answer", "admin-view"):
        result["options"] = [build_dict_option(type, question.question_type, option) for option in question.options]
    elif type == "admin-review":
        if details is None:
            raise ValueError("admin-review 模式必须提供 details 参数")
        result["options"] = [
            build_dict_option("admin-review", question.question_type, option, details) for option in question.options
        ]
        result["userGetScore"] = response_score.score if response_score is not None else 0

    return result
