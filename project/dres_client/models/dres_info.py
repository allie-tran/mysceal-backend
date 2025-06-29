from collections.abc import Mapping
from typing import Any, TypeVar, Union

from attrs import define as _attrs_define

from ..types import UNSET, Unset

T = TypeVar("T", bound="DresInfo")


@_attrs_define
class DresInfo:
    """
    Attributes:
        version (str):
        start_time (int):
        uptime (int):
        os (Union[Unset, str]):
        jvm (Union[Unset, str]):
        args (Union[Unset, str]):
        cores (Union[Unset, int]):
        free_memory (Union[Unset, int]):
        total_memory (Union[Unset, int]):
        load (Union[Unset, float]):
        available_sever_threads (Union[Unset, int]):
    """

    version: str
    start_time: int
    uptime: int
    os: Union[Unset, str] = UNSET
    jvm: Union[Unset, str] = UNSET
    args: Union[Unset, str] = UNSET
    cores: Union[Unset, int] = UNSET
    free_memory: Union[Unset, int] = UNSET
    total_memory: Union[Unset, int] = UNSET
    load: Union[Unset, float] = UNSET
    available_sever_threads: Union[Unset, int] = UNSET

    def to_dict(self) -> dict[str, Any]:
        version = self.version

        start_time = self.start_time

        uptime = self.uptime

        os = self.os

        jvm = self.jvm

        args = self.args

        cores = self.cores

        free_memory = self.free_memory

        total_memory = self.total_memory

        load = self.load

        available_sever_threads = self.available_sever_threads

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "version": version,
                "startTime": start_time,
                "uptime": uptime,
            }
        )
        if os is not UNSET:
            field_dict["os"] = os
        if jvm is not UNSET:
            field_dict["jvm"] = jvm
        if args is not UNSET:
            field_dict["args"] = args
        if cores is not UNSET:
            field_dict["cores"] = cores
        if free_memory is not UNSET:
            field_dict["freeMemory"] = free_memory
        if total_memory is not UNSET:
            field_dict["totalMemory"] = total_memory
        if load is not UNSET:
            field_dict["load"] = load
        if available_sever_threads is not UNSET:
            field_dict["availableSeverThreads"] = available_sever_threads

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        version = d.pop("version")

        start_time = d.pop("startTime")

        uptime = d.pop("uptime")

        os = d.pop("os", UNSET)

        jvm = d.pop("jvm", UNSET)

        args = d.pop("args", UNSET)

        cores = d.pop("cores", UNSET)

        free_memory = d.pop("freeMemory", UNSET)

        total_memory = d.pop("totalMemory", UNSET)

        load = d.pop("load", UNSET)

        available_sever_threads = d.pop("availableSeverThreads", UNSET)

        dres_info = cls(
            version=version,
            start_time=start_time,
            uptime=uptime,
            os=os,
            jvm=jvm,
            args=args,
            cores=cores,
            free_memory=free_memory,
            total_memory=total_memory,
            load=load,
            available_sever_threads=available_sever_threads,
        )

        return dres_info
