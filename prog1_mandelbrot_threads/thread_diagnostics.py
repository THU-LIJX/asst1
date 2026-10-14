"""Validate and summarize complete worker sets from one instrumented trial."""

from collections import defaultdict
import csv
import json
import math


WORKER_FIELDS = ["round", "order", "view", "threads", "iteration", "thread_id",
                 "start_row", "num_rows", "elapsed_ms", "parallel_iteration_ms",
                 "iteration_sum", "total_iterations", "work_share_percent", "selected"]
INTEGER_FIELDS = set(WORKER_FIELDS) - {"elapsed_ms", "parallel_iteration_ms", "work_share_percent"}


def validate_records(records, threads, total, parallel_ms, width=1600, height=1200, repeats=5):
    if len(records) != repeats * threads or not isinstance(total, int) or total <= 0:
        raise ValueError("Incomplete worker records or invalid reference iteration sum")
    expected = {(iteration, thread) for iteration in range(1, repeats + 1) for thread in range(threads)}
    keys = [(record["iteration"], record["thread_id"]) for record in records]
    if set(keys) != expected or len(set(keys)) != len(keys):
        raise ValueError("Duplicate, missing, or unexpected worker IDs/trials")
    per_iteration = defaultdict(list)
    signatures = {}
    for record in records:
        for field in ("iteration", "thread_id", "start_row", "num_rows", "iteration_sum"):
            if type(record[field]) is not int:
                raise ValueError(f"Non-integer worker field: {field}")
        row, count = record["start_row"], record["num_rows"]
        if row < 0 or count < 0 or row + count > height:
            raise ValueError("Invalid row range")
        work = record["iteration_sum"]
        if not 0 <= work <= count * width * 256:
            raise ValueError("Invalid workload iteration sum")
        duration, wall = record["elapsed_ms"], record["parallel_iteration_ms"]
        if (not all(isinstance(value, (int, float)) and math.isfinite(value) for value in (duration, wall))
                or duration < 0 or wall <= 0 or duration > wall + 0.001):
            raise ValueError("Invalid worker timing or duration exceeds whole-trial time")
        signature = row, count, work
        if signatures.setdefault(record["thread_id"], signature) != signature:
            raise ValueError("Worker mapping or workload changed between internal trials")
        per_iteration[record["iteration"]].append(record)
    walls = {}
    for iteration, group in per_iteration.items():
        cursor = 0
        for record in sorted(group, key=lambda item: item["start_row"]):
            if record["start_row"] != cursor:
                raise ValueError("Worker row ranges have a gap or overlap")
            cursor += record["num_rows"]
        if cursor != height or sum(record["iteration_sum"] for record in group) != total:
            raise ValueError("Rows or workload do not cover the serial reference")
        values = {record["parallel_iteration_ms"] for record in group}
        if len(values) != 1:
            raise ValueError("Inconsistent wall times within an internal trial")
        if sum(record["elapsed_ms"] for record in group) <= 0:
            raise ValueError("All workers have zero duration")
        walls[iteration] = values.pop()
    selected = min(walls, key=lambda iteration: (walls[iteration], iteration))
    if not math.isclose(walls[selected], parallel_ms, rel_tol=0, abs_tol=0.001):
        raise ValueError("Selected whole-trial time disagrees with the reported minimum")
    return selected


def parse_output(output, threads, parallel_ms):
    totals = [json.loads(line.removeprefix("THREAD_TIMING_TOTAL "))
              for line in output.splitlines() if line.startswith("THREAD_TIMING_TOTAL ")]
    records = [json.loads(line.removeprefix("THREAD_TIMING "))
               for line in output.splitlines() if line.startswith("THREAD_TIMING ")]
    if len(totals) != 1 or any(totals[0].get(key) != value for key, value in
                               (("width", 1600), ("height", 1200), ("internal_repeats", 5))):
        raise ValueError("Missing or inconsistent diagnostic header")
    total = totals[0]["iteration_sum"]
    selected = validate_records(records, threads, total, parallel_ms)
    return [{**record, "total_iterations": total,
             "work_share_percent": 100 * record["iteration_sum"] / total,
             "selected": int(record["iteration"] == selected)} for record in records]


