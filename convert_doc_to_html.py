import sys
import json
import re
import os

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Thư viện 'beautifulsoup4' chưa được cài đặt. Vui lòng chạy lệnh: pip install beautifulsoup4")
    sys.exit(1)

def process_file(input_file, output_file):
    sys.stdout.reconfigure(encoding='utf-8')
    print(f"Dang xu ly: {input_file} ...")
    content = ""
    # Thử đọc file với các encoding khác nhau
    for enc in ['utf-8', 'utf-8-sig', 'windows-1258', 'cp1252', 'latin1']:
        try:
            with open(input_file, 'r', encoding=enc) as f:
                content = f.read()
            break
        except UnicodeDecodeError:
            continue
            
    if not content:
        print(f"Không thể đọc nội dung file {input_file}")
        return

    soup = BeautifulSoup(content, 'html.parser')
    qblocks = soup.find_all('div', class_='qblock')
    
    if not qblocks:
        print("Không tìm thấy các câu hỏi (không có thẻ <div class='qblock'>). File có thể không đúng định dạng mong đợi.")
        return False

    quiz_data = []
    
    for idx, qblock in enumerate(qblocks):
        qtitle = qblock.find('div', class_='qtitle')
        
        # Lấy nội dung câu hỏi
        question_html_parts = []
        if qtitle:
            node = qtitle.next_sibling
            while node:
                if node.name == 'div' and node.has_attr('class') and any(c.startswith('opt') for c in node.get('class', [])):
                    break
                if node.name is not None or str(node).strip():
                    question_html_parts.append(str(node))
                node = node.next_sibling
                
        question_text = "".join(question_html_parts).strip()
        if not question_text:
            question_text = f"Câu hỏi {idx + 1}"
        
        # Lấy các lựa chọn (options)
        options = []
        correct_idx = 0
        opt_divs = qblock.find_all('div', class_=re.compile(r'^opt'))
        for o_idx, opt_div in enumerate(opt_divs):
            opt_text = opt_div.get_text(strip=True)
            
            # Xác định đáp án đúng
            classes = opt_div.get('class', [])
            if 'correct' in classes or 'selectedright' in classes or '[Đáp án đúng]' in opt_text or '[p n ng]' in opt_text:
                correct_idx = o_idx
            
            # Làm sạch text lựa chọn
            clean_text = opt_text
            clean_text = re.sub(r'\[Thí sinh.*?\]', '', clean_text)
            clean_text = re.sub(r'\[Đáp án.*?\]', '', clean_text)
            # Regex cho các ký tự bị lỗi font
            clean_text = re.sub(r'\[Th sinh.*?\]', '', clean_text)
            clean_text = re.sub(r'\[p n.*?\]', '', clean_text)
            options.append(clean_text.strip())
            
        # Lấy giải thích
        explain_div = qblock.find('div', class_='explain')
        explanation = explain_div.decode_contents().strip() if explain_div else ""
        explanation = re.sub(r'^Lời giải:\s*', '', explanation, flags=re.IGNORECASE)
        explanation = re.sub(r'^L\?i gi\?i:\s*', '', explanation, flags=re.IGNORECASE)
        
        quiz_data.append({
            "id": idx + 1,
            "question": question_text,
            "options": options,
            "correct": correct_idx,
            "explanation": explanation
        })
        
    # Tạo HTML
    template = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Đề Trắc Nghiệm</title>
    <style>
        :root {
            --primary-color: #1a365d;
            --primary-light: #2b6cb0;
            --secondary-color: #319795;
            --bg-color: #f7fafc;
            --card-bg: #ffffff;
            --text-color: #2d3748;
            --border-color: #e2e8f0;
            --correct-bg: #c6f6d5;
            --correct-border: #38a169;
            --incorrect-bg: #fed7d7;
            --incorrect-border: #e53e3e;
            --explain-bg: #ebf8ff;
            --explain-border: #3182ce;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }

        body {
            background-color: var(--bg-color);
            color: var(--text-color);
            line-height: 1.6;
            padding: 20px;
        }

        .container {
            max-width: 900px;
            margin: 0 auto;
        }

        header {
            background: linear-gradient(135deg, var(--primary-color), var(--primary-light));
            color: white;
            padding: 25px 30px;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            margin-bottom: 25px;
        }

        header h1 {
            font-size: 22px;
            margin-bottom: 8px;
        }

        header p {
            font-size: 14px;
            opacity: 0.9;
        }

        .stats-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: var(--card-bg);
            padding: 15px 20px;
            border-radius: 10px;
            margin-bottom: 25px;
            border: 1px solid var(--border-color);
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        }

        .stats-item {
            font-weight: 600;
            font-size: 14px;
        }

        .score-display {
            color: var(--primary-light);
            font-size: 16px;
        }

        .question-card {
            background: var(--card-bg);
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 20px;
            border: 1px solid var(--border-color);
            box-shadow: 0 2px 10px rgba(0,0,0,0.03);
            transition: all 0.2s ease;
        }

        .question-title {
            font-size: 16px;
            font-weight: 600;
            color: var(--primary-color);
            margin-bottom: 15px;
        }

        .options-list {
            list-style: none;
            margin-bottom: 15px;
        }

        .option-item {
            padding: 12px 15px;
            margin-bottom: 8px;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.15s ease;
            font-size: 14.5px;
            display: flex;
            align-items: center;
        }

        .option-item:hover {
            background-color: #f8fafc;
            border-color: #cbd5e0;
        }

        .option-item.selected {
            border-color: var(--primary-light);
            background-color: #ebf8ff;
            font-weight: 500;
        }

        .option-item.correct {
            background-color: var(--correct-bg) !important;
            border-color: var(--correct-border) !important;
            color: #22543d;
            font-weight: 600;
        }

        .option-item.incorrect {
            background-color: var(--incorrect-bg) !important;
            border-color: var(--incorrect-border) !important;
            color: #742a2a;
        }

        .btn-toggle-explain {
            background-color: #edf2f7;
            color: #2d3748;
            border: 1px solid #cbd5e0;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13.5px;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            transition: all 0.2s ease;
            margin-top: 10px;
        }

        .btn-toggle-explain:hover {
            background-color: #e2e8f0;
            border-color: #a0aec0;
        }

        .explanation-box {
            display: none;
            margin-top: 15px;
            padding: 15px;
            background-color: var(--explain-bg);
            border-left: 4px solid var(--explain-border);
            border-radius: 6px;
            font-size: 14px;
            color: #2b6cb0;
        }

        .explanation-box strong {
            display: block;
            margin-bottom: 5px;
            color: #2c5282;
        }

        .action-bar {
            text-align: center;
            margin: 30px 0;
        }

        .btn-submit {
            background-color: var(--secondary-color);
            color: white;
            border: none;
            padding: 12px 30px;
            font-size: 16px;
            font-weight: 600;
            border-radius: 8px;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(49, 151, 149, 0.3);
            transition: all 0.2s;
        }

        .btn-submit:hover {
            background-color: #2c7a7b;
            transform: translateY(-1px);
        }

        .btn-reset {
            background-color: #718096;
            color: white;
            border: none;
            padding: 12px 30px;
            font-size: 16px;
            font-weight: 600;
            border-radius: 8px;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(113, 128, 150, 0.3);
            transition: all 0.2s;
            margin-left: 15px;
        }

        .btn-reset:hover {
            background-color: #4a5568;
            transform: translateY(-1px);
        }

        @media (max-width: 600px) {
            body { padding: 10px; }
            .question-card { padding: 15px; }
        }
    </style>
