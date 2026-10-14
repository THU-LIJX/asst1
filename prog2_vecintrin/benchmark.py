"""Collect deterministic CS149 simulated-vector statistics from source copies."""

import argparse
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "prog2_vecintrin"
WIDTHS = (2, 4, 8, 16)
SIZE = 10000
REPEATS = 2
SOURCE_FILES = ("main.cpp", "CS149intrin.cpp", "CS149intrin.h",
                "logger.cpp", "logger.h", "Makefile")
FIELDS = ("vector_width", "size", "total_vector_instructions", "utilized_vector_lanes",
          "total_vector_lanes", "utilization_percent", "printed_utilization_percent",
          "clamped_exp_verification", "array_sum_verification", "repeats", "repeat_consistent")
ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def now():
    return datetime.now().astimezone().isoformat()


def inspect_command(arguments):
    result = subprocess.run(arguments, cwd=ROOT, capture_output=True, text=True)
    if result.returncode:
        return {"unavailable": (result.stderr or result.stdout).strip(), "exit_code": result.returncode}
    return result.stdout.strip()


def parse_output(output, width, size):
    text = ANSI.sub("", output)
    if text.count("CLAMPED EXPONENT (required)") != 1 or text.count("ARRAY SUM (bonus)") != 1:
        raise ValueError("Missing or duplicate verification sections")
    required, bonus = text.split("ARRAY SUM (bonus)")
    if (required.count("Results matched with answer!") != 1
            or required.count("Passed!!!") != 1 or "Failed!!!" in required
            or "out of bound" in required or "Wrong calculation" in required):
        raise ValueError("Clamped exponent verification failed or is incomplete")
    if size % width == 0:
        if bonus.count("Passed!!!") != 1 or "Failed!!!" in bonus or "Must have" in bonus:
            raise ValueError("Array sum verification failed or is incomplete")
        bonus_status = "passed"
    else:
        expected = f"Must have N % VECTOR_WIDTH == 0 for this problem (VECTOR_WIDTH is {width})"
        if bonus.strip() != expected:
            raise ValueError("Unexpected array sum skip status")
        bonus_status = "skipped_nondivisible"
    values = {}
    for field, label in (
        ("vector_width", "Vector Width"),
        ("total_vector_instructions", "Total Vector Instructions"),
        ("utilized_vector_lanes", "Utilized Vector Lanes"),
        ("total_vector_lanes", "Total Vector Lanes"),
    ):
        matches = re.findall(rf"^{label}:\s*(\d+)\s*$", required, re.MULTILINE)
        if len(matches) != 1:
            raise ValueError(f"Missing or duplicate timing-independent statistic: {label}")
        values[field] = int(matches[0])
    printed = re.findall(r"^Vector Utilization:\s*(\d+\.\d)%\s*$", required, re.MULTILINE)
    if len(printed) != 1:
        raise ValueError("Missing or duplicate utilization statistic")
    if (values["vector_width"] != width or values["total_vector_instructions"] <= 0
            or values["total_vector_lanes"] != width * values["total_vector_instructions"]
            or not 0 <= values["utilized_vector_lanes"] <= values["total_vector_lanes"]):
        raise ValueError("Inconsistent width, instruction count or lane counts")
    utilization = 100 * values["utilized_vector_lanes"] / values["total_vector_lanes"]
    if abs(utilization - float(printed[0])) > 0.050000001:
        raise ValueError("Printed utilization disagrees with exact lane counts")
    return {**values, "size": size, "utilization_percent": utilization,
            "printed_utilization_percent": float(printed[0]),
            "clamped_exp_verification": "passed", "array_sum_verification": bonus_status}


def run_logged(arguments, cwd, log_path):
    # Keep the failed process output before inspecting its exit code or markers.
    with log_path.open("w") as stream:
        result = subprocess.run(arguments, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT,
                                text=True, timeout=120)
    if result.returncode:
        raise RuntimeError(f"Exit status {result.returncode}; see {log_path}")
    return log_path.read_text()


