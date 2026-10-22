#!/usr/bin/env bash
# ==============================================================================
#  🎸 GUITAR GIRL SERVER - CONTROL CENTER & LIVE MONITOR
#  Khởi động server chạy nền (không cần mở thủ công, không bị tắt khi ngắt SSH)
#  Giao diện Terminal TUI trực quan, theo dõi livetime CPU, RAM, Disk, Status, Logs
# ==============================================================================

set -o pipefail

# Thư mục gốc dự án
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EMULATOR_DIR="$ROOT_DIR/emulator"

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
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
GRAY='\033[0;90m'
BG_BLUE='\033[44m'
BG_DARK='\033[40m'
NC='\033[0m' # No Color

# Tìm PID đang lắng nghe trên cổng PORT
listen_pid() {
    ss -ltnp 2>/dev/null | grep ":${PORT} " | grep -oP 'pid=\K[0-9]+' | head -1
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

# Vẽ thanh tiến trình đồ họa (Progress Bar)
# Cách dùng: draw_bar <phần_trăm> <độ_rộng>
draw_bar() {
    local pct="${1:-0}"
    local width="${2:-20}"
    # Đảm bảo pct là số nguyên 0-100
    pct=$(printf "%.0f" "$pct" 2>/dev/null || echo 0)
    [ "$pct" -lt 0 ] && pct=0
    [ "$pct" -gt 100 ] && pct=100

    local filled=$(( pct * width / 100 ))
    local empty=$(( width - filled ))
    local bar=""

    # Chọn màu dựa trên mức tải
    local bar_color="$GREEN"
    if [ "$pct" -ge 85 ]; then
        bar_color="$RED"
    elif [ "$pct" -ge 65 ]; then
        bar_color="$YELLOW"
    fi

    local i
    for ((i=0; i<filled; i++)); do bar="${bar}█"; done
    local empty_bar=""
    for ((i=0; i<empty; i++)); do empty_bar="${empty_bar}░"; done

    echo -e "${bar_color}${bar}${GRAY}${empty_bar}${NC}"
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
        echo -e "${GREEN}✓ Server khởi động THÀNH CÔNG!${NC}"
        echo -e "  • PID tiến trình: ${BOLD}${CYAN}$pid${NC}"
        echo -e "  • Cổng lắng nghe: ${BOLD}${WHITE}$PORT${NC}"
        echo -e "  • URL Công khai:  ${BOLD}${MAGENTA}$GG_PUBLIC_BASE${NC}"
        echo -e "  • Web Admin:      ${BOLD}${CYAN}$GG_PUBLIC_BASE/admin${NC}"
        echo -e "  • Mật khẩu Admin: ${BOLD}${YELLOW}$GG_ADMIN_PASSWORD${NC}"
        echo -e "  • Tệp nhật ký:    ${BOLD}$LOG_FILE${NC}"
        echo -e "${GREEN}✓ Server đã chạy độc lập (An toàn ngắt kết nối SSH mà server vẫn chạy!)${NC}"
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

    echo -e "${CYAN}Đang tắt server (PID: $pid)...${NC}"
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

# Hiển thị trạng thái chi tiết
show_status() {
    local pid=$(listen_pid)
    echo -e "${BOLD}${CYAN}=== GUITAR GIRL SERVER STATUS ===${NC}"
    if [ -n "$pid" ]; then
        echo -e "Trạng thái:     ${GREEN}${BOLD}● RUNNING${NC}"
        echo -e "PID:            ${BOLD}$pid${NC}"
        echo -e "Cổng:           ${BOLD}$PORT${NC}"
        echo -e "Public URL:     ${CYAN}$GG_PUBLIC_BASE${NC}"
        echo -e "Admin URL:      ${CYAN}$GG_PUBLIC_BASE/admin${NC}"
        echo -e "Tài nguyên PID: $(get_process_stats "$pid")"
        echo -n "Health Check:   "
        local health
        health=$(curl -s -m 3 "http://127.0.0.1:${PORT}/health" 2>/dev/null || echo "FAIL")
        if [ "$health" = "GG emulator OK" ]; then
            echo -e "${GREEN}${BOLD}200 OK (${health})${NC}"
        else
            echo -e "${RED}${BOLD}Không phản hồi ($health)${NC}"
        fi
    else
        echo -e "Trạng thái:     ${RED}${BOLD}● STOPPED${NC} (Không có tiến trình nào nghe cổng $PORT)"
    fi
    echo -e "File Log:       $LOG_FILE"
}

# Xem logs trực tiếp
view_logs() {
    echo -e "${CYAN}Đang theo dõi log trực tiếp từ ${BOLD}$LOG_FILE${NC} (Nhấn ${BOLD}Ctrl+C${NC} để thoát)..."
    touch "$LOG_FILE"
    tail -n 100 -f "$LOG_FILE" | grep --line-buffered -v -E "(/health|\"GET / HTTP|\"GET /admin|CONNECT|/SDK/| 404 -| 501 -)"
}

# Dọn dẹp sạch toàn bộ database và capture
clear_all_data() {
    echo -e "${YELLOW}${BOLD}⚠️  CẢNH BÁO: Thao tác này sẽ xóa sạch toàn bộ Database và các file Capture!${NC}"
    read -rp "Bạn có chắc chắn muốn xóa không? [y/N]: " confirm
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
    # Xóa database file
    rm -f "$EMULATOR_DIR/data/database.db"* "$EMULATOR_DIR/data/"*.migrated
    mkdir -p "$EMULATOR_DIR/data"
    
    # Khởi tạo lại bảng schema trắng sạch
    PYTHONPATH="$EMULATOR_DIR" python3 -c "
from server.state import init_db
init_db()
print('✓ Đã khởi tạo lại cấu trúc bảng cơ sở dữ liệu trống thành công!')
"

    # Xóa captures
    rm -f "$EMULATOR_DIR/captures/"*.json "$EMULATOR_DIR/captures/banned/"*.json 2>/dev/null || true
    mkdir -p "$EMULATOR_DIR/captures/banned"

    echo -e "${GREEN}✓ Đã dọn dẹp sạch toàn bộ Database và Captures thành công!${NC}"

    if [ "$was_running" -eq 1 ]; then
        echo -e "${CYAN}Đang khởi động lại server...${NC}"
        start_server
    fi
}

# Chạy toàn bộ Test Suite (102 tests)
run_tests() {
    echo -e "${BOLD}${CYAN}======================================================${NC}"
    echo -e "${BOLD}${CYAN}   CHẠY KIỂM THỬ TOÀN BỘ TEST SUITE GUITAR GIRL       ${NC}"
    echo -e "${BOLD}${CYAN}======================================================${NC}"
    cd "$ROOT_DIR" || exit 1
    PYTHONPATH="$EMULATOR_DIR" python3 -m unittest discover -s emulator -p "test_*.py" -v
}

# ==============================================================================
#  GIAO DIỆN TERMINAL TUI / LIVE DASHBOARD (Livetime Metrics)
# ==============================================================================
run_gui() {
    # Ẩn con trỏ chuột trong chế độ TUI
    tput civis 2>/dev/null || true
    trap 'tput cnorm 2>/dev/null; clear; exit 0' INT TERM EXIT

    while true; do
        # Lấy thông tin Server
        local pid=$(listen_pid)
        local status_str="${RED}● STOPPED${NC}"
        local proc_stats="Không hoạt động"
        local health_str="${RED}N/A${NC}"

        if [ -n "$pid" ]; then
            status_str="${GREEN}● RUNNING (PID: $pid)${NC}"
            proc_stats=$(get_process_stats "$pid")
            local health
            health=$(curl -s -m 1 "http://127.0.0.1:${PORT}/health" 2>/dev/null || echo "FAIL")
            if [ "$health" = "GG emulator OK" ]; then
                health_str="${GREEN}200 OK${NC}"
            else
                health_str="${RED}FAIL${NC}"
            fi
        fi

        # Lấy thông số CPU (tổng thể)
        local cpu_idle
        cpu_idle=$(top -bn1 2>/dev/null | grep "Cpu(s)" | awk '{for(i=1;i<=NF;i++) if($i=="id," || $i=="id") print $(i-1)}' | head -1 | tr -d ',')
        local cpu_used=0
        if [ -n "$cpu_idle" ]; then
            cpu_used=$(awk -v idle="$cpu_idle" 'BEGIN { printf "%.1f", 100 - idle }')
        fi

        # Lấy thông số RAM
        local mem_line
        mem_line=$(free -m 2>/dev/null | grep -i "Mem:")
        local mem_total=$(echo "$mem_line" | awk '{print $2}')
        local mem_used=$(echo "$mem_line" | awk '{print $3}')
        local mem_pct=0
        if [ -n "$mem_total" ] && [ "$mem_total" -gt 0 ]; then
            mem_pct=$(awk -v u="$mem_used" -v t="$mem_total" 'BEGIN { printf "%.1f", (u / t) * 100 }')
        fi
        local mem_used_gb=$(awk -v u="$mem_used" 'BEGIN { printf "%.2f", u / 1024 }')
        local mem_total_gb=$(awk -v t="$mem_total" 'BEGIN { printf "%.2f", t / 1024 }')

        # Lấy thông số Disk (phần vùng root)
        local disk_info
        disk_info=$(df -h / 2>/dev/null | awk 'NR==2 {print $2, $3, $5}' | tr -d '%')
        local disk_total=$(echo "$disk_info" | awk '{print $1}')
        local disk_used=$(echo "$disk_info" | awk '{print $2}')
        local disk_pct=$(echo "$disk_info" | awk '{print $3}')
        [ -z "$disk_pct" ] && disk_pct=0

        # Lấy thời gian & Uptime máy chủ
        local cur_time=$(date "+%d/%m/%y %H:%M:%S")
        local sys_uptime=$(uptime -p 2>/dev/null || uptime | awk -F',' '{print $1}')

        # Xóa màn hình vẽ lại (Flicker-free)
        clear
        echo -e "${BOLD}${MAGENTA}┌────────────────────────────────────────────────────────────────────────────┐${NC}"
        echo -e "${BOLD}${MAGENTA}│${NC}  ${BOLD}${WHITE}🎸 GUITAR GIRL EMULATOR SERVER - LIVE CONTROL CENTER${NC}                   ${BOLD}${MAGENTA}│${NC}"
        echo -e "${BOLD}${MAGENTA}│${NC}  ${GRAY}Hệ thống điều khiển máy chủ độc lập & Giám sát tài nguyên thời gian thực${NC}   ${BOLD}${MAGENTA}│${NC}"
        echo -e "${BOLD}${MAGENTA}├────────────────────────────────────────────────────────────────────────────┤${NC}"
        echo -e "${BOLD}${MAGENTA}│${NC}  ${CYAN}Thời gian:${NC} $cur_time   ${GRAY}│${NC}   ${CYAN}System Uptime:${NC} $sys_uptime"
        echo -e "${BOLD}${MAGENTA}├────────────────────────────────────────────────────────────────────────────┤${NC}"
        echo -e "${BOLD}${MAGENTA}│${NC}  ${BOLD}${YELLOW}[ THÔNG TIN MÁY CHỦ (SERVER STATUS) ]${NC}"
        echo -e "${BOLD}${MAGENTA}│${NC}  • Trạng thái server:  $status_str"
        echo -e "${BOLD}${MAGENTA}│${NC}  • Cổng lắng nghe:     ${BOLD}${WHITE}$PORT${NC} (TCP)"
        echo -e "${BOLD}${MAGENTA}│${NC}  • Public Domain:      ${BOLD}${CYAN}$GG_PUBLIC_BASE${NC}"
        echo -e "${BOLD}${MAGENTA}│${NC}  • Dashboard Admin:    ${BOLD}${MAGENTA}$GG_PUBLIC_BASE/admin${NC}"
        echo -e "${BOLD}${MAGENTA}│${NC}  • Mật khẩu Admin:     ${BOLD}${YELLOW}$GG_ADMIN_PASSWORD${NC}"
        echo -e "${BOLD}${MAGENTA}│${NC}  • Trạng thái Health:  $health_str"
        echo -e "${BOLD}${MAGENTA}│${NC}  • Tiến trình Server:  ${GRAY}$proc_stats${NC}"
        echo -e "${BOLD}${MAGENTA}├────────────────────────────────────────────────────────────────────────────┤${NC}"
        echo -e "${BOLD}${MAGENTA}│${NC}  ${BOLD}${YELLOW}[ TÀI NGUYÊN MÁY CHỦ LIVETIME (SYSTEM RESOURCES) ]${NC}"
        
        # In thanh CPU
        local cpu_bar=$(draw_bar "$cpu_used" 22)
        printf "${BOLD}${MAGENTA}│${NC}  • CPU Usage:  [%s] ${BOLD}%5.1f%%${NC}\n" "$cpu_bar" "$cpu_used"

        # In thanh RAM
        local ram_bar=$(draw_bar "$mem_pct" 22)
        printf "${BOLD}${MAGENTA}│${NC}  • RAM Memory: [%s] ${BOLD}%5.1f%%${NC}  (${mem_used_gb} GB / ${mem_total_gb} GB)\n" "$ram_bar" "$mem_pct"

        # In thanh Disk
        local disk_bar=$(draw_bar "$disk_pct" 22)
        printf "${BOLD}${MAGENTA}│${NC}  • Ổ cứng (/): [%s] ${BOLD}%5s%%${NC}  (${disk_used} / ${disk_total})\n" "$disk_bar" "$disk_pct"

        echo -e "${BOLD}${MAGENTA}├────────────────────────────────────────────────────────────────────────────┤${NC}"
        echo -e "${BOLD}${MAGENTA}│${NC}  ${BOLD}${YELLOW}[ NHẬT KÝ HOẠT ĐỘNG TRỰC TIẾP (LIVE LOGS - TAIL) ]${NC}"
        echo -e "${BOLD}${MAGENTA}├────────────────────────────────────────────────────────────────────────────┤${NC}"
        
        # Hiển thị 8 dòng log mới nhất (lọc bỏ health check, admin ping và scanner bot)
        if [ -f "$LOG_FILE" ]; then
            local term_cols=$(tput cols 2>/dev/null || echo 120)
            local max_w=$(( term_cols - 6 ))
            [ "$max_w" -lt 72 ] && max_w=72
            [ "$max_w" -gt 130 ] && max_w=130
            tail -n 50 "$LOG_FILE" 2>/dev/null | grep -v -E "(/health|\"GET / HTTP|\"GET /admin|CONNECT|/SDK/| 404 -| 501 -)" | tail -n 8 | while IFS= read -r line; do
                local clean_line="${line:0:$max_w}"
                echo -e "${BOLD}${MAGENTA}│${NC}  ${DIM}${clean_line}${NC}"
            done
        else
            echo -e "${BOLD}${MAGENTA}│${NC}  ${GRAY}(Chưa có log - Khởi động server để bắt đầu ghi log)${NC}"
        fi

        echo -e "${BOLD}${MAGENTA}├────────────────────────────────────────────────────────────────────────────┤${NC}"
        echo -e "${BOLD}${MAGENTA}│${NC}  ${BOLD}${WHITE}PHÍM ĐIỀU KHIỂN:${NC}"
        echo -e "${BOLD}${MAGENTA}│${NC}  ${BOLD}${GREEN}[1]${NC} Khởi động   ${BOLD}${RED}[2]${NC} Dừng       ${BOLD}${CYAN}[3]${NC} Khởi động lại   ${BOLD}${YELLOW}[4]${NC} Xem Full Log"
        echo -e "${BOLD}${MAGENTA}│${NC}  ${BOLD}${MAGENTA}[5]${NC} Xóa DB & Captures      ${BOLD}${BLUE}[6]${NC} Chạy Test Suite ${BOLD}${WHITE}[q]${NC} Thoát Monitor"
        echo -e "${BOLD}${MAGENTA}└────────────────────────────────────────────────────────────────────────────┘${NC}"
        echo -e "${GRAY}Tự động làm mới mỗi 2 giây • Nhấn phím để thực hiện thao tác...${NC}"

        # Đọc 1 phím với timeout 2 giây
        read -t 2 -n 1 -r choice || true

        case "$choice" in
            1)
                clear
                start_server
                echo -e "\n${GRAY}Nhấn phím bất kỳ để quay lại Monitor...${NC}"
                read -n 1 -r
                ;;
            2)
                clear
                stop_server
                echo -e "\n${GRAY}Nhấn phím bất kỳ để quay lại Monitor...${NC}"
                read -n 1 -r
                ;;
            3)
                clear
                restart_server
                echo -e "\n${GRAY}Nhấn phím bất kỳ để quay lại Monitor...${NC}"
                read -n 1 -r
                ;;
            4)
                clear
                view_logs
                ;;
            5)
                clear
                clear_all_data
                echo -e "\n${GRAY}Nhấn phím bất kỳ để quay lại Monitor...${NC}"
                read -n 1 -r
                ;;
            6)
                clear
                run_tests
                echo -e "\n${GRAY}Nhấn phím bất kỳ để quay lại Monitor...${NC}"
                read -n 1 -r
                ;;
            q|Q)
                tput cnorm 2>/dev/null || true
                clear
                echo -e "${GREEN}✓ Đã thoát khỏi giao diện Monitor.${NC}"
                local cur_p=$(listen_pid)
                if [ -n "$cur_p" ]; then
                    echo -e "${CYAN}ℹ️  LƯU Ý: Guitar Girl Server vẫn đang CHẠY NGẦM an toàn (PID: ${BOLD}$cur_p${NC}${CYAN}, Cổng: ${BOLD}$PORT${NC}${CYAN}).${NC}"
                    echo -e "${CYAN}   Bạn có thể yên tâm thoát / ngắt kết nối SSH mà không lo server bị dừng!${NC}"
                fi
                echo -e "   Gõ ${BOLD}./run.sh${NC} bất cứ lúc nào để mở lại bảng điều khiển."
                exit 0
                ;;
        esac
    done
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
    gui|monitor)
        run_gui
        ;;
    help|--help|-h)
        echo -e "${BOLD}Cách dùng:${NC} $0 [lệnh]"
        echo -e ""
        echo -e "  ${BOLD}$0${NC}               Mở giao diện trực quan TUI Monitor livetime & menu tương tác"
        echo -e "  ${BOLD}$0 start${NC}         Khởi động server ngầm (không dừng khi ngắt SSH)"
        echo -e "  ${BOLD}$0 stop${NC}          Dừng server"
        echo -e "  ${BOLD}$0 restart${NC}       Khởi động lại server"
        echo -e "  ${BOLD}$0 status${NC}        Xem trạng thái, PID, cổng, tài nguyên đang chiếm dụng"
        echo -e "  ${BOLD}$0 logs${NC}          Xem trực tiếp toàn bộ log (tail -f)"
        echo -e "  ${BOLD}$0 test${NC}          Chạy toàn bộ 102 test cases tự động"
        echo -e "  ${BOLD}$0 clear${NC}         Xóa sạch Database & Captures"
        echo -e ""
        ;;
    "")
        # Không có tham số -> Chạy trực tiếp giao diện TUI Live Dashboard
        run_gui
        ;;
    *)
        echo -e "${RED}Lệnh không hợp lệ: $1${NC}"
        echo -e "Dùng: ${BOLD}$0 help${NC} để xem hướng dẫn."
        exit 1
        ;;
esac
