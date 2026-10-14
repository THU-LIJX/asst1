#!/usr/bin/env python3
"""Measure the existing row-block implementation without changing its kernel."""

import argparse
from collections import Counter
from contextlib import ExitStack
import csv
from datetime import datetime
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import platform
import random
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from zoneinfo import ZoneInfo

import thread_diagnostics


ROOT = Path(__file__).resolve().parents[1]
PROGRAM = Path(__file__).resolve().parent
FLAGS = "-I../common -Iobjs/ -O3 -std=c++11 -Wall -fPIC"
SEED = 7
FIELDS = ["round", "order", "view", "threads", "serial_ms", "parallel_ms",
          "speedup", "verification", "log"]
TIMINGS = {
    name: re.compile(rf"^\[mandelbrot {label}\]:\s*\[([\d.]+)\] ms$", re.MULTILINE)
    for name, label in (("serial_ms", "serial"), ("parallel_ms", "thread"))
}


def now():
    return datetime.now(ZoneInfo("Asia/Shanghai"))


def integer_list(value):
    try:
        values = []
        for item in value.split(","):
            if "-" in item:
                start, end = map(int, item.split("-"))
                if start > end:
                    raise ValueError
                values.extend(range(start, end + 1))
            else:
                values.append(int(item))
        if not values or len(values) != len(set(values)):
            raise ValueError
        return sorted(values)
    except ValueError as error:
        raise argparse.ArgumentTypeError("Use distinct integers or ranges, e.g. 1,3 or 1-16") from error


def command_output(command):
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=30)
    return result.stdout.strip() if result.returncode == 0 else f"Unavailable: {result.stderr.strip()}"


def save_metadata(directory, metadata):
    temporary = directory / "metadata.tmp"
    temporary.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(directory / "metadata.json")


def environment():
    hardware = {}
    for key in ("machdep.cpu.brand_string", "hw.physicalcpu", "hw.logicalcpu", "hw.memsize",
                "hw.perflevel0.physicalcpu", "hw.perflevel1.physicalcpu"):
        value = command_output(["sysctl", "-n", key])
        hardware[key] = int(value) if value.isdigit() else value
    return {
        "hardware": hardware,
        "macos": command_output(["sw_vers"]),
        "python": sys.version,
        "architecture": platform.machine(),
        "clang": command_output(["clang++", "--version"]),
        "make": command_output(["make", "--version"]),
        "power": command_output(["pmset", "-g", "batt"]),
        "power_settings": command_output(["pmset", "-g", "custom"]),
        "git_commit": command_output(["git", "rev-parse", "HEAD"]),
        "git_status": command_output(["git", "status", "--short"]),
    }


def parse_measurement(output, threads):
    if re.search(r"^(?:Error|Mismatch)\b", output, re.MULTILINE):
        raise ValueError("Program reported a result verification error")
    # The success marker is printed only after the C++ result comparison passes.
    markers = re.findall(r"\(([\d.]+)x speedup from (\d+) threads\)", output)
    if len(markers) != 1 or int(markers[0][1]) != threads:
        raise ValueError("Missing or inconsistent verification success marker")
    measurements = {}
    for field, pattern in TIMINGS.items():
        matches = pattern.findall(output)
        if len(matches) != 1:
            raise ValueError(f"Expected one {field} timing, got {len(matches)}")
        value = float(matches[0])
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"Invalid {field}: {value}")
        measurements[field] = value
    measurements["speedup"] = measurements["serial_ms"] / measurements["parallel_ms"]
    return measurements