def save_csv(path, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def create_report(rows, metadata):
    hardware = metadata['environment']['hardware']
    hardware_keys = ('machdep.cpu.brand_string', 'hw.physicalcpu', 'hw.logicalcpu', 'hw.memsize')
    if all(isinstance(hardware[key], str) for key in hardware_keys):
        machine = (f"{hardware['machdep.cpu.brand_string']}，{hardware['hw.physicalcpu']} 个物理核心、"
                   f"{hardware['hw.logicalcpu']} 个逻辑 CPU，{int(hardware['hw.memsize']) // (1024 ** 3)} GiB 内存")
    else:
        machine = "硬件查询未完整返回；详细状态见 experiments.json"
    utilization = [row["utilization_percent"] for row in rows]
    if all(a > b for a, b in zip(utilization, utilization[1:])):
        trend = "随向量宽度增大而逐步下降"
    elif all(a < b for a, b in zip(utilization, utilization[1:])):
        trend = "随向量宽度增大而逐步上升"
    elif len(set(utilization)) == 1:
        trend = "保持不变"
    else:
        trend = "呈非单调变化"
    lines = [
        "# Problem 2：向量宽度与模拟 SIMD 利用率", "",
        "本实验使用当前工作区的 clampedExpVector 实现，完成 README 要求的 "
        "N=10000、VECTOR_WIDTH=2、4、8、16 扫描。"
        "每种宽度运行两次，指令数和通道计数完全一致；全部正式运行通过必做指数计算及加分求和的结果校验。", "",
        "## 实验方法", "",
        f"- 实验开始：{metadata['started_at']}。平台：{metadata['environment']['platform']}，"
        f"架构：{metadata['environment']['architecture']}。",
        f"- 机器：{machine}。",
        f"- 编译器：{metadata['environment']['clang'].splitlines()[0]}。",
        f"- 编译参数：`{metadata['build']['cxxflags']}`；头文件参数：`{metadata['build']['cppflags']}`。"
        "保持原 Makefile 默认配置，没有增加优化参数。",
        "- 不修改原源码。在临时副本中调整 VECTOR_WIDTH，每种宽度强制重新编译所有编译单元，"
        "独立进程运行 `./myexp -s 10000`；完成后清理副本。",
        "- 保留原输入生成方式：程序未调用 srand，各次独立进程从同一默认 rand 序列开始。"
        "初始化按元素依次调用 rand；尽管缓冲区长度随宽度变化，前 10000 个元素及指数相同。"
        "该输入序列依赖本机 C 运行库，不保证跨平台相同。",
        "- 每种宽度额外检查 N=1、3、5、W−1、W、W+1，去除重复值；"
        "验证输出及额外保护区。求和只在 N 能被 W 整除时执行。",
        "- 利用率从精确整数计数重新计算，并核对程序只保留一位小数的输出。"
        "这些计数是模拟器的确定性统计，不进行墙钟测速，不取性能中位数。", "",
        "## 正式实验结果", "",
        "利用率 = 已启用向量通道数 / 总向量通道数 × 100%；"
        "总向量通道数 = 向量宽度 × 总向量指令数。", "",
        "| 向量宽度 | 总向量指令数 | 已启用通道数 | 总通道数 | 重算利用率 | 程序显示 | 必做校验 | 加分校验 |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for row in rows:
        lines.append(f"| {row['vector_width']} | {row['total_vector_instructions']} | "
                     f"{row['utilized_vector_lanes']} | {row['total_vector_lanes']} | "
                     f"{row['utilization_percent']:.4f}% | {row['printed_utilization_percent']:.1f}% | 通过 | 通过 |")
    lines += ["", "精确计数和未作显示舍入的利用率见 [data.csv](data.csv)。每个配置两次统计一致，表中展示一份代表值。", "",
              "## 利用率趋势与解释", "",
              f"**实测结果：**利用率{trend}；从宽度 2 的 {utilization[0]:.4f}% "
              f"变为宽度 16 的 {utilization[-1]:.4f}%。", "",
              "每个元素的指数来自 rand() % 10，取值为 0–9。向量组内不同元素需要不同次数的乘法；"
              "当前循环在所有非零计数通道完成后才退出。已经完成的通道会被掩码关闭，"
              "但整个组仍要等待尚未完成的通道。向量越宽，一个组内包含较大指数并形成不同完成时间的机会越多，"
              "因此循环中的通道空闲可以解释利用率下降的趋势。这是结合当前实现与输入的解释，"
              "并不是任意程序的利用率都会随宽度下降。", "",
              "N=10000 可被四种宽度整除，正式实验没有不完整尾块，不能把趋势归因于最后一组未填满。"
              "源码中的索引更新、比较和其他向量操作也参与统计。logger 按每条已记录指令的掩码累计通道数，"
              "cntbits 等操作记录为全通道启用，init_ones 本身不记录指令；"
              "整体利用率包含这些操作，不能只用乘法次数推导它。", "",
              "利用率与总指令数是不同指标：较低利用率不等于总模拟指令更多。"
              "按照 README 的简化模型，每条模拟向量指令视为一个周期，可以比较表中的总向量指令数。"
              "这些统计不是 M3 原生 SIMD 的硬件利用率，也不能直接作为真实 CPU 加速比。", "",
              "## 边界检查与加分项", "",
              "| 向量宽度 | 检查的 N | 必做校验 | 求和校验 |", "| ---: | --- | --- | --- |"]
    for width in WIDTHS:
        checks = [run for run in metadata['runs'] if run['kind'] == 'boundary' and run['width'] == width]
        sizes = "、".join(str(run['size']) for run in checks)
        sum_sizes = "、".join(str(run['size']) for run in checks
                             if run['statistics']['array_sum_verification'] == 'passed')
        lines.append(f"| {width} | {sizes} | 全部通过 | N={sum_sizes} 通过；其他按约束跳过 |")
    lines += ["", "边界检查包含程序原有的额外保护区校验，只说明这些已测样例通过，不宣称穷尽任意输入。", "",
              "主程序在调用 arraySumVector 之前输出统计，因此上述指令数和利用率只覆盖必做指数计算。"
              "加分项在正式输入下通过原有校验，但本实验没有独立统计它的指令数或分析其复杂度达标情况。", "",
              "## 记录与复现", "",
              "- [experiments.json](experiments.json)：环境、编译参数、源码哈希、提交及工作区差异哈希，"
              "每次运行的校验和统计，以及日志路径。",
              "- [data.csv](data.csv)：四个正式配置的精确数据。",
              "- logs/：四次构建、全部边界检查及八次正式运行的输出。", "",
              "实验使用未提交的当前工作区源码，HEAD 提交号本身不能代表测量版本；文件哈希以实验记录为准。", "",
              "从仓库根目录执行以下命令可复现；输出目录必须为空，防止覆盖已有结果：", "",
              "```sh", ".venv/bin/python prog2_vecintrin/benchmark.py --output-dir /tmp/cs149-problem2-results", "```", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=SOURCE / "results",
                        help="Empty output directory (default: prog2_vecintrin/results)")
    output = parser.parse_args().output_dir.expanduser().resolve()
    if output.exists() and any(output.iterdir()):
        parser.error(f"Output directory is not empty: {output}")
    source_bytes = {name: (SOURCE / name).read_bytes() for name in SOURCE_FILES}
    git_before = {
        "staged_diff_sha256": sha256(subprocess.check_output(["git", "diff", "--cached", "--binary"], cwd=ROOT)),
        "unstaged_diff_sha256": sha256(subprocess.check_output(["git", "diff", "--binary"], cwd=ROOT)),
    }
    (output / "logs").mkdir(parents=True, exist_ok=True)
    flags = source_bytes['Makefile'].decode()
    metadata = {
        "status": "running", "started_at": now(), "widths": list(WIDTHS), "size": SIZE,
        "repeats": REPEATS, "expected_formal_runs": len(WIDTHS) * REPEATS,
        "completed_formal_runs": 0,
        "input": "Unmodified initValue; independent processes; libc default rand sequence; EXP_MAX=10",
        "git_commit": inspect_command(["git", "rev-parse", "HEAD"]),
        "git_status_at_start": inspect_command(["git", "status", "--short"]),
        **git_before,
        "source_sha256": {name: sha256(data) for name, data in source_bytes.items()},
        "benchmark_sha256": sha256(Path(__file__).read_bytes()),
        "environment": {
            "platform": platform.platform(), "architecture": platform.machine(),
            "python": platform.python_version(),
            "clang": inspect_command(["clang++", "--version"]),
            "make": inspect_command(["make", "--version"]),
            "hardware": {key: inspect_command(["sysctl", "-n", key]) for key in
                         ("machdep.cpu.brand_string", "hw.physicalcpu", "hw.logicalcpu", "hw.memsize")},
        },
        "build": {"cxx": "clang++", "cxxflags": re.search(r"^CXXFLAGS=(.*)$", flags, re.MULTILINE)[1],
                  "cppflags": re.search(r"^CPPFLAGS=(.*)$", flags, re.MULTILINE)[1],
                  "command_template": ["make", "-B", "-C", "<temporary-copy>/prog2_vecintrin", "CXX=clang++"]},
        "reproduce_command": shlex.join([".venv/bin/python", "prog2_vecintrin/benchmark.py",
                                         "--output-dir", str(output)]),
        "builds": [], "runs": [], "repeat_checks": [],
    }
    rows = []

    def checkpoint():
        (output / "experiments.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")

    checkpoint()
    try:
        for width in WIDTHS:
            with tempfile.TemporaryDirectory(prefix=f"cs149-vector-width{width}-") as temp:
                temporary = Path(temp)
                copy = temporary / "prog2_vecintrin"
                copy.mkdir()
                shutil.copytree(ROOT / "common", temporary / "common")
                for name, data in source_bytes.items():
                    (copy / name).write_bytes(data)
                header, count = re.subn(r"^#define[ \t]+VECTOR_WIDTH[ \t]+\d+[ \t]*$", f"#define VECTOR_WIDTH {width}",
                                        source_bytes['CS149intrin.h'].decode(), flags=re.MULTILINE)
                if count != 1:
                    raise ValueError("Expected exactly one VECTOR_WIDTH definition")
                (copy / "CS149intrin.h").write_text(header)
                build_log = f"logs/build-width{width}.log"
                run_logged(["make", "-B", "-C", str(copy), "CXX=clang++"], ROOT, output / build_log)
                executable = copy / "myexp"
                metadata['builds'].append({"width": width, "log": build_log,
                                           "header_sha256": sha256((copy / 'CS149intrin.h').read_bytes()),
                                           "binary_sha256": sha256(executable.read_bytes())})
                boundary_sizes = sorted({1, 3, 5, width - 1, width, width + 1})
                formal = []
                cases = [("boundary", size, 1) for size in boundary_sizes]
                cases += [("formal", SIZE, repeat) for repeat in range(1, REPEATS + 1)]
                for kind, size, repeat in cases:
                    log = f"logs/{kind}-width{width}-size{size}-run{repeat}.log"
                    run = {"kind": kind, "width": width, "size": size, "repeat": repeat,
                           "command": ["./myexp", "-s", str(size)], "log": log, "status": "running"}
                    metadata['runs'].append(run)
                    checkpoint()
                    text = run_logged([str(executable), "-s", str(size)], copy, output / log)
                    statistics = parse_output(text, width, size)
                    run.update(status="passed", statistics=statistics)
                    if kind == "formal":
                        formal.append(statistics)
                        metadata['completed_formal_runs'] += 1
                    checkpoint()
                if formal[0] != formal[1]:
                    raise ValueError(f"Repeated statistics differ at width {width}")
                rows.append({**formal[0], "repeats": REPEATS, "repeat_consistent": True})
                metadata['repeat_checks'].append({"width": width, "identical": True})
                save_csv(output / "data.csv", rows)
                checkpoint()
                print(f"Width {width}: boundaries passed; {formal[0]['total_vector_instructions']} instructions; "
                      f"{formal[0]['utilization_percent']:.4f}% utilization; two identical formal runs", flush=True)
        if metadata['completed_formal_runs'] != metadata['expected_formal_runs'] or len(rows) != len(WIDTHS):
            raise ValueError("Formal experiment is incomplete")
        if any((SOURCE / name).read_bytes() != data for name, data in source_bytes.items()):
            raise RuntimeError("Workspace source changed during the experiment")
        for key, arguments in (("staged_diff_sha256", ["git", "diff", "--cached", "--binary"]),
                               ("unstaged_diff_sha256", ["git", "diff", "--binary"])):
            if sha256(subprocess.check_output(arguments, cwd=ROOT)) != git_before[key]:
                raise RuntimeError("Tracked workspace or index changed during the experiment")
        metadata.update(status="complete", finished_at=now(),
                        completed_boundary_runs=sum(run['kind'] == 'boundary' for run in metadata['runs']),
                        workspace_and_index_unchanged=True,
                        report_generator_sha256=sha256(Path(__file__).read_bytes()))
        (output / "README.md").write_text(create_report(rows, metadata))
        checkpoint()
        print(f"Saved complete results to {output}")
        return 0
    except Exception as error:
        if metadata['runs'] and metadata['runs'][-1]['status'] == 'running':
            metadata['runs'][-1].update(status='failed', error=str(error))
        metadata.update(status="failed", finished_at=now(), error=str(error))
        checkpoint()
        print(f"Experiment stopped: {error}. Saved logs and partial data in {output}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
