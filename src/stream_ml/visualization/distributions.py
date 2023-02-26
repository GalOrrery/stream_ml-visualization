"""Core library for stream membership likelihood, with ML."""

from __future__ import annotations

import itertools
from typing import TYPE_CHECKING, Any, cast

import numpy as np
from matplotlib import gridspec
from matplotlib import pyplot as plt
from matplotlib.patches import ConnectionPatch

from stream_ml.visualization.defaults import (
    COL_NAME_DEFAULTS,
    COORD_TO_YLABEL,
    YLABEL_DEFAULTS,
)
from stream_ml.visualization.utils.arg_decorators import make_tuple
from stream_ml.visualization.utils.plt_decorators import (
    add_savefig_option,
    with_tight_layout,
)

__all__: list[str] = []


if TYPE_CHECKING:
    from collections.abc import Mapping

    from astropy.table import QTable
    from astropy.units import Quantity
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure
    from numpy.typing import NDArray
    from streaam_ml.core.data import Data

    from stream_ml.core.typing import ArrayLike


########################################################################


def _connect_slices_to_top(
    fig: Figure,
    axes1: Axes,
    axes2: Axes,
    left: Quantity | NDArray[Any],
    right: Quantity | NDArray[Any],
) -> None:
    # Add edges to top plot
    axes1.axvline(left, color="tab:red", ls="--")
    axes1.axvline(right, color="tab:red", ls="--")

    # Add connection
    con = ConnectionPatch(
        xyA=(np.array(left), axes1.get_ylim()[0]),
        xyB=(0, 1),
        coordsA="data",
        coordsB="axes fraction",
        axesA=axes1,
        axesB=axes2,
        color="tab:red",
        ls="--",
        zorder=-200,
    )
    axes1.add_artist(con)

    con = ConnectionPatch(
        xyA=(np.array(right), axes1.get_ylim()[0]),
        xyB=(1, 1),
        coordsA="data",
        coordsB="axes fraction",
        axesA=axes1,
        axesB=axes2,
        color="tab:red",
        ls="--",
        zorder=-200,
    )
    axes1.add_artist(con)


def _plot_cooordinate_histogram_column(
    table: QTable | Data[ArrayLike],
    coords: tuple[str, ...],
    *,
    ylabels: Mapping[str, str],
    axes: NDArray[Axes],
    kwargs: dict[str, Any],
) -> None:
    """Plot coordinate histograms."""
    kwargs.setdefault("bins", 10)
    kwargs.setdefault("color", "gray")
    kwargs.setdefault("density", True)

    # Iterate over coordinates
    for row, cn in enumerate(coords):
        # Histogram
        axes[row].hist(table[cn].flatten(), **kwargs)

        axes[row].set_xlabel(
            f"{ylabels.get(cn, cn)}"
            + (f" [{axes[row].get_xlabel()}]" if axes[row].get_xlabel() else "")
        )

        # Settings
        axes[row].grid()
        axes[row].set_axisbelow(True)  # gridlines behind data
        axes[row].set_ylabel("fraction")


