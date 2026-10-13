CXX=clang++
CXXFLAGS=-std=c++11
CPPFLAGS=-I../common

.PHONY: all clean

all: myexp

logger.o: logger.cpp logger.h CS149intrin.h CS149intrin.cpp
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -c logger.cpp

CS149intrin.o: CS149intrin.cpp CS149intrin.h logger.cpp logger.h
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -c CS149intrin.cpp

myexp: CS149intrin.o logger.o main.cpp
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) logger.o CS149intrin.o main.cpp $(LDFLAGS) -o myexp

clean:
	rm -f *.o myexp *~
