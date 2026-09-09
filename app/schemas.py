"""Pydantic schemas for inference API (drd.md §6)."""
from typing import List, Optional
from pydantic import BaseModel


class FlowInput(BaseModel):
    duration: Optional[float] = 0
    protocol_type: Optional[str] = "tcp"
    service: Optional[str] = "http"
    flag: Optional[str] = "SF"
    src_bytes: Optional[float] = 0
    dst_bytes: Optional[float] = 0
    land: Optional[int] = 0
    wrong_fragment: Optional[int] = 0
    urgent: Optional[int] = 0
    hot: Optional[int] = 0
    num_failed_logins: Optional[int] = 0
    logged_in: Optional[int] = 0
    num_compromised: Optional[int] = 0
    root_shell: Optional[int] = 0
    su_attempted: Optional[int] = 0
    num_root: Optional[int] = 0
    num_file_creations: Optional[int] = 0
    num_shells: Optional[int] = 0
    num_access_files: Optional[int] = 0
    num_outbound_cmds: Optional[int] = 0
    is_host_login: Optional[int] = 0
    is_guest_login: Optional[int] = 0
    count: Optional[float] = 0
    srv_count: Optional[float] = 0
    serror_rate: Optional[float] = 0
    srv_serror_rate: Optional[float] = 0
    rerror_rate: Optional[float] = 0
    srv_rerror_rate: Optional[float] = 0
    same_srv_rate: Optional[float] = 0
    diff_srv_rate: Optional[float] = 0
    srv_diff_host_rate: Optional[float] = 0
    dst_host_count: Optional[float] = 0
    dst_host_srv_count: Optional[float] = 0
    dst_host_same_srv_rate: Optional[float] = 0
    dst_host_diff_srv_rate: Optional[float] = 0
    dst_host_same_src_port_rate: Optional[float] = 0
    dst_host_srv_diff_host_rate: Optional[float] = 0
    dst_host_serror_rate: Optional[float] = 0
    dst_host_srv_serror_rate: Optional[float] = 0
    dst_host_rerror_rate: Optional[float] = 0
    dst_host_srv_rerror_rate: Optional[float] = 0

    class Config:
        extra = "ignore"


class BatchInput(BaseModel):
    rows: List[FlowInput]

    class Config:
        extra = "ignore"