def measure(directory, work, view, threads, log_name, thread_timing=False):
    command = [str(PROGRAM / "mandelbrot"), "--view", str(view), "-t", str(threads)]
    if thread_timing:
        command.append("--thread-timing")
    log_path = directory / "logs" / log_name
    with log_path.open("w") as log:
        log.write(f"Command: {' '.join(command)}\n")
        log.flush()
        result = subprocess.run(command, cwd=work, stdout=log, stderr=subprocess.STDOUT, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(f"Exit {result.returncode}; see {log_path}")
    try:
        output = log_path.read_text()
        measurement = parse_measurement(output, threads)
        if thread_timing:
            measurement["workers"] = thread_diagnostics.parse_output(output, threads, measurement["parallel_ms"])
        return measurement
    except (ValueError, KeyError, TypeError) as error:
        raise RuntimeError(f"{error}; see {log_path}") from error


def validate_rows(rows, metadata):
    configurations = set(itertools.product(metadata["views"], metadata["threads"]))
    expected = metadata["repeats"]
    counts = Counter((int(row["view"]), int(row["threads"])) for row in rows)
    if set(counts) != configurations or any(count != expected for count in counts.values()):
        raise ValueError("Incomplete or unexpected configuration sample counts")
    rounds = Counter((int(row["round"]), int(row["view"]), int(row["threads"])) for row in rows)
    if any(count != 1 or not 1 <= key[0] <= expected for key, count in rounds.items()):
        raise ValueError("Duplicate measurements or invalid round numbers")
    for row in rows:
        serial, parallel, speedup = (float(row[key]) for key in ("serial_ms", "parallel_ms", "speedup"))
        if (row["verification"] != "passed" or
                not all(math.isfinite(value) and value > 0 for value in (serial, parallel, speedup)) or
                not math.isclose(serial / parallel, speedup, rel_tol=1e-12)):
            raise ValueError("Invalid measurement or inconsistent paired speedup")


def summarize(rows):
    import numpy as np

    summary = []
    configurations = sorted({(int(row["view"]), int(row["threads"])) for row in rows})
    for view, threads in configurations:
        group = [row for row in rows if int(row["view"]) == view and int(row["threads"]) == threads]
        entry = {"view": view, "threads": threads, "samples": len(group)}
        for field in ("serial_ms", "parallel_ms", "speedup"):
            q25, median, q75 = np.percentile([float(row[field]) for row in group], [25, 50, 75], method="linear")
            entry.update({f"{field}_q25": float(q25), f"{field}_median": float(median), f"{field}_q75": float(q75)})
        summary.append(entry)
    return summary


def plot(directory, rows, summary, metadata):
    # Keep font caches writable without changing the user's global configuration.
    os.environ.setdefault("MPLCONFIGDIR", str(directory / ".cache" / "matplotlib"))
    os.environ.setdefault("XDG_CACHE_HOME", str(directory / ".cache"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    import numpy as np

    metadata["plot_versions"] = {"matplotlib": matplotlib.__version__, "numpy": np.__version__}
    plt.rcParams.update({"font.size": 11, "pdf.fonttype": 42})
    font_path = Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf")
    if font_path.exists():
        font_manager.fontManager.addfont(str(font_path))
        plt.rcParams["font.family"] = font_manager.FontProperties(fname=font_path).get_name()
    colors = {1: "#0072B2", 2: "#D55E00"}
    hardware = metadata["hardware"]
    p_cores = hardware.get("hw.perflevel0.physicalcpu")
    all_cores = hardware.get("hw.physicalcpu")
    chip = hardware.get("machdep.cpu.brand_string", "CPU")
    for metric, title, ylabel, filename in (
        ("speedup", "Mandelbrot：线程数与加速比", "加速比（相对串行参考，倍）", "speedup"),
        ("parallel_ms", "Mandelbrot：线程数与运行时间", "运行时间（ms）", "runtime"),
    ):
        fig, ax = plt.subplots(figsize=(10.5, 6.5), layout="constrained")
        for view in metadata["views"]:
            entries = [entry for entry in summary if entry["view"] == view]
            x = [entry["threads"] for entry in entries]
            y = [entry[f"{metric}_median"] for entry in entries]
            ax.plot(x, y, "o-", color=colors[view], label=f"视图 {view}", linewidth=2, markersize=4)
            ax.fill_between(x, [entry[f"{metric}_q25"] for entry in entries],
                            [entry[f"{metric}_q75"] for entry in entries], color=colors[view], alpha=0.2)
            if metric == "parallel_ms":
                baseline = float(np.median([float(row["serial_ms"]) for row in rows if int(row["view"]) == view]))
                ax.axhline(baseline, color=colors[view], linestyle="--", alpha=0.65,
                           label=f"视图 {view} 串行中位数（{baseline:.1f} ms）")
        if metric == "speedup":
            x = metadata["threads"]
            ax.plot(x, x, "--", color="#999999", linewidth=1.2, label="理想线性参考")
            ax.axhline(1, color="#BBBBBB", linewidth=0.8)
        for count, label, y in ((p_cores, "个性能核心", 0.98), (all_cores, "个总核心", 0.9)):
            if isinstance(count, int) and min(metadata["threads"]) <= count <= max(metadata["threads"]):
                ax.axvline(count, color="#64748B", linestyle=":", linewidth=1)
                ax.text(count + 0.12, y, f"{count} {label}", transform=ax.get_xaxis_transform(),
                        va="top", fontsize=9, color="#475569")
        ax.set(title=title, xlabel="线程数", ylabel=ylabel)
        ax.set_xticks(metadata["threads"])
        ax.set_xlim(min(metadata["threads"]) - 0.4, max(metadata["threads"]) + 0.6)
        ax.set_ylim(bottom=0)
        ax.grid(axis="y", alpha=0.2)
        ax.legend(loc="best", fontsize=9)
        ax.spines[["top", "right"]].set_visible(False)
        fig.supxlabel(f"{chip} | {metadata['repeats']} 轮独立运行 | 5 次计时取最小值，再汇总中位数和四分位范围",
                      fontsize=9, color="#475569")
        for extension in ("png", "pdf"):
            fig.savefig(directory / f"{filename}.{extension}", dpi=180)
        plt.close(fig)


def report(directory, rows, summary, metadata, diagnostic_lines=None):
    lines = ["# Problem 1：线程数与加速比实验", "",
             f"实验开始：{metadata['started_at']}。CPU：{metadata['hardware'].get('machdep.cpu.brand_string')}。",
             f"已验证 {len(rows)} 次正式运行；每个配置 {metadata['repeats']} 轮，全部通过程序内置结果校验。", "",
             "## 测量方法", "",
             "保留当前连续行分块算法，仅最后一个线程处理余数行。每次启动分别计时串行与并行各 5 次，取最短值；"
             "加速比使用同一次启动的串行时间除以并行时间，再跨轮取中位数。四分位范围是样本波动范围，不是置信区间。",
             "每个视图先以 1 线程预热一次，不计入正式数据。每轮按种子 7 打散配置，所有测量顺序执行。"
             "图像写入、数组清零和结果校验在计时区间之外；线程创建与 join 在并行计时区间之内。",
             "加速比从输出的毫秒数重算（程序打印到小数点后 3 位），不使用只保留两位小数的加速比输出。", "",
             "## 实测结果", ""]
    for view in metadata["views"]:
        entries = [entry for entry in summary if entry["view"] == view]
        best = max(entries, key=lambda entry: (entry["speedup_median"], -entry["threads"]))
        lines += [f"### View {view}", "",
                  f"本次加速比中位数最高的点是 **{best['threads']} 线程，{best['speedup_median']:.3f}x**，"
                  f"并行耗时中位数 {best['parallel_ms_median']:.3f} ms。最佳点只代表此次测量，接近的结果需结合波动范围判断。", "",
                  "| 线程数 | 串行中位数 (ms) | 并行中位数 (ms) | 加速比中位数 | 加速比 Q25–Q75 |", "| --- | ---: | ---: | ---: | ---: |"]
        for entry in entries:
            lines.append(f"| {entry['threads']} | {entry['serial_ms_median']:.3f} | {entry['parallel_ms_median']:.3f} | "
                         f"{entry['speedup_median']:.3f}x | {entry['speedup_q25']:.3f}–{entry['speedup_q75']:.3f} |")
        indexed = {entry["threads"]: entry for entry in entries}
        lines += [""]
        if 3 in indexed:
            lines.append(f"3 线程加速比为 {indexed[3]['speedup_median']:.3f}x。")
            for neighbor in (2, 4):
                if neighbor in indexed:
                    change = (indexed[3]["speedup_median"] / indexed[neighbor]["speedup_median"] - 1) * 100
                    lines.append(f"相对于 {neighbor} 线程，加速比变化 {change:+.1f}%。")
        comparisons = [f"{threads} 线程：{indexed[threads]['speedup_median']:.3f}x / "
                       f"{indexed[threads]['parallel_ms_median']:.3f} ms" for threads in (4, 8, 16) if threads in indexed]
        if comparisons:
            lines += ["", "4、8、16 线程对比（加速比 / 并行耗时）：" + "；".join(comparisons) + "。"]
        lines += [""]
    lines += ["## 解释与后续验证", "",
              "曲线中的非线性和两个视图的差异，需要结合以下假设解释；本实验没有逐线程计时或核心调度追踪，不能仅凭曲线确认原因。", "",
              "- Mandelbrot 每个像素的迭代次数不同，连续行块包含的工作量可能不均衡；3 线程时的行块边界可能让某个线程承担较多计算。",
              "- M3 的 4 个性能核心和 4 个能效核心速度不同，等行数不意味着等完成时间；实际线程与核心的对应关系由系统调度。",
              "- 超过 8 个软件线程仍共享 8 个逻辑 CPU。更细的分块可能改善负载分布，也可能增加创建和调度开销。M3 不支持 SMT，不能将变化归因于超线程。",
              "- 当前仅将余数行交给最后一个线程；此外还有频率、温度和后台负载变化。单线程封装与串行参考的差异也包含计时波动。",
              "- 后续可在第三部分加入逐线程计算耗时，验证负载不均假设，再在第四部分比较新的任务划分。本次不修改算法。", "",
              "## 文件与复现", "",
              "- `raw.csv`：每次有效测量、轮次、顺序及对应日志。",
              "- `summary.csv`：每个配置的样本数、中位数和四分位数，百分位采用线性插值。",
              "- `speedup.png/pdf`、`runtime.png/pdf`：两种视图的对比图；线性参考线不代表异构 CPU 的预期加速比。",
              "- `metadata.json`、`source.diff`、`logs/`：环境、参数、源码状态、构建、预热及运行记录。", "",
              "```bash", metadata["reproduce_command"], "```", "",
              "本次只读取供电和低电量模式信息，没有修改系统设置，也没有固定线程到某类核心。",
              "环境状态见 metadata.json；实验结果仅代表记录的代码、机器及当时负载。", ""]
    if diagnostic_lines is not None:
        first = lines.index("## 解释与后续验证")
        last = lines.index("## 文件与复现")
        lines[first:last] = diagnostic_lines
    (directory / "report.md").write_text("\n".join(lines))


def create_outputs(directory, metadata):
    with (directory / "raw.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    validate_rows(rows, metadata)
    summary = summarize(rows)
    with (directory / "summary.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    plot(directory, rows, summary, metadata)
    diagnostic_lines = None
    if metadata.get("thread_timing"):
        diagnostic_lines = thread_diagnostics.create_outputs(directory, rows, summary, metadata)
    report(directory, rows, summary, metadata, diagnostic_lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--views", type=integer_list, default=[1, 2], help="Comma-separated views (default: 1,2)")
    parser.add_argument("--threads", type=integer_list, default=list(range(1, 17)), help="Thread list or range (default: 1-16)")
    parser.add_argument("--repeats", type=int, default=10, help="Independent rounds (default: 10)")
    parser.add_argument("--output-dir", type=Path, help="New directory; defaults to results/problem1/<timestamp>")
    parser.add_argument("--plot-only", type=Path, help="Regenerate outputs from a complete raw.csv without new measurements")
    parser.add_argument("--thread-timing", action="store_true", help="Collect per-worker times and iteration workload")
    parser.add_argument("--baseline-dir", type=Path, help="Read-only completed experiment to compare against")
    args = parser.parse_args()
    if args.plot_only:
        directory = args.plot_only.resolve()
        metadata = json.loads((directory / "metadata.json").read_text())
        create_outputs(directory, metadata)
        metadata["status"] = "complete"
        save_metadata(directory, metadata)
        print(f"Regenerated outputs: {directory}")
        return
    if not set(args.views) <= {1, 2} or not all(1 <= count <= 32 for count in args.threads) or args.repeats < 1:
        parser.error("Views must be 1 or 2, threads must be 1..32, and repeats must be positive")
    if args.baseline_dir:
        args.baseline_dir = args.baseline_dir.resolve()
        baseline_metadata = json.loads((args.baseline_dir / "metadata.json").read_text())
        baseline_keys = {(int(row["view"]), int(row["threads"]))
                         for row in thread_diagnostics.read_csv(args.baseline_dir / "summary.csv")}
        if (baseline_metadata["status"] != "complete" or baseline_metadata["cxxflags"] != FLAGS or
                any(baseline_metadata.get(key) != value for key, value in (("width", 1600), ("height", 1200), ("max_iterations", 256))) or
                not set(itertools.product(args.views, args.threads)) <= baseline_keys):
            parser.error("Baseline must be complete, compatible, and cover all requested configurations")
    directory = (args.output_dir or ROOT / "results" / "problem1" / now().strftime("%Y%m%d-%H%M%S-%f")).resolve()
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "logs").mkdir()
    total = len(args.views) * len(args.threads) * args.repeats
    metadata = environment()
    metadata.update({"status": "running", "started_at": now().isoformat(), "views": args.views,
                     "threads": args.threads, "repeats": args.repeats, "seed": SEED,
                     "internal_repeats": 5, "width": 1600, "height": 1200, "max_iterations": 256,
                     "thread_timing": args.thread_timing,
                     "statistic": "median of paired best-of-5 speedups; linear Q25/Q75",
                     "expected_measurements": total, "completed_measurements": 0, "cxxflags": FLAGS,
                     "reproduce_command": f".venv/bin/python prog1_mandelbrot_threads/benchmark.py --views {','.join(map(str, args.views))} "
                                          f"--threads {','.join(map(str, args.threads))} --repeats {args.repeats}"})
    if args.thread_timing:
        metadata["reproduce_command"] += " --thread-timing"
        metadata["expected_worker_records"] = args.repeats * len(args.views) * sum(args.threads) * 5
        metadata["expected_selected_records"] = args.repeats * len(args.views) * sum(args.threads)
    if args.baseline_dir:
        metadata["baseline_dir"] = str(args.baseline_dir)
        metadata["reproduce_command"] += f" --baseline-dir {shlex.quote(str(args.baseline_dir))}"
        for source, target in (("summary.csv", "baseline_summary.csv"), ("metadata.json", "baseline_metadata.json")):
            shutil.copyfile(args.baseline_dir / source, directory / target)
    # Include untracked headers/helpers that Git's diff cannot capture yet.
    metadata["source_sha256"] = {}
    for relative in ("prog1_mandelbrot_threads/main.cpp", "prog1_mandelbrot_threads/mandelbrotThread.cpp",
                     "prog1_mandelbrot_threads/mandelbrotThread.h", "prog1_mandelbrot_threads/mandelbrotSerial.cpp",
                     "prog1_mandelbrot_threads/Makefile", "prog1_mandelbrot_threads/benchmark.py",
                     "prog1_mandelbrot_threads/thread_diagnostics.py", "common/CycleTimer.h", "common/ppm.cpp"):
        target = directory / "sources" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
        metadata["source_sha256"][relative] = hashlib.sha256(target.read_bytes()).hexdigest()
    save_metadata(directory, metadata)
    (directory / "source.diff").write_text(command_output(["git", "diff", "HEAD", "--", "prog1_mandelbrot_threads", "common"]))
    print(f"Results: {directory}\nConfigurations: {total // args.repeats}; measurements: {total}", flush=True)
    try:
        build = ["make", "-B", "-C", str(PROGRAM), "CXX=clang++", f"CXXFLAGS={FLAGS}"]
        metadata["build_command"] = build
        build_env = os.environ.copy()
        for variable in ("MAKEFLAGS", "MFLAGS", "GNUMAKEFLAGS"):
            build_env.pop(variable, None)
        with (directory / "logs" / "build.log").open("w") as stream:
            subprocess.run(build, stdout=stream, stderr=subprocess.STDOUT, env=build_env, check=True, timeout=60)
        metadata["binary_sha256"] = hashlib.sha256((PROGRAM / "mandelbrot").read_bytes()).hexdigest()
        rng = random.Random(SEED)
        with tempfile.TemporaryDirectory(prefix="cs149-prog1-benchmark-") as work:
            for view in args.views:
                measure(directory, work, view, 1, f"warmup-view{view}.log", args.thread_timing)
                print(f"Warmup view={view}: passed", flush=True)
            with ExitStack() as stack:
                stream = stack.enter_context((directory / "raw.csv").open("w", newline=""))
                writer = csv.DictWriter(stream, fieldnames=FIELDS)
                writer.writeheader()
                stream.flush()
                worker_writers = {}
                if args.thread_timing:
                    for name in ("thread_raw", "thread_selected"):
                        worker_stream = stack.enter_context((directory / f"{name}.csv").open("w", newline=""))
                        worker_writer = csv.DictWriter(worker_stream, fieldnames=thread_diagnostics.WORKER_FIELDS)
                        worker_writer.writeheader()
                        worker_stream.flush()
                        worker_writers[name] = worker_writer, worker_stream
                for round_number in range(1, args.repeats + 1):
                    configurations = list(itertools.product(args.views, args.threads))
                    rng.shuffle(configurations)
                    for view, threads in configurations:
                        order = metadata["completed_measurements"] + 1
                        log_name = f"round{round_number:02d}-order{order:03d}-view{view}-threads{threads:02d}.log"
                        timing = measure(directory, work, view, threads, log_name, args.thread_timing)
                        workers = timing.pop("workers", [])
                        for worker in workers:
                            record = {"round": round_number, "order": order, "view": view, "threads": threads, **worker}
                            worker_writers["thread_raw"][0].writerow(record)
                            if worker["selected"]:
                                worker_writers["thread_selected"][0].writerow(record)
                        for _, worker_stream in worker_writers.values():
                            worker_stream.flush()
                        writer.writerow({"round": round_number, "order": order, "view": view, "threads": threads,
                                         **timing, "verification": "passed", "log": f"logs/{log_name}"})
                        stream.flush()
                        metadata["completed_measurements"] = order
                        print(f"[{order}/{total}] round={round_number} view={view} threads={threads} "
                              f"parallel={timing['parallel_ms']:.3f} ms speedup={timing['speedup']:.3f}x", flush=True)
                    save_metadata(directory, metadata)
        metadata["status"] = "rendering"
        metadata["measurements_finished_at"] = now().isoformat()
        save_metadata(directory, metadata)
        create_outputs(directory, metadata)
        metadata.update({"status": "complete", "finished_at": now().isoformat()})
        save_metadata(directory, metadata)
        print(f"Completed {total} verified measurements: {directory}", flush=True)
    except (Exception, KeyboardInterrupt) as error:
        metadata.update({"status": "failed", "error": str(error) or type(error).__name__, "finished_at": now().isoformat()})
        save_metadata(directory, metadata)
        print(f"Experiment stopped: {error}. Partial results: {directory}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
