"""
Pydantic DTO schemas for Curriculum (Subjects & Syllabus Lessons).
Optimized for client bandwidth by excluding internal DB audit timestamps.

===============================================================================
විෂය නිර්දේශයේ DTO Schemas (Curriculum & Lesson Hierarchy):
-------------------------------------------------------------------------------
1. `SubjectCreate` / `SubjectResponse`:
   විෂයයන් (Combined Maths, Physics, etc.) සඳහා ඉල්ලුම් සහ ප්‍රතිචාර schemas.
2. `LessonCreate` / `LessonResponse`:
   පාඩම් සහ උප-පාඩම් සඳහා schemas. `parent_lesson_id` මඟින් Main Unit එකක් යටතේ
   Sub-lessons (Chapters & Sub-topics) ගොනු කර දැක්වීම සහ නිර්මාණය කිරීම කළමනාකරණය කරයි.
===============================================================================
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class SubjectCreate(BaseModel):
    """
    Request schema to create or update a curriculum subject.
    විෂයයක් අලුතින් ඇතුළත් කිරීමට හෝ යාවත්කාලීන කිරීමට යොදාගන්නා schema එක.
    """

    id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=255, description="Subject name in English")
    sinhala_name: Optional[str] = Field("", description="Subject name in Sinhala (e.g. 'ශුද්ධ ගණිතය')")
    code: str = Field(..., min_length=1, max_length=50, description="Unique uppercase code (e.g. 'PMAT')")
    order_index: int = Field(1, description="Display order sequence")
    description: Optional[str] = Field("", description="Overview notes or description")


class SubjectResponse(BaseModel):
    """
    Clean lightweight response schema for a curriculum subject.
    Client වෙත විෂය විස්තර ලබාදෙන සැහැල්ලු response schema එක.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    sinhala_name: Optional[str] = None
    code: str
    order_index: int
    description: Optional[str] = None


class LessonCreate(BaseModel):
    """
    Request schema to create or update a syllabus lesson or sub-lesson.
    ප්‍රධාන පාඩමක් හෝ උප-පාඩමක් නිර්මාණය කිරීමට යොදාගන්නා schema එක.
    """

    id: Optional[str] = Field(None, description="Optional custom ID (e.g. 'les_trig_01'). Auto-generated if omitted.")
    subject_id: str = Field(..., min_length=1, max_length=100, description="Parent subject ID (e.g. 'subj_pmat')")
    parent_lesson_id: Optional[str] = Field(
        None,
        description="Self-referencing parent lesson ID. Set to None for root units, or parent ID for sub-lessons.",
    )
    title: str = Field(..., min_length=1, max_length=255, description="Lesson title in English")
    sinhala_title: Optional[str] = Field("", description="Lesson title in Sinhala (ප්‍රධාන මාතෘකාව)")
    order_index: int = Field(1, description="Sort order among siblings (1, 2, 3...)")
    description: Optional[str] = Field("", description="Overview, objectives, or syllabus syllabus notes")


class LessonResponse(BaseModel):
    """
    Clean lightweight response schema for a syllabus lesson.
    පාඩම් විස්තර සහ ඒ යටතේ ඇති ප්‍රශ්න ප්‍රමාණයන් පෙන්වන response schema එක.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    subject_id: str
    parent_lesson_id: Optional[str] = Field(
        None,
        description="Parent lesson ID if this is a sub-lesson; None if top-level unit.",
    )
    subject_code: Optional[str] = None
    subject_name: Optional[str] = None
    title: str
    sinhala_title: Optional[str] = None
    order_index: int
    description: Optional[str] = None
    question_count: Optional[int] = 0
    premium_count: Optional[int] = 0