</head>
<body>

<div class="container">
    <header>
        <h1 id="quiz-title">Bộ Đề Trắc Nghiệm</h1>
        <p>Luyện Tập</p>
    </header>

    <div class="stats-bar">
        <div class="stats-item">Tổng số câu: <span id="total-count">0</span></div>
        <div class="stats-item score-display" id="score-display">Điểm số: -- / --</div>
    </div>

    <div id="quiz-container"></div>

    <div class="action-bar">
        <button class="btn-submit" onclick="submitQuiz()">Nộp Bài & Kiểm Tra Đáp Án</button>
        <button class="btn-reset" onclick="resetQuiz()">Làm Lại</button>
    </div>
</div>

<script>
const quizData = __QUIZ_DATA__;

let userAnswers = {};

function renderQuiz() {
  const container = document.getElementById('quiz-container');
  document.getElementById('total-count').textContent = quizData.length;

  container.innerHTML = quizData.map((q, idx) => `
    <div class="question-card" id="card-${q.id}">
      <div class="question-title">Câu ${idx + 1}: ${q.question}</div>
      <ul class="options-list">
        ${q.options.map((opt, optIdx) => `
          <li class="option-item" 
              id="opt-${q.id}-${optIdx}" 
              onclick="selectOption(${q.id}, ${optIdx})">
            ${opt}
          </li>
        `).join('')}
      </ul>
      
      <button class="btn-toggle-explain" onclick="toggleExplanation(${q.id})">
        💡 Lời giải / Tham chiếu
      </button>

      <div class="explanation-box" id="explain-${q.id}">
        <strong>💡 Giải thích chi tiết:</strong>
        <div>${q.explanation}</div>
      </div>
    </div>
  `).join('');
}

