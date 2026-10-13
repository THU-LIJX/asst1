# 在 Apple Silicon Mac 上完成 Assignment 1

本地配置面向 ARM 原生开发、运行和调试。实验题目参考 `README_aarch64.md`；性能结论以自己的机器实测为准。

## 已验证的环境

2026-10-13 完成环境配置与验证：

| 项目 | 配置 |
| --- | --- |
| CPU | Apple M3，ARM64 |
| 核心 | 4 个性能核心 + 4 个能效核心，8 个物理 / 逻辑核心 |
| 内存 | 16 GiB |
| 操作系统 | macOS 26.5.2，构建号 25F84 |
| C++ 编译器 | Apple Clang 16.0.0（clang-1600.0.26.4），C++11 |
| ISPC | 1.31.0，LLVM 23.1.3 |
| Python | 3.13.1，项目内 `.venv` |
| 绘图与分析 | NumPy 2.5.4、matplotlib 3.11.2、scikit-learn 1.9.1 |

六个程序的 Makefile 默认使用 `clang++`，已移除 `-m64` 和 `-march=native`。Program 1、3、4、6 的 C++ 优化等级为 `-O3`，Program 5 为 `-O2`，Program 2 保持原来的未指定优化等级。

Program 3–5 的 ISPC 参数为 `-O3 --target=neon-i32x8 --arch=aarch64 --pic`。Program 3 另保留 `--opt=disable-fma` 和 C++ 的 `-ffp-contract=off`，使浮点结果与参考实现一致。任务并行使用现有 macOS GCD 运行时，计时沿用 `std::chrono::steady_clock`。

## 安装与重建 Python 环境

下面的命令从仓库根目录执行。当前机器已经安装并验证，无需重复安装。

```bash
brew install ispc
ispc --version
clang++ --version
python3 --version

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-macos.txt
python -m pip check
```

`requirements-macos.txt` 固定了本次验证通过的直接与间接依赖。Program 6 的原始 `requirements.txt` 保留不变；本地 Python 3.13 环境使用根目录的 macOS 依赖文件。

后续每次打开终端，需要使用 Python 绘图时执行 `source .venv/bin/activate`；结束时执行 `deactivate`。

## 编译与运行

从仓库根目录编译所有程序，按顺序执行：

```bash
make -C prog1_mandelbrot_threads
make -C prog2_vecintrin
make -C prog3_mandelbrot_ispc
make -C prog4_sqrt
make -C prog5_saxpy
make -C prog6_kmeans
```

运行时进入对应程序目录，使图片、日志和数据路径落在正确位置。下表的命令均在对应目录内执行：

| 目录 | 运行命令 |
| --- | --- |
| `prog1_mandelbrot_threads` | `./mandelbrot -t 2 --view 1` |
| `prog2_vecintrin` | `./myexp -s 16`；实现后可用 `./myexp -s 3`、`./myexp -s 10000` |
| `prog3_mandelbrot_ispc` | `./mandelbrot_ispc --view 1`、`./mandelbrot_ispc --view 2 --tasks` |
| `prog4_sqrt` | `./sqrt` |
| `prog5_saxpy` | `./saxpy` |
| `prog6_kmeans` | 准备 `data.dat` 后执行 `./kmeans`，再执行 `python plot.py` |

需要完整重编译时，可使用 `make -B -C <程序目录>`。原有 `make clean` 还会删除该程序生成的图片等输出；Program 6 也会删除生成的日志。

调试示例：

```bash
cd prog1_mandelbrot_threads
make -B CXXFLAGS='-I../common -Iobjs/ -O0 -g -std=c++11 -Wall -fPIC'
lldb ./mandelbrot
```

在 LLDB 中执行 `run -t 2` 启动。调试构建会影响计时；性能实验前用 `make -B` 恢复该程序默认的优化构建。

## 验证结果与待完成部分

- 六个程序均从无构建产物的状态成功编译，`file` 确认为 ARM64 Mach-O 可执行文件。
- Program 3 的两个视图分别验证了无任务与任务并行模式，均通过内置结果校验。
- Program 4、5 的现有实现均正常运行，内置校验没有输出错误。
- Program 1 已验证串行计算、图片输出和两个线程启动；线程工作函数仍为原始 TODO，因此线程结果校验失败并以状态码 1 退出。
- Program 2 的串行参考计算可以运行；向量指数与求和仍为原始 TODO，输出 `Failed` 属于待实现作业逻辑。该程序即使校验失败也可能以状态码 0 退出。
- Program 6 编译成功，尚未准备 `data.dat`；启动时会报告缺少数据并退出。本阶段没有生成数据或执行聚类与 `plot.py`。
- Python 已验证三个库导入、PCA 二维投影及 PNG 绘图，`pip check` 通过。验证使用临时数据与图片，没有生成 K-means 数据集。

算法源码、函数接口和二进制数据格式均保持原样。Program 6 原有未使用变量警告不影响构建。

## 记录性能实验

Program 1 的线程数由 `-t` 指定；Program 3 的 `--tasks` 使用原有两个任务；其他 ISPC 程序的任务划分见各自源码，工作线程由 GCD 调度。环境验证只确认运行与正确性，输出时间不作为正式性能基线。

每次实验记录：机器与工具链版本、输入或视图、线程数或任务数、优化参数、重复次数、串行与并行时间以及加速比。保持供电、关闭低电量模式，并减少其他高负载程序。针对这台 M3，可在完成 Program 1 后比较 1、2、3、4、8、16 个线程，结合性能核心和能效核心解释曲线。

更新环境记录时可使用：

```bash
sw_vers
sysctl -n machdep.cpu.brand_string
sysctl hw.physicalcpu hw.logicalcpu hw.memsize
sysctl hw.perflevel0.physicalcpu hw.perflevel1.physicalcpu
clang++ --version
ispc --version
python --version
```
