#!/usr/bin/env bash
set -euo pipefail

APP_SUPPORT="$HOME/Library/Application Support/CGV Presenter Dev"
LOG_FILE="$APP_SUPPORT/launcher.log"
PID_FILE="$APP_SUPPORT/presenter.pid"
LOCK_FILE="$APP_SUPPORT/launching.lock"
CONFIG_FILE="$APP_SUPPORT/project-root"

mkdir -p "$APP_SUPPORT"

setup_runtime_path() {
  local dir
  export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

  if [[ -n "${HOME:-}" ]]; then
    for dir in "$HOME/.fnm/aliases/default/bin" "$HOME/.volta/bin"; do
      [[ -d "$dir" ]] && PATH="$dir:$PATH"
    done

    if [[ -s "$HOME/.nvm/nvm.sh" ]]; then
      for dir in "$HOME/.nvm"/versions/node/*/bin; do
        [[ -d "$dir" ]] && PATH="$dir:$PATH"
      done
    fi
  fi

  export PATH
}

find_tool() {
  local name="$1"
  shift
  local candidate

  setup_runtime_path
  if command -v "$name" >/dev/null 2>&1; then
    command -v "$name"
    return 0
  fi

  for candidate in "$@"; do
    if [[ -x "$candidate" ]]; then
      printf '%s' "$candidate"
      return 0
    fi
  done

  return 1
}

notify() {
  /usr/bin/osascript -e "display notification \"$2\" with title \"$1\"" >/dev/null 2>&1 || true
}

info_alert() {
  /usr/bin/osascript -e "display alert \"$1\" message \"$2\" buttons {\"OK\"} default button \"OK\"" >/dev/null 2>&1 || true
}

error_alert() {
  /usr/bin/osascript -e "display alert \"$1\" message \"$2\" buttons {\"OK\"} default button \"OK\" as critical" >/dev/null 2>&1 || true
}

choose_project_root() {
  local chosen=""
  chosen="$(/usr/bin/osascript <<'EOF'
set picked to choose folder with prompt "Select the roots-presenter folder (CGV Presenter project):"
POSIX path of picked
EOF
)" || return 1

  chosen="${chosen%/}"
  if [[ ! -f "$chosen/package.json" || ! -f "$chosen/main.js" ]]; then
    error_alert "CGV Presenter Dev" "That folder does not look like roots-presenter."
    return 1
  fi

  printf '%s\n' "$chosen" > "$CONFIG_FILE"
  printf '%s' "$chosen"
}

resolve_project_root() {
  local bundled_root script_dir candidate

  script_dir="$(cd "$(dirname "$0")" && pwd)"
  if [[ "$(basename "$(dirname "$(dirname "$script_dir")")")" == *.app ]]; then
    bundled_root="$(cd "$script_dir/../../../.." && pwd 2>/dev/null || true)"
    if [[ "$bundled_root" == "/" || ! -f "$bundled_root/package.json" ]]; then
      bundled_root=""
    fi
  fi
  if [[ -n "$bundled_root" && -f "$bundled_root/package.json" && -f "$bundled_root/main.js" ]]; then
    printf '%s' "$bundled_root"
    return 0
  fi

  if [[ -f "$CONFIG_FILE" ]]; then
    candidate="$(tr -d '\r' < "$CONFIG_FILE")"
    if [[ -f "$candidate/package.json" && -f "$candidate/main.js" ]]; then
      printf '%s' "$candidate"
      return 0
    fi
  fi

  choose_project_root
}

repo_root_for() {
  local project_root="$1"
  if git -C "$project_root" rev-parse --show-toplevel >/dev/null 2>&1; then
    git -C "$project_root" rev-parse --show-toplevel
  else
    dirname "$project_root"
  fi
}

listener_pid() {
  /usr/sbin/lsof -nP -iTCP:3000 -sTCP:LISTEN -t 2>/dev/null | head -1 || true
}

is_presenter_running() {
  [[ -n "$(listener_pid)" ]]
}

acquire_launch_lock() {
  local lock_pid=""

  if [[ -f "$LOCK_FILE" ]]; then
    lock_pid="$(tr -d '\r' < "$LOCK_FILE" 2>/dev/null || true)"
    if [[ -n "$lock_pid" ]] && kill -0 "$lock_pid" 2>/dev/null; then
      info_alert "CGV Presenter Dev" "A launch is already in progress. Wait a few seconds and try again."
      exit 0
    fi
  fi

  printf '%s\n' "$$" > "$LOCK_FILE"
}

release_launch_lock() {
  rm -f "$LOCK_FILE"
}

focus_presenter() {
  local project_root="$1"
  local pid electron_app

  pid="$(listener_pid)"
  if [[ -n "$pid" ]]; then
    /usr/bin/osascript <<EOF >/dev/null 2>&1 || true
tell application "System Events"
  try
    set frontmost of (first process whose unix id is ${pid}) to true
  end try
end tell
EOF
  fi

  electron_app="$project_root/node_modules/electron/dist/Electron.app"
  if [[ -d "$electron_app" ]]; then
    /usr/bin/open "$electron_app" --args "$project_root" >/dev/null 2>&1 || true
  fi
}

use_existing_presenter() {
  local project_root="$1"

  if ! is_presenter_running; then
    return 0
  fi

  focus_presenter "$project_root"
  info_alert "CGV Presenter" "Presenter is already running.

Look for the Electron icon in your Dock, or check the menu bar for a CGV Presenter window behind other apps."
  exit 0
}

require_tools() {
  local npm_bin git_bin

  npm_bin="$(find_tool npm /opt/homebrew/bin/npm /usr/local/bin/npm)" || {
    error_alert "CGV Presenter Dev" "Node.js/npm was not found.

Install Node from https://nodejs.org or Homebrew, then try again."
    exit 1
  }

  git_bin="$(find_tool git /opt/homebrew/bin/git /usr/bin/git)" || {
    error_alert "CGV Presenter Dev" "git was not found on this Mac."
    exit 1
  }

  NPM_BIN="$npm_bin"
  GIT_BIN="$git_bin"
}

wait_for_presenter() {
  local attempt
  for attempt in $(seq 1 45); do
    if is_presenter_running; then
      return 0
    fi
    sleep 1
  done
  return 1
}

start_presenter() {
  local project_root="$1"
  local start_script="$APP_SUPPORT/start-presenter.sh"

  cat > "$start_script" <<EOF
#!/usr/bin/env bash
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:\$PATH"
cd "$project_root"
echo "==== \$(date) ===="
exec "$NPM_BIN" start
EOF
  chmod +x "$start_script"

  echo "==== $(date) launcher ====" >> "$LOG_FILE"
  /usr/bin/nohup "$start_script" >> "$LOG_FILE" 2>&1 &
  echo $! > "$PID_FILE"
  disown -h $! 2>/dev/null || disown $! 2>/dev/null || true
}

main() {
  local project_root repo_root pull_output

  trap release_launch_lock EXIT
  acquire_launch_lock
  require_tools
  project_root="$(resolve_project_root)" || exit 0
  repo_root="$(repo_root_for "$project_root")"

  use_existing_presenter "$project_root"

  notify "CGV Presenter" "Checking for updates..."
  if "$GIT_BIN" -C "$repo_root" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    if pull_output="$("$GIT_BIN" -C "$repo_root" pull --ff-only 2>&1)"; then
      printf '%s\n' "$pull_output" >> "$LOG_FILE"
    else
      printf '%s\n' "$pull_output" >> "$LOG_FILE"
      error_alert "CGV Presenter Dev" "Could not pull the latest changes from git.

$pull_output"
      exit 1
    fi
  fi

  notify "CGV Presenter" "Preparing dependencies..."
  (
    setup_runtime_path
    cd "$project_root"
    "$NPM_BIN" install --no-fund --no-audit
  ) >> "$LOG_FILE" 2>&1

  use_existing_presenter "$project_root"

  notify "CGV Presenter" "Starting..."
  start_presenter "$project_root"

  if wait_for_presenter; then
    sleep 2
    focus_presenter "$project_root"
    info_alert "CGV Presenter" "Presenter is running.

If you do not see the window, check the Electron icon in your Dock."
    exit 0
  fi

  if is_presenter_running; then
    focus_presenter "$project_root"
    info_alert "CGV Presenter" "Presenter is already running on port 3000."
    exit 0
  fi

  error_alert "CGV Presenter Dev" "Presenter did not start within 45 seconds.

If you see a port 3000 error, quit any open Electron/CGV Presenter windows and try again.

Log:
$LOG_FILE"
  exit 1
}

main "$@"
