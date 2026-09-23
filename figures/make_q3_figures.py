"""Figure 5: the Q3 token-efficiency study (values are those of Table 11, mean of n=3).

    python figures/make_q3_figures.py      # writes figures/fig-q3-cost.pdf and fig-q3-steps.pdf
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

MODELS = ["DeepSeek\nV3.2", "DeepSeek\nV4 Flash", "Gemini\n3.1 Pro", "Qwen3-Coder\n(30B)"]
PARADIGMS = ["CaveAgent", "JSON FC", "Bash (filesystem)"]
COLORS = ["#2a78d6", "#eb6834", "#1baf7a"]          # validated categorical slots 1-3
TOKENS_PER_TURN = [[7999, 12853, 34209], [7825, 10339, 14474], [6357, 6971, 9540], [7632, 12667, 25723]]
STEPS = [[118, 174, 302], [121, 130, 166], [101, 119, 127], [114, 179, 225]]
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"


def grouped_bars(values, ylabel, labels, path):
    fig, ax = plt.subplots(figsize=(4.6, 3.0))
    width, gap = 0.26, 0.02
    for j, (name, color) in enumerate(zip(PARADIGMS, COLORS)):
        xs = [i + (j - 1) * (width + gap) for i in range(len(MODELS))]
        bars = ax.bar(xs, [row[j] for row in values], width, color=color, label=name, zorder=3)
        for i, bar in enumerate(bars):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), labels(values[i], j),
                    ha="center", va="bottom", fontsize=7.5, color=MUTED)
    ax.set_xticks(range(len(MODELS)), MODELS, fontsize=8, color=INK)
    ax.set_ylabel(ylabel, fontsize=8.5, color=INK)
    ax.tick_params(axis="y", labelsize=7.5, colors=MUTED, length=0)
    ax.yaxis.set_major_formatter(lambda value, _: f"{value / 1000:g}K" if value >= 1000 else f"{value:g}")
    ax.tick_params(axis="x", length=0)
    ax.yaxis.grid(True, color=GRID, linewidth=0.6, zorder=0)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.set_ylim(0, max(max(row) for row in values) * 1.14)
    fig.legend(frameon=False, fontsize=8, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.0),
               handlelength=1.2, columnspacing=1.4)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(path)
    plt.close(fig)


here = Path(__file__).parent
grouped_bars(TOKENS_PER_TURN, "Tokens per completed turn",
             lambda row, j: f"{row[j] / 1000:.1f}K" if j == 0 else f"{row[j] / row[0]:.2f}$\\times$",
             here / "fig-q3-cost.pdf")
grouped_bars(STEPS, "LLM calls (steps)", lambda row, j: str(row[j]), here / "fig-q3-steps.pdf")
