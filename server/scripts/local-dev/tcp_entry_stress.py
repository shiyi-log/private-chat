#!/usr/bin/env python3
import argparse
import socket
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


def parse_args():
    parser = argparse.ArgumentParser(description="私有聊天服务端入口 TCP 短连接压测")
    parser.add_argument("--host", default="127.0.0.1", help="目标主机，默认 127.0.0.1")
    parser.add_argument("--ports", default="5222,10443,11443", help="逗号分隔端口，默认 5222,10443,11443")
    parser.add_argument("--requests", type=int, default=500, help="每个端口连接次数，默认 500")
    parser.add_argument("--concurrency", type=int, default=50, help="每个端口并发数，默认 50")
    parser.add_argument("--timeout", type=float, default=2.0, help="单次连接超时秒数，默认 2.0")
    return parser.parse_args()


def connect_once(host, port, timeout):
    started = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            pass
        return True, (time.perf_counter() - started) * 1000.0, ""
    except OSError as exc:
        return False, (time.perf_counter() - started) * 1000.0, str(exc)


def percentile(values, percent):
    if not values:
        return 0.0
    ordered = sorted(values)
    index = int(round((len(ordered) - 1) * percent / 100.0))
    return ordered[index]


def run_port(host, port, requests, concurrency, timeout):
    started = time.perf_counter()
    latencies = []
    errors = {}
    ok_count = 0
    workers = max(1, min(concurrency, requests))

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(connect_once, host, port, timeout) for _ in range(requests)]
        for future in as_completed(futures):
            ok, latency, error = future.result()
            if ok:
                ok_count += 1
                latencies.append(latency)
            else:
                errors[error] = errors.get(error, 0) + 1

    elapsed = time.perf_counter() - started
    failed_count = requests - ok_count
    return {
        "port": port,
        "requests": requests,
        "ok": ok_count,
        "failed": failed_count,
        "elapsed": elapsed,
        "qps": requests / elapsed if elapsed > 0 else 0.0,
        "min_ms": min(latencies) if latencies else 0.0,
        "avg_ms": statistics.fmean(latencies) if latencies else 0.0,
        "p95_ms": percentile(latencies, 95),
        "max_ms": max(latencies) if latencies else 0.0,
        "errors": errors,
    }


def main():
    args = parse_args()
    ports = [int(item.strip()) for item in args.ports.split(",") if item.strip()]

    print("私有聊天服务端入口 TCP 短连接压测")
    print(f"- 目标：{args.host}")
    print(f"- 端口：{', '.join(str(port) for port in ports)}")
    print(f"- 每端口连接次数：{args.requests}")
    print(f"- 每端口并发数：{args.concurrency}")
    print(f"- 单次超时：{args.timeout:.1f}s")
    print("")

    has_failure = False
    for port in ports:
        result = run_port(args.host, port, args.requests, args.concurrency, args.timeout)
        if result["failed"]:
            has_failure = True
        print(
            f"端口 {result['port']}：成功 {result['ok']}/{result['requests']}，"
            f"失败 {result['failed']}，耗时 {result['elapsed']:.2f}s，"
            f"吞吐 {result['qps']:.1f} 次/秒，"
            f"延迟 min/avg/p95/max = "
            f"{result['min_ms']:.2f}/{result['avg_ms']:.2f}/{result['p95_ms']:.2f}/{result['max_ms']:.2f} ms"
        )
        for error, count in sorted(result["errors"].items(), key=lambda item: item[1], reverse=True):
            print(f"  - {count} 次失败：{error}")

    print("")
    print("说明：该脚本只验证入口 TCP 短连接稳定性，不等同于登录、收发消息、上传文件等完整业务压测。")
    return 1 if has_failure else 0


if __name__ == "__main__":
    sys.exit(main())
