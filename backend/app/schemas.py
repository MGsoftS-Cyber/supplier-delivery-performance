"""Bounded delivery and supplier-performance input contracts."""

import re
from datetime import date
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Credentials(StrictModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=128)

    @field_validator("password", mode="before")
    @classmethod
    def preserve_password(cls, value):
        # Password whitespace is meaningful; reject it at the boundaries instead of silently changing it.
        if isinstance(value, str) and value != value.strip():
            raise ValueError("Password must not start or end with whitespace.")
        return value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value):
        value = value.lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("Enter a valid email address.")
        return value


class StoreInput(StrictModel):
    name: str = Field(min_length=1, max_length=120)
    unit: str = Field(default="unit", min_length=1, max_length=20)


class DeliveryInput(StrictModel):
    supplier_id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    supplier_name: str = Field(min_length=1, max_length=120)
    delivery_id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    ordered_date: date
    promised_date: date
    actual_date: date | None = None
    ordered_qty: int = Field(gt=0, le=1000000000, strict=True)
    received_qty: int = Field(ge=0, le=1000000000, strict=True)
    defect_qty: int = Field(default=0, ge=0, le=1000000000, strict=True)
    returned_qty: int = Field(default=0, ge=0, le=1000000000, strict=True)

    @model_validator(mode="after")
    def consistent(self):
        if self.ordered_date > date.today() or self.promised_date < self.ordered_date:
            raise ValueError("Order must not be future; promise cannot precede order.")
        if self.actual_date and (self.actual_date < self.ordered_date or self.actual_date > date.today()):
            raise ValueError("Actual receipt must be between order date and today.")
        if self.actual_date is None and (self.received_qty or self.defect_qty or self.returned_qty):
            raise ValueError("Pending deliveries have no received, defective or returned units.")
        if self.actual_date is not None and self.received_qty == 0:
            raise ValueError("An actual receipt date requires a positive received quantity.")
        if self.defect_qty + self.returned_qty > self.received_qty:
            raise ValueError("Defects and returns are disjoint quantities and cannot exceed received units.")
        return self


class DatasetInput(StrictModel):
    source: str = Field(min_length=1, max_length=200)
    coverage_end: date
    deliveries: list[DeliveryInput] = Field(min_length=1, max_length=10000)

    @field_validator("coverage_end")
    @classmethod
    def not_future(cls, value):
        if value > date.today():
            raise ValueError("Coverage end cannot be in the future.")
        return value


class CsvInput(StrictModel):
    csv_text: str = Field(min_length=1, max_length=2000000)


class PerformanceInput(StrictModel):
    dataset_id: str
    scenario_name: str = Field(default="Supplier review", min_length=1, max_length=120)
    grace_days: int = Field(default=0, ge=0, le=30, strict=True)
    minimum_due: int = Field(default=3, ge=1, le=100, strict=True)


class ComparisonInput(StrictModel):
    analysis_ids: list[str] = Field(min_length=2, max_length=10)

    @field_validator("analysis_ids")
    @classmethod
    def unique_ids(cls, values):
        if len(set(values)) != len(values):
            raise ValueError("Select distinct analyses.")
        return values
