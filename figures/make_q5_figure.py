"""Figure 7: the Q5 chain study at eight crossings (values are those of Table 16, 9 runs per cell).

    python figures/make_q5_figure.py      # writes figures/fig-q5-hops.pdf
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HOPS = list(range(9))
ARMS = ["CaveAgent", "Code→file", "Code→text", "JSON→text"]
# The same slots as Figure 6, so an arm keeps its colour across the two figures.
COLORS = ["#2a78d6", "#1baf7a", "#eb6834", "#7a5cc6"]
MARKERS = ["o", "s", "^", "D"]
DASHES = ["-", (0, (4, 1.5)), "-", (0, (1.2, 1.2))]
NUDGE = [0.012, 0.004, -0.004, -0.012]
# Fraction of the 9 runs whose object still matched the host's standard after each hop
# (hop 0 is the producer's object). From x5_table.py, "the object still right at each hop".
PANELS = [
    ("DeepSeek-V4 Flash", {
        "CaveAgent": [1, 1, 1, 1, 1, 1, 1, 1, 1],
        "Code→file": [1, .889, .778, .778, .778, .889, .889, .667, .667],
        "Code→text": [1, .889, .667, .556, .556, .556, .556, .556, .444],
        "JSON→text": [.778, .667, .333, .222, .222, .222, .222, .222, .333]}),
    ("Qwen3.8 Flash", {
        "CaveAgent": [1, 1, 1, 1, 1, 1, 1, 1, 1],
        "Code→file": [1, 1, 1, 1, 1, 1, 1, 1, 1],
        "Code→text": [1, .333, .333, .333, .333, .333, .333, .333, .556],
        "JSON→text": [.889, .111, .111, .222, .222, .222, .222, .222, .333]}),
    ("Qwen3-Coder (30B)", {
        "CaveAgent": [.556, .556, .556, .444, .444, .444, .444, .444, .444],
        "Code→file": [.333, .111, .111, .111, .111, .111, .111, .111, .111],
        "Code→text": [.667, 0, 0, 0, 0, 0, 0, 0, 0],
        "JSON→text": [.556, 0, 0, 0, 0, 0, 0, 0, 0]}),
]
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"

fig, axes = plt.subplots(1, 3, figsize=(7.0, 2.5), sharey=True)
for ax, (title, data) in zip(axes, PANELS):
    for arm, color, marker, dash, nudge in zip(ARMS, COLORS, MARKERS, DASHES, NUDGE):
        ax.plot(HOPS, [v + nudge for v in data[arm]], color=color, marker=marker, linestyle=dash,
                markersize=4, linewidth=1.6,
                markeredgecolor="white", markeredgewidth=0.6, label=arm, zorder=3)
    ax.set_xticks(HOPS, [str(h) for h in HOPS], fontsize=7.5, color=INK)
    ax.set_xlabel("Crossings", fontsize=8.5, color=INK)
    ax.set_title(title, fontsize=9, color=INK, pad=6)
    ax.set_ylim(-0.05, 1.07)
    ax.set_yticks([0, .25, .5, .75, 1], ["0", "0.25", "0.5", "0.75", "1"])
    ax.tick_params(axis="y", labelsize=7.5, colors=MUTED, length=0)
    ax.tick_params(axis="x", which="both", length=0)
    ax.yaxis.grid(True, color=GRID, linewidth=0.6, zorder=0)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
axes[0].set_ylabel("Object still correct", fontsize=8.5, color=INK)
handles, labels = axes[0].get_legend_handles_labels()
fig.legend(handles, labels, frameon=False, fontsize=8, ncol=4, loc="upper center",
           bbox_to_anchor=(0.5, 1.0), handlelength=2.4, columnspacing=1.6)
fig.tight_layout(rect=(0, 0, 1, 0.9))
fig.savefig(Path(__file__).parent / "fig-q5-hops.pdf")
