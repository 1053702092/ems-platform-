/**
 * LeetCode 1. Two Sum (Easy)
 *
 * 题意：给定整数数组 nums 和目标值 target，找两数之和等于 target 的索引。
 * 要求：每种输入只有唯一解，不能重复使用同一元素。
 *
 * 学习要点：
 * - unordered_map (哈希表) 的 O(1) 查找
 * - 边遍历边构建哈希表，一次遍历完成
 * - 与 Python dict 的对应关系
 *
 * 编译：g++ -std=c++17 -o build/01_two_sum 01_two_sum.cpp && ./build/01_two_sum
 */

#include <iostream>
#include <vector>
#include <unordered_map>

using namespace std;

class Solution {
public:
    vector<int> twoSum(vector<int>& nums, int target) {
        unordered_map<int, int> seen;  // value -> index

        for (int i = 0; i < nums.size(); i++) {
            int complement = target - nums[i];

            // 在哈希表中找差值
            if (seen.find(complement) != seen.end()) {
                return {seen[complement], i};
            }

            // 当前值存入哈希表
            seen[nums[i]] = i;
        }

        return {};  // 题目保证有解，不会走到这里
    }
};

// ====== 测试 ======
int main() {
    Solution sol;

    // 测试用例 1
    vector<int> nums1 = {2, 7, 11, 15};
    int target1 = 9;
    auto res1 = sol.twoSum(nums1, target1);
    cout << "Test 1: nums=[2,7,11,15], target=9" << endl;
    cout << "  Result: [" << res1[0] << ", " << res1[1] << "]" << endl;
    cout << "  Expected: [0, 1]" << endl;

    // 测试用例 2
    vector<int> nums2 = {3, 2, 4};
    int target2 = 6;
    auto res2 = sol.twoSum(nums2, target2);
    cout << "Test 2: nums=[3,2,4], target=6" << endl;
    cout << "  Result: [" << res2[0] << ", " << res2[1] << "]" << endl;
    cout << "  Expected: [1, 2]" << endl;

    return 0;
}
