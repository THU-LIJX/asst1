"""Run reproducible iterative-sqrt input experiments on the native ISPC build."""

import argparse
import csv
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import platform
import random
import re
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'prog4_sqrt'
CONFIGS = (
    ('random', 'random', None, '原始随机输入'),
    ('user', 'user', None, '你的 2.0–2.1 输入'),
    ('uniform_01', 'uniform', '0.1', '统一 0.1'),
    ('uniform_near3', 'uniform', '2.99999976', '统一 nextafterf(3, 0)'),
    ('uniform_tiny', 'uniform', '1e-30', '统一 1e-30'),
    ('divergent_01', 'divergent', '0.1', '每组 0.1 + 七个 1'),
    ('divergent_299', 'divergent', '2.99', '每组 2.99 + 七个 1'),
)
METRICS = ('serial_ms', 'ispc_ms', 'tasks_ms', 'simd_speedup', 'total_speedup', 'multicore_gain')
LABELS = ('sqrt serial', 'sqrt ispc', 'sqrt task ispc')


def now():
    return datetime.now().astimezone().isoformat()


def inspect(args):
    p = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    return p.stdout.strip() if p.returncode == 0 else {'unavailable': p.stderr.strip()}


def logged(args, path, expected=0):
    with path.open('w') as stream:
        p = subprocess.run(args, cwd=SOURCE, stdout=stream, stderr=subprocess.STDOUT,
                           text=True, timeout=180)
    if p.returncode != expected:
        raise RuntimeError(f'Unexpected exit status {p.returncode}: {path}')
    return path.read_text()


def parse(text, mode, size, seed, value):
    configs = re.findall(r'^SQRT_CONFIG (.+)$', text, re.M)
    if len(configs) != 1 or 'Error:' in text:
        raise ValueError('Missing/duplicate config or failed verification')
    config = json.loads(configs[0])
    if (config['input'] != mode or config['size'] != size or config['seed'] != seed
            or config['initial_guess'] != 1 or config['internal_repeats'] != 3
            or config['gang_width'] != 8
            or config['task_count'] != (size - 1) // ((size - 1) // 64 + 1) + 1
            or (value is not None and not math.isclose(config['value'], float(value), rel_tol=1e-6))):
        raise ValueError(f'Unexpected configuration: {config}')
    times = []
    for label in LABELS:
        hits = re.findall(r'^\[' + re.escape(label) + r'\]:\s*\[([0-9.]+)\] ms$', text, re.M)
        marker = f'VERIFICATION {label} passed trials=3'
        if len(hits) != 1 or text.splitlines().count(marker) != 1:
            raise ValueError(f'Missing/duplicate time or verification: {label}')
        elapsed = float(hits[0])
        if not math.isfinite(elapsed) or elapsed <= 0:
            raise ValueError('Invalid elapsed time')
        times.append(elapsed)
    serial, vector, tasks = times
    ratios = (serial / vector, serial / tasks, vector / tasks)
    for ratio, suffix in zip(ratios, ('speedup from ISPC', 'speedup from task ISPC',
                                     'multicore gain over single-core ISPC')):
        printed = re.findall(r'^\(([0-9.]+)x ' + re.escape(suffix) + r'\)$', text, re.M)
        if len(printed) != 1 or not math.isclose(float(printed[0]), ratio, rel_tol=1e-4, abs_tol=1e-4):
            raise ValueError('Printed speedup disagrees with timings')
    return dict(zip(METRICS, (*times, *ratios)))


def command(mode, size, value=None):
    args = [str(SOURCE / 'sqrt'), '--input', mode, '--size', str(size), '--seed', '1']
    if value is not None:
        args += ['--value', value]
    return args


def save_csv(path, rows):
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def quantile(values, q):
    values = sorted(values)
    position = (len(values) - 1) * q
    low = math.floor(position)
    high = math.ceil(position)
    return values[low] + (values[high] - values[low]) * (position - low)


