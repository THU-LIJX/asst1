#include <stdio.h>
#include <algorithm>
#include <getopt.h>
#include <cstdint>
#include <vector>

#include "CycleTimer.h"
#include "mandelbrotThread.h"

extern void mandelbrotSerial(
    float x0, float y0, float x1, float y1,
    int width, int height,
    int startRow, int numRows,
    int maxIterations,
    int output[]);

extern void writePPMImage(
    int* data,
    int width, int height,
    const char *filename,
    int maxIterations);

void
scaleAndShift(float& x0, float& x1, float& y0, float& y1,
              float scale,
              float shiftX, float shiftY)
{

    x0 *= scale;
    x1 *= scale;
    y0 *= scale;
    y1 *= scale;
    x0 += shiftX;
    x1 += shiftX;
    y0 += shiftY;
    y1 += shiftY;

}

void usage(const char* progname) {
    printf("Usage: %s [options]\n", progname);
    printf("Program Options:\n");
    printf("  -t  --threads <N>  Use N threads\n");
    printf("  -v  --view <INT>   Use specified view settings\n");
    printf("      --thread-timing  Report per-worker timing after verification\n");
    printf("  -?  --help         This message\n");
}

bool verifyResult (int *gold, int *result, int width, int height) {

    int i, j;

    for (i = 0; i < height; i++) {
        for (j = 0; j < width; j++) {
            if (gold[i * width + j] != result[i * width + j]) {
                printf ("Mismatch : [%d][%d], Expected : %d, Actual : %d\n",
                            i, j, gold[i * width + j], result[i * width + j]);
                return 0;
            }
        }
    }

    return 1;
}

int main(int argc, char** argv) {

    const unsigned int width = 1600;
    const unsigned int height = 1200;
    const int maxIterations = 256;
    int numThreads = 2;
    bool threadTiming = false;

    float x0 = -2;
    float x1 = 1;
    float y0 = -1;
    float y1 = 1;

    // parse commandline options ////////////////////////////////////////////
    int opt;
    static struct option long_options[] = {
        {"threads", 1, 0, 't'},
        {"view", 1, 0, 'v'},
        {"thread-timing", 0, 0, 1000},
        {"help", 0, 0, '?'},
        {0 ,0, 0, 0}
    };

    while ((opt = getopt_long(argc, argv, "t:v:?", long_options, NULL)) != EOF) {

        switch (opt) {
        case 1000:
            threadTiming = true;
            break;
        case 't':
        {
            numThreads = atoi(optarg);
            break;
        }
        case 'v':
        {
            int viewIndex = atoi(optarg);
            // change view settings
            if (viewIndex == 2) {
                float scaleValue = .015f;
                float shiftX = -.986f;
                float shiftY = .30f;
                scaleAndShift(x0, x1, y0, y1, scaleValue, shiftX, shiftY);
            } else if (viewIndex > 1) {
                fprintf(stderr, "Invalid view index\n");
                return 1;
            }
            break;
        }
        case '?':
        default:
            usage(argv[0]);
            return 1;
        }
    }
    // end parsing of commandline options

    if (threadTiming && (numThreads < 1 || numThreads > 32)) {
        fprintf(stderr, "Error: Thread timing requires 1 to 32 threads\n");
        return 1;
    }


    int* output_serial = new int[width*height];
    int* output_thread = new int[width*height];
    
    //
    // Run the serial implementation.  Run the code three times and
    // take the minimum to get a good estimate.
    //

    double minSerial = 1e30;
    for (int i = 0; i < 5; ++i) {
       memset(output_serial, 0, width * height * sizeof(int));
        double startTime = CycleTimer::currentSeconds();
        mandelbrotSerial(x0, y0, x1, y1, width, height, 0, height, maxIterations, output_serial);
        double endTime = CycleTimer::currentSeconds();
        minSerial = std::min(minSerial, endTime - startTime);
    }

    printf("[mandelbrot serial]:\t\t[%.3f] ms\n", minSerial * 1000);
    writePPMImage(output_serial, width, height, "mandelbrot-serial.ppm", maxIterations);

    //
    // Run the threaded version
    //

    double minThread = 1e30;
    std::vector<ThreadTiming> workerTimings[5];
    double parallelTimes[5] = {};
    if (threadTiming) {
        for (int i = 0; i < 5; ++i)
            workerTimings[i].resize(numThreads);
    }
    for (int i = 0; i < 5; ++i) {
      memset(output_thread, 0, width * height * sizeof(int));
        double startTime = CycleTimer::currentSeconds();
        mandelbrotThread(numThreads, x0, y0, x1, y1, width, height, maxIterations, output_thread,
                         threadTiming ? workerTimings[i].data() : nullptr);
        double endTime = CycleTimer::currentSeconds();
        minThread = std::min(minThread, endTime - startTime);
        if (threadTiming)
            parallelTimes[i] = (endTime - startTime) * 1000;
    }

    printf("[mandelbrot thread]:\t\t[%.3f] ms\n", minThread * 1000);
    writePPMImage(output_thread, width, height, "mandelbrot-thread.ppm", maxIterations);

    if (! verifyResult (output_serial, output_thread, width, height)) {
        printf ("Error : Output from threads does not match serial output\n");

        delete[] output_serial;
        delete[] output_thread;

        return 1;
    }

    // compute speedup
    printf("\t\t\t\t(%.2fx speedup from %d threads)\n", minSerial/minThread, numThreads);

    if (threadTiming) {
        // The fixed input and row mapping give identical work in all five trials.
        // Scan the verified output only after all timed computation has finished.
        std::uint64_t serialIterations = 0;
        for (unsigned int i = 0; i < width * height; ++i)
            serialIterations += output_serial[i];
        printf("THREAD_TIMING_TOTAL {\"iteration_sum\": %llu, \"width\": %u, "
               "\"height\": %u, \"internal_repeats\": 5}\n",
               static_cast<unsigned long long>(serialIterations), width, height);

        std::vector<std::uint64_t> workIterations(numThreads, 0);
        for (int thread = 0; thread < numThreads; ++thread) {
            const ThreadTiming& timing = workerTimings[0][thread];
            for (int row = timing.startRow; row < timing.startRow + timing.numRows; ++row)
                for (unsigned int column = 0; column < width; ++column)
                    workIterations[thread] += output_thread[row * width + column];
        }
        for (int iteration = 0; iteration < 5; ++iteration) {
            for (const ThreadTiming& timing : workerTimings[iteration]) {
                printf("THREAD_TIMING {\"iteration\": %d, \"thread_id\": %d, "
                       "\"start_row\": %d, \"num_rows\": %d, \"elapsed_ms\": %.6f, "
                       "\"parallel_iteration_ms\": %.6f, \"iteration_sum\": %llu}\n",
                       iteration + 1, timing.threadId, timing.startRow, timing.numRows,
                       (timing.endSeconds - timing.startSeconds) * 1000,
                       parallelTimes[iteration],
                       static_cast<unsigned long long>(workIterations[timing.threadId]));
            }
        }
    }

    delete[] output_serial;
    delete[] output_thread;

    return 0;
}
