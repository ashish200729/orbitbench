"""
Executor self-test: feed KNOWN-CORRECT reference solutions through the real
executor for every task and assert a perfect 100/100. This validates the test
harnesses independently of any LLM. Run: python -m tests.verify_executor
"""
import json
import os
import sys

from runner.executor import execute_task
from runner.scorer import score_task, calculate_benchmark_score

REFERENCE = {
    # task_001 — Expression Evaluator (Python)
    "task_001": """
def calculate(expression):
    s = expression.replace(" ", ""); pos = 0
    def expr_():
        nonlocal pos
        v = term_()
        while pos < len(s) and s[pos] in "+-":
            op = s[pos]; pos += 1; r = term_(); v = v + r if op == "+" else v - r
        return v
    def term_():
        nonlocal pos
        v = factor_()
        while pos < len(s) and s[pos] in "*/":
            op = s[pos]; pos += 1; r = factor_()
            if op == "*": v *= r
            else:
                q = abs(v) // abs(r); v = q if (v < 0) == (r < 0) else -q
        return v
    def factor_():
        nonlocal pos
        if s[pos] == "+": pos += 1; return factor_()
        if s[pos] == "-": pos += 1; return -factor_()
        if s[pos] == "(":
            pos += 1; v = expr_(); pos += 1; return v
        start = pos
        while pos < len(s) and s[pos].isdigit(): pos += 1
        return int(s[start:pos])
    return expr_()
""",
    # task_002 — LRU Cache with TTL (Python class)
    "task_002": """
class LRUCache:
    def __init__(self, capacity):
        self.cap = capacity
        self.cache = {}   # key -> [value, expire_at]
        self.order = []   # LRU order, most-recent last

    def _evict_expired(self, now):
        expired = [k for k, (v, e) in self.cache.items() if e <= now]
        for k in expired:
            del self.cache[k]
            if k in self.order: self.order.remove(k)

    def get(self, key, now):
        self._evict_expired(now)
        if key in self.cache:
            self.order.remove(key); self.order.append(key)
            return self.cache[key][0]
        return -1

    def put(self, key, val, ttl, now):
        self._evict_expired(now)
        if self.cap <= 0: return
        if key in self.cache:
            self.cache[key] = [val, now + ttl]
            self.order.remove(key); self.order.append(key)
        else:
            if len(self.cache) >= self.cap:
                lru = self.order.pop(0)
                del self.cache[lru]
            self.cache[key] = [val, now + ttl]
            self.order.append(key)
""",
    # task_003 — LFU Cache (JavaScript)
    "task_003": """
class LFUCache {
  constructor(capacity) {
    this.cap = capacity;
    this.keyVal = new Map();
    this.keyFreq = new Map();
    this.freqKeys = new Map();
    this.minFreq = 0;
  }
  _touch(key) {
    const f = this.keyFreq.get(key);
    const ks = this.freqKeys.get(f);
    ks.delete(key);
    if (ks.size === 0) {
      this.freqKeys.delete(f);
      if (this.minFreq === f) this.minFreq = f + 1;
    }
    this.keyFreq.set(key, f + 1);
    if (!this.freqKeys.has(f + 1)) this.freqKeys.set(f + 1, new Map());
    this.freqKeys.get(f + 1).set(key, true);
  }
  get(key) {
    if (!this.keyVal.has(key)) return -1;
    this._touch(key);
    return this.keyVal.get(key);
  }
  put(key, value) {
    if (this.cap <= 0) return;
    if (this.keyVal.has(key)) { this.keyVal.set(key, value); this._touch(key); return; }
    if (this.keyVal.size >= this.cap) {
      const ks = this.freqKeys.get(this.minFreq);
      const evict = ks.keys().next().value;
      ks.delete(evict); this.keyVal.delete(evict); this.keyFreq.delete(evict);
    }
    this.keyVal.set(key, value);
    this.keyFreq.set(key, 1);
    if (!this.freqKeys.has(1)) this.freqKeys.set(1, new Map());
    this.freqKeys.get(1).set(key, true);
    this.minFreq = 1;
  }
}
""",
    # task_004 — Design Twitter (TypeScript)
    "task_004": """
class Twitter {
  time: number = 0;
  tweets: Map<number, number[][]> = new Map();
  follows: Map<number, Set<number>> = new Map();
  postTweet(userId: number, tweetId: number): void {
    const arr = this.tweets.get(userId) || [];
    arr.push([this.time++, tweetId]);
    this.tweets.set(userId, arr);
  }
  getNewsFeed(userId: number): number[] {
    const users: Set<number> = new Set(this.follows.get(userId) || []);
    users.add(userId);
    let cand: number[][] = [];
    for (const u of users) cand = cand.concat(this.tweets.get(u) || []);
    cand.sort((a, b) => b[0] - a[0]);
    return cand.slice(0, 10).map((x) => x[1]);
  }
  follow(followerId: number, followeeId: number): void {
    const s = this.follows.get(followerId) || new Set();
    s.add(followeeId);
    this.follows.set(followerId, s);
  }
  unfollow(followerId: number, followeeId: number): void {
    if (followerId !== followeeId) {
      const s = this.follows.get(followerId);
      if (s) s.delete(followeeId);
    }
  }
}
""",
    # task_005 — RLE Edit Distance (Python)
    "task_005": """
def rle_edit_distance(s, t):
    def decode(rle):
        return "".join(c * n for c, n in rle)
    a, b = decode(s), decode(t)
    m, n = len(a), len(b)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev, dp[0] = dp[0], i
        for j in range(1, n + 1):
            tmp = dp[j]
            dp[j] = prev if a[i-1] == b[j-1] else 1 + min(prev, dp[j], dp[j-1])
            prev = tmp
    return dp[n]
""",
    # task_006 — Sliding Window Median (Python)
    "task_006": """
import heapq
def median_sliding_window(nums, k):
    lo, hi = [], []  # lo is max-heap (negated), hi is min-heap
    def balance():
        if len(lo) > len(hi) + 1:
            heapq.heappush(hi, -heapq.heappop(lo))
        elif len(hi) > len(lo):
            heapq.heappush(lo, -heapq.heappop(hi))
    def remove(heap, val):
        idx = heap.index(val)
        heap[idx] = heap[-1]; heap.pop()
        if idx < len(heap): heapq._siftup(heap, idx); heapq._siftdown(heap, 0, idx)
    result = []
    for i, num in enumerate(nums):
        if not lo or num <= -lo[0]:
            heapq.heappush(lo, -num)
        else:
            heapq.heappush(hi, num)
        balance()
        if i >= k:
            out = nums[i - k]
            if out <= -lo[0]:
                remove(lo, -out)
            else:
                remove(hi, out)
            balance()
        if i >= k - 1:
            if k % 2 == 1:
                result.append(float(-lo[0]))
            else:
                result.append((-lo[0] + hi[0]) / 2.0)
    return result
""",
    # task_007 — Weighted Job Scheduling with Cooldown (Python)
    "task_007": """
import bisect
def max_weight(jobs, cooldown):
    if not jobs: return 0
    jobs = sorted(jobs, key=lambda x: x[1])
    n = len(jobs)
    dp = [0] * (n + 1)
    for i in range(1, n + 1):
        s, e, w = jobs[i-1]
        lo, hi = 0, i - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if jobs[mid-1][1] + cooldown <= s: lo = mid
            else: hi = mid - 1
        dp[i] = max(dp[i-1], dp[lo] + w)
    return dp[n]
""",
    # task_008 — Matrix Chain with Forbidden Splits (Python)
    "task_008": """
def matrix_chain(dims, forbidden):
    n = len(dims) - 1
    forb = set(tuple(p) for p in forbidden)
    INF = float('inf')
    dp = [[INF] * n for _ in range(n)]
    for i in range(n):
        dp[i][i] = 0
    for length in range(2, n + 1):
        for i in range(n - length + 1):
            j = i + length - 1
            for k in range(i, j):
                # Skip this split if the pair (i,j) is forbidden AND it's a direct
                # multiplication of two adjacent matrices (length==2, no sub-splits)
                if (i, j) in forb and length == 2:
                    continue
                cost = dp[i][k] + dp[k+1][j] + dims[i] * dims[k+1] * dims[j+1]
                if cost < dp[i][j]:
                    dp[i][j] = cost
    r = dp[0][n - 1]
    return -1 if r == INF else r
""",
}


def main():
    task_scores = []
    all_perfect = True
    for fname in sorted(os.listdir("tasks")):
        with open(os.path.join("tasks", fname)) as f:
            task = json.load(f)
        results = execute_task(task, REFERENCE[task["id"]])
        score = score_task(results)
        task_scores.append(score)
        status = "OK " if score["score"] == 100 else "BAD"
        print(f"[{status}] {task['id']} {task['language']:<11} {score['pass_rate']:>6}  {score['score']}/100")
        if score["score"] != 100:
            all_perfect = False
            for r in results:
                if not r["passed"]:
                    print(f"        {r['test_case_id']}: {r.get('error') or ('got ' + str(r.get('result')) + ' want ' + str(r.get('expected')))}")
    print(f"\nFINAL: {calculate_benchmark_score(task_scores)}/100")
    sys.exit(0 if all_perfect else 1)


if __name__ == "__main__":
    main()
