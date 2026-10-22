#!/usr/bin/env bash
# ==============================================================================
#  🎸 GUITAR GIRL SERVER - CONTROL CENTER & LIVE MONITOR
#  Khởi động server chạy nền độc lập (Detached daemon)
#  Giao diện Terminal TUI trực quan, theo dõi realtime CPU, RAM, Disk, Status, Logs
# ==============================================================================

set -o pipefail

# Thư mục gốc dự án
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EMULATOR_DIR="$ROOT_DIR/emulator"
TOOLS_DIR="$ROOT_DIR/tools"

# Tải cấu hình môi trường (.env) nếu có
[ -f "$ROOT_DIR/.env" ] && set -a && . "$ROOT_DIR/.env" && set +a
[ -f "$EMULATOR_DIR/.env" ] && set -a && . "$EMULATOR_DIR/.env" && set +a

PORT="${PORT:-8080}"
LOG_FILE="${GG_LOG:-/tmp/gg_server.log}"
GG_PUBLIC_BASE="${GG_PUBLIC_BASE:-https://kotori.click}"
GG_ADMIN_PASSWORD="${GG_ADMIN_PASSWORD:-admin123}"

# Mã màu ANSI
BOLD='\033[1m'
DIM='\033[2m'
RED='\033[1;38;5;203m'
GREEN='\033[1;38;5;48m'
YELLOW='\033[1;38;5;220m'
BLUE='\033[1;38;5;75m'
MAGENTA='\033[1;38;5;213m'
CYAN='\033[1;38;5;51m'
WHITE='\033[1;38;5;231m'
GRAY='\033[38;5;244m'
BORDER='\033[38;5;45m'
NC='\033[0m'

# Tìm PID đang lắng nghe trên cổng PORT
listen_pid() {
    local pid
    pid=$(ss -ltnp 2>/dev/null | grep ":${PORT} " | grep -oP 'pid=\K[0-9]+' | head -1)
    if [ -z "$pid" ]; then
        pid=$(pgrep -f 'run.py --host' 2>/dev/null | head -1)
    fi
    echo "$pid"
}

# Lấy thông tin tài nguyên tiến trình server
get_process_stats() {
    local pid="$1"
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        ps -p "$pid" -o %cpu,%mem,rss,etime --no-headers 2>/dev/null | awk '{
            rss_mb = $3 / 1024;
            printf "CPU: %.1f%%  |  RAM: %.1f MB (%.1f%%)  |  Uptime: %s", $1, rss_mb, $2, $4
        }'
    else
        echo "Không khả dụng"
    fi
}

# Khởi động server dạng daemon nền độc lập
start_server() {
    local pid=$(listen_pid)
    if [ -n "$pid" ]; then
        echo -e "${YELLOW}Server đã đang chạy (PID: ${BOLD}$pid${NC}${YELLOW}) trên cổng ${BOLD}$PORT${NC}${YELLOW}!${NC}"
        return 0
    fi

    echo -e "${CYAN}Đang khởi động Guitar Girl Server ở chế độ nền (Detached daemon)...${NC}"
    cd "$EMULATOR_DIR" || exit 1
    
    # setsid + redirect /dev/null giúp tiến trình tách rời shell và không bị kill khi ngắt SSH
    setsid env GG_PUBLIC_BASE="$GG_PUBLIC_BASE" GG_ADMIN_PASSWORD="$GG_ADMIN_PASSWORD" PORT="$PORT" \
        python3 -u run.py --host "127.0.0.1" --port "$PORT" </dev/null >>"$LOG_FILE" 2>&1 &
    
    disown 2>/dev/null || true
    sleep 2

    pid=$(listen_pid)
    if [ -n "$pid" ]; then
        echo -e "${GREEN}╭────────────────────────────────────────────────────────────╮${NC}"
        echo -e "${GREEN}│${NC}  ${BOLD}${WHITE}✓ SERVER ĐÃ KHỞI ĐỘNG THÀNH CÔNG!${NC}                        ${GREEN}│${NC}"
        echo -e "${GREEN}├────────────────────────────────────────────────────────────┤${NC}"
        echo -e "${GREEN}│${NC}  • PID tiến trình:  ${BOLD}${CYAN}$pid${NC}"
        echo -e "${GREEN}│${NC}  • Cổng lắng nghe:  ${BOLD}${WHITE}$PORT${NC} (TCP / IPv4)"
        echo -e "${GREEN}│${NC}  • Public URL:      ${BOLD}${CYAN}$GG_PUBLIC_BASE${NC}"
        echo -e "${GREEN}│${NC}  • Web Admin:       ${BOLD}${MAGENTA}$GG_PUBLIC_BASE/admin${NC}"
        echo -e "${GREEN}│${NC}  • Mật khẩu Admin:  ${BOLD}${YELLOW}$GG_ADMIN_PASSWORD${NC}"
        echo -e "${GREEN}│${NC}  • Tệp nhật ký:     ${BOLD}$LOG_FILE${NC}"
        echo -e "${GREEN}├────────────────────────────────────────────────────────────┤${NC}"
        echo -e "${GREEN}│${NC}  ${GRAY}Server đã chạy nền an toàn (Ngắt SSH server vẫn chạy!)${NC}  ${GREEN}│${NC}"
        echo -e "${GREEN}╰────────────────────────────────────────────────────────────╯${NC}"
    else
        echo -e "${RED}✗ Khởi động THẤT BẠI! 25 dòng nhật ký lỗi cuối cùng:${NC}"
        tail -n 25 "$LOG_FILE" 2>/dev/null || echo "(Không có log)"
        return 1
    fi
}

