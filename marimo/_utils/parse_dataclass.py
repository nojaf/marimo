# Copyright 2024 Marimo. All rights reserved.
from __future__ import annotations

import dataclasses
import datetime
import json
import sys
from enum import Enum
from typing import (
    Any,
    Literal,
    Optional,
    TypeVar,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

# Import NotRequired from typing_extensions for Python < 3.11
if sys.version_info < (3, 11):
    from typing_extensions import NotRequired
else:
    from typing import NotRequired

T = TypeVar("T")


def to_snake(string: str) -> str:
    # basic conversion of javascript camel case to snake
    # does not handle contiguous caps
    return "".join(
        ["_" + i.lower() if i.isupper() else i for i in string]
    ).lstrip("_")


class DataclassParser:
    def __init__(self, allow_unknown_keys: bool = False):
        self.allow_unknown_keys = allow_unknown_keys

    def _build_value(self, value: Any, cls: type[T]) -> T:
        # Handle basic types
        if cls is float and isinstance(value, (int, float)):
            return float(value)  # type: ignore[return-value]
        if cls is int and isinstance(value, int):
            return int(value)  # type: ignore[return-value]
        if cls is str and isinstance(value, str):
            return str(value)  # type: ignore[return-value]
        if cls is bool and isinstance(value, bool):
            return bool(value)  # type: ignore[return-value]
        if cls is bytes and isinstance(value, bytes):
            return bytes(value)  # type: ignore[return-value]

        # Handle date and datetime types
        if cls is datetime.date and isinstance(value, str):
            return datetime.datetime.fromisoformat(value).date()  # type: ignore[return-value]
        if cls is datetime.datetime and isinstance(value, str):
            return datetime.datetime.fromisoformat(value)  # type: ignore[return-value]

        if cls is Any:  # type: ignore[comparison-overlap]
            return value  # type: ignore[no-any-return]

        # Already a dataclass
        if dataclasses.is_dataclass(value):
            return value  # type: ignore[return-value]

        # Handle container types
        # origin_cls is not None if cls is a container (such as list,
        # tuple, set, ...)
        origin_cls = get_origin(cls)

        # Handle NewType - check if cls has __supertype__ attribute
        if hasattr(cls, "__supertype__"):
            # NewType returns its argument at runtime, but we need to validate
            # against the supertype
            supertype = cls.__supertype__  # type: ignore
            return cls(self._build_value(value, supertype))  # type: ignore

        # Handle NotRequired type
        if origin_cls is NotRequired:
            (arg_type,) = get_args(cls)
            if value is None:
                return None  # type: ignore[return-value]
            return self._build_value(value, arg_type)  # type: ignore[no-any-return]

        if origin_cls is Optional:
            (arg_type,) = get_args(cls)
            if value is None:
                return None  # type: ignore[return-value]
            else:
                return self._build_value(value, arg_type)  # type: ignore # noqa: E501
        elif origin_cls in (list, set) and isinstance(
            value, (tuple, list, set)
        ):
            (arg_type,) = get_args(cls)
            return origin_cls(self._build_value(v, arg_type) for v in value)  # type: ignore # noqa: E501
        elif origin_cls is tuple and isinstance(value, (tuple, list)):
            arg_types = get_args(cls)
            if len(arg_types) == 2 and isinstance(
                arg_types[1], type(Ellipsis)
            ):
                return origin_cls(  # type: ignore
                    self._build_value(v, arg_types[0]) for v in value
                )
            else:
                return origin_cls(  # type: ignore # noqa: E501
                    self._build_value(v, t) for v, t in zip(value, arg_types)
                )
        elif origin_cls is dict and isinstance(value, dict):
            key_type, value_type = get_args(cls)
            return origin_cls(  # type: ignore[no-any-return]
                **{
                    self._build_value(k, key_type): self._build_value(
                        v, value_type
                    )
                    for k, v in value.items()
                }
            )
        elif origin_cls == Union:
            arg_types = get_args(cls)
            for arg_type in arg_types:
                try:
                    return self._build_value(value, arg_type)  # type: ignore # noqa: E501
                # catch expected exceptions when conversion fails
                except (TypeError, ValueError):
                    continue
                except:
                    raise
            raise ValueError(
                f"Value '{value}' does not fit any type of the union"
            )
        elif origin_cls is Literal:
            # if its a single Literal of an enum, we can just return the enum
            arg_types = get_args(cls)
            first_arg_type = arg_types[0]
            if (
                len(arg_types) == 1
                and isinstance(first_arg_type, Enum)
                and first_arg_type.value == value
            ):
                return first_arg_type  # type: ignore[return-value]
            if value not in arg_types:
                raise ValueError(
                    f"Value '{value}' does not fit any type of the literal"
                )
            return value  # type: ignore[no-any-return]
        elif type(cls) is type(Enum) and issubclass(cls, Enum):
            return cls(value)  # type: ignore[return-value]
        elif dataclasses.is_dataclass(cls):
            return self.build_dataclass(value, cls)  # type: ignore[return-value]

        try:
            if isinstance(value, cls):
                return value  # type: ignore[no-any-return]
        except TypeError:
            pass

        raise ValueError(f"Value '{value}' does not fit '{cls}'")

    def build_dataclass(self, values: dict[Any, Any], cls: type[T]) -> T:
        """Returns instance of dataclass [cls] instantiated from [values]."""

        if not isinstance(values, dict):
            raise ValueError(
                "value passed to build_dataclass needs to be a dictionary"
            )

        types = get_type_hints(cls)

        snake_cased_values = {
            to_snake(k): v for k, v in values.items() if not k.startswith("_")
        }
        if (
            not self.allow_unknown_keys
            and not snake_cased_values.keys() <= types.keys()
        ):
            unknown_keys = snake_cased_values.keys() - types.keys()
            raise ValueError(
                f"values in build_dataclass do not match arguments "
                f"for constructor. Unknown keys: {unknown_keys}. "
                f"Expected keys: {types.keys()}"
            )

        transformed = {
            k: self._build_value(v, types[k])
            for k, v in snake_cased_values.items()
            if k in types
        }

        return cls(**transformed)


def parse_raw(
    message: Union[bytes, dict[Any, Any]],
    cls: type[T],
    allow_unknown_keys: bool = False,
) -> T:
    """Utility to parse a message as JSON, and instantiate into supplied type.

    Args:
        message: The message to parse
        cls: The type to instantiate. Must be a dataclass.
        allow_unknown_keys: Whether to allow unknown keys in the message.

    Returns:
        An instance of the supplied dataclass type.

    Notes:
        Supported collection types in the dataclass:
        - List, Tuple, Set, Dict
        - for Python 3.8 compatibility, must use collection types from
          the typing module (e.g., `typing.List[int]` instead of `list[int]`)

        Transforms all fields in the parsed JSON from camel case to snake case.
    """
    # If it is a dict, it is already parsed and we can just build the
    # dataclass.
    if isinstance(message, dict):
        return DataclassParser(allow_unknown_keys).build_dataclass(
            message, cls
        )
    parsed = json.loads(message)
    return DataclassParser(allow_unknown_keys).build_dataclass(parsed, cls)
