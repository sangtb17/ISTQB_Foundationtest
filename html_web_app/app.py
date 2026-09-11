import os
import re
import hmac
import shutil
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, abort
from werkzeug.utils import secure_filename
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'), encoding='utf-8')
except ImportError:
    pass
try:
    from flask_httpauth import HTTPBasicAuth
    HAS_AUTH = True
    auth = HTTPBasicAuth()
except ImportError:
    HAS_AUTH = False
    auth = None
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', os.urandom(32).hex())
PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def _resolve_data_dir():
    raw = os.getenv('DATA_DIR', PARENT_DIR)
    if not os.path.isabs(raw):
        # Trên Render, CWD là repo root nên ./seed_data -> <repo>/seed_data
        cwd_based = os.path.abspath(os.path.join(os.getcwd(), raw))
        app_based = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), raw))
        raw = cwd_based if os.path.isdir(cwd_based) or not os.path.isdir(app_based) else app_based
    return os.path.abspath(raw)
DATA_DIR = _resolve_data_dir()
UPLOAD_FOLDER = DATA_DIR
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# Seed dữ liệu mẫu khi thư mục rỗng (Render Free không có Disk persistent)
try:
    if not os.listdir(UPLOAD_FOLDER):
        for _cand in (os.path.join(PARENT_DIR, 'Chương 1'),
                      os.path.join(os.getcwd(), 'Chương 1'),
                      os.path.join(os.getcwd(), 'seed_data')):
            if os.path.isdir(_cand):
                for _f in os.listdir(_cand):
                    if _f.lower().endswith('.html'):
                        try:
                            shutil.copy2(os.path.join(_cand, _f), os.path.join(UPLOAD_FOLDER, _f))
                        except OSError:
                            pass
                break
except OSError:
    pass

def _seed_folder_if_missing(folder_name):
    """Chép 1 thư mục con từ repo vào DATA_DIR nếu chưa tồn tại (idempotent)."""
    dest = os.path.join(UPLOAD_FOLDER, folder_name)
    if os.path.isdir(dest):
        return False
    for _cand in (os.path.join(PARENT_DIR, 'seed_data', folder_name),
                  os.path.join(PARENT_DIR, folder_name),
                  os.path.join(os.getcwd(), 'seed_data', folder_name),
                  os.path.join(os.getcwd(), folder_name)):
        if os.path.isdir(_cand):
            try:
                shutil.copytree(_cand, dest)
                print(f"[seed] da tao folder: {folder_name}")
            except OSError as e:
                print(f"[seed] khong tao duoc {folder_name}: {e}")
            return True
    return False


def _seed_folders_if_missing(*folder_names):
    """Chép các thư mục con (vd: F2026_ Đề thi tổng hợp) từ repo vào DATA_DIR
    nếu chưa tồn tại. Chạy lại mỗi lần deploy nên idempotent — thư mục đã có
    trên Disk /data sẽ được giữ nguyên và không bị ghi đè."""
    for folder_name in folder_names:
        _seed_folder_if_missing(folder_name)


def _consolidate_home_into(folder_name):
    """Di chuyển mọi file .html đang nằm thẳng ở Trang chủ (DATA_DIR) vào trong
    thư mục folder_name, để Trang chủ chỉ còn các thư mục. Idempotent: lần sau
    sẽ không còn file .html nào ở root để di chuyển."""
    dest = os.path.join(UPLOAD_FOLDER, folder_name)
    if not os.path.isdir(dest):
        return
    try:
        for item in os.listdir(UPLOAD_FOLDER):
            src = os.path.join(UPLOAD_FOLDER, item)
            if item.lower().endswith('.html') and os.path.isfile(src):
                target = os.path.join(dest, item)
                try:
                    if os.path.exists(target):
                        os.remove(src)  # trùng file đã có trong folder
                    else:
                        shutil.move(src, target)
                    print(f"[seed] da chuyen Trang chu/{item} -> {folder_name}/")
                except OSError as e:
                    print(f"[seed] loi chuyen {item}: {e}")
    except OSError as e:
        print(f"[seed] loi quet Trang chu: {e}")


_seed_folders_if_missing('F2026_ Đề thi tổng hợp', 'F2026_ Đề theo chương')
_consolidate_home_into('F2026_ Đề theo chương')
try:
    MAX_MB = int(os.getenv('MAX_CONTENT_MB', '200'))
except ValueError:
    MAX_MB = 16
