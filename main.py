"""CLI entry point:  python main.py "Summarize today's important emails and create a task list" """
import sys

from hub.agent import Agent

request = " ".join(sys.argv[1:]) or "Summarize today's important emails and create a task list."
result = Agent().run(request)

print(f"\n[mode] {result.mode}\n[request] {request}\n")
for i, s in enumerate(result.steps, 1):
    print(f"  step {i}: {s.tool}({', '.join(s.args)})")
print(f"\n=== FINAL OUTPUT ===\n{result.answer}")