# Tắt server
stop_server() {
    local pid=$(listen_pid)
    if [ -z "$pid" ]; then
        echo -e "${YELLOW}Không có server nào đang lắng nghe trên cổng $PORT.${NC}"
        return 0
    fi

    echo -e "${CYAN}Đang dừng server (PID: $pid)...${NC}"
    kill "$pid" 2>/dev/null
    sleep 2
    pid=$(listen_pid)
    if [ -n "$pid" ]; then
        echo -e "${YELLOW}Tiến trình chưa dừng, đang cưỡng chế dừng (kill -9 $pid)...${NC}"
        kill -9 "$pid" 2>/dev/null
        sleep 1
    fi

    if [ -z "$(listen_pid)" ]; then
        echo -e "${GREEN}✓ Đã dừng server thành công!${NC}"
    else
        echo -e "${RED}✗ Không thể dừng server (PID: $(listen_pid))!${NC}"
        return 1
    fi
}

# Khởi động lại server
restart_server() {
    echo -e "${CYAN}Đang khởi động lại Guitar Girl Server...${NC}"
    stop_server
    sleep 1
    start_server
}

# Hiển thị trạng thái chi tiết (CLI mode)
show_status() {
    local pid=$(listen_pid)
    echo -e "${BORDER}╭────────────────────────────────────────────────────────────╮${NC}"
    echo -e "${BORDER}│${NC}  ${BOLD}${WHITE}🎸 GUITAR GIRL EMULATOR SERVER - TRẠNG THÁI${NC}              ${BORDER}│${NC}"
    echo -e "${BORDER}├────────────────────────────────────────────────────────────┤${NC}"
    if [ -n "$pid" ]; then
        echo -e "${BORDER}│${NC}  • Trạng thái:     ${GREEN}${BOLD}● RUNNING${NC}"
        echo -e "${BORDER}│${NC}  • PID:            ${BOLD}${CYAN}$pid${NC}"
        echo -e "${BORDER}│${NC}  • Cổng:           ${BOLD}${WHITE}$PORT${NC}"
        echo -e "${BORDER}│${NC}  • Public URL:     ${BOLD}${CYAN}$GG_PUBLIC_BASE${NC}"
        echo -e "${BORDER}│${NC}  • Admin URL:      ${BOLD}${MAGENTA}$GG_PUBLIC_BASE/admin${NC}"
        echo -e "${BORDER}│${NC}  • Mật khẩu:       ${BOLD}${YELLOW}$GG_ADMIN_PASSWORD${NC}"
        echo -e "${BORDER}│${NC}  • Tài nguyên:     ${GRAY}$(get_process_stats "$pid")${NC}"
        
        local health
        health=$(curl -s -m 1 "http://127.0.0.1:${PORT}/health" 2>/dev/null || echo "FAIL")
        if [ "$health" = "GG emulator OK" ]; then
            echo -e "${BORDER}│${NC}  • Health Check:   ${GREEN}${BOLD}● 200 OK${NC}"
        else
            echo -e "${BORDER}│${NC}  • Health Check:   ${RED}${BOLD}● FAIL ($health)${NC}"
        fi
    else
        echo -e "${BORDER}│${NC}  • Trạng thái:     ${RED}${BOLD}● STOPPED${NC} (Cổng $PORT chưa mở)"
    fi
    echo -e "${BORDER}│${NC}  • File Log:       ${GRAY}$LOG_FILE${NC}"
    echo -e "${BORDER}╰────────────────────────────────────────────────────────────╯${NC}"
}

