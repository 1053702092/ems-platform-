/**
 * LeetCode 704. Binary Search (Easy)
 *
 * 题意：在升序数组中找目标值的索引，不存在返回 -1。
 *
 * 学习要点：
 * - 二分查找 O(log n) 的两种写法（闭区间 [l, r] / 开区间 [l, r)）
 * - 边界条件处理（与 Python bisect 对比）
 * - 控制类岗位手撕代码高频题
 *
 * 编译：g++ -std=c++17 -o build/704_binary_search 704_binary_search.cpp && ./build/704_binary_search
 */

#include <iostream>
#include <vector>

using namespace std;

class Solution {
public:
    // 写法一：闭区间 [left, right]
    int search(vector<int>& nums, int target) {
        int left = 0, right = nums.size() - 1;

        while (left <= right) {  // 闭区间：left == right 时仍要检查
            int mid = left + (right - left) / 2;  // 防溢出

            if (nums[mid] == target) {
                return mid;
            } else if (nums[mid] < target) {
                left = mid + 1;
            } else {
                right = mid - 1;
            }
        }

        return -1;
    }

    // 写法二：开区间 [left, right) — 面试中同样常见
    int searchOpen(vector<int>& nums, int target) {
        int left = 0, right = nums.size();

        while (left < right) {  // 开区间：left == right 时区间为空
            int mid = left + (right - left) / 2;

            if (nums[mid] == target) {
                return mid;
            } else if (nums[mid] < target) {
                left = mid + 1;
            } else {
                right = mid;
            }
        }

        return -1;
    }
};

// ====== 测试 ======
int main() {
    Solution sol;
    vector<int> nums = {-1, 0, 3, 5, 9, 12};

    cout << "Binary Search Test" << endl;
    cout << "nums = [-1, 0, 3, 5, 9, 12]" << endl;

    cout << "\n--- 闭区间写法 ---" << endl;
    cout << "search(9) = " << sol.search(nums, 9) << " (expected: 4)" << endl;
    cout << "search(2) = " << sol.search(nums, 2) << " (expected: -1)" << endl;

    cout << "\n--- 开区间写法 ---" << endl;
    cout << "searchOpen(9) = " << sol.searchOpen(nums, 9) << " (expected: 4)" << endl;
    cout << "searchOpen(2) = " << sol.searchOpen(nums, 2) << " (expected: -1)" << endl;

    return 0;
}
