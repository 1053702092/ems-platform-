/**
 * LeetCode 20. Valid Parentheses (Easy)
 *
 * 题意：判断括号字符串是否有效。'()', '{}', '[]' 必须正确嵌套。
 *
 * 学习要点：
 * - stack (栈) 的 LIFO 特性
 * - 匹配时检查栈顶元素
 * - 与 Python list 模拟栈的对应
 *
 * 编译：g++ -std=c++17 -o build/20_valid_parentheses 20_valid_parentheses.cpp && ./build/20_valid_parentheses
 */

#include <iostream>
#include <stack>
#include <unordered_map>

using namespace std;

class Solution {
public:
    bool isValid(string s) {
        stack<char> st;
        unordered_map<char, char> pairs = {
            {')', '('},
            {'}', '{'},
            {']', '['}
        };

        for (char c : s) {
            // 是右括号
            if (pairs.find(c) != pairs.end()) {
                // 栈空或不匹配 → 无效
                if (st.empty() || st.top() != pairs[c]) {
                    return false;
                }
                st.pop();  // 匹配成功，弹出左括号
            } else {
                // 左括号 → 入栈
                st.push(c);
            }
        }

        // 所有括号都匹配完才有效
        return st.empty();
    }
};

// ====== 测试 ======
int main() {
    Solution sol;

    cout << "Test 1: '()' → " << (sol.isValid("()") ? "true" : "false") << " (expected: true)" << endl;
    cout << "Test 2: '()[]{}' → " << (sol.isValid("()[]{}") ? "true" : "false") << " (expected: true)" << endl;
    cout << "Test 3: '(]' → " << (sol.isValid("(]") ? "true" : "false") << " (expected: false)" << endl;
    cout << "Test 4: '([)]' → " << (sol.isValid("([)]") ? "true" : "false") << " (expected: false)" << endl;
    cout << "Test 5: '{[]}' → " << (sol.isValid("{[]}") ? "true" : "false") << " (expected: true)" << endl;

    return 0;
}