# Xem logs trực tiếp với bộ lọc
view_logs() {
    echo -e "${CYAN}Đang theo dõi log trực tiếp từ ${BOLD}$LOG_FILE${NC} (Nhấn ${BOLD}Ctrl+C${NC} để dừng)..."
    touch "$LOG_FILE"
    tail -n 80 -f "$LOG_FILE" | grep --line-buffered -v -E "(/health|\"GET / HTTP|\"GET /admin|CONNECT|/SDK/| 404 -| 501 -)"
}

# Dọn dẹp sạch toàn bộ database và capture
clear_all_data() {
    echo -e "${YELLOW}${BOLD}⚠️  CẢNH BÁO: Thao tác này sẽ xóa sạch toàn bộ Database và các file Capture!${NC}"
    read -rp "Sensei có chắc chắn muốn xóa không? [y/N]: " confirm
    if [[ ! "$confirm" =~ ^[yY]$ ]]; then
        echo -e "${GRAY}Đã hủy thao tác.${NC}"
        return 0
    fi

    local was_running=0
    local pid=$(listen_pid)
    if [ -n "$pid" ]; then
        was_running=1
        echo -e "${CYAN}Đang tạm dừng server để làm sạch dữ liệu...${NC}"
        stop_server
    fi

    echo -e "${CYAN}Đang làm sạch Database và Captures...${NC}"
    rm -f "$EMULATOR_DIR/data/database.db"* "$EMULATOR_DIR/data/"*.migrated
    mkdir -p "$EMULATOR_DIR/data"
    
    PYTHONPATH="$EMULATOR_DIR" python3 -c "
from server.state import init_db
init_db()
print('✓ Đã khởi tạo lại cấu trúc bảng cơ sở dữ liệu trống thành công!')
"

    rm -f "$EMULATOR_DIR/captures/"*.json "$EMULATOR_DIR/captures/banned/"*.json 2>/dev/null || true
    mkdir -p "$EMULATOR_DIR/captures/banned"

    echo -e "${GREEN}✓ Đã dọn dẹp sạch toàn bộ Database và Captures thành công!${NC}"

    if [ "$was_running" -eq 1 ]; then
        echo -e "${CYAN}Đang khởi động lại server...${NC}"
        start_server
    fi
}

# Chạy toàn bộ Test Suite
run_tests() {
    echo -e "${BOLD}${CYAN}======================================================${NC}"
    echo -e "${BOLD}${CYAN}   CHẠY KIỂM THỬ TOÀN BỘ TEST SUITE GUITAR GIRL       ${NC}"
    echo -e "${BOLD}${CYAN}======================================================${NC}"
    cd "$ROOT_DIR" || exit 1
    PYTHONPATH="$EMULATOR_DIR" python3 -m unittest discover -s emulator -p "test_*.py" -v
}

# ==============================================================================
#  XỬ LÝ THAM SỐ DÒNG LỆNH (CLI Arguments)
# ==============================================================================
case "${1:-}" in
    start)
        start_server
        ;;
    stop)
        stop_server
        ;;
    restart)
        restart_server
        ;;
    status)
        show_status
        ;;
    log|logs)
        view_logs
        ;;
    test|tests)
        run_tests
        ;;
    clear|clean)
        clear_all_data
        ;;
    gui|monitor|"")
        if [ -t 0 ] && command -v python3 >/dev/null 2>&1 && [ -f "$TOOLS_DIR/dashboard.py" ] || [ -f "$EMULATOR_DIR/dashboard.py" ]; then
            exec python3 "$TOOLS_DIR/dashboard.py"
        else
            show_status
        fi
        ;;
    help|--help|-h)
        echo -e "${BOLD}Cách dùng:${NC} $0 [lệnh]"
        echo -e ""
        echo -e "  ${BOLD}$0${NC}               Mở giao diện TUI Live Control Center thời gian thực"
        echo -e "  ${BOLD}$0 start${NC}         Khởi động server ngầm (không dừng khi ngắt SSH)"
        echo -e "  ${BOLD}$0 stop${NC}          Dừng server"
        echo -e "  ${BOLD}$0 restart${NC}       Khởi động lại server"
        echo -e "  ${BOLD}$0 status${NC}        Xem trạng thái, PID, cổng, tài nguyên đang chiếm dụng"
        echo -e "  ${BOLD}$0 logs${NC}          Xem trực tiếp toàn bộ log (tail -f)"
        echo -e "  ${BOLD}$0 test${NC}          Chạy toàn bộ test cases tự động"
        echo -e "  ${BOLD}$0 clear${NC}         Xóa sạch Database & Captures"
        echo -e ""
        ;;
    *)
        echo -e "${RED}Lệnh không hợp lệ: $1${NC}"
        echo -e "Dùng: ${BOLD}$0 help${NC} để xem hướng dẫn."
        exit 1
        ;;
esac
