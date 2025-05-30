"""Pydantic schemas for the datawarehouse module."""

from typing import Optional, List
from pydantic import BaseModel, ConfigDict


# Deal Schemas
class DealBase(BaseModel):
    dl_nbr: int
    issr_cde: str
    cdi_file_nme: str
    CDB_cdi_file_nme: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class DealCreate(DealBase):
    pass


class DealRead(DealBase):
    pass


class DealUpdate(BaseModel):
    issr_cde: Optional[str] = None
    cdi_file_nme: Optional[str] = None
    CDB_cdi_file_nme: Optional[str] = None
    model_config = ConfigDict(from_attributes=True, extra="forbid")


# Tranche Schemas
class TrancheBase(BaseModel):
    dl_nbr: int
    tr_id: str
    tr_cusip_id: str
    model_config = ConfigDict(from_attributes=True, extra="forbid")


class TrancheCreate(TrancheBase):
    pass


class TrancheRead(TrancheBase):
    pass


class TrancheUpdate(BaseModel):
    dl_nbr: Optional[int] = None
    tr_id: Optional[str] = None
    tr_cusip_id: Optional[str] = None
    model_config = ConfigDict(from_attributes=True, extra="forbid")


# TrancheBal Schemas
class TrancheBalBase(BaseModel):
    dl_nbr: int
    tr_id: str
    cycle_cde: int
    tr_end_bal_amt: float
    tr_prin_rel_ls_amt: float
    tr_pass_thru_rte: float
    tr_accrl_days: int
    tr_int_dstrb_amt: float
    tr_prin_dstrb_amt: float
    tr_int_accrl_amt: float
    tr_int_shtfl_amt: float
    model_config = ConfigDict(from_attributes=True, extra="forbid")


class TrancheBalCreate(TrancheBalBase):
    pass


class TrancheBalRead(TrancheBalBase):
    pass


class TrancheBalUpdate(BaseModel):
    dl_nbr: Optional[int] = None
    tr_id: Optional[str] = None
    cycle_cde: Optional[int] = None
    tr_end_bal_amt: Optional[float] = None
    tr_prin_rel_ls_amt: Optional[float] = None
    tr_pass_thru_rte: Optional[float] = None
    tr_accrl_days: Optional[int] = None
    tr_int_dstrb_amt: Optional[float] = None
    tr_prin_dstrb_amt: Optional[float] = None
    tr_int_accrl_amt: Optional[float] = None
    tr_int_shtfl_amt: Optional[float] = None
    model_config = ConfigDict(from_attributes=True, extra="forbid")


# Combined schemas
class DealWithTranches(DealRead):
    tranches: List[TrancheRead] = []


class TrancheWithDeal(TrancheRead):
    deal: DealRead


class TrancheWithBals(TrancheRead):
    tranchebals: List[TrancheBalRead] = []


class TrancheBalWithTranche(TrancheBalRead):
    tranche: TrancheRead
