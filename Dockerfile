# Sử dụng Python 3.11-slim làm base image để tối ưu dung lượng
FROM python:3.11-slim

# Cài đặt openssl để tự động tạo chứng chỉ self-signed khi sử dụng --https
RUN apt-get update && apt-get install -y openssl && rm -rf /var/lib/apt/lists/*

# Thiết lập thư mục làm việc trong container
WORKDIR /app

# Sao chép các tệp tin từ thư mục emulator vào container
COPY emulator/ /app/

# Mở cổng mạng mặc định
# 8080: Cổng HTTP
# 443: Cổng HTTPS
EXPOSE 8080 443

# Tạo volume để lưu trữ dữ liệu bền vững (persistent data)
# /app/data: Chứa chứng chỉ SSL (server.pem) và dữ liệu người chơi (player data)
# /app/captures: Chứa log request API
VOLUME ["/app/data", "/app/captures"]

# Lệnh chạy server mặc định (HTTP trên cổng 8080)
# Có thể override command khi chạy docker run để truyền thêm tham số (ví dụ: --https --port 443)
CMD ["python3", "run.py", "--host", "0.0.0.0", "--port", "8080"]
