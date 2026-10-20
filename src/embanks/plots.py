"""Chart style shared by every figure: hairline axes, ink-colored text, one legend under the subtitle."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

INK, INK2, MUTED, GRID, AXIS, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"

def style(ax):
    """Recessive hairline grid and axes, ink-colored text."""
    ax.set_facecolor(SURFACE)
    ax.grid(color=GRID, linewidth=0.6, linestyle="-")
    ax.set_axisbelow(True)
    for side, spine in ax.spines.items():
        spine.set_visible(side in ("left", "bottom"))
        spine.set_color(AXIS)
    ax.tick_params(colors=MUTED, labelcolor=INK2, labelsize=8)

def figure(title, subtitle, nrows, ncols, size):
    """A figure on the chart surface with a bold title and a secondary-ink subtitle."""
    fig, axes = plt.subplots(nrows, ncols, figsize=size, squeeze=False, facecolor=SURFACE)
    fig.text(0.01, 0.985, title, ha="left", va="top", color=INK, fontsize=12, fontweight="bold")
    fig.text(0.01, 0.985 - 0.32 / size[1], subtitle, ha="left", va="top", color=INK2, fontsize=9)
    return fig, axes

def finish(fig, ax, path, size_y, top, ncol=2):
    """Lay out the plots below `top`, add one figure-level legend under the subtitle, save."""
    fig.tight_layout(rect=(0, 0, 1, top))
    handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper left", bbox_to_anchor=(0.01, 0.985 - 0.62 / size_y), ncol=ncol,
               frameon=False, fontsize=8.5, labelcolor=INK2, handletextpad=0.4, columnspacing=1.6)
    fig.savefig(path, dpi=160, facecolor=SURFACE)
    plt.close(fig)
