#!/usr/bin/env bash
set -euo pipefail

pid_dir="${PRIVATECHAT_LOCALTEST_PID_DIR:-/run/privatechat-localtest/pids}"
mkdir -p "$pid_dir"
rm -f "$pid_dir"/*.pid

declare -A service_pids=()

cleanup() {
	local status=$?
	trap - EXIT INT TERM
	for service in "${!service_pids[@]}"; do
		kill "${service_pids[$service]}" 2>/dev/null || true
	done
	for service in "${!service_pids[@]}"; do
		wait "${service_pids[$service]}" 2>/dev/null || true
	done
	exit "$status"
}

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

check_children() {
	for service in "${!service_pids[@]}"; do
		local pid="${service_pids[$service]}"
		if ! kill -0 "$pid" 2>/dev/null; then
			local status=0
			wait "$pid" || status=$?
			echo "localtest service $service (pid $pid) exited with status $status" >&2
			exit 1
		fi
	done
}

sleep_with_monitor() {
	local seconds="$1"
	local elapsed=0
	while (( elapsed < seconds )); do
		check_children
		sleep 1
		((elapsed += 1))
	done
	check_children
}

start_service() {
	local service="$1"
	echo "run $service ..."
	"./$service" "-f=../etc2/$service.yaml" &
	local pid=$!
	service_pids["$service"]="$pid"
	printf '%s\n' "$pid" > "$pid_dir/$service.pid"
}

bash /app/docker/configure-runtime.sh
cd /app/bin

start_service idgen
sleep_with_monitor 1
start_service status
sleep_with_monitor 1
start_service authsession
sleep_with_monitor 1
start_service dfs
sleep_with_monitor 1
start_service media
sleep_with_monitor 1
start_service biz
sleep_with_monitor 1
start_service msg
sleep_with_monitor 1
start_service sync
sleep_with_monitor 1
start_service bff
sleep_with_monitor 5
start_service session
sleep_with_monitor 1
start_service gnetway

while :; do
	check_children
	sleep 1
done
