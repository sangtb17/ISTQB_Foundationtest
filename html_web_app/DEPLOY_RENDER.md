# Render deploy — Kho Đề Trắc Nghiệm (html_web_app)

## 1. Chuẩn bị GitHub
1. Tạo repo mới (public/private đều được).
2. Push toàn bộ thư mục `F2026_ Đề theo chương` lên, giữ cấu trúc:
   - `html_web_app/app.py`, `requirements.txt`, `Procfile`, `render.yaml`
   - `Chương 1/*.html` (seed data)
3. KHÔNG commit file `html_web_app/.env` (chứa pass thật).

## 2. Tạo Web Service trên Render (Host A)
1. Vào https://dashboard.render.com → New → Web Service → chọn repo.
2. Render tự đọc `html_web_app/render.yaml` (Blueprint) hoặc nhập tay:
   - Build Command: `pip install -r html_web_app/requirements.txt`
   - Start Command: `waitress-serve --listen=0.0.0.0:$PORT html_web_app.app:app`
   - Health Check Path: `/healthz`
3. Add Disk: Name `quizdata`, Mount Path `/data`, Size `1 GB`.
4. Environment Variables:
   - `FLASK_ENV=production`
   - `DATA_DIR=/data`
   - `MAX_CONTENT_MB=16`
   - `SECRET_KEY` → Generate Random
   - `ADMIN_USER=admin`
   - `ADMIN_PASS=abc13579` (đổi sau khi test xong)
5. Deploy → nhận URL `https://xxx.onrender.com`.

## 3. Seed dữ liệu lần đầu
- Sau deploy, upload 1 file `.html` từ `Chương 1/` qua giao diện web (đăng nhập admin),
  hoặc dùng Render Shell: `cp -r "Chương 1" /data/` (nếu giữ seed trong repo).
- Từ lần 2 trở đi, dữ liệu nằm trên Disk `/data`, redeploy không mất.

## 4. Kiểm tra sau deploy
- `GET /healthz` → `ok` (không cần pass).
- `GET /` không pass → `401`.
- Đăng nhập `admin / abc13579` → thấy danh sách đề.
- `GET /view/<file>.html` yêu cầu pass.
- Upload file `.exe` → bị từ chối. Truy cập `/view/../../etc/passwd` → `403`.

## 5. Đổi pass / vận hành
- Đổi `ADMIN_PASS` trong Render Dashboard → Restart service.
- Backup: tải file từ giao diện hoặc `tar -czf backup.tgz /data`.
- Free plan ngủ sau 15p không dùng — lần mở đầu chậm ~30s là bình thường.
