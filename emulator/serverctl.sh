#!/usr/bin/env bash
# Quản lý Guitar Girl emulator server.
#   ./serverctl.sh start     # khởi động (nền), log -> /tmp/gg_server.log
#   ./serverctl.sh stop      # tắt
#   ./serverctl.sh restart   # tắt rồi khởi động lại
#   ./serverctl.sh status    # xem đang chạy / port / health
#   ./serverctl.sh log       # theo dõi log realtime (Ctrl-C để thoát)
#
# Tuỳ biến: PORT=8080  GG_PUBLIC_BASE=https://ggserver.kotori.click  ./serverctl.sh start
HERE="$(cd "$(dirname "$0")" && pwd)"
PORT="${PORT:-8080}"
LOG="${GG_LOG:-/tmp/gg_server.log}"

# PID nghe trên cổng PORT (chắc chắn đúng tiến trình, không khớp nhầm shell như pgrep)
listen_pid() { ss -ltnp 2>/dev/null | grep ":${PORT} " | grep -oP 'pid=\K[0-9]+' | head -1; }

start() {
  if [ -n "$(listen_pid)" ]; then echo "đã chạy sẵn (pid $(listen_pid)) trên cổng ${PORT}"; return 0; fi
  cd "$HERE"
  nohup python3 run.py --port "$PORT" >"$LOG" 2>&1 & disown
  sleep 2
  if [ -n "$(listen_pid)" ]; then
    echo "started (pid $(listen_pid)) -> http://0.0.0.0:${PORT}  log: $LOG"
  else
    echo "KHỞI ĐỘNG THẤT BẠI — log cuối:"; tail -n 20 "$LOG"; return 1
  fi
}

stop() {
  local pid; pid="$(listen_pid)"
  if [ -z "$pid" ]; then echo "không có server nào nghe cổng ${PORT}"; return 0; fi
  kill "$pid" 2>/dev/null; sleep 2
  pid="$(listen_pid)"; [ -n "$pid" ] && { kill -9 "$pid" 2>/dev/null; sleep 1; }
  [ -z "$(listen_pid)" ] && echo "stopped" || { echo "không tắt được"; return 1; }
}

status() {
  local pid; pid="$(listen_pid)"
  if [ -n "$pid" ]; then echo "RUNNING  pid=$pid  cổng ${PORT}"; else echo "STOPPED (không ai nghe cổng ${PORT})"; fi
  echo -n "health: "; curl -s -m5 "http://127.0.0.1:${PORT}/health" 2>/dev/null || echo "(không phản hồi)"; echo
}

case "${1:-status}" in
  start)   start ;;
  stop)    stop ;;
  restart) stop; start ;;
  status)  status ;;
  log)     tail -f "$LOG" ;;
  *) echo "dùng: $0 {start|stop|restart|status|log}"; exit 2 ;;
esac