app.config['MAX_CONTENT_LENGTH'] = MAX_MB * 1024 * 1024
ADMIN_USER = os.getenv('ADMIN_USER', 'admin')
ADMIN_PASS = os.getenv('ADMIN_PASS', 'changeme')
EXCLUDE_DIRS = {'.git', '__pycache__', 'html_web_app', '.vscode', '.env'}
ALLOWED_EXT = {'.html'}
def is_safe(path):
    try:
        base = os.path.abspath(UPLOAD_FOLDER)
        target = os.path.abspath(path)
        return os.path.commonpath([base]) == os.path.commonpath([base, target])
    except ValueError:
        return False
if HAS_AUTH:
    @auth.verify_password
    def verify_password(username, password):
        if not username or not password:
            return False
        return hmac.compare_digest(username, ADMIN_USER) and hmac.compare_digest(password, ADMIN_PASS)
    @auth.error_handler
    def auth_error(status):
        return ('<h3>401 - Can dang nhap</h3>', 401, {'WWW-Authenticate': 'Basic realm="Kho De"'})
@app.before_request
def require_auth():
    if request.path == '/healthz' or request.path.startswith('/static'):
        return None
    if HAS_AUTH:
        return auth.login_required(lambda: None)()
    return None
@app.route('/healthz')
def healthz():
    return 'ok', 200

def get_all_folders(base_path):
    folders = []
    for root, dirs, files in os.walk(base_path):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for d in dirs:
            full_path = os.path.join(root, d)
            rel_path = os.path.relpath(full_path, base_path)
            folders.append(rel_path.replace('\\', '/'))
    return folders

@app.route('/')
@app.route('/<path:req_path>')
def index(req_path=''):
    abs_path = os.path.join(UPLOAD_FOLDER, req_path)

    # Kiểm tra bảo mật
    if not is_safe(abs_path):
        flash('Đường dẫn không hợp lệ.', 'error')
        return redirect(url_for('index'))

    if not os.path.exists(abs_path) or not os.path.isdir(abs_path):
        flash('Thư mục không tồn tại.', 'error')
        return redirect(url_for('index'))

    items = os.listdir(abs_path)
    folders = []
    html_files = []

    for item in items:
        if item in EXCLUDE_DIRS:
            continue
        item_path = os.path.join(abs_path, item)
        if os.path.isdir(item_path):
            folders.append(item)
        elif item.lower().endswith('.html') and os.path.isfile(item_path):
            html_files.append(item)

    # Sort toggle A-Z / Z-A (mặc daso asc)
    sort = request.args.get('sort', 'asc')
    if sort not in ('asc', 'desc'):
        sort = 'asc'
    folders.sort(key=str.casefold, reverse=(sort == 'desc'))
    html_files.sort(key=str.casefold, reverse=(sort == 'desc'))

    all_folders = get_all_folders(UPLOAD_FOLDER)
    all_folders.sort()
    all_folders.insert(0, '') # Thêm thư mục gốc đại diện bằng chuỗi rỗng

    # Tạo Breadcrumbs
    breadcrumbs = []
    if req_path:
        parts = req_path.strip('/').split('/')
        current_build = ''
        for part in parts:
            current_build = f"{current_build}/{part}".strip('/')
            breadcrumbs.append({'name': part, 'path': current_build})

    return render_template('index.html', 
                           folders=folders, 
                           files=html_files, 
                           current_path=req_path,
                           breadcrumbs=breadcrumbs,
                           all_folders=all_folders,
                           sort=sort)

@app.route('/upload', methods=['POST'])
def upload_file():
    current_path = request.form.get('current_path', '')
    target_dir = os.path.join(UPLOAD_FOLDER, current_path)

    if not is_safe(target_dir) or not os.path.isdir(target_dir):
        flash('Đường dẫn không hợp lệ.', 'error')
        return redirect(url_for('index'))

    if 'file' not in request.files:
        flash('Không tìm thấy file', 'error')
        return redirect(url_for('index', req_path=current_path))
    
    file = request.files['file']
    if file.filename == '':
        flash('Chưa chọn file nào', 'error')
        return redirect(url_for('index', req_path=current_path))
    filename = secure_filename(file.filename)
    if not filename:
        flash('Tên file không hợp lệ.', 'error')
        return redirect(url_for('index', req_path=current_path))
    if os.path.splitext(filename)[1].lower() not in ALLOWED_EXT:
        flash('Chỉ hỗ trợ tải lên file .html', 'error')
        return redirect(url_for('index', req_path=current_path))
    dest = os.path.join(target_dir, filename)
    if not is_safe(dest):
        flash('Đường dẫn không hợp lệ.', 'error')
        return redirect(url_for('index', req_path=current_path))
    file.save(dest)
    flash(f'Tải lên thành công: {filename}', 'success')
    return redirect(url_for('index', req_path=current_path))

