# Copyright 2024 Marimo. All rights reserved.
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta  # noqa: TCH003
from decimal import Decimal
from typing import Any, List, Literal, Optional, Union

from marimo._types.ids import VariableName

DataType = Literal[
    "string",
    "boolean",
    "integer",
    "number",
    "date",
    "datetime",
    "time",
    "unknown",
]
# This is the data type based on the source library
# e.g. polars, pandas, numpy, etc.
ExternalDataType = str


@dataclass
class DataTableColumn:
    """
    Represents a column in a data table.

    Attributes:
        name (str): The name of the column.
        type (DataType): The data type of the column.
    """

    name: str
    type: DataType
    external_type: ExternalDataType
    sample_values: List[Any]


DataTableSource = Literal["local", "duckdb", "connection"]


@dataclass
class DataTable:
    """
    Represents a data table.

    Attributes:
        source (str): The source of the data table.
        name (str): The name of the data table.
        num_rows (Optional[int]): The number of rows in the data table.
        num_columns (Optional[int]): The number of columns in the data table.
        variable_name (Optional[VariableName]): The variable name associated with
        the data table.
        columns (List[DataTableColumn]): The list of columns in the data table.
        engine (Optional[VariableName]): The engine associated with the data table.
    """

    source_type: DataTableSource
    source: str
    name: str
    num_rows: Optional[int]
    num_columns: Optional[int]
    variable_name: Optional[VariableName]
    columns: List[DataTableColumn]
    engine: Optional[VariableName] = None


NumericLiteral = Union[int, float, Decimal]
TemporalLiteral = Union[date, time, datetime, timedelta]
NonNestedLiteral = Union[NumericLiteral, TemporalLiteral, str, bool, bytes]


@dataclass
class ColumnSummary:
    """
    Represents a summary of a column in a data table.

    """

    total: Optional[int] = None
    nulls: Optional[int] = None
    unique: Optional[int] = None
    min: Optional[NonNestedLiteral] = None
    max: Optional[NonNestedLiteral] = None
    mean: Optional[NonNestedLiteral] = None
    median: Optional[NonNestedLiteral] = None
    std: Optional[NonNestedLiteral] = None
    true: Optional[int] = None
    false: Optional[int] = None
    p5: Optional[NonNestedLiteral] = None
    p25: Optional[NonNestedLiteral] = None
    # p50 is the median
    p75: Optional[NonNestedLiteral] = None
    p95: Optional[NonNestedLiteral] = None


@dataclass
class DataSourceConnection:
    """
    Represents a data source connection.

    Attributes:
        source (str): The source of the data source connection. E.g 'postgres'.
        dialect (str): The dialect of the data source connection. E.g 'postgresql'.
        name (str): The name of the data source connection. E.g 'engine'.
        display_name (str): The display name of the data source connection. E.g 'PostgresQL (engine)'.
    """

    source: str
    dialect: str
    name: str
    display_name: str
