from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class Strict(BaseModel):
    model_config=ConfigDict(extra="forbid")

class Credentials(Strict):
    username:str=Field(min_length=3,max_length=100,pattern=r"^[a-zA-Z0-9_.@-]+$")
    password:str=Field(min_length=10,max_length=128)
    name:str=Field(default="",max_length=40)

class Review(Strict):
    status:Literal["pending","confirmed","rejected"]
    version:int=Field(ge=1)
    note:str=Field(default="",max_length=500)

class TaskUpdate(Strict):
    status:Literal["pending","completed","skipped"]
    version:int=Field(ge=1)

class BatchReviewItem(Strict):
    id:str=Field(min_length=1,max_length=32)
    version:int=Field(ge=1)

class BatchReview(Strict):
    items:list[BatchReviewItem]=Field(min_length=1,max_length=200)

class Question(Strict):
    question:str=Field(min_length=1,max_length=1500)

class ExtractedFact(Strict):
    category:Literal["复诊","检查","用药","诊断","病理","治疗","其他"]
    quote:str=Field(min_length=1,max_length=1200)
    page:int=Field(ge=1)
    is_schedule:bool=False
    scheduled_date:str | None=None
    scheduled_time:str | None=None

class Extraction(Strict):
    facts:list[ExtractedFact]=Field(default_factory=list,max_length=150)

class Answer(Strict):
    answer:str=Field(min_length=1,max_length=5000)
    status:Literal["supported","insufficient_evidence","safety_escalation"]
    citations:list[str]=Field(default_factory=list)

class ROIRun(Strict):
    name:str=Field(default="筛查扩容方案",max_length=100)
    inputs:dict
    approval_ids:list[str]=Field(default_factory=list,max_length=20)
    sources:dict[str,str]=Field(default_factory=dict,max_length=30)
