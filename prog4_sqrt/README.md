# Problem 4：Iterative sqrt

已完成前三个必做问题。完整答案、性能表格与统计方法见 [实验报告](results/README.md)，逐次记录见 [raw.csv](results/raw.csv)，环境与源码标识见 [experiments.json](results/experiments.json)。不包含手写 NEON 的加分题。

## 运行

在仓库根目录执行：

```sh
make -B -C prog4_sqrt
./prog4_sqrt/sqrt
./prog4_sqrt/sqrt --input user
./prog4_sqrt/sqrt --input uniform --value 1e-30
./prog4_sqrt/sqrt --input divergent --value 0.1
```

| 参数 | 含义 |
| --- | --- |
| `--input random` | 原始随机输入，默认模式 |
| `--input user` | 保留你已有的 `2.0f + 0.1f * rand() / RAND_MAX` 输入 |
| `--input uniform --value X` | 所有元素相同，避免迭代次数分歧 |
| `--input divergent --value X` | 每个逻辑 gang 的第一个元素为 X，其余为 1 |
| `--size N` | 元素数，默认 20000000 |
| `--seed S` | 输入随机种子，默认 1 |

`--value` 仅用于 uniform/divergent，默认取小于 3 的最大 float；初始猜测仍固定为 1。不要使用 3：这一迭代在该端点不会收敛。

每个实现独立计时三次，报告最短时间；每次结果都与标准平方根校验。程序明确返回校验失败状态，并输出机器可读的配置和校验标记。牛顿迭代公式、收敛阈值和优化参数保持原样。

## 重复实验

```sh
.venv/bin/python prog4_sqrt/benchmark.py --output-dir /tmp/sqrt-repeat
```

默认对 7 种输入各重复 10 次，先执行小规模/尾块检查和候选筛选，再预热，最后逐轮打乱配置、顺序测量。每次启动使用三个实现各自内部的三次最短耗时。支持 `--size`、`--repeats`；小规模值只适合检查流程，不应用来代替正式性能结果。

默认输出到本目录的 `results/`。脚本拒绝覆盖非空目录；复跑时指定新的输出目录。失败时立即停止并保留已有记录，不生成完成报告。构建日志、原始运行输出、CSV 和环境记录一起保存，便于追溯。

性能表中的“提高/降低加速比”以本机实测为准。输入一致性改善了 SIMD 的有效通道比例，但同时也会改变串行的迭代成本和分支可预测性，因此不能只看输入是否一致就判断最终加速比。