def read_csv(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def write_csv(path, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def validate_saved(workers, processes, metadata):
    groups = defaultdict(list)
    for row in workers:
        groups[row["order"]].append(row)
    if set(groups) != {row["order"] for row in processes}:
        raise ValueError("Worker records do not match the set of successful runs")
    selected_rows = []
    for process in processes:
        group = groups[process["order"]]
        converted = [{key: int(row[key]) if key in INTEGER_FIELDS else float(row[key])
                      for key in WORKER_FIELDS} for row in group]
        if any(str(row[key]) != process[key] for row in converted for key in ("round", "order", "view", "threads")):
            raise ValueError("Worker run/configuration identifiers disagree")
        totals = {row["total_iterations"] for row in converted}
        if len(totals) != 1:
            raise ValueError("Inconsistent reference iteration sum")
        total = totals.pop()
        selected = validate_records(converted, int(process["threads"]), total, float(process["parallel_ms"]),
                                    metadata["width"], metadata["height"], metadata["internal_repeats"])
        for row in converted:
            if (row["selected"] != int(row["iteration"] == selected) or
                    not math.isclose(row["work_share_percent"], 100 * row["iteration_sum"] / total, rel_tol=1e-12, abs_tol=1e-12)):
                raise ValueError("Invalid selection or workload share")
        selected_rows.extend(row for row in converted if row["selected"])
    return selected_rows


def summarize_selected(selected):
    import numpy as np

    groups = defaultdict(list)
    runs = defaultdict(list)
    for row in selected:
        groups[row["view"], row["threads"], row["thread_id"]].append(row)
        runs[row["view"], row["threads"], row["order"]].append(row)
    summaries = []
    for (view, threads, thread_id), group in sorted(groups.items()):
        q25, median, q75 = np.percentile([row["elapsed_ms"] for row in group], [25, 50, 75])
        first = group[0]
        if any((row["start_row"], row["num_rows"], row["iteration_sum"]) !=
               (first["start_row"], first["num_rows"], first["iteration_sum"]) for row in group):
            raise ValueError("Worker workload/mapping changed across independent runs")
        summaries.append({"view": view, "threads": threads, "thread_id": thread_id,
                          "samples": len(group), "start_row": first["start_row"], "num_rows": first["num_rows"],
                          "elapsed_ms_q25": float(q25), "elapsed_ms_median": float(median), "elapsed_ms_q75": float(q75),
                          "iteration_sum": first["iteration_sum"], "work_share_percent": first["work_share_percent"]})
    imbalances = defaultdict(list)
    for (view, threads, _), group in runs.items():
        durations = [row["elapsed_ms"] for row in group]
        work = [row["iteration_sum"] for row in group]
        imbalances[view, threads].append({"time_imbalance": max(durations) / np.mean(durations),
                                         "work_imbalance": threads * max(work) / sum(work),
                                         "max_worker_ms": max(durations), "mean_worker_ms": float(np.mean(durations))})
    aggregate = []
    for (view, threads), group in sorted(imbalances.items()):
        entry = {"view": view, "threads": threads, "samples": len(group)}
        for field in group[0]:
            q25, median, q75 = np.percentile([row[field] for row in group], [25, 50, 75])
            entry.update({f"{field}_q25": float(q25), f"{field}_median": float(median), f"{field}_q75": float(q75)})
        aggregate.append(entry)
    return summaries, aggregate


def plot_diagnostics(directory, summary, metadata):
    import matplotlib.pyplot as plt
    import numpy as np

    largest = max(row["elapsed_ms_median"] for row in summary)
    columns = max(metadata["threads"])
    for view in metadata["views"]:
        entries = [row for row in summary if row["view"] == view]
        fig, axes = plt.subplots(2, 1, figsize=(12, 7.5), layout="constrained")
        for ax, metric, title, limit, cmap_name, unit in (
            (axes[0], "elapsed_ms_median", "各线程耗时中位数", largest, "viridis", "ms"),
            (axes[1], "work_share_percent", "各线程负责的迭代量占比", 100, "YlGnBu", "%"),
        ):
            data = np.full((len(metadata["threads"]), columns), np.nan)
            for row in entries:
                data[metadata["threads"].index(row["threads"]), row["thread_id"]] = row[metric]
            cmap = plt.get_cmap(cmap_name).copy()
            cmap.set_bad("#F1F5F9")
            image = ax.imshow(data, aspect="auto", vmin=0, vmax=limit, cmap=cmap)
            ax.set_xticks(range(columns), labels=range(columns), fontsize=9)
            ax.set_yticks(range(len(metadata["threads"])), labels=[f"{count} 线程" for count in metadata["threads"]])
            ax.set(title=title, xlabel="线程编号")
            fig.colorbar(image, ax=ax, label=f"{title}（{unit}）", fraction=0.03, pad=0.02)
            for (y, x), value in np.ndenumerate(data):
                if np.isfinite(value):
                    red, green, blue, _ = cmap(value / limit)
                    luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue
                    ax.text(x, y, f"{value:.1f}", ha="center", va="center", fontsize=8,
                            color="white" if luminance < 0.5 else "#111827")
        fig.suptitle(f"视图 {view}：逐线程耗时与工作量分布", fontsize=15)
        fig.supxlabel(f"{metadata['repeats']} 轮独立运行；每轮使用整体最快内部测量的完整线程记录；灰色格为未创建的线程",
                      fontsize=9, color="#475569")
        for extension in ("png", "pdf"):
            fig.savefig(directory / f"thread_diagnostics_view{view}.{extension}", dpi=180)
        plt.close(fig)


def report_lines(directory, summary, imbalances, process_summary, metadata):
    lines = ["## 第三部分：逐线程计时与工作量", "",
             "每次启动保存 5 套完整线程记录；按整体并行耗时选取最快的内部测量，再对该次全部线程的耗时跨独立运行汇总。"
             "没有对各线程分别取最短值。逐线程打印、最终输出的迭代量统计均在所有计时结束后执行。",
             "迭代量统计复用通过校验的最终输出，因为每次内部测量的输入及行块不变。各行块迭代量之和与串行参考完全一致。",
             "耗时不均衡度为每个完整线程集合的最大耗时 / 平均耗时，再跨轮取中位数；1 表示耗时均衡。"
             "工作量不均衡度为最大迭代量 / 平均迭代量；相同配置的工作量是确定的。", "",
             "| 视图 | 线程数 | 耗时不均衡度中位数 | Q25-Q75 | 工作量不均衡度 |", "| --- | ---: | ---: | ---: | ---: |"]
    for row in imbalances:
        lines.append(f"| {row['view']} | {row['threads']} | {row['time_imbalance_median']:.3f} | "
                     f"{row['time_imbalance_q25']:.3f}-{row['time_imbalance_q75']:.3f} | {row['work_imbalance_median']:.3f} |")
    for view in metadata["views"]:
        lines += ["", f"### View {view}：逐线程证据", ""]
        for threads in metadata["threads"]:
            workers = [row for row in summary if row["view"] == view and row["threads"] == threads]
            slowest = max(workers, key=lambda row: row["elapsed_ms_median"])
            heaviest = max(workers, key=lambda row: row["iteration_sum"])
            lines.append(f"- {threads} 线程：耗时中位数最大的线程为 {slowest['thread_id']}，"
                         f"负责行 [{slowest['start_row']}, {slowest['start_row'] + slowest['num_rows']})，"
                         f"耗时 {slowest['elapsed_ms_median']:.3f} ms、迭代量占比 {slowest['work_share_percent']:.2f}%；"
                         f"迭代量最多的线程为 {heaviest['thread_id']}，占比 {heaviest['work_share_percent']:.2f}%。")
        workers3 = [row for row in summary if row["view"] == view and row["threads"] == 3]
        if workers3:
            lines += ["", "| 3 线程编号 | 行范围 | 耗时中位数 (ms) | Q25-Q75 (ms) | 迭代数总和 | 迭代量占比 |",
                      "| --- | --- | ---: | ---: | ---: | ---: |"]
            for row in workers3:
                lines.append(f"| {row['thread_id']} | [{row['start_row']}, {row['start_row'] + row['num_rows']}) | "
                             f"{row['elapsed_ms_median']:.3f} | {row['elapsed_ms_q25']:.3f}-{row['elapsed_ms_q75']:.3f} | "
                             f"{row['iteration_sum']} | {row['work_share_percent']:.2f}% |")
            slowest = max(workers3, key=lambda row: row["elapsed_ms_median"])
            heaviest = max(workers3, key=lambda row: row["iteration_sum"])
            lines += ["", ("最慢线程同时承担最多迭代，实测支持工作量不均对该配置的影响。" if slowest["thread_id"] == heaviest["thread_id"]
                            else "耗时最大的线程与迭代量最多的线程不同，仅用迭代量不能解释该配置全部耗时差异。")]
    baseline_path = directory / "baseline_summary.csv"
    if baseline_path.exists():
        baseline = {(int(row["view"]), int(row["threads"])): row for row in read_csv(baseline_path)}
        lines += ["", "### 与第二部分的对照", "",
                  f"基线目录：`{metadata['baseline_dir']}`。原始目录只读，引用的汇总与环境记录已复制到本实验目录。",
                  "",
                  "| 视图 | 线程数 | 原加速比中位数 | 本次加速比中位数 | 变化 |", "| --- | ---: | ---: | ---: | ---: |"]
        for row in process_summary:
            previous = float(baseline[row["view"], row["threads"]]["speedup_median"])
            current = row["speedup_median"]
            lines.append(f"| {row['view']} | {row['threads']} | {previous:.3f}x | {current:.3f}x | {(current / previous - 1) * 100:+.1f}% |")
        lines += ["", "本次含两次逐线程时钟读取及记录写入，且测量时刻与基线不同，因此差值不能直接当作纯计时开销。"]
    lines += ["", "### 结论的边界", "",
              "逐线程时间是墙钟时间，包含系统暂停或抢占；没有追踪线程运行在哪类核心上。"
              "像素迭代数总和只是工作量指标，不完全反映判断分支、访存和线程创建/调度成本。",
              "如果 view 1 的 3 线程中间行块承担更多迭代并成为慢线程，就能解释为何增加线程却降低加速比："
              "其他线程结束后仍需等待该线程。view 2 的工作量分布则需按图表与数据单独判断。",
              "8、16 线程仍可能受到工作划分、M3 性能/能效核心差异和调度的共同影响；本次没有改变分块，也不能归因于 SMT。",
              "后续第四部分才比较新的负载均衡策略。", "",
              "新增文件：`thread_raw.csv`（全部记录）、`thread_selected.csv`（完整最快内部测量）、"
              "`thread_summary.csv`（逐线程统计）、`imbalance_summary.csv`（不均衡度）及各视图的诊断图。", ""]
    return lines


def create_outputs(directory, processes, process_summary, metadata):
    workers = read_csv(directory / "thread_raw.csv")
    selected = validate_saved(workers, processes, metadata)
    saved_selected = read_csv(directory / "thread_selected.csv")
    if len(saved_selected) != len(selected) or any(
            any(not math.isclose(float(original[field]), row[field], rel_tol=1e-12, abs_tol=1e-12)
                for field in WORKER_FIELDS) for original, row in zip(saved_selected, selected)):
        raise ValueError("Selected worker CSV does not match full-trial selection")
    summary, imbalances = summarize_selected(selected)
    if any(row["samples"] != metadata["repeats"] for row in summary + imbalances):
        raise ValueError("Incomplete diagnostic sample counts")
    write_csv(directory / "thread_summary.csv", summary)
    write_csv(directory / "imbalance_summary.csv", imbalances)
    plot_diagnostics(directory, summary, metadata)
    return report_lines(directory, summary, imbalances, process_summary, metadata)
