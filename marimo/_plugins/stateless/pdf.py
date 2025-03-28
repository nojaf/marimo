# Copyright 2024 Marimo. All rights reserved.
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, Union

import marimo._output.data.data as mo_data
from marimo._output.builder import h
from marimo._output.hypertext import Html
from marimo._output.rich_help import mddoc
from marimo._output.utils import create_style

if TYPE_CHECKING:
    import io


@mddoc
def pdf(
    src: Union[Path, str, io.IOBase],
    initial_page: Optional[int] = None,
    width: Optional[Union[int, str]] = "100%",
    height: Optional[Union[int, str]] = "70vh",  # arbitrary, but good default
    style: Optional[dict[str, Any]] = None,
) -> Html:
    """Render a PDF.

    This currently uses the native browser PDF viewer,
    but may be replaced with a custom viewer.

    Example:
        ```python3
        # from a URL
        mo.pdf(
            src="https://arxiv.org/pdf/2104.00282.pdf",
            width="100%",
            height="50vh",
        )

        # from a local file
        from pathlib import Path

        mo.pdf(src=Path("paper.pdf"))
        ```

    Args:
        src: the URL of the pdf, a file-like object, or a pathlib.Path object
        initial_page: the page to open the pdf to.
            only works if `src` is a URL
        width: the width of the pdf
        height: the height of the pdf. for a percentage
            of the user's viewport, use a string like `"50vh"`
        style: a dictionary of CSS styles to apply to the pdf

    Returns:
        `Html` object
    """
    if isinstance(src, str):
        resolved_src = src
    elif isinstance(src, Path):
        resolved_src = mo_data.pdf(src.read_bytes()).url
    else:
        resolved_src = mo_data.pdf(src.read()).url

    if initial_page is not None and isinstance(src, str):
        # FitV is "fit to vertical"
        resolved_src += f"#page={initial_page}&view=FitV"
    styles = create_style(
        {
            "border-radius": "4px",
            "width": width,
            "height": height,
            **(style or {}),
        }
    )
    return Html(
        h.iframe(
            src=resolved_src,
            style=styles,
        )
    )
