from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class MonitorCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    url: HttpUrl
    monitoring_interval: int = Field(default=300, ge=30, le=86400)
    enabled: bool = True

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Name must contain at least 2 non-space characters.")
        return value


class MonitorUpdate(MonitorCreate):
    pass


class CheckOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    monitored_api_id: int
    checked_at: datetime
    status: str
    http_status_code: int | None
    response_time_ms: float | None
    error_message: str | None


class IncidentOut(CheckOut):
    monitor_name: str


class MonitorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    url: str
    monitoring_interval: int
    enabled: bool
    latest_status: str | None
    created_at: datetime
    updated_at: datetime
    # Most recent saved check, or null if the monitor has never been checked.
    last_check: CheckOut | None = None