# TODO: Add option for CMD plot
# TODO: chang "coords" to "coord"
@add_savefig_option
@make_tuple("coords")
def plot_coordinate_histograms_in_phi1_slices(
    data: QTable | Data[ArrayLike],
    /,
    phi1_edges: tuple[Quantity | NDArray[Any], ...],
    *,
    coords: tuple[str, ...] = COL_NAME_DEFAULTS,
    ylabels: Mapping[str, str] = YLABEL_DEFAULTS,
    **kwargs: Any,
) -> Figure:
    r"""Bin plot.

    Parameters
    ----------
    data : `~astropy.table.QTable` or `~stream_ml.core.data.Data`
        Data with the column names ``coords``. Must have at least ``phi1``
        and ``phi2``.
    phi1_edges : tuple[Quantity, ...]
        Tuple of phi1 bounds.
    coords : tuple[str, ...], optional keyword-only
        Tuple of coordinate names to plot.

    ylabels : dict[str, str], optional keyword-only
        Dictionary of ylabels for the columns, by default:

        .. code-block:: python
            {
                "phi1": f"$\\phi_1$",
                "phi2": r"$\\phi_2$",
                "parallax": r"$\varpi$",
                "pm_phi1_cosphi2_unrefl": r"$\\mu_{phi_1}^*$",
                "pm_phi2_unrefl": r"$\\mu_{phi_2}$",
            }

    **kwargs : Any
        Keyword arguments to pass to stuff.

        - figure : dict[str, Any]

    Returns
    -------
    `matplotlib.figure.Figure`
        The figure.
    """
    # -----------------------------------------------------
    # Setup

    # # Connecting line between top plot slice edges and the histograms
    # con_y_top = table["phi2"].min().value
    # Number of rows per column
    nrows = len(coords)
    ncols = len(phi1_edges) - 1

    # Make the plot and GridSpec, with 2 rows and one column per phi1 slice
    fig = plt.figure(**kwargs.pop("figure", {"figsize": (20, 20)}))
    gs0 = gridspec.GridSpec(
        2,
        len(phi1_edges) - 1,
        figure=fig,
        height_ratios=(1, nrows),
        wspace=0.02,
        hspace=0.08,
    )

    # -----------------------------------------------------
    # Phi1-Phi2 top plot

    ax0 = fig.add_subplot(gs0[0, :])
    ax0.scatter(data["phi1"].flatten(), data["phi2"].flatten(), s=1, c="black")
    ax0.set_xlabel(
        r"$\phi_1$" + (rf" [{ax0.get_xlabel()}]" if ax0.get_xlabel() else ""),
        fontsize=15,
    )
    ax0.set_ylabel(
        r"$\phi_2$" + (rf" [{ax0.get_ylabel()}]" if ax0.get_ylabel() else ""),
        fontsize=15,
    )

    # -----------------------------------------------------
    # Phi1-slice column histograms

    # Make axes array
    axes = np.empty((nrows, len(phi1_edges) - 1), dtype=object)
    # Iterate over columns
    for col in range(len(phi1_edges) - 1):
        # Make sub-gridspec column of sub-axes
        gsi = gs0[1:, col].subgridspec(nrows, 1, hspace=0.3)
        # Add subplot axes to array
        for row in range(len(coords)):
            axes[row, col] = fig.add_subplot(gsi[row], sharey=axes[row, 0])

    # Iterate over phi1 slices, making a column of histograms for each component
    for col, (left, right) in enumerate(itertools.pairwise(phi1_edges)):
        # Per-coordinate plot
        data_slice = cast(
            "QTable | Data[ArrayLike]",
            data[(data["phi1"].flatten() >= left) & (data["phi1"].flatten() < right)],
        )

        _plot_cooordinate_histogram_column(
            data_slice, coords, ylabels=ylabels, axes=axes[:, col], kwargs=kwargs
        )

        # Connect coordinate plots to top plot
        _connect_slices_to_top(
            fig, ax0, fig.axes[1 + col * nrows], left=left, right=right
        )

    # Adjust y-axis labels for all but the first column
    for row, col in itertools.product(range(nrows), range(1, ncols)):
        axes[row, col].tick_params(axis="y", which="both", left=False, labelleft=False)
        axes[row, col].set_ylabel("")

    return fig


##############################################################################


@add_savefig_option
@with_tight_layout
@make_tuple("coords")
def coord_panels(
    data: QTable | Data[ArrayLike],
    /,
    coords: tuple[str, ...],
    *,
    use_hist: bool = False,
    **kwargs: Any,
) -> Figure:
    """Plot a grid of coordinate panels.

    Parameters
    ----------
    data : `~astropy.table.QTable` or `~stream_ml.core.data.Data`
        Data with the column names ``coords``. Must have at least ``phi1``
        and ``phi2``.
    coords : tuple[str, ...]
        Tuple of coordinate names to plot.
    use_hist : bool, optional keyword-only
        Whether to use a histogram or scatter plot, by default `False`.
    **kwargs : Any
        Keyword arguments to pass to stuff.

    Returns
    -------
    `matplotlib.figure.Figure`
        The figure.
    """
    fig, axs = plt.subplots(1, len(coords), figsize=(4 * len(coords), 4))

    for i, c in enumerate(coords):
        ckw = kwargs.pop(c, {})
        ckw.setdefault("rasterize", True)

        if use_hist:
            ckw.setdefault("density", True)
            ckw.setdefault("bins", 100)
            axs[i].hist2d(data["phi1"].flatten(), data[c].flatten(), **ckw)
        else:
            ckw.setdefault("s", 1)
            axs[i].scatter(data["phi1"].flatten(), data[c].flatten(), **ckw)

        axs[i].set_xlabel(r"$\phi_1$")
        axs[i].set_ylabel(COORD_TO_YLABEL.get(c, c))

    return fig