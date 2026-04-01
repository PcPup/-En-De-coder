#!/usr/bin/env bash
set -euo pipefail

DISPLAY_NUMBER="${DISPLAY_NUMBER:-1}"
DISPLAY_VALUE=":${DISPLAY_NUMBER}"
APT_SOURCE_FILE="/etc/apt/sources.list.d/ubuntu.sources"

ensure_package() {
	if ! dpkg -s "$1" >/dev/null 2>&1; then
		return 1
	fi
}

install_dependencies() {
	local missing=()

	for package in xvfb x11vnc fluxbox websockify novnc; do
		if ! ensure_package "$package"; then
			missing+=("$package")
		fi
	done

	if [ "${#missing[@]}" -gt 0 ]; then
		echo "Installing missing dependencies: ${missing[*]}"
		sudo apt-get update \
			-o Dir::Etc::sourcelist="${APT_SOURCE_FILE}" \
			-o Dir::Etc::sourceparts=/dev/null
		sudo apt-get install -y \
			-o Dir::Etc::sourcelist="${APT_SOURCE_FILE}" \
			-o Dir::Etc::sourceparts=/dev/null \
			"${missing[@]}"
	fi
}

start_if_needed() {
	local process_name="$1"
	shift

	if pgrep -f "$process_name" >/dev/null 2>&1; then
		return 0
	fi

	"$@" >/tmp/"${process_name//[^a-zA-Z0-9]/_}".log 2>&1 &
}

wait_for_display() {
	local attempts=0

	while [ ! -S "/tmp/.X11-unix/X${DISPLAY_NUMBER}" ]; do
		attempts=$((attempts + 1))
		if [ "$attempts" -ge 20 ]; then
			echo "Display ${DISPLAY_VALUE} did not start in time." >&2
			exit 1
		fi
		sleep 0.5
	done
}

install_dependencies

export DISPLAY="${DISPLAY_VALUE}"

echo "Starting virtual display on ${DISPLAY}..."
start_if_needed "Xvfb ${DISPLAY}" Xvfb "${DISPLAY}" -screen 0 1024x768x24
wait_for_display
start_if_needed "fluxbox" fluxbox

echo "Starting VNC server..."
start_if_needed "x11vnc -display ${DISPLAY}" x11vnc -display "${DISPLAY}" -nopw -forever -shared -rfbport 5900

echo "Starting noVNC on port 6080..."
start_if_needed "websockify.* 6080 " websockify --web=/usr/share/novnc 6080 localhost:5900

echo
echo "GUI environment is ready on ${DISPLAY}."
echo "Open port 6080 in the browser after making it public if needed."

if [ "$#" -gt 0 ]; then
	echo "Running command with DISPLAY=${DISPLAY}: $*"
	exec "$@"
fi

echo "Run your GUI app in this same shell, or use: ./start-gui.sh python3 app.py"