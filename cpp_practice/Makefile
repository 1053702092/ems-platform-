# C++ Practice Makefile
# 编译所有练习文件

CXX = g++
CXXFLAGS = -std=c++17 -Wall -Wextra -O2
BUILD_DIR = build

LEETCODE_SRCS = $(wildcard leetcode_easy/*.cpp)
EMS_SRCS = $(wildcard ems_basics/*.cpp)
LEETCODE_BINS = $(patsubst leetcode_easy/%.cpp, $(BUILD_DIR)/%, $(LEETCODE_SRCS))
EMS_BINS = $(patsubst ems_basics/%.cpp, $(BUILD_DIR)/%, $(EMS_SRCS))

.PHONY: all leetcode ems clean

all: leetcode ems

leetcode: $(LEETCODE_BINS)
ems: $(EMS_BINS)

$(BUILD_DIR)/%: leetcode_easy/%.cpp | $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) -o $@ $<

$(BUILD_DIR)/%: ems_basics/%.cpp | $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) -o $@ $<

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

clean:
	rm -rf $(BUILD_DIR)

run-all: all
	@echo "\n=== LeetCode Easy ==="
	@for f in $(LEETCODE_BINS); do \
		echo "\n--- $$f ---"; ./$$f; done
	@echo "\n=== EMS Basics ==="
	@for f in $(EMS_BINS); do \
		echo "\n--- $$f ---"; ./$$f; done
