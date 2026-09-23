"""Figure 6: the Q4 controlled study (values are those of Table 12, success over 15 runs per cell).

    python figures/make_q4_figure.py      # writes figures/fig-q4-cliff.pdf
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROWS = [10, 100, 250, 500, 1000, 5000]
ARMS = ["CaveAgent", "Code→file", "Code→text", "JSON→text"]
# The three Q3 slots plus a fourth, validated together (CVD ΔE ≥ 9.2, normal ≥ 27.6).
COLORS = ["#2a78d6", "#1baf7a", "#eb6834", "#7a5cc6"]
MARKERS = ["o", "s", "^", "D"]
DASHES = ["-", (0, (4, 1.5)), "-", (0, (1.2, 1.2))]   # texture as a second cue where lines coincide
# Coincident points (four arms all at 1.0) would hide three of the four lines; nudge each arm
# by a hair so every line stays visible. The offsets are far below the plotted resolution.
NUDGE = [0.012, 0.004, -0.004, -0.012]
DEEPSEEK = {"CaveAgent": [1, 1, 1, 1, 1, 1], "Code→file": [1, 1, 1, .933, 1, 1],
            "Code→text": [1, 1, 1, .867, 0, 0], "JSON→text": [1, 1, .933, .867, 0, 0]}
QWEN = {"CaveAgent": [.667, .867, .933, .733, 1, .8], "Code→file": [.4, .333, .333, .4, .467, .6],
        "Code→text": [.267, .533, .333, .133, 0, 0], "JSON→text": [.667, .467, .2, .067, 0, 0]}
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"

fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.7), sharey=True)
for ax, (title, data) in zip(axes, [("DeepSeek-V4 Flash", DEEPSEEK), ("Qwen3-Coder (30B)", QWEN)]):
    for arm, color, marker, dash, nudge in zip(ARMS, COLORS, MARKERS, DASHES, NUDGE):
        ax.plot(ROWS, [v + nudge for v in data[arm]], color=color, marker=marker, linestyle=dash,
                markersize=4.5, linewidth=1.6,
                markeredgecolor="white", markeredgewidth=0.6, label=arm, zorder=3)
    ax.set_xscale("log")
    ax.set_xticks(ROWS, [f"{r:,}" for r in ROWS], fontsize=7.5, color=INK)
    ax.set_xlabel("Rows delivered", fontsize=8.5, color=INK)
    ax.set_title(title, fontsize=9, color=INK, pad=6)
    ax.set_ylim(-0.05, 1.07)
    ax.set_yticks([0, .25, .5, .75, 1], ["0", "0.25", "0.5", "0.75", "1"])
    ax.tick_params(axis="y", labelsize=7.5, colors=MUTED, length=0)
    ax.tick_params(axis="x", which="both", length=0)
    ax.minorticks_off()
    ax.yaxis.grid(True, color=GRID, linewidth=0.6, zorder=0)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
axes[0].set_ylabel("Success rate", fontsize=8.5, color=INK)
handles, labels = axes[0].get_legend_handles_labels()
fig.legend(handles, labels, frameon=False, fontsize=8, ncol=4, loc="upper center",
           bbox_to_anchor=(0.5, 1.0), handlelength=2.4, columnspacing=1.6)
fig.tight_layout(rect=(0, 0, 1, 0.9))
fig.savefig(Path(__file__).parent / "fig-q4-cliff.pdf")
