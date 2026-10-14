#ifndef MANDELBROT_THREAD_H
#define MANDELBROT_THREAD_H

struct ThreadTiming {
    int threadId;
    int startRow;
    int numRows;
    double startSeconds;
    double endSeconds;
};

void mandelbrotThread(
    int numThreads,
    float x0, float y0, float x1, float y1,
    int width, int height,
    int maxIterations, int output[],
    ThreadTiming* timings = nullptr);

#endif
