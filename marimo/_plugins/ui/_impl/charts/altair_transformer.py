# Copyright 2024 Marimo. All rights reserved.
from __future__ import annotations

import base64
from typing import Any, Literal, TypedDict, Union

import narwhals.stable.v1 as nw
from narwhals.typing import IntoDataFrame

import marimo._output.data.data as mo_data
from marimo import _loggers
from marimo._dependencies.dependencies import DependencyManager
from marimo._plugins.ui._impl.tables.utils import (
    get_table_manager,
    get_table_manager_or_none,
)
from marimo._utils.data_uri import build_data_url

LOGGER = _loggers.marimo_logger()

Data = Union[dict[Any, Any], IntoDataFrame, nw.DataFrame[Any]]
_DataType = Union[dict[Any, Any], IntoDataFrame, nw.DataFrame[Any]]


class _JsonFormatDict(TypedDict):
    type: Literal["json"]


class _CsvFormatDict(TypedDict):
    type: Literal["csv"]


class _ArrowFormatDict(TypedDict):
    type: Literal["arrow"]


class _TransformResult(TypedDict):
    url: str
    format: Union[_CsvFormatDict, _JsonFormatDict, _ArrowFormatDict]


def _to_marimo_json(data: Data, **kwargs: Any) -> _TransformResult:
    """
    Custom implementation of altair.utils.data.to_json that
    returns a VirtualFile URL instead of writing to disk.
    """
    del kwargs
    data_json = _data_to_json_string(data)
    virtual_file = mo_data.json(data_json.encode("utf-8"))
    return {"url": virtual_file.url, "format": {"type": "json"}}


def _to_marimo_csv(data: Data, **kwargs: Any) -> _TransformResult:
    """
    Custom implementation of altair.utils.data.to_csv that
    returns a VirtualFile URL instead of writing to disk.
    """
    del kwargs
    data_csv = _data_to_csv_string(data)
    virtual_file = mo_data.csv(data_csv.encode("utf-8"))
    return {"url": virtual_file.url, "format": {"type": "csv"}}


def _to_marimo_arrow(data: Data, **kwargs: Any) -> _TransformResult:
    """
    Convert data to arrow format, falls back to CSV if not possible.
    """
    del kwargs
    try:
        data_arrow = get_table_manager(data).to_arrow_ipc()
    except NotImplementedError:
        return _to_marimo_csv(data)
    except Exception as e:
        LOGGER.warning(
            f"Failed to convert data to arrow format, falling back to CSV: {e}"
        )
        return _to_marimo_csv(data)
    virtual_file = mo_data.arrow(data_arrow)
    return {"url": virtual_file.url, "format": {"type": "arrow"}}


def _to_marimo_inline_csv(data: Data, **kwargs: Any) -> _TransformResult:
    """
    Custom implementation of altair.utils.data.to_csv that
    inlines the CSV data in the URL.
    """
    del kwargs
    data_csv = _data_to_csv_string(data)
    url = build_data_url(
        mimetype="text/csv",
        data=base64.b64encode(data_csv.encode("utf-8")),
    )
    return {"url": url, "format": {"type": "csv"}}


# Copied from https://github.com/altair-viz/altair/blob/0ca83784e2455f2b84d0f6d789af2abbe8814348/altair/utils/data.py#L263C1-L288C10
def _data_to_json_string(data: _DataType) -> str:
    """Return a JSON string representation of the input data"""
    import altair as alt
    import pandas as pd

    if isinstance(data, pd.DataFrame):
        if "sanitize_pandas_dataframe" in dir(alt.utils):
            sanitized = alt.utils.sanitize_pandas_dataframe(data)  # type: ignore[attr-defined]
        elif "sanitize_dataframe" in dir(alt.utils):
            sanitized = alt.utils.sanitize_dataframe(data)  # type: ignore[attr-defined]
        else:
            raise NotImplementedError(
                "No sanitize_pandas_dataframe or "
                "sanitize_dataframe in altair.utils."
            )
        as_str = sanitized.to_json(orient="records", double_precision=15)
        assert isinstance(as_str, str)
        return as_str

    if DependencyManager.narwhals.has():
        import narwhals

        if isinstance(data, narwhals.DataFrame):
            return _data_to_json_string(narwhals.to_native(data))

    tm = get_table_manager_or_none(data)
    if tm:
        return tm.to_json().decode("utf-8")

    raise NotImplementedError(
        "to_marimo_json only works with data expressed as a DataFrame "
        + f" or as a dict. Got {type(data)}"
    )


def _data_to_csv_string(data: _DataType) -> str:
    """Return a CSV string representation of the input data"""
    return get_table_manager(data).to_csv().decode("utf-8")


def register_transformers() -> None:
    """
    Register custom data transformers for Altair.

    We register a CSV transformer and a JSON transformer. These
    transformers return a VirtualFile URL instead of writing to disk,
    which is the default behavior of Altair's to_csv and to_json.

    By registering these transformers, we are able to use
    much larger datasets.
    """
    import altair as alt

    # We keep the previous options, in case the user has set them
    # we don't want to override them.

    # Default to CSV. Due to the columnar nature of CSV, it is more efficient
    # than JSON for large datasets (~80% smaller file size).
    alt.data_transformers.register("marimo", _to_marimo_csv)  # type: ignore[arg-type]
    alt.data_transformers.register("marimo_inline_csv", _to_marimo_inline_csv)  # type: ignore[arg-type]
    alt.data_transformers.register("marimo_json", _to_marimo_json)  # type: ignore[arg-type]
    alt.data_transformers.register("marimo_csv", _to_marimo_csv)  # type: ignore[arg-type]
    alt.data_transformers.register("marimo_arrow", _to_marimo_arrow)  # type: ignore[arg-type]
