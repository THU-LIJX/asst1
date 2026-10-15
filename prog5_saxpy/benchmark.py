"""Measure SAXPY bandwidth and controlled compiler/task variants in source copies."""

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
import shutil
import statistics
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'prog5_saxpy'
SIZE = 20000000
CXXFLAGS = '-I../common -Iobjs/ -O2 -std=c++11 -Wall'
ISPCFLAGS = '-O3 --target=neon-i32x8 --arch=aarch64 --pic'
VARIANTS = [('default', 8, 64, False), ('no_autovec', 8, 64, True),
            ('neon_x4', 4, 64, False)] + [
                (f'tasks_{n}', 8, n, False) for n in (1, 2, 4, 8, 16, 32, 128)]
METRICS = ('serial_ms', 'ispc_ms', 'tasks_ms', 'simd_speedup', 'total_speedup', 'multicore_gain')


def now():
    return datetime.now().astimezone().isoformat()


def inspect(args):
    p = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    return p.stdout.strip() if p.returncode == 0 else {'unavailable': p.stderr.strip()}


def logged(args, cwd, path):
    with path.open('w') as stream:
        p = subprocess.run(args, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT,
                           timeout=120, text=True)
    if p.returncode:
        raise RuntimeError(f'Exit status {p.returncode}: {path}')
    return path.read_text()


def parse(text):
    # The starter program reports mismatches but still exits with status zero.
    if 'Error:' in text:
        raise ValueError('SAXPY result verification failed')
    result = {}
    for phase, label in (('serial', 'saxpy serial'), ('ispc', 'saxpy ispc'),
                         ('tasks', 'saxpy task ispc')):
        matches = re.findall(r'^\[' + re.escape(label) + r'\]:\s*\[([0-9.]+)\] ms\s*'
                             r'\[([0-9.]+)\] GB/s\s*\[([0-9.]+)\] GFLOPS$', text, re.M)
        if len(matches) != 1:
            raise ValueError(f'Missing/duplicate timing: {label}')
        elapsed, bandwidth, flops = map(float, matches[0])
        if not all(math.isfinite(v) and v > 0 for v in (elapsed, bandwidth, flops)):
            raise ValueError('Invalid performance statistic')
        # Printed times have only three decimals; validate rates within that interval.
        for rate, numerator in ((bandwidth, 16 * SIZE / 2**30), (flops, 2 * SIZE / 1e9)):
            low = numerator / ((elapsed + .0005) / 1000)
            high = numerator / (max(elapsed - .0005, 1e-12) / 1000)
            if not low - .000501 <= rate <= high + .000501:
                raise ValueError('Printed rate is inconsistent with the elapsed time')
        result[f'{phase}_ms'] = elapsed
        result[f'{phase}_printed_gib_s'] = bandwidth
        result[f'{phase}_printed_gflop_s'] = flops
        result[f'{phase}_useful_gb_s'] = 12 * SIZE / (elapsed / 1000) / 1e9
    serial, vector, tasks = (result[f'{p}_ms'] for p in ('serial', 'ispc', 'tasks'))
    result.update(simd_speedup=serial / vector, total_speedup=serial / tasks,
                  multicore_gain=vector / tasks)
    for metric, label in (('simd_speedup', 'ISPC'), ('total_speedup', 'task ISPC'),
                          ('multicore_gain', 'use of tasks')):
        ratios = re.findall(r'\(([0-9.]+)x speedup from ' + re.escape(label) + r'\)', text)
        if len(ratios) != 1 or abs(float(ratios[0]) - result[metric]) > .006:
            raise ValueError('Missing/duplicate/inconsistent speedup')
    return result


def save_csv(path, rows):
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def summaries(raw, repeats):
    rows = []
    for name, width, tasks, no_autovec in VARIANTS:
        group = [r for r in raw if r['variant'] == name]
        if len(group) != repeats or {r['round'] for r in group} != set(range(1, repeats + 1)):
            raise ValueError(f'Incomplete or duplicate records: {name}')
        row = dict(variant=name, logical_width=width, task_count=tasks,
                   cpp_autovec=not no_autovec, size=SIZE, runs=repeats)
        for metric in (*METRICS, *(f'{p}_useful_gb_s' for p in ('serial', 'ispc', 'tasks'))):
            values = [r[metric] for r in group]
            if repeats == 1:
                quartiles = [values[0]] * 3
            else:
                quartiles = statistics.quantiles(values, n=4, method='inclusive')
            for suffix, value in zip(('q25', 'median', 'q75'),
                                     (quartiles[0], statistics.median(values), quartiles[2])):
                row[f'{metric}_{suffix}'] = value
        rows.append(row)
    return rows