function selectOption(qId, optionIdx) {
  userAnswers[qId] = optionIdx;
  
  // Highlight selected option
  const options = document.querySelectorAll(`#card-${qId} .option-item`);
  options.forEach((opt, idx) => {
    if (idx === optionIdx) {
      opt.classList.add('selected');
    } else {
      opt.classList.remove('selected');
    }
  });
}

function toggleExplanation(qId) {
  const box = document.getElementById(`explain-${qId}`);
  if (box.style.display === 'none' || box.style.display === '') {
    box.style.display = 'block';
  } else {
    box.style.display = 'none';
  }
}

function submitQuiz() {
  let score = 0;
  
  quizData.forEach(q => {
    const userAns = userAnswers[q.id];
    const card = document.getElementById(`card-${q.id}`);
    
    // Highlight correct & incorrect answers
    q.options.forEach((_, optIdx) => {
      const optElem = document.getElementById(`opt-${q.id}-${optIdx}`);
      optElem.classList.remove('selected');
      
      if (optIdx === q.correct) {
        optElem.classList.add('correct');
      }
      if (userAns !== undefined && userAns === optIdx && userAns !== q.correct) {
        optElem.classList.add('incorrect');
      }
    });

    if (userAns === q.correct) {
      score++;
    }

    // Tự động mở lời giải sau khi nộp bài
    document.getElementById(`explain-${q.id}`).style.display = 'block';
  });

  const scoreDisplay = document.getElementById('score-display');
  scoreDisplay.textContent = `Điểm số: ${score} / ${quizData.length} (${Math.round(score/quizData.length*100)}%)`;
  scoreDisplay.style.fontWeight = 'bold';
  
  alert(`Bạn đã hoàn thành bài thi! Điểm số: ${score}/${quizData.length}`);
}

