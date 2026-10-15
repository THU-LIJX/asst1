#include <algorithm>
#include <cerrno>
#include <climits>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <exception>
#include <getopt.h>
#include <limits>
#include <vector>

#include "CycleTimer.h"
#include "sqrt_ispc.h"

extern void sqrtSerial(int N, float startGuess, float* values, float* output);

static void usage(const char* program) {
    std::printf("Usage: %s [--input random|user|uniform|divergent] [--value X] [--size N] [--seed S]\n", program);
    std::printf("Defaults: random input, N=20000000, seed=1, initial guess=1, three internal trials.\n");
    std::printf("--value applies to uniform/divergent inputs and must be finite and strictly between 0 and 3.\n");
}

static bool parseUnsigned(const char* text, unsigned long long maximum, unsigned long long& value) {
    char* end = nullptr;
    errno = 0;
    value = std::strtoull(text, &end, 10);
    return text[0] != '-' && end != text && *end == '\0' && errno == 0 && value <= maximum;
}

static bool verifyResult(int N, const float* result, const float* gold, const char* label) {
    for (int i = 0; i < N; ++i) {
        const float error = std::fabs(result[i] - gold[i]);
        // Relative validation also catches incorrect zeros for tiny positive inputs.
        if (!std::isfinite(result[i]) || error > 1e-4f || error > 1e-5f * std::fabs(gold[i])) {
            std::fprintf(stderr, "Error: %s [%d] Got %.9g expected %.9g\n", label, i, result[i], gold[i]);
            return false;
        }
    }
    return true;
}

template <typename Kernel>
static bool measureKernel(const char* label, Kernel kernel, int N, float initialGuess,
                          float* values, float* output, const float* gold, double& minimum) {
    minimum = std::numeric_limits<double>::infinity();
    for (int trial = 0; trial < 3; ++trial) {
        // A sentinel catches omitted elements even when the previous kernel was correct.
        std::fill(output, output + N, std::numeric_limits<float>::quiet_NaN());
        const double start = CycleTimer::currentSeconds();
        kernel(N, initialGuess, values, output);
        const double end = CycleTimer::currentSeconds();
        if (!verifyResult(N, output, gold, label))
            return false;
        minimum = std::min(minimum, end - start);
    }
    std::printf("[%s]:\t[%.6f] ms\n", label, minimum * 1000);
    std::printf("VERIFICATION %s passed trials=3\n", label);
    return true;
}

int main(int argc, char** argv) {
    int N = 20 * 1000 * 1000;
    const float initialGuess = 1.0f;
    unsigned int seed = 1;
    const char* input = "random";
    float value = 2.99999976f;
    bool valueSpecified = false;
    const option options[] = {
        {"input", required_argument, nullptr, 'i'},
        {"value", required_argument, nullptr, 'v'},
        {"size", required_argument, nullptr, 's'},
        {"seed", required_argument, nullptr, 'r'},
        {"help", no_argument, nullptr, 'h'},
        {nullptr, 0, nullptr, 0}
    };
    int optionValue;
    while ((optionValue = getopt_long(argc, argv, "i:v:s:r:h", options, nullptr)) != -1) {
        unsigned long long number;
        switch (optionValue) {
        case 'i': input = optarg; break;
        case 'v': {
            char* end = nullptr;
            errno = 0;
            value = std::strtof(optarg, &end);
            if (end == optarg || *end != '\0' || errno != 0 || !std::isfinite(value) || value <= 0 || value >= 3) {
                std::fprintf(stderr, "Error: --value must be finite and strictly between 0 and 3\n");
                return 1;
            }
            valueSpecified = true;
            break;
        }
        case 's':
            if (!parseUnsigned(optarg, INT_MAX, number) || number == 0) {
                std::fprintf(stderr, "Error: --size must be 1..INT_MAX\n");
                return 1;
            }
            N = static_cast<int>(number);
            break;
        case 'r':
            if (!parseUnsigned(optarg, UINT_MAX, number)) {
                std::fprintf(stderr, "Error: --seed must be 0..UINT_MAX\n");
                return 1;
            }
            seed = static_cast<unsigned int>(number);
            break;
        case 'h': usage(argv[0]); return 0;
        default: usage(argv[0]); return 1;
        }
    }
    const bool randomInput = std::strcmp(input, "random") == 0;
    const bool userInput = std::strcmp(input, "user") == 0;
    const bool uniformInput = std::strcmp(input, "uniform") == 0;
    const bool divergentInput = std::strcmp(input, "divergent") == 0;
    if (optind != argc || !(randomInput || userInput || uniformInput || divergentInput)
        || (valueSpecified && !(uniformInput || divergentInput))) {
        usage(argv[0]);
        return 1;
    }

    try {
        const int gangWidth = ispc::sqrt_ispc_program_count();
        if (gangWidth <= 0) {
            std::fprintf(stderr, "Error: Invalid ISPC program count\n");
            return 1;
        }
        const int span = (N - 1) / 64 + 1;
        const int taskCount = (N - 1) / span + 1;
        std::printf("SQRT_CONFIG {\"input\":\"%s\",\"size\":%d,\"seed\":%u,"
                    "\"value\":%.9g,\"initial_guess\":1,\"internal_repeats\":3,"
                    "\"gang_width\":%d,\"task_count\":%d}\n",
                    input, N, seed, value, gangWidth, taskCount);
        std::vector<float> values(N), output(N), gold(N);
        std::srand(seed);
        for (int i = 0; i < N; ++i) {
            if (randomInput)
                values[i] = .001f + 2.998f * static_cast<float>(std::rand()) / RAND_MAX;
            else if (userInput)
                values[i] = 2.0f + 0.1f * static_cast<float>(std::rand()) / RAND_MAX;
            else if (uniformInput)
                values[i] = value;
            else
                values[i] = i % gangWidth == 0 ? value : 1.0f;
            gold[i] = std::sqrt(values[i]);
        }

        double serial, vector, tasks;
        if (!measureKernel("sqrt serial", sqrtSerial, N, initialGuess, values.data(), output.data(), gold.data(), serial)
            || !measureKernel("sqrt ispc", ispc::sqrt_ispc, N, initialGuess, values.data(), output.data(), gold.data(), vector)
            || !measureKernel("sqrt task ispc", ispc::sqrt_ispc_withtasks, N, initialGuess, values.data(), output.data(), gold.data(), tasks))
            return 1;
        std::printf("(%.6fx speedup from ISPC)\n", serial / vector);
        std::printf("(%.6fx speedup from task ISPC)\n", serial / tasks);
        std::printf("(%.6fx multicore gain over single-core ISPC)\n", vector / tasks);
    } catch (const std::exception& error) {
        std::fprintf(stderr, "Error: %s\n", error.what());
        return 1;
    }
    return 0;
}