def report(rows, meta):
    lines = ['# Problem 5 实验数据', '',
        f"实验时间：{meta['started_at']} 至 {meta['finished_at']}。每个配置独立运行 "
        f"{meta['repeats']} 次，N={SIZE:,}。每次保留原程序的内部三次最短耗时，"
        '统计跨启动中位数及四分位数；比值先按启动计算再取中位数。', '',
        '源码只在临时副本中调整：default 完全沿用工作区输入和构建参数；'
        'no_autovec 仅在 C++ 增加 `-fno-vectorize -fno-slp-vectorize`；'
        'neon_x4 只调整 ISPC 逻辑宽度；tasks_* 只调整任务数。没有改变 SAXPY 算式或减少处理元素。'
        '所有任务数均整除 N，避免原程序非整除划分的问题。', '',
        '每配置预热一次；种子 7 在每轮打乱配置，顺序执行。每个进程内部顺序仍为 C++、单核 ISPC、task ISPC。'
        '保留原程序基于 C++ 结果的两项逐元素校验，任何 Error 输出均视为失败。', '',
        '## 耗时与加速比中位数', '',
        '| 配置 | 逻辑宽度 | tasks | C++ ms | ISPC ms | task ms | C++/ISPC | C++/task | ISPC/task |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for r in rows:
        lines.append(f"| {r['variant']} | {r['logical_width']} | {r['task_count']} | " +
                     ' | '.join(f"{r[k + '_median']:.3f}" for k in METRICS) + ' |')
    lines += ['', 'no_autovec 的 C++ 基线不同，不能把它的加速比当作相对原始 C++ 的优化收益。'
              '各配置相对 default 的改进应比较同类实现的实际耗时。', '',
              '## 耗时第 25–75 百分位', '',
              '| 配置 | C++ ms | ISPC ms | task ms |', '| --- | ---: | ---: | ---: |']
    for r in rows:
        lines.append(f"| {r['variant']} | " + ' | '.join(
            f"{r[k + '_q25']:.3f}–{r[k + '_q75']:.3f}" for k in METRICS[:3]) + ' |')
    lines += ['', '原程序带宽字段以 `16*N / 2^30 / 秒` 计算，实际单位是 GiB/s。'
              '它是假定写分配流量的模型值，不是内存控制器计数。CSV 另列 `12*N / 秒 / 10^9` 的'
              '逻辑有效数据速率，也不声称这是实测 DRAM 流量。', '',
              '- [raw.csv](raw.csv)：所有正式运行、日志路径及统计字段。',
              '- [summary.csv](summary.csv)：中位数、四分位数。',
              '- [experiments.json](experiments.json)：机器、工具、源码哈希、修改差异和构建参数。',
              '- [logs/](logs/)：全部构建、预热与正式输出。',
              '- [codegen/](codegen/)：默认 C++、ISPC 以及禁用自动向量化的汇编和编译诊断。', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repeats', type=int, default=10)
    parser.add_argument('--output-dir', type=Path, default=SOURCE / 'results')
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error('repeats must be positive')
    out = args.output_dir.resolve()
    if out.exists() and any(out.iterdir()):
        parser.error('output directory must be empty or absent')
    logs = out / 'logs'
    codegen = out / 'codegen'
    logs.mkdir(parents=True)
    codegen.mkdir()
    files = ['prog5_saxpy/main.cpp', 'prog5_saxpy/saxpySerial.cpp', 'prog5_saxpy/saxpy.ispc',
             'prog5_saxpy/Makefile', 'prog5_saxpy/benchmark.py', 'common/tasksys.cpp', 'common/CycleTimer.h']
    meta = dict(status='running', started_at=now(), repeats=args.repeats, size=SIZE,
                ordering_seed=7, invocation=shlex.join(sys.argv), variants=[], valid_runs=0)
    raw = []
    try:
        meta['environment'] = dict(platform=platform.platform(), python=sys.version,
            clang=inspect(['clang++', '--version']), ispc=inspect(['ispc', '--version']),
            make=inspect(['make', '--version']), power=inspect(['pmset', '-g', 'batt']),
            power_settings=inspect(['pmset', '-g', 'custom']),
            hardware={key: inspect(['sysctl', '-n', key]) for key in (
                'machdep.cpu.brand_string', 'hw.physicalcpu', 'hw.logicalcpu', 'hw.memsize',
                'hw.perflevel0.physicalcpu', 'hw.perflevel1.physicalcpu')})
        meta['source'] = dict(commit=inspect(['git', 'rev-parse', 'HEAD']),
            diff=inspect(['git', 'diff', 'HEAD', '--', *files]),
            sha256={f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in files})
        (out / 'experiments.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n')
        with tempfile.TemporaryDirectory(prefix='cs149-saxpy-') as temporary:
            directories = {}
            for name, width, tasks, no_autovec in VARIANTS:
                base = Path(temporary) / name
                src = base / 'prog5_saxpy'
                src.mkdir(parents=True)
                shutil.copytree(ROOT / 'common', base / 'common')
                for file in ('main.cpp', 'saxpySerial.cpp', 'saxpy.ispc', 'Makefile'):
                    shutil.copy2(SOURCE / file, src / file)
                if tasks != 64:
                    p = src / 'saxpy.ispc'
                    text = p.read_text()
                    old = 'N / 64;  // 64 tasks'
                    if text.count(old) != 1:
                        raise ValueError('Unexpected task-count source; review replacement')
                    p.write_text(text.replace(old, f'N / {tasks};  // {tasks} tasks'))
                cxxflags = CXXFLAGS + (' -fno-vectorize -fno-slp-vectorize' if no_autovec else '')
                ispcflags = ISPCFLAGS.replace('neon-i32x8', f'neon-i32x{width}')
                cmd = ['make', '-B', f'CXXFLAGS={cxxflags}', f'ISPCFLAGS={ispcflags}']
                logged(cmd, src, logs / f'build_{name}.log')
                meta['variants'].append(dict(name=name, logical_width=width, task_count=tasks,
                    cpp_autovec=not no_autovec, build_command=shlex.join(cmd),
                    executable=inspect(['file', str(src / 'saxpy')]),
                    ispc_source_sha256=hashlib.sha256((src / 'saxpy.ispc').read_bytes()).hexdigest()))
                directories[name] = src
                if name in ('default', 'no_autovec'):
                    flags = cxxflags.split()
                    logged(['clang++', *flags, '-Rpass=loop-vectorize', '-Rpass-missed=loop-vectorize',
                            '-S', 'saxpySerial.cpp', '-o', str(codegen / f'{name}_cpp.s')],
                           src, codegen / f'{name}_vectorization.log')
                if name == 'default':
                    logged(['ispc', *ispcflags.split(), '--emit-asm', 'saxpy.ispc',
                            '-o', str(codegen / 'default_ispc.s')], src, codegen / 'ispc_codegen.log')
            for name, *_ in VARIANTS:
                parse(logged(['./saxpy'], directories[name], logs / f'warmup_{name}.log'))
            print('Builds, assembly capture and warmups passed.', flush=True)
            rng = random.Random(7)
            for repeat in range(1, args.repeats + 1):
                variants = list(VARIANTS)
                rng.shuffle(variants)
                for name, *_ in variants:
                    path = logs / f'run_{repeat:02d}_{name}.log'
                    stats = parse(logged(['./saxpy'], directories[name], path))
                    raw.append(dict(sequence=len(raw) + 1, round=repeat, variant=name, **stats,
                                    verification='no_mismatches', log=str(path.relative_to(out))))
                    save_csv(out / 'raw.csv', raw)
                    print(f"Run {len(raw)}/{len(VARIANTS) * args.repeats}: {name}, "
                          f"ISPC {stats['ispc_ms']:.3f} ms, tasks {stats['tasks_ms']:.3f} ms", flush=True)
        summary = summaries(raw, args.repeats)
        if any(hashlib.sha256((ROOT / f).read_bytes()).hexdigest() != digest
               for f, digest in meta['source']['sha256'].items()):
            raise RuntimeError('Workspace source changed during measurement')
        save_csv(out / 'summary.csv', summary)
        meta.update(status='complete', finished_at=now(), valid_runs=len(raw))
        meta['environment']['power_at_end'] = inspect(['pmset', '-g', 'batt'])
        (out / 'README.md').write_text(report(summary, meta))
    except BaseException as error:
        meta.update(status='failed', finished_at=now(), valid_runs=len(raw),
                    error=f'{type(error).__name__}: {error}')
        raise
    finally:
        (out / 'experiments.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n')
    print(f'Complete: {out}', flush=True)


if __name__ == '__main__':
    main()