def _safe_path_part(name):
    """Sanitize one folder/file segment, keeping Unicode letters/digits."""
    name = (name or '').replace('\\', '/')
    name = re.sub(r'[^\w\.\- ]', '', name)      # unicode word chars + . - space
    name = re.sub(r'[\/\\]', '-', name)
    name = ' '.join(name.split()).strip(' .')
    return '' if name in ('', '.', '..') else name


@app.route('/upload_folder', methods=['POST'])
def upload_folder():
    current_path = request.form.get('current_path', '')
    base_dir = os.path.join(UPLOAD_FOLDER, current_path)

    if not is_safe(base_dir) or not os.path.isdir(base_dir):
        flash('Đường dẫn không hợp lệ.', 'error')
        return redirect(url_for('index'))

    files = request.files.getlist('files')
    files = [f for f in files if f and f.filename]
    if not files:
        flash('Chưa chọn folder nào', 'error')
        return redirect(url_for('index', req_path=current_path))

    ok, skip = 0, 0
    seen = set()
    for f in files:
        rel = (f.filename or '').replace('\\', '/').lstrip('/')
        parts = [p for p in rel.split('/') if p not in ('', '.', '..')]
        if not parts:
            skip += 1
            continue
        safe_parts = [_safe_path_part(p) for p in parts]
        if not safe_parts or not safe_parts[-1]:
            skip += 1
            continue
        if os.path.splitext(safe_parts[-1])[1].lower() not in ALLOWED_EXT:
            skip += 1
            continue
        dest = os.path.join(base_dir, *safe_parts)
        if not is_safe(dest):
            skip += 1
            continue
        try:
            dest_key = os.path.normpath(dest).lower()
            if dest_key in seen:      # mangled-name collision -> do not silently overwrite
                skip += 1
                continue
            parent = os.path.dirname(dest) or base_dir
            os.makedirs(parent, exist_ok=True)
            f.save(dest)
            seen.add(dest_key)
            ok += 1
        except OSError:
            skip += 1

    msg = f'Đã tải {ok} file' + (f', bỏ qua {skip} file không phải .html.' if skip else '.')
    flash(msg, 'success' if ok else 'error')
    return redirect(url_for('index', req_path=current_path))


@app.route('/create_folder', methods=['POST'])
def create_folder():
    current_path = request.form.get('current_path', '')
    folder_name = request.form.get('folder_name', '').strip()
    
    if not folder_name:
        flash('Tên thư mục không được để trống.', 'error')
        return redirect(url_for('index', req_path=current_path))
    if '/' in folder_name or '\\' in folder_name or '..' in folder_name:
        flash('Tên thư mục không được chứa / \\ hoặc ..', 'error')
        return redirect(url_for('index', req_path=current_path))
    target_dir = os.path.join(UPLOAD_FOLDER, current_path, folder_name)
    if not is_safe(target_dir):
        flash('Đường dẫn không hợp lệ.', 'error')
        return redirect(url_for('index', req_path=current_path))

    try:
        os.makedirs(target_dir, exist_ok=True)
        flash(f'Đã tạo thư mục: {folder_name}', 'success')
    except Exception as e:
        flash(f'Lỗi khi tạo thư mục: {str(e)}', 'error')

    return redirect(url_for('index', req_path=current_path))