function resetQuiz() {
  userAnswers = {};
  
  quizData.forEach(q => {
    // Xóa các class highlight
    q.options.forEach((_, optIdx) => {
      const optElem = document.getElementById(`opt-${q.id}-${optIdx}`);
      optElem.classList.remove('selected', 'correct', 'incorrect');
    });
    
    // Ẩn giải thích
    document.getElementById(`explain-${q.id}`).style.display = 'none';
  });

  // Reset điểm
  const scoreDisplay = document.getElementById('score-display');
  scoreDisplay.textContent = `Điểm số: -- / --`;
  scoreDisplay.style.fontWeight = 'normal';
  
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Khởi chạy khi load trang
window.onload = function() {
    const titleMatch = window.location.pathname.match(/([^/\\\\]+)\.html$/);
    if(titleMatch) {
        document.getElementById('quiz-title').textContent = decodeURIComponent(titleMatch[1]);
    }
    renderQuiz();
};
</script>

</body>
</html>
"""

    # Thay thế dữ liệu quiz
    html_content = template.replace("__QUIZ_DATA__", json.dumps(quiz_data, ensure_ascii=False, indent=2))
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    print(f"Da tao thanh cong file: {output_file} ({len(quiz_data)} cau hoi).")
    return True

def launch_gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox, scrolledtext
    import threading
    import glob

    root = tk.Tk()
    root.title("Công Cụ Chuyển Đổi Đề Trắc Nghiệm")
    root.geometry("650x450")
    
    target_path = tk.StringVar()
    
    def select_file():
        files = filedialog.askopenfilenames(title="Chọn file(s) .doc", filetypes=[("Word/HTML Document", "*.doc *.docx"), ("All files", "*.*")])
        if files:
            target_path.set(";".join(files))
            
    def select_folder():
        folder = filedialog.askdirectory(title="Chọn thư mục chứa file .doc")
        if folder:
            target_path.set(folder)
            
    def run_conversion():
        path_val = target_path.get()
        if not path_val:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn file hoặc thư mục trước!")
            return
            
        btn_convert.config(state=tk.DISABLED)
        txt_log.delete(1.0, tk.END)
        
        def process():
            files_to_convert = []
            if os.path.isdir(path_val):
                for ext in ["*.doc", "*.docx"]:
                    files_to_convert.extend(glob.glob(os.path.join(path_val, ext)))
            else:
                files_to_convert = path_val.split(";")
                
            if not files_to_convert:
                log("Không tìm thấy file .doc hoặc .docx nào để chuyển đổi.")
                root.after(0, lambda: btn_convert.config(state=tk.NORMAL))
                return
                
            log(f"Tìm thấy {len(files_to_convert)} file(s). Bắt đầu chuyển đổi...\n")
            success_count = 0
            for file in files_to_convert:
                if not os.path.exists(file):
                    continue
                out_file = os.path.splitext(file)[0] + ".html"
                try:
                    res = process_file(file, out_file)
                    if res is not False:
                        log(f"Thành công: {os.path.basename(file)}")
                        success_count += 1
                    else:
                        log(f"Thất bại (Sai định dạng): {os.path.basename(file)}")
                except Exception as e:
                    log(f"Lỗi khi xử lý {os.path.basename(file)}: {e}")
                    
            log(f"\nHoàn tất! Chuyển đổi thành công {success_count}/{len(files_to_convert)} file.")
            root.after(0, lambda: messagebox.showinfo("Hoàn tất", f"Đã chuyển đổi thành công {success_count} file!"))
            root.after(0, lambda: btn_convert.config(state=tk.NORMAL))
            
        threading.Thread(target=process, daemon=True).start()

    def log(msg):
        root.after(0, lambda: _append_log(msg))
        
    def _append_log(msg):
        txt_log.insert(tk.END, msg + "\n")
        txt_log.see(tk.END)

    # UI Layout
    frame_top = tk.Frame(root, pady=15, padx=15)
    frame_top.pack(fill=tk.X)
    
    tk.Label(frame_top, text="Đường dẫn:", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
    tk.Entry(frame_top, textvariable=target_path, width=40, font=("Arial", 10)).pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
    tk.Button(frame_top, text="Chọn File", command=select_file, bg="#e2e8f0").pack(side=tk.LEFT, padx=5)
    tk.Button(frame_top, text="Chọn Thư Mục", command=select_folder, bg="#e2e8f0").pack(side=tk.LEFT, padx=5)
    
    frame_mid = tk.Frame(root, pady=5, padx=15)
    frame_mid.pack(fill=tk.BOTH, expand=True)
    
    tk.Label(frame_mid, text="Trạng thái (Log):").pack(anchor=tk.W)
    txt_log = scrolledtext.ScrolledText(frame_mid, height=12, bg="#f7fafc")
    txt_log.pack(fill=tk.BOTH, expand=True, pady=5)
    
    frame_bot = tk.Frame(root, pady=15)
    frame_bot.pack(fill=tk.X)
    
    btn_convert = tk.Button(frame_bot, text="Bắt Đầu Convert", command=run_conversion, bg="#319795", fg="white", font=("Arial", 12, "bold"), padx=30, pady=10)
    btn_convert.pack()
    
    root.mainloop()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # CLI Mode
        input_file = sys.argv[1]
        if len(sys.argv) >= 3:
            output_file = sys.argv[2]
        else:
            output_file = os.path.splitext(input_file)[0] + ".html"
        process_file(input_file, output_file)
    else:
        # GUI Mode
        launch_gui()
