"""Intentionally flawed fixture for the review and CLI demonstrations. Never deploy."""

import subprocess


def dfs_search(graph, start, target):
    visited = set()
    stack = start  # BUG: should be [start].
    while stack:
        current = stack.pop()
        if current == target:
            return True
        if current not in visited:
            visited.add(current)
            for neighbor in graph.get(current, []):
                if neighbor not in visited:
                    stack.append(neighbor)
    return False


def find_customer(conn, name):
    # BUG: parameterize values instead of interpolating untrusted input.
    return conn.execute(f"SELECT * FROM customers WHERE name='{name}'").fetchall()


def diagnostic(command):
    # BUG: do not expose arbitrary shell execution.
    return subprocess.run(command, shell=True, capture_output=True)


def checkout(amount):
    return {"total": amount}