@app.route('/rename_folder', methods=['POST'])
def rename_folder():
    current_path = request.form.get('current_path', '')
    old_name = request.form.get('old_name', '').strip()
    new_name = request.form.get('new_name', '').strip()

    if not old_name or not new_name:
        flash('Tên thư mục không được để trống.', 'error')
        return redirect(url_for('index', req_path=current_path))
    if old_name == new_name:
        return redirect(url_for('index', req_path=current_path))
    for bad in ('/', '\\', '..'):
        if bad in new_name or bad in old_name:
            flash('Tên thư mục không được chứa / \\ hoặc ..', 'error')
            return redirect(url_for('index', req_path=current_path))

    src = os.path.join(UPLOAD_FOLDER, current_path, old_name)
    dst = os.path.join(UPLOAD_FOLDER, current_path, new_name)
    if not (is_safe(src) and is_safe(dst)):
        flash('Đường dẫn không hợp lệ.', 'error')
        return redirect(url_for('index', req_path=current_path))
    if not os.path.isdir(src):
        flash('Thư mục không tồn tại.', 'error')
        return redirect(url_for('index', req_path=current_path))
    if os.path.exists(dst):
        flash('Đã tồn tại thư mục cùng tên.', 'error')
        return redirect(url_for('index', req_path=current_path))

    try:
        os.rename(src, dst)
        flash(f'Đã đổi tên: {old_name} → {new_name}', 'success')
    except Exception as e:
        flash(f'Lỗi khi đổi tên: {str(e)}', 'error')

    return redirect(url_for('index', req_path=current_path))

@app.route('/move_file', methods=['POST'])
def move_file():
    current_path = request.form.get('current_path', '')
    filename = secure_filename(request.form.get('filename', ''))
    target_folder = request.form.get('target_folder', '') 
    
    source_path = os.path.join(UPLOAD_FOLDER, current_path, filename)
    dest_path = os.path.join(UPLOAD_FOLDER, target_folder, filename)
    
    if not (is_safe(source_path) and is_safe(dest_path)):
        flash('Đường dẫn không hợp lệ.', 'error')
        return redirect(url_for('index', req_path=current_path))
        
    if not os.path.isfile(source_path):
        flash('File không tồn tại.', 'error')
        return redirect(url_for('index', req_path=current_path))

    try:
        os.makedirs(os.path.dirname(dest_path) or UPLOAD_FOLDER, exist_ok=True)
        shutil.move(source_path, dest_path)
        flash(f'Đã chuyển {filename} sang thư mục mới.', 'success')
    except Exception as e:
        flash(f'Lỗi khi chuyển file: {str(e)}', 'error')

    return redirect(url_for('index', req_path=current_path))

@app.route('/delete', methods=['POST'])
def delete_item():
    current_path = request.form.get('current_path', '')
    item_name = request.form.get('item_name', '')
    is_folder = request.form.get('is_folder') == 'true'
    if '/' in item_name or '\\' in item_name or '..' in item_name:
        flash('Tên mục không hợp lệ.', 'error')
        return redirect(url_for('index', req_path=current_path))
    target_path = os.path.join(UPLOAD_FOLDER, current_path, item_name)
    if not is_safe(target_path):
        flash('Đường dẫn không hợp lệ.', 'error')
        return redirect(url_for('index', req_path=current_path))
        
    if not os.path.exists(target_path):
        flash('Không tìm thấy mục cần xóa.', 'error')
        return redirect(url_for('index', req_path=current_path))

    try:
        if is_folder:
            if not os.path.isdir(target_path):
                flash('Thư mục không tồn tại.', 'error')
            else:
                shutil.rmtree(target_path)
                flash(f'Đã xóa thư mục: {item_name}', 'success')
        else:
            if not os.path.isfile(target_path):
                flash('File không tồn tại.', 'error')
            else:
                os.remove(target_path)
                flash(f'Đã xóa file: {item_name}', 'success')
    except Exception as e:
        flash(f'Lỗi khi xóa: {str(e)}', 'error')

    return redirect(url_for('index', req_path=current_path))

@app.route('/view/<path:filename>')
def view_file(filename):
    abs_path = os.path.join(UPLOAD_FOLDER, filename)
    if not is_safe(abs_path):
        abort(403)
    if not os.path.isfile(abs_path):
        abort(404)
    if os.path.splitext(abs_path)[1].lower() not in ALLOWED_EXT:
        abort(403)
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__ == '__main__':
    port = int(os.getenv('PORT', '5000'))
    env = os.getenv('FLASK_ENV', 'development')
    if env == 'production':
        try:
            from waitress import serve
            print(f"Serving (production, waitress) at http://0.0.0.0:{port} DATA_DIR={UPLOAD_FOLDER}")
            serve(app, host='0.0.0.0', port=port)
        except ImportError:
            print("waitress chua cai, fallback Flask dev server (khong dung production).")
            app.run(host='0.0.0.0', port=port, debug=False)
    else:
        print(f"Server is starting at: http://0.0.0.0:{port} (dev)")
        app.run(host='0.0.0.0', port=port, debug=True)
