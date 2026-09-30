#!/usr/bin/env python3
"""Plot PPO TensorBoard diagnostics and periodic deterministic evaluations."""

import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).parent))
from read_tb_events import events  # noqa: E402


def load_events(run_dir):
    series = {}
    for path in sorted((run_dir / "summaries").glob("events.out.tfevents.*")):
        for step, tag, value in events(path):
            if value is not None:
                series.setdefault(tag, []).append((step, value))
    return series


def epoch_points(points, direct=False):
    return [(step if direct else step / 32768 + 1, value) for step, value in points]


def plot_line(ax, title, ylabel, points, direct=False):
    xs, ys = zip(*epoch_points(points, direct=direct))
    ax.plot(xs, ys, linewidth=1.5)
    ax.set(title=title, xlabel="Training epoch", ylabel=ylabel)
    ax.grid(alpha=0.25)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--eval-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    series = load_events(args.run_dir)
    clip = []
    for i in range(4):
        clip.append(dict(series[f"diagnostics/clip_frac/{i}"]))
    clip_steps = sorted(set.intersection(*(set(x) for x in clip)))
    series["avg_clip_frac"] = [(step, sum(item[step] for item in clip) / 4) for step in clip_steps]

    specs = [
        ("Training Episode Return", "Return", "rewards/iter", True),
        ("Episode Length", "Steps", "episode_lengths/iter", True),
        ("Actor / Policy Loss", "PPO actor loss", "losses/a_loss", False),
        ("Value Loss", "Critic loss", "losses/c_loss", False),
        ("Entropy", "Entropy", "losses/entropy", False),
        ("Approx KL Divergence", "KL", "info/kl", False),
        ("Average Clip Fraction", "Fraction", "avg_clip_frac", True),
        ("Explained Variance", "Explained variance", "diagnostics/exp_var", True),
    ]
    fig, axes = plt.subplots(4, 2, figsize=(13, 15), constrained_layout=True)
    for ax, (title, ylabel, tag, direct) in zip(axes.flat, specs):
        plot_line(ax, title, ylabel, series[tag], direct)
    fig.suptitle("PPO training diagnostics (epochs 601–700)", fontsize=14)
    fig.savefig(args.output_dir / "ppo_training_diagnostics_ep601_700.png", dpi=180)
    plt.close(fig)

    results = []
    for path in sorted(args.eval_dir.glob("eval_ep*_seed1000.json")):
        data = json.loads(path.read_text())
        epoch = int(path.name.split("_seed", 1)[0].split("ep", 1)[1])
        results.append((epoch, data["mean_eval_return"], data["std_eval_return"], data["success_rate"]))
    assert len(results) == 10 and [x[0] for x in results] == list(range(610, 701, 10))
    epochs, means, stds, successes = zip(*results)
    fig, ax = plt.subplots(figsize=(9, 5), constrained_layout=True)
    ax.errorbar(epochs, means, yerr=stds, marker="o", capsize=4, linewidth=1.5)
    ax.set(title="Deterministic Evaluation Return vs Epoch", xlabel="Checkpoint epoch", ylabel="Evaluation return")
    ax.grid(alpha=0.25)
    fig.savefig(args.output_dir / "evaluation_return_vs_epoch_ep610_700.png", dpi=180)
    plt.close(fig)

    (args.output_dir / "evaluation_summary.json").write_text(
        json.dumps(
            [
                {"epoch": epoch, "mean_eval_return": mean, "std_eval_return": std, "success_rate": success}
                for epoch, mean, std, success in results
            ],
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