def summarize(rows, repeats):
    summaries = []
    for name, mode, value, _ in CONFIGS:
        group = [row for row in rows if row['config'] == name]
        if len(group) != repeats or {row['round'] for row in group} != set(range(1, repeats + 1)):
            raise ValueError(f'Incomplete/duplicate data for {name}')
        entry = dict(config=name, input=mode, value=value or '', size=group[0]['size'], runs=repeats)
        for metric in METRICS:
            vals = [row[metric] for row in group]
            for suffix, q in [('q25', .25), ('median', .5), ('q75', .75)]:
                entry[f'{metric}_{suffix}'] = quantile(vals, q)
        summaries.append(entry)
    return summaries


def report(rows, metadata):
    by_name = {row['config']: row for row in rows}
    base = by_name['random']
    uniform = [row for row in rows if row['input'] == 'uniform']
    best = max(uniform, key=lambda row: row['simd_speedup_median'])
    best_total = max(uniform, key=lambda row: row['total_speedup_median'])
    worst = min((row for row in rows if row['input'] == 'divergent'),
                key=lambda row: row['simd_speedup_median'])
    matched = by_name['uniform_01']
    div = by_name['divergent_01']
    hardware = metadata['environment']['hardware']
    hardware_text = '；'.join(f'{key}={value}' for key, value in hardware.items())
    labels = {name: label for name, _, _, label in CONFIGS}
    def fmt(row, key):
        return f"{row[key + '_median']:.2f}"
    lines = [
        '# Problem 4：迭代平方根的 SIMD 与多核实验', '',
        '本目录完成前三个必做问题；不包含手写向量指令的加分题。', '',
        '## 方法与统计口径', '',
        f"实验时间：{metadata['started_at']} 至 {metadata['finished_at']}。"
        f'硬件查询：{hardware_text}。'
        '本轮没有固定核心、改变 QoS 或系统设置；供电与低电量模式状态见环境记录。', '',
        f"- 每种输入 N={metadata['size']:,}，独立启动 {metadata['repeats']} 次。每次三个实现各运行 3 次，"
        '分别取最短时间；表中报告跨启动的中位数。加速比先在每次启动内计算，再汇总中位数和四分位数。',
        '- 正式配置每轮使用种子 7 打乱，逐个运行；输入 rand 种子为 1。'
        '每种配置先预热一次，预热不计入统计。未同时运行其他性能测试。',
        '- SIMD 加速比 = T串行 / T单核ISPC；总加速比 = T串行 / TtaskISPC；'
        '多核额外收益 = T单核ISPC / TtaskISPC。三个中位数因独立统计不要求严格相乘。',
        '- 使用原来的牛顿迭代公式、初值 1、阈值 1e-5、编译优化及 GCD 任务运行时。'
        '不在内核中加入计数或诊断。每次计时前填充 NaN，计时后检查所有元素有限，'
        '绝对误差 ≤ 1e-4 且相对误差 ≤ 1e-5；初始化和校验均不计时。',
        '- C++：`clang++ -O3 -std=c++11 -Wall`；ISPC：'
        '`ispc -O3 --target=neon-i32x8 --arch=aarch64 --pic`。未关闭 FMA。'
        'Clang 与 ISPC 的指令生成、浮点收缩及循环控制可能不同，不能将时间比完全视为通道利用率。',
        '- `neon-i32x8` 的 programCount 为 8，即逻辑 gang 宽度 8；M3 NEON 原生向量宽度为 128 bit，'
        '一次容纳 4 个 float。题目将此目标简称为“8-wide 指令”不够准确，8×不是 M3 的严格加速上限。',
        '- 默认 2000 万输入沿用 64 个 task，每块 312500 个元素。'
        '只修复小规模输入的零 span 和非整除尾块问题，默认规模的划分未变。'
        '任务数不等于核心数，也没有实测每个 task 落在哪类核心。', '',
        '## 1. 原始随机输入', '',
        '输入保留原公式 `0.001f + 2.998f * rand() / RAND_MAX`，独立进程使用相同随机序列。', '',
        f"原始输入的 SIMD 加速为 **{fmt(base, 'simd_speedup')}×**，task 版本相对串行为 "
        f"**{fmt(base, 'total_speedup')}×**；从单核 ISPC 切换到 tasks 的额外收益为 "
        f"**{fmt(base, 'multicore_gain')}×**。后者才是这里的多核加速比。", '',
        '## 完整结果表', '',
        '| 输入 | 串行 ms | 单核 ISPC ms | task ISPC ms | SIMD 加速 | 总加速 | 多核额外收益 |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: |',
    ]
    for row in rows:
        lines.append('| ' + labels[row['config']] + ' | ' + ' | '.join(
            fmt(row, key) + ('×' if key.endswith(('speedup', 'gain')) else '') for key in METRICS) + ' |')
    lines += ['', '各加速比的第 25–75 百分位如下；精确时间及四分位数见 [summary.csv](summary.csv)。', '',
              '| 输入 | SIMD 加速 IQR | 总加速 IQR | 多核额外收益 IQR |',
              '| --- | ---: | ---: | ---: |']
    for row in rows:
        lines.append('| ' + labels[row['config']] + ' | ' + ' | '.join(
            f"{row[key + '_q25']:.2f}–{row[key + '_q75']:.2f}×"
            for key in ('simd_speedup', 'total_speedup', 'multicore_gain')) + ' |')
    lines += ['', '## 2. 提高相对加速比的输入', '',
        f"本轮统一输入中，单核 SIMD 加速比最高的是 **{labels[best['config']]}**："
        f"SIMD **{fmt(best, 'simd_speedup')}×**，总加速 **{fmt(best, 'total_speedup')}×**，"
        f"多核额外收益 **{fmt(best, 'multicore_gain')}×**。"
        f"总加速最高的统一配置为 {labels[best_total['config']]}，"
        f"达到 {fmt(best_total, 'total_speedup')}×。", '',
        '让所有元素取同一个较难收敛的正数，各 lane 的终止条件一致，消除迭代次数差异导致的掩码空转。'
        '较多迭代也能摊薄加载、写回和循环外围开销。`1e-30f` 在题目允许的 (0, 3) 内，'
        '是正常浮点数，但超出了原随机生成器约 [0.001, 2.999] 的范围；'
        '因此同时保留接近 3 的统一输入作为另一组对照。'
        '`2.99999976f` 是小于 3 的最大 float，不能写成 3：初值 1 在 x=3 时下一步成为 0，无法收敛。', '',
        f"相对原始随机输入，所选统一输入的 SIMD 比值为 "
        f"{fmt(best, 'simd_speedup')}× 对 {fmt(base, 'simd_speedup')}×，"
        f"多核额外收益为 {fmt(best, 'multicore_gain')}× 对 {fmt(base, 'multicore_gain')}×。"
        '前者反映相对 SIMD 性能的变化；后者不保证同步提高。消除 gang 内分歧主要改善单核向量执行，'
        '并不会增加可用核心。多核比值还受任务开销、P/E 核算力差异、调度、频率和内存访问影响。', '',
        '你的 `2.0f + 0.1f * rand() / RAND_MAX` 保留为 `--input user`。'
        '它减少总迭代次数，可能降低绝对耗时，但不能据此推出相对串行的加速比更高。'
        '表中的“最优”仅指本次所测候选及机器状态，不声称穷举所有 float 后的数学全局最大值。', '',
        '## 3. 降低单核 ISPC 相对性能的输入', '',
        f"正式分歧配置中最低 SIMD 加速比来自 **{labels[worst['config']]}**："
        f"SIMD **{fmt(worst, 'simd_speedup')}×**，即单核 ISPC 耗时约为串行的 "
        f"**{1 / worst['simd_speedup_median']:.2f} 倍**；task 总加速为 "
        f"**{fmt(worst, 'total_speedup')}×**。", '',
        '按逻辑 gang 宽度 8 构造：`values[i] = (i % 8 == 0 ? slow : 1.0f)`。'
        '`x=1` 在初值 1 时立即满足精度条件；其余每组仅一个 lane 需要反复迭代。'
        '串行能直接跳过七个简单元素，ISPC 的 gang 必须等最慢 lane，循环中最多只有约 1/8 的逻辑 lane 有效。'
        '这只是迭代主体的有效 lane 比例，不是整段程序或物理执行单元的实测利用率。', '',
        f"控制慢值同为 0.1 时，统一输入 SIMD 为 {fmt(matched, 'simd_speedup')}×，"
        f"分歧输入为 {fmt(div, 'simd_speedup')}×。"
        '这一对照支持分歧降低向量效率的解释。mask、终止判断以及代码生成也有成本，'
        '所以实际时间比不会精确等于统一版本的 1/8。tasks 仍可让不同 gang 并行，'
        '但不会消除 gang 内的掩码空转。绝对耗时更短与相对加速比更低可以同时发生。', '',
        '任务版本的块起点有时不按 8 对齐；上述周期输入依然让每个完整连续八元素包含一个慢值，'
        '块尾仅有少量部分 gang。没有通过调整划分或任务数量来改善实验结果。'
        '候选筛选不是全输入空间搜索；“最低”同样仅限本轮正式候选。', '',
        '## 复现与记录', '',
        '在仓库根目录执行：', '', '```sh', 'make -B -C prog4_sqrt',
        './prog4_sqrt/sqrt --input random', './prog4_sqrt/sqrt --input user',
        './prog4_sqrt/sqrt --input uniform --value 1e-30',
        './prog4_sqrt/sqrt --input divergent --value 0.1',
        '.venv/bin/python prog4_sqrt/benchmark.py --output-dir /tmp/sqrt-repeat', '```', '',
        '- [raw.csv](raw.csv)：每次启动的三个最短耗时、重算比值及日志路径。',
        '- [summary.csv](summary.csv)：每配置中位数及第 25、75 百分位。',
        '- [experiments.json](experiments.json)：时间、配置、工具、编译命令、源码标识与校验记录。',
        '- [logs/](logs/)：构建、小规模/无效参数检查、预热和全部正式输出。',
        '- [pilot/](pilot/)：正式实验前的小规模候选筛选；只用于选取配置，不混入正式统计。', '',
        '筛选每个配置仅运行一次、内部仍取三次最短值；它适合发现候选，不能替代完整规模的重复测量。'
        '正式配置固定为原始输入、你的输入、三组统一输入和两组分歧输入，'
        '重复实验使用相同集合，便于复现。', '',
        '本轮没有测量各 lane 的实际指令数、各核心频率或调度轨迹；'
        '关于掩码行为的解释来自输入结构和源码，关于异构核心及频率的影响属于可能原因。', '',
    ]
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--size', type=int, default=20000000)
    parser.add_argument('--repeats', type=int, default=10)
    parser.add_argument('--output-dir', type=Path, default=SOURCE / 'results')
    args = parser.parse_args()
    if args.size < 1 or args.size > 2147483647 or args.repeats < 1:
        parser.error('size must be 1..INT_MAX and repeats must be positive')
    out = args.output_dir.resolve()
    if out.exists() and any(out.iterdir()):
        parser.error('output directory must be empty or absent')
    logs = out / 'logs'
    logs.mkdir(parents=True)
    metadata = dict(status='running', started_at=now(), size=args.size, repeats=args.repeats,
                    input_seed=1, ordering_seed=7, internal_trials=3,
                    configurations=[dict(name=n, mode=m, value=v) for n, m, v, _ in CONFIGS],
                    invocation=shlex.join(sys.argv), commands=[], checks=[])
    meta_path = out / 'experiments.json'
    rows = []
    try:
        metadata['environment'] = dict(platform=platform.platform(), architecture=platform.machine(),
            python=sys.version, clang=inspect(['clang++', '--version']), ispc=inspect(['ispc', '--version']),
            make=inspect(['make', '--version']), power=inspect(['pmset', '-g', 'batt']),
            power_settings=inspect(['pmset', '-g', 'custom']),
            hardware={key: inspect(['sysctl', '-n', key]) for key in (
                'machdep.cpu.brand_string', 'hw.physicalcpu', 'hw.logicalcpu', 'hw.memsize',
                'hw.perflevel0.physicalcpu', 'hw.perflevel1.physicalcpu')})
        files = ['prog4_sqrt/main.cpp', 'prog4_sqrt/sqrt.ispc', 'prog4_sqrt/sqrtSerial.cpp',
                 'prog4_sqrt/Makefile', 'prog4_sqrt/benchmark.py', 'common/CycleTimer.h', 'common/tasksys.cpp']
        metadata['source'] = dict(commit=inspect(['git', 'rev-parse', 'HEAD']),
            status=inspect(['git', 'status', '--short']), diff=inspect(['git', 'diff', 'HEAD', '--', *files]),
            sha256={f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in files})
        metadata['build'] = dict(command='make -B', cxxflags='-I../common -Iobjs/ -O3 -std=c++11 -Wall',
                                 ispcflags='-O3 --target=neon-i32x8 --arch=aarch64 --pic')
        meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n')
        logged(['make', '-B'], logs / 'build.log')
        metadata['executable'] = inspect(['file', str(SOURCE / 'sqrt')])
        for mode in ('random', 'user', 'uniform', 'divergent'):
            for size in (1, 7, 8, 9, 63, 64, 65, 1003):
                args_check = command(mode, size)
                parse(logged(args_check, logs / f'check_{mode}_{size}.log'), mode, size, 1, None)
                metadata['checks'].append(dict(command=shlex.join(args_check), status='passed'))
        for index, invalid in enumerate((['--size', '0'], ['--size', '-1'], ['--input', 'bad'],
                ['--input', 'uniform', '--value', '3'], ['--input', 'uniform', '--value', '0'],
                ['--input', 'uniform', '--value', 'nan'], ['--input', 'random', '--value', '2'])):
            cmd = [str(SOURCE / 'sqrt'), *invalid]
            logged(cmd, logs / f'invalid_{index}.log', expected=1)
            metadata['checks'].append(dict(command=shlex.join(cmd), status='rejected_as_expected'))
        pilot = out / 'pilot'
        pilot.mkdir()
        pilot_rows = []
        pilot_size = min(args.size, 1000000)
        for mode in ('uniform', 'divergent'):
            for value in ('0.001', '0.1', '0.5', '2', '2.1', '2.9', '2.99', '2.999',
                          '2.99999976', '1e-6', '1e-12', '1e-30'):
                cmd = command(mode, pilot_size, value)
                path = pilot / f'{mode}_{value}.log'
                stats = parse(logged(cmd, path), mode, pilot_size, 1, value)
                pilot_rows.append(dict(input=mode, value=value, size=pilot_size, **stats,
                                       command=shlex.join(cmd)))
                save_csv(pilot / 'data.csv', pilot_rows)
        metadata['pilot'] = dict(size=pilot_size, configurations=len(pilot_rows), runs_per_config=1)
        print('Candidate screening passed.', flush=True)
        for name, mode, value, _ in CONFIGS:
            cmd = command(mode, args.size, value)
            parse(logged(cmd, logs / f'warmup_{name}.log'), mode, args.size, 1, value)
            metadata['commands'].append(dict(config=name, command=shlex.join(cmd)))
            print(f'Warmup passed: {name}', flush=True)
        rng = random.Random(7)
        for repeat in range(1, args.repeats + 1):
            configs = list(CONFIGS)
            rng.shuffle(configs)
            for name, mode, value, _ in configs:
                path = logs / f'run_{repeat:02d}_{name}.log'
                stats = parse(logged(command(mode, args.size, value), path), mode, args.size, 1, value)
                rows.append(dict(sequence=len(rows) + 1, round=repeat, config=name, size=args.size,
                                 **stats, verification='passed_all_9_trials', log=str(path.relative_to(out))))
                save_csv(out / 'raw.csv', rows)
                print(f'Run {len(rows)}/{args.repeats * len(CONFIGS)}: {name}, '
                      f"SIMD {stats['simd_speedup']:.2f}x, total {stats['total_speedup']:.2f}x", flush=True)
        summary = summarize(rows, args.repeats)
        save_csv(out / 'summary.csv', summary)
        if any(hashlib.sha256((ROOT / f).read_bytes()).hexdigest() != digest
               for f, digest in metadata['source']['sha256'].items()):
            raise RuntimeError('Source changed during the benchmark')
        metadata['environment']['power_at_end'] = inspect(['pmset', '-g', 'batt'])
        metadata.update(status='complete', finished_at=now(), valid_runs=len(rows))
        (out / 'README.md').write_text(report(summary, metadata))
    except BaseException as error:
        metadata.update(status='failed', finished_at=now(), error=f'{type(error).__name__}: {error}',
                        valid_runs=len(rows))
        raise
    finally:
        meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n')
    print(f'Complete: {out}', flush=True)


if __name__ == '__main__':
    main()
