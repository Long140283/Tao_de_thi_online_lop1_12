import streamlit as st
import random
import os
import glob
import json
import docx
import pdfplumber
import google.generativeai as genai
import time
from PIL import Image
from datetime import datetime, timedelta
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import cm
from io import BytesIO
import database as db

# --- CONFIGURATION ---
st.set_page_config(page_title="Hệ Thống Thi Trực Tuyến Thông Minh", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
        html, body, p, div:not([class*="st-emotion-cache"]) > span { 
            font-family: 'Roboto', sans-serif !important; 
        }
        .st-emotion-cache-16idsys p, .st-emotion-cache-16idsys span, [data-testid="stExpander"] svg {
            font-family: inherit !important;
        }
        .notranslate { translate: no !important; }
        @media (max-width: 768px) {
            .stMainBlockContainer { padding: 1rem !important; }
            .stButton button { width: 100% !important; }
        }
        /* Mobile optimization for quiz */
        .question-box {
            background-color: #f0f2f6;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            border-left: 5px solid #4CAF50;
        }
        .timer-box {
            position: fixed;
            top: 70px;
            right: 20px;
            background: #ff4b4b;
            color: white;
            padding: 10px 20px;
            border-radius: 50px;
            z-index: 1000;
            font-weight: bold;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
    </style>
    <script>
        var body = document.querySelector('body');
        body.setAttribute('translate', 'no');
        body.classList.add('notranslate');
    </script>
    """, unsafe_allow_html=True)

FONT_PATH = "Roboto-Regular.ttf"
EXPORT_DIR = "exports"
GEMINI_API_KEY = "AIzaSyBZ-LE1wTgDBiSt7-jDPpUqQaG6yqc_Svw"

if not os.path.exists(EXPORT_DIR): os.makedirs(EXPORT_DIR)
if os.path.exists(FONT_PATH):
    pdfmetrics.registerFont(TTFont('Roboto', FONT_PATH))
    PDF_FONT = "Roboto"
else: PDF_FONT = "Helvetica"

# --- REAL QUESTIONS DATABASE ---
GRADES = [f"Lớp {i}" for i in range(1, 13)]
SEMESTERS = ["Học kỳ 1", "Học kỳ 2"]
SUBJECTS = ["Tiếng Anh", "Toán", "Ngữ văn"]

def get_real_questions(subject, grade_idx):
    if subject == "Tiếng Anh":
        return {
            "Multiple Choice": [
                {"question": "How ______ oranges are there in the fridge?", "options": ["many", "much", "long", "far"], "answer": "many", "translation": "Có bao nhiêu quả cam trong tủ lạnh?"},
                {"question": "She ______ to music every evening.", "options": ["listen", "listens", "listening", "listened"], "answer": "listens", "translation": "Cô ấy nghe nhạc mỗi tối."},
                {"question": "What is the capital of Vietnam?", "options": ["Hue", "Da Nang", "Hanoi", "Ho Chi Minh City"], "answer": "Hanoi", "translation": "Thủ đô của Việt Nam là gì?"},
                {"question": "I ______ my homework at the moment.", "options": ["do", "does", "am doing", "did"], "answer": "am doing", "translation": "Tôi đang làm bài tập về nhà ngay lúc này."},
                {"question": "The book is ______ the table.", "options": ["in", "on", "at", "under"], "answer": "on", "translation": "Cuốn sách ở trên bàn."},
                {"question": "Choose the word with different stress: 'Teacher', 'Doctor', 'Advice', 'Student'", "options": ["Teacher", "Doctor", "Advice", "Student"], "answer": "Advice", "translation": "Chọn từ có trọng âm khác."},
                {"question": "They ______ to the zoo last Sunday.", "options": ["go", "goes", "went", "going"], "answer": "went", "translation": "Họ đã đi sở thú vào chủ nhật tuần trước."},
                {"question": "If it rains, I ______ an umbrella.", "options": ["take", "takes", "will take", "took"], "answer": "will take", "translation": "Nếu trời mưa, tôi sẽ mang theo ô."},
                {"question": "My father is a ______. He works in a hospital.", "options": ["teacher", "farmer", "doctor", "driver"], "answer": "doctor", "translation": "Bố tôi là bác sĩ. Ông ấy làm việc ở bệnh viện."},
                {"question": "How ______ is a bowl of beef noodles?", "options": ["many", "much", "often", "long"], "answer": "much", "translation": "Một bát phở bò giá bao nhiêu?"}
            ],
            "Essay": [
                {"question": "Write a paragraph (50 words) about your daily routine.", "answer": "Students should mention waking up, eating breakfast, going to school...", "translation": "Viết đoạn văn về thói quen hàng ngày."},
                {"question": "Why is learning English important for your future?", "answer": "Communication, job opportunities, information access.", "translation": "Tại sao học tiếng Anh lại quan trọng cho tương lai?"}
            ]
        }
    elif subject == "Toán":
        level = grade_idx + 1
        return {
            "Multiple Choice": [
                {"question": f"Kết quả của phép tính {15*level} + {25*level} là:", "options": [f"{40*level-5}", f"{40*level}", f"{40*level+5}", f"{40*level+10}"], "answer": f"{40*level}"},
                {"question": f"Tìm x, biết x - {10*level} = {50*level}:", "options": [f"{40*level}", f"{60*level}", f"{70*level}", f"{50*level}"], "answer": f"{60*level}"},
                {"question": "Số nào sau đây là số nguyên tố?", "options": ["4", "9", "15", "17"], "answer": "17"},
                {"question": "Diện tích hình chữ nhật có chiều dài 10cm, chiều rộng 5cm là:", "options": ["15cm2", "50cm2", "30cm2", "25cm2"], "answer": "50cm2"},
                {"question": "1 giờ 15 phút bằng bao nhiêu phút?", "options": ["65 phút", "75 phút", "85 phút", "95 phút"], "answer": "75 phút"},
                {"question": "Số lớn nhất có 3 chữ số khác nhau là:", "options": ["999", "987", "900", "978"], "answer": "987"},
                {"question": "Căn bậc hai của 144 là:", "options": ["10", "11", "12", "14"], "answer": "12"},
                {"question": f"Giá trị của {level} x 9 là:", "options": [f"{level*8}", f"{level*9}", f"{level*10}", f"{level*7}"], "answer": f"{level*9}"},
                {"question": "Phân số nào lớn hơn 1?", "options": ["3/4", "5/5", "7/6", "1/2"], "answer": "7/6"},
                {"question": "Hình nào có 3 cạnh?", "options": ["Hình vuông", "Hình tròn", "Hình tam giác", "Hình thoi"], "answer": "Hình tam giác"}
            ],
            "Essay": [
                {"question": "Giải bài toán: Một cửa hàng có 200kg gạo, buổi sáng bán được 1/4 số gạo. Hỏi cửa hàng còn lại bao nhiêu kg?", "answer": "Số gạo bán: 200/4 = 50kg. Còn lại: 200 - 50 = 150kg."},
                {"question": "Tính diện tích hình thang có đáy lớn 10cm, đáy nhỏ 6cm và chiều cao 5cm.", "answer": "S = (10+6)*5/2 = 40cm2."}
            ]
        }
    else: # Ngữ văn
        return {
            "Multiple Choice": [
                {"question": "Tác giả của tác phẩm 'Truyện Kiều' là ai?", "options": ["Nguyễn Khuyến", "Nguyễn Du", "Nguyễn Trãi", "Chu Văn An"], "answer": "Nguyễn Du"},
                {"question": "Câu 'Lá ơi! Hãy về với đất' sử dụng biện pháp nghệ thuật gì?", "options": ["So sánh", "Ẩn dụ", "Nhân hóa", "Hoán dụ"], "answer": "Nhân hóa"},
                {"question": "Tác phẩm 'Lão Hạc' của Nam Cao thuộc thể loại gì?", "options": ["Tiểu thuyết", "Truyện ngắn", "Tùy bút", "Hồi ký"], "answer": "Truyện ngắn"},
                {"question": "Nhân vật chính trong truyện 'Dế Mèn phiêu lưu ký' là ai?", "options": ["Dế Choắt", "Dế Mèn", "Chị Cốc", "Dế Trũi"], "answer": "Dế Mèn"},
                {"question": "Sông Hương chảy qua thành phố nào của nước ta?", "options": ["Hà Nội", "Huế", "Đà Nẵng", "Cần Thơ"], "answer": "Huế"},
                {"question": "Từ nào sau đây viết đúng chính tả?", "options": ["Xắp sếp", "Sắp sếp", "Sắp xếp", "Xắp xếp"], "answer": "Sắp xếp"},
                {"question": "Thành ngữ 'Học đi đôi với hành' nhấn mạnh điều gì?", "options": ["Chỉ học lý thuyết", "Chỉ làm thực tế", "Học phải áp dụng", "Không cần học"], "answer": "Học phải áp dụng"},
                {"question": "Ai là người được mệnh danh là 'Tiên thơ'?", "options": ["Lý Bạch", "Đỗ Phủ", "Bạch Cư Dị", "Vương Duy"], "answer": "Lý Bạch"},
                {"question": "Tác phẩm 'Tắt đèn' của tác giả nào?", "options": ["Nam Cao", "Ngô Tất Tố", "Vũ Trọng Phụng", "Nguyên Hồng"], "answer": "Ngô Tất Tố"},
                {"question": "Câu 'Ôi! Đẹp quá!' thuộc kiểu câu gì?", "options": ["Câu kể", "Câu hỏi", "Câu cảm", "Câu cầu khiến"], "answer": "Câu cảm"}
            ],
            "Essay": [
                {"question": "Phân tích nhân vật Lão Hạc trong truyện ngắn cùng tên của Nam Cao.", "answer": "Lòng tự trọng, tình thương con, số phận bi thảm của người nông dân."},
                {"question": "Viết đoạn văn ngắn nêu cảm nhận của em về tình mẫu tử.", "answer": "Sự hy sinh vô điều kiện, tình yêu thương bao la của mẹ."}
            ]
        }

QUESTIONS_DB = {sub: {grade: get_real_questions(sub, idx) for idx, grade in enumerate(GRADES)} for sub in SUBJECTS}

# --- FUNCTIONS ---
def extract_text_from_file(uploaded_file):
    if uploaded_file.name.endswith(".docx"):
        doc = docx.Document(uploaded_file)
        return "\n".join([p.text for p in doc.paragraphs])
    elif uploaded_file.name.endswith(".pdf"):
        with pdfplumber.open(uploaded_file) as pdf:
            return "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
    return uploaded_file.read().decode("utf-8")

def ai_process_questions(input_data, api_key, num_q):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = f"Phân tích dữ liệu (văn bản hoặc hình ảnh) này và bóc tách đúng {num_q} câu trắc nghiệm và 2 câu tự luận. Trả về JSON duy nhất với cấu trúc: {{'mc': [{{'question': '...', 'options': ['...', '...', '...', '...'], 'answer': '...'}}], 'es': [{{'question': '...', 'answer': '...'}}]}}"
        
        response = model.generate_content([prompt, input_data])
        content = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(content)
    except Exception as e:
        st.error(f"Lỗi AI: {str(e)}"); return None

def ai_grade_essay(question, student_answer, reference_answer):
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = f"Câu hỏi: {question}\nĐáp án mẫu: {reference_answer}\nBài làm học sinh: {student_answer}\n\nHãy chấm điểm bài làm này trên thang điểm 10. Trả về JSON: {{'score': float, 'comment': string}}"
        response = model.generate_content(prompt)
        content = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(content)
    except:
        return {"score": 0, "comment": "Không thể chấm điểm tự động."}

def generate_test(subject, grade, test_type, mc_ratio, total_q, custom_db=None):
    db_source = custom_db if custom_db else QUESTIONS_DB[subject][grade]
    mc_pool, essay_pool = db_source["Multiple Choice"], db_source["Essay"]
    
    if test_type == "Trắc nghiệm":
        num_mc_q, num_essay_q = total_q, 0
    elif test_type == "Tự luận":
        num_mc_q, num_essay_q = 0, total_q
    else:
        num_mc_q = int(total_q * (mc_ratio/100))
        num_essay_q = total_q - num_mc_q
    
    if mc_pool:
        if len(mc_pool) >= num_mc_q:
            selected_mc = random.sample(mc_pool, num_mc_q)
        else:
            selected_mc = random.choices(mc_pool, k=num_mc_q)
    else:
        selected_mc = []

    if essay_pool:
        if len(essay_pool) >= num_essay_q:
            selected_essay = random.sample(essay_pool, num_essay_q)
        else:
            selected_essay = random.choices(essay_pool, k=num_essay_q)
    else:
        selected_essay = []
    
    return {"mc": selected_mc, "es": selected_essay}

def export_pdf(subject, grade, semester, duration, questions):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"De_Thi_{subject}_{grade}_{timestamp}.pdf".replace(" ", "_")
    filepath = os.path.join(EXPORT_DIR, filename)
    buffer = BytesIO(); p = canvas.Canvas(buffer, pagesize=A4); width, height = A4
    ml, mr, mt, mb = 3*cm, 2*cm, 2*cm, 2*cm
    
    def header(c, t=f"BÀI KIỂM TRA MÔN {subject.upper()}"):
        c.setFont(PDF_FONT, 16); c.drawCentredString(width/2, height-mt, t)
        c.setFont(PDF_FONT, 12); c.drawCentredString(width/2, height-mt-0.7*cm, f"{grade} | {semester} | {duration}p")
        c.line(ml, height-mt-1.2*cm, width-mr, height-mt-1.2*cm); return height-mt-2*cm
    
    y = header(p)
    mc_qs, essay_qs = questions.get('mc', []), questions.get('es', [])
    
    if mc_qs:
        p.setFont(PDF_FONT, 14); p.drawString(ml, y, "I. Trắc nghiệm"); y -= 0.8*cm
        for i, q in enumerate(mc_qs):
            if y < mb+2*cm: p.showPage(); y=height-mt-1*cm
            p.setFont(PDF_FONT, 11); p.drawString(ml, y, f"Câu {i+1}: {q['question']}"); y -= 0.6*cm
            for idx, opt in enumerate(q['options']): 
                p.drawString(ml+0.5*cm, y, f"[ ] {chr(65+idx)}. {opt}"); y -= 0.5*cm
            y -= 0.2*cm
    
    if essay_qs:
        if y < mb+3*cm: p.showPage(); y=height-mt-1*cm
        p.setFont(PDF_FONT, 14); p.drawString(ml, y, "II. Tự luận"); y -= 0.8*cm
        for i, q in enumerate(essay_qs):
            if y < mb+2*cm: p.showPage(); y=height-mt-1*cm
            p.setFont(PDF_FONT, 11); p.drawString(ml, y, f"Câu {len(mc_qs)+i+1}: {q['question']}"); y -= 1.2*cm
            p.line(ml+0.5*cm, y, width-mr, y); y -= 0.8*cm
            
    p.setFont(PDF_FONT, 10); p.drawString(ml, mb-0.5*cm, "Bản quyền: Hệ thống Thi Online")
    p.showPage(); header(p, "ĐÁP ÁN")
    p.save(); buffer.seek(0)
    with open(filepath, "wb") as f: f.write(buffer.getvalue())
    return buffer, filename

# --- UI LOGIC ---
query_params = st.query_params
test_id_param = query_params.get("test_id")

if test_id_param:
    # --- STUDENT MODE ---
    test_data = db.get_test(test_id_param)
    if not test_data:
        st.error("Không tìm thấy đề thi này!")
    else:
        st.title(f"📝 {test_data['title']}")
        st.info(f"Môn: {test_data['subject']} | Khối: {test_data['grade']} | Thời gian: {test_data['duration']} phút")
        
        if 'student_name' not in st.session_state:
            with st.form("enter_name"):
                name = st.text_input("Nhập họ và tên của em để bắt đầu:")
                if st.form_submit_button("Vào thi"):
                    if name:
                        if db.check_existing_submission(test_id_param, name):
                            st.warning("Em đã nộp bài thi này rồi!")
                        else:
                            st.session_state['student_name'] = name
                            st.session_state['start_time'] = time.time()
                            st.rerun()
                    else:
                        st.error("Vui lòng nhập tên!")
        else:
            # Quiz Interface
            elapsed = time.time() - st.session_state['start_time']
            remaining = (test_data['duration'] * 60) - elapsed
            
            if remaining <= 0:
                st.warning("Hết thời gian làm bài! Hệ thống đang tự động nộp bài...")
                remaining = 0
            
            # Timer Display
            st.markdown(f"<div class='timer-box'>⏳ {int(remaining // 60)}:{int(remaining % 60):02d}</div>", unsafe_allow_html=True)
            
            with st.form("exam_form"):
                answers = {}
                q_idx = 1
                for q in test_data['questions']['mc']:
                    st.markdown(f"<div class='question-box'><b>Câu {q_idx}:</b> {q['question']}</div>", unsafe_allow_html=True)
                    answers[f"mc_{q_idx-1}"] = st.radio(f"Chọn đáp án (Câu {q_idx})", q['options'], key=f"q_{q_idx}", index=None)
                    q_idx += 1
                
                for q in test_data['questions']['es']:
                    st.markdown(f"<div class='question-box'><b>Câu {q_idx}:</b> {q['question']} (Tự luận)</div>", unsafe_allow_html=True)
                    answers[f"es_{q_idx-len(test_data['questions']['mc'])-1}"] = st.text_area(f"Trả lời (Câu {q_idx})", key=f"q_{q_idx}")
                    q_idx += 1
                
                submitted = st.form_submit_button("NỘP BÀI")
                if submitted or remaining <= 0:
                    # Calculate Score
                    score = 0
                    total_mc = len(test_data['questions']['mc'])
                    for i, q in enumerate(test_data['questions']['mc']):
                        if answers.get(f"mc_{i}") == q['answer']:
                            score += (10 / q_idx) # Rough score calculation
                    
                    db.save_submission(test_id_param, st.session_state['student_name'], answers, score, q_idx-1)
                    st.success(f"Chúc mừng {st.session_state['student_name']} đã hoàn thành bài thi!")
                    st.balloons()
                    # Clean up
                    del st.session_state['student_name']
                    st.stop()
            
            if remaining > 0:
                time.sleep(1)
                st.rerun()

else:
    # --- TEACHER MODE ---
    st.title("🎓 Hệ Thống Quản Lý Thi Thông Minh")
    
    tab_gen, tab_bank_mgmt, tab_results, tab_history = st.tabs(["🚀 Tạo đề thi mới", "📂 Quản lý Ngân hàng", "📊 Kết quả học sinh", "📜 Lịch sử PDF"])
    
    with tab_gen:
        with st.expander("⚙️ CẤU HÌNH ĐỀ THI", expanded=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                subj = st.selectbox("Môn học:", SUBJECTS)
                grd = st.selectbox("Khối lớp:", GRADES)
                num_q = st.number_input("Số lượng câu hỏi:", 5, 50, 10)
            with col2:
                sem = st.selectbox("Học kỳ:", SEMESTERS)
                dur = st.number_input("Thời gian (phút):", 15, 180, 45)
            with col3:
                t_type = st.radio("Hình thức:", ["Trắc nghiệm", "Tự luận", "Kết hợp"])
                ratio = st.slider("Tỉ lệ Trắc nghiệm (%)", 0, 100, 70) if t_type == "Kết hợp" else 70

        source = st.radio("Nguồn câu hỏi:", ["Ngân hàng hệ thống", "AI (File/Camera)", "Folder cá nhân"], horizontal=True)
        
        current_questions = None
        
        if source == "Ngân hàng hệ thống":
            if st.button("Tạo đề từ hệ thống"):
                current_questions = generate_test(subj, grd, t_type, ratio, num_q)
        
        elif source == "AI (File/Camera)":
            tab_file, tab_cam = st.tabs(["📁 Tải file", "📸 Chụp ảnh"])
            ai_data = None
            with tab_file:
                up_file = st.file_uploader("Tải lên file (Word/PDF):", type=["docx", "pdf"])
                if up_file: ai_data = extract_text_from_file(up_file)
            with tab_cam:
                cam_img = st.camera_input("Chụp ảnh đề cương/sách")
                if cam_img: ai_data = Image.open(cam_img)
            
            if st.button("🔍 AI Bóc tách dữ liệu"):
                if ai_data:
                    with st.spinner("AI đang phân tích dữ liệu..."):
                        custom = ai_process_questions(ai_data, GEMINI_API_KEY, num_q)
                        if custom:
                            st.session_state['temp_ai_qs'] = custom
                            st.success("Bóc tách thành công! Bạn có muốn lưu vào Folder không?")
                else: st.error("Chưa có dữ liệu đầu vào!")
            
            if 'temp_ai_qs' in st.session_state:
                st.write("### Câu hỏi vừa bóc tách:")
                st.json(st.session_state['temp_ai_qs'])
                
                folders = db.get_folders()
                if folders:
                    f_names = [f['name'] for f in folders]
                    sel_f = st.selectbox("Chọn Folder để lưu:", f_names)
                    if st.button("💾 Lưu vào Folder & Tạo đề"):
                        f_id = next(f['id'] for f in folders if f['name'] == sel_f)
                        db.save_questions_to_folder(f_id, subj, grd, st.session_state['temp_ai_qs'])
                        current_questions = generate_test(subj, grd, t_type, ratio, num_q, custom_db=st.session_state['temp_ai_qs'])
                        st.success(f"Đã lưu vào folder {sel_f}!")
                else:
                    st.warning("Bạn chưa có Folder nào. Hãy tạo Folder trong tab 'Quản lý Ngân hàng'.")
                    if st.button("Tạo đề ngay không lưu"):
                        current_questions = generate_test(subj, grd, t_type, ratio, num_q, custom_db=st.session_state['temp_ai_qs'])

        elif source == "Folder cá nhân":
            folders = db.get_folders()
            if folders:
                f_names = [f['name'] for f in folders]
                sel_f = st.selectbox("Chọn Folder nguồn:", f_names)
                if st.button("🚀 Tạo đề từ Folder"):
                    f_id = next(f['id'] for f in folders if f['name'] == sel_f)
                    folder_db = db.get_questions_from_folder(f_id)
                    if folder_db['Multiple Choice'] or folder_db['Essay']:
                        current_questions = generate_test(subj, grd, t_type, ratio, num_q, custom_db=folder_db)
                    else:
                        st.error("Folder này chưa có câu hỏi nào!")
            else:
                st.info("Hãy tạo folder và thêm câu hỏi từ AI trước.")

        if current_questions:
            st.session_state['current_questions'] = current_questions
            st.session_state['test_info'] = {"subj": subj, "grd": grd, "sem": sem, "dur": dur}
            st.success("Đã tạo đề thi thành công! Xem bên dưới.")

        if 'current_questions' in st.session_state:
            q = st.session_state['current_questions']
            info = st.session_state['test_info']
            
            st.divider()
            c1, c2 = st.columns([2, 1])
            with c1:
                st.subheader("Xem trước đề thi")
                if q['mc']:
                    for i, item in enumerate(q['mc']): st.write(f"**Câu {i+1}:** {item['question']}")
                if q['es']:
                    for i, item in enumerate(q['es']): st.write(f"**Câu {len(q['mc'])+i+1}:** {item['question']}")
            
            with c2:
                st.subheader("Hành động")
                # PDF Export
                if st.button("📥 Xuất bản PDF"):
                    pdf_buf, pdf_name = export_pdf(info['subj'], info['grd'], info['sem'], info['dur'], q)
                    st.download_button("Tải PDF về máy", pdf_buf, pdf_name, "application/pdf")
                
                # Online Share
                if st.button("🔗 Lưu & Chia sẻ Link Thi"):
                    title = f"Đề thi {info['subj']} - {info['grd']}"
                    t_id = db.save_test(title, info['subj'], info['grd'], q, info['dur'])
                    # Generate link
                    base_url = "http://localhost:8501" # Default for local
                    full_link = f"{base_url}/?test_id={t_id}"
                    
                    st.success("Đã lưu đề thi lên hệ thống!")
                    st.write("**Mã đề thi (Test ID):**")
                    st.code(t_id)
                    st.write("**Đường link chia sẻ cho học sinh:**")
                    st.code(full_link)
                    st.info("💡 Lưu ý: Khi đưa lên mạng, hãy thay 'localhost:8501' bằng địa chỉ trang web của bạn.")

    with tab_bank_mgmt:
        st.subheader("📁 Quản lý Thư mục Câu hỏi")
        with st.form("new_folder"):
            f_name = st.text_input("Tên Folder mới (VD: Ôn tập Chương 1):")
            f_note = st.text_input("Ghi chú:")
            if st.form_submit_button("Tạo Folder"):
                if f_name:
                    db.create_folder(f_name, f_note)
                    st.success(f"Đã tạo folder {f_name}")
                    st.rerun()
        
        st.divider()
        folders = db.get_folders()
        if not folders:
            st.info("Chưa có folder nào. Hãy tạo folder đầu tiên ở trên!")
        for f in folders:
            with st.expander(f"📂 {f['name']} ({f['note']})"):
                qs = db.get_questions_from_folder(f['id'])
                st.write(f"Tổng số: {len(qs['Multiple Choice'])} câu trắc nghiệm, {len(qs['Essay'])} câu tự luận")
                if st.button("Xem chi tiết", key=f"view_{f['id']}"):
                    st.json(qs)

    with tab_results:
        st.subheader("Danh sách kết quả học sinh")
        test_id_input = st.text_input("Nhập Mã Đề Thi (Test ID) để xem kết quả:", placeholder="Ví dụ: a1b2c3d4")
        if test_id_input:
            results = db.get_submissions(test_id_input)
            if results:
                for res in results:
                    with st.expander(f"👤 {res['student_name']} - Điểm: {res['score']:.2f}/{res['total_q']}"):
                        st.write(f"⏰ Nộp lúc: {res['submitted_at']}")
                        st.write("---")
                        st.json(res['answers'])
                        
                        if st.button(f"🤖 Chấm điểm Tự luận bằng AI", key=f"ai_{res['id']}"):
                            with st.spinner("AI đang chấm bài..."):
                                test_info = db.get_test(test_id_input)
                                total_ai_score = res['score'] # Start with current score (MC)
                                
                                for i, q in enumerate(test_info['questions']['es']):
                                    ans = res['answers'].get(f"es_{i}")
                                    if ans:
                                        result = ai_grade_essay(q['question'], ans, q['answer'])
                                        st.info(f"**Câu {i+1} (AI):** {result['score']}đ - {result['comment']}")
                                        total_ai_score += result['score']
                                
                                db.update_submission_score(res['id'], total_ai_score)
                                st.success(f"Đã cập nhật điểm tổng: {total_ai_score:.2f}")
                                st.rerun()
            else:
                st.info("Chưa có học sinh nào nộp bài cho mã đề này.")

    with tab_history:
        st.subheader("Các tệp PDF đã tạo")
        pdfs = sorted(glob.glob("exports/*.pdf"), key=os.path.getmtime, reverse=True)
        for f in pdfs:
            n = os.path.basename(f)
            col_i, col_d = st.columns([3, 1])
            with col_i: st.write(f"📄 {n}")
            with col_d:
                with open(f, "rb") as rb: st.download_button("Tải lại", rb, n, "application/pdf", key=f"h_{n}")

st.markdown("<div style='text-align:center; padding:20px; color:gray;'>Phát triển bởi Hệ thống Thi Online | © 2024</div>", unsafe_allow_html=True)
