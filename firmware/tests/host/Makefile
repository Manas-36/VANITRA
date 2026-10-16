# PC unit tests for the firmware logic (no ESP32 needed).   make -C firmware/tests/host
CXX ?= g++
CXXFLAGS = -std=c++17 -O2 -Wall -Wextra

all: test_glove test_morse
	./test_glove
	./test_morse

test_glove: test_glove.cpp ../../glove_unit/features.h ../../glove_unit/mlp.h ../../glove_unit/model.h test_vectors.h
	$(CXX) $(CXXFLAGS) -o $@ $<

test_morse: test_morse.cpp ../../wristband_unit/morse.h
	$(CXX) $(CXXFLAGS) -o $@ $<

clean:
	rm -f test_glove test_morse
