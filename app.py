import streamlit as st
import random
import os
import glob
import json
import docx
import pdfplumber
import google.generativeai as genai
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import cm
from io import BytesIO

# --- CONFIGURATION ---
st.set_page_config(page_title="Hệ Thống Tạo Đề Thi Thông Minh", layout="wide")

# Chèn CSS và JS để ép trình duyệt KHÔNG ĐƯỢC DỊCH
st.markdown("""
    <style>
        html, body, [data-testid="stWidgetLabel"], .stText, p, span:not(.material-icons) { 
            font-family: 'Roboto', sans-serif !important; 
        }
        .notranslate { translate: no !important; }
    </style>
    <script>
        var body = document.querySelector('body');
        body.setAttribute('translate', 'no');
        body.classList.add('notranslate');
        var meta = document.createElement('meta');
        meta.name = "google";
        meta.content = "notranslate";
        document.getElementsByTagName('head')[0].appendChild(meta);
    </script>
    """, unsafe_allow_html=True)

FONT_PATH = "Roboto-Regular.ttf"
EXPORT_DIR = "exports"

if not os.path.exists(EXPORT_DIR):
    os.makedirs(EXPORT_DIR)

if os.path.exists(FONT_PATH):
    pdfmetrics.registerFont(TTFont('Roboto', FONT_PATH))
    PDF_FONT = "Roboto"
else:
    PDF_FONT = "Helvetica"

# --- MOCK DATA ---
GRADES = [f"Lớp {i}" for i in range(1, 13)]
SEMESTERS = ["Học kỳ 1", "Học kỳ 2"]
SUBJECTS = ["Tiếng Anh", "Toán", "Ngữ văn"]

# Ngân hàng câu hỏi mẫu
QUESTIONS_DB = {
    "Tiếng Anh": {
        f"Lớp {i}": {
            "Multiple Choice": [
                {"question": "Choose the word that has a different stress pattern.", "translation": "Chọn từ có trọng âm khác với các từ còn lại.", "options": ["Doctor", "Student", "Advice", "Teacher"], "answer": "Advice"},
                {"question": "I ______ a student in this school last year.", "translation": "Tôi ______ một học sinh ở trường này vào năm ngoái.", "options": ["am", "is", "was", "were"], "answer": "was"},
                {"question": "What is the synonym of 'beautiful'?", "translation": "Từ đồng nghĩa của 'beautiful' (đẹp) là gì?", "options": ["Ugly", "Pretty", "Bad", "Smart"], "answer": "Pretty"},
                {"question": "She ______ to school by bus every day.", "translation": "Cô ấy ______ đến trường bằng xe buýt mỗi ngày.", "options": ["go", "goes", "going", "went"], "answer": "goes"},
                {"question": "Which one is a fruit?", "translation": "Cái nào sau đây là một loại trái cây?", "options": ["Carrot", "Potato", "Apple", "Onion"], "answer": "Apple"}
            ],
            "Essay": [
                {"question": "Write a short paragraph (50 words) about your family.", "translation": "Viết một đoạn văn ngắn (50 từ) về gia đình của bạn.", "answer": "Paragraph about family members and their jobs."},
                {"question": "What are the benefits of learning English?", "translation": "Những lợi ích của việc học tiếng Anh là gì?", "answer": "Communication, career opportunities, accessing information."}
            ]
        } for i in range(1, 13)
    },
    "Toán": {
        f"Lớp {i}": {
            "Multiple Choice": [
                {"question": "Kết quả của phép tính 25 + 75 là bao nhiêu?", "options": ["90", "100", "110", "120"], "answer": "100"},
                {"question": "Tìm x, biết x - 15 = 20.", "options": ["5", "25", "35", "45"], "answer": "35"},
                {"question": "Số nào sau đây là số nguyên tố?", "options": ["4", "6", "8", "7"], "answer": "7"},
                {"question": "1 giờ có bao nhiêu giây?", "options": ["60", "360", "3600", "120"], "answer": "3600"},
                {"question": "Hình nào có 3 cạnh?", "options": ["Hình vuông", "Hình tròn", "Hình tam giác", "Hình chữ nhật"], "answer": "Hình tam giác"}
            ],
            "Essay": [
                {"question": "Giải bài toán: Một cửa hàng có 100kg gạo, đã bán được 2/5 số gạo. Hỏi còn lại bao nhiêu kg gạo?", "answer": "Số gạo đã bán: 100 * 2/5 = 40kg. Số gạo còn lại: 100 - 40 = 60kg."},
                {"question": "Chứng minh rằng tổng ba góc của một tam giác bằng 180 độ.", "answer": "Sử dụng tính chất đường thẳng song song và góc so le trong."}
            ]
        } for i in range(1, 13)
    },
    "Ngữ văn": {
        f"Lớp {i}": {
            "Multiple Choice": [
                {"question": "Ai là tác giả của tác phẩm 'Truyện Kiều'?", "options": ["Nguyễn Khuyến", "Nguyễn Du", "Nguyễn Trãi", "Chu Văn An"], "answer": "Nguyễn Du"},
                {"question": "Câu 'Lá ơi! Hãy về với đất' sử dụng biện pháp nghệ thuật gì?", "options": ["So sánh", "Ẩn dụ", "Nhân hóa", "Hoán dụ"], "answer": "Nhân hóa"},
                {"question": "Tác phẩm 'Lão Hạc' của Nam Cao thuộc thể loại gì?", "options": ["Tiểu thuyết", "Truyện ngắn", "Tùy bút", "Hồi ký"], "answer": "Truyện ngắn"}
            ],
            "Essay": [
                {"question": "Phân tích nhân vật Lão Hạc trong truyện ngắn cùng tên của Nam Cao.", "answer": "Tập trung vào lòng tự trọng, tình yêu con và số phận bi thảm."},
                {"question": "Nêu cảm nghĩ của em về tình mẫu tử qua một tác phẩm văn học đã học.", "answer": "Dẫn chứng từ 'Trong lòng mẹ' hoặc các bài thơ về mẹ."}
            ]
        } for i in range(1, 13)
    }
}

# --- HELPER FUNCTIONS ---

def extract_text_from_file(uploaded_file):
    if uploaded_file.name.endswith(".docx"):
        doc = docx.Document(uploaded_file)
        return "\n".join([p.text for p in doc.paragraphs])
    elif uploaded_file.name.endswith(".pdf"):
        with pdfplumber.open(uploaded_file) as pdf:
            return "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
    else:
        return uploaded_file.read().decode("utf-8")

def ai_process_questions(text, api_key):
    try:
        genai.configure(api_key=api_key)
        
        # Tự động tìm mô hình khả dụng nhất
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        if not available_models:
            st.error("Không tìm thấy mô hình AI nào khả dụng trong tài khoản của bạn.")
            return None
            
        # Ưu tiên các dòng 1.5 mới, nếu không có thì lấy cái đầu tiên
        target_model = "models/gemini-1.5-flash"
        if target_model not in available_models:
            target_model = available_models[0]
            
        model = genai.GenerativeModel(target_model)
        prompt = f"""
        Analyze the following syllabus/text and extract exactly 10 multiple-choice questions and 5 essay questions.
        Return the result ONLY as a JSON object with this structure:
        {{
            "Multiple Choice": [
                {{"question": "text", "options": ["A", "B", "C", "D"], "answer": "correct_option_text", "translation": "vietnamese_translation_if_english"}},
                ...
            ],
            "Essay": [
                {{"question": "text", "answer": "suggested_answer", "translation": "vietnamese_translation_if_english"}},
                ...
            ]
        }}
        Text to analyze:
        {text}
        """
        response = model.generate_content(prompt)
        clean_json = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(clean_json)
    except Exception as e:
        st.error(f"Lỗi AI ({target_model if 'target_model' in locals() else 'Unknown'}): {str(e)}")
        return None

def generate_test(subject, grade, test_type, mc_ratio, duration, custom_db=None):
    db = custom_db if custom_db else QUESTIONS_DB[subject][grade]
    mc_pool = db["Multiple Choice"]
    essay_pool = db["Essay"]
    
    if test_type == "Trắc nghiệm":
        num_mc_q = 10
        num_essay_q = 0
    elif test_type == "Tự luận":
        num_mc_q = 0
        num_essay_q = 5
    else:
        num_mc_q = int(10 * (mc_ratio / 100))
        num_essay_q = 10 - num_mc_q

    selected_mc = random.sample(mc_pool, min(len(mc_pool), num_mc_q))
    selected_essay = random.sample(essay_pool, min(len(essay_pool), num_essay_q))
    return selected_mc, selected_essay

def get_answer_letter(q):
    try:
        idx = q['options'].index(q['answer'])
        return chr(65 + idx)
    except:
        return "?"

def export_pdf(subject, grade, semester, test_type, duration, mc_qs, essay_qs):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"De_Thi_{subject}_{grade}_{timestamp}.pdf".replace(" ", "_")
    filepath = os.path.join(EXPORT_DIR, filename)
    
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    MARGIN_LEFT, MARGIN_RIGHT, MARGIN_TOP, MARGIN_BOTTOM = 3*cm, 2*cm, 2*cm, 2*cm
    
    def draw_header(canvas_obj, title=f"BÀI KIỂM TRA MÔN {subject.upper()}"):
        canvas_obj.setFont(PDF_FONT, 16)
        canvas_obj.drawCentredString(width/2, height - MARGIN_TOP, title)
        canvas_obj.setFont(PDF_FONT, 12)
        canvas_obj.drawCentredString(width/2, height - MARGIN_TOP - 0.7*cm, f"{grade} | {semester} | Thời gian: {duration} phút | Thang điểm: 10")
        canvas_obj.line(MARGIN_LEFT, height - MARGIN_TOP - 1.2*cm, width - MARGIN_RIGHT, height - MARGIN_TOP - 1.2*cm)
        return height - MARGIN_TOP - 2*cm

    y = draw_header(p)
    
    if mc_qs:
        p.setFont(PDF_FONT, 14); p.drawString(MARGIN_LEFT, y, "Phần I: Trắc nghiệm"); y -= 0.8*cm
        p.setFont(PDF_FONT, 11)
        for i, q in enumerate(mc_qs):
            if y < MARGIN_BOTTOM + 2*cm: p.showPage(); y = height - MARGIN_TOP - 1*cm; p.setFont(PDF_FONT, 11)
            p.drawString(MARGIN_LEFT, y, f"Câu {i+1}: {q['question']}"); y -= 0.6*cm
            for idx, opt in enumerate(q['options']):
                p.drawString(MARGIN_LEFT + 0.5*cm, y, f"[  ] {chr(65+idx)}. {opt}"); y -= 0.5*cm
            y -= 0.3*cm
            
    if essay_qs:
        if y < MARGIN_BOTTOM + 3*cm: p.showPage(); y = height - MARGIN_TOP - 1*cm
        p.setFont(PDF_FONT, 14); p.drawString(MARGIN_LEFT, y, "Phần II: Tự luận"); y -= 0.8*cm
        p.setFont(PDF_FONT, 11)
        for i, q in enumerate(essay_qs):
            idx = i + 1 + len(mc_qs)
            if y < MARGIN_BOTTOM + 2*cm: p.showPage(); y = height - MARGIN_TOP - 1*cm; p.setFont(PDF_FONT, 11)
            p.drawString(MARGIN_LEFT, y, f"Câu {idx}: {q['question']}"); y -= 1.2*cm
            p.line(MARGIN_LEFT + 0.5*cm, y, width - MARGIN_RIGHT, y); y -= 0.8*cm

    p.setFont(PDF_FONT, 10); p.line(MARGIN_LEFT, MARGIN_BOTTOM, width - MARGIN_RIGHT, MARGIN_BOTTOM)
    p.drawString(MARGIN_LEFT, MARGIN_BOTTOM - 0.5*cm, "Bản quyền thuộc về: Tô Hoàng Long_PC")
    
    p.showPage()
    y = draw_header(p, title=f"ĐÁP ÁN CHI TIẾT MÔN {subject.upper()}")
    if mc_qs:
        p.setFont(PDF_FONT, 14); p.drawString(MARGIN_LEFT, y, "Đáp án Trắc nghiệm:"); y -= 0.8*cm
        p.setFont(PDF_FONT, 11)
        for i, q in enumerate(mc_qs):
            ans_letter = get_answer_letter(q)
            p.drawString(MARGIN_LEFT + 0.5*cm, y, f"Câu {i+1}: {ans_letter} ({q['answer']})"); y -= 0.5*cm
            if "translation" in q and q["translation"]:
                p.setFont(PDF_FONT, 10); p.drawString(MARGIN_LEFT + 1*cm, y, f"-> Dịch: {q['translation']}"); p.setFont(PDF_FONT, 11); y -= 0.6*cm
            if y < MARGIN_BOTTOM: p.showPage(); y = height - MARGIN_TOP
    
    y -= 0.5 * cm
    if essay_qs:
        p.setFont(PDF_FONT, 14); p.drawString(MARGIN_LEFT, y, "Gợi ý đáp án Tự luận:"); y -= 0.8*cm
        p.setFont(PDF_FONT, 11)
        for i, q in enumerate(essay_qs):
            p.drawString(MARGIN_LEFT + 0.5*cm, y, f"Câu {i + 1 + len(mc_qs)}: {q['answer']}"); y -= 0.5*cm
            if "translation" in q and q["translation"]:
                p.setFont(PDF_FONT, 10); p.drawString(MARGIN_LEFT + 1*cm, y, f"-> Dịch: {q['translation']}"); p.setFont(PDF_FONT, 11); y -= 0.6*cm
            if y < MARGIN_BOTTOM: p.showPage(); y = height - MARGIN_TOP

    p.save()
    with open(filepath, "wb") as f: f.write(buffer.getvalue())
    buffer.seek(0)
    return buffer, filename

# --- UI ---
st.title("🎓 Hệ Thống Tạo Đề Thi Thông Minh")

tab_create, tab_upload, tab_history = st.tabs(["📄 Tạo từ ngân hàng", "📁 Tạo từ đề cương cá nhân", "📜 Lịch sử file"])

with st.sidebar:
    st.header("⚙️ Cấu hình chung")
    subject = st.selectbox("Chọn môn học:", SUBJECTS)
    grade = st.selectbox("Chọn khối lớp:", GRADES)
    semester = st.selectbox("Chọn học kỳ:", SEMESTERS)
    test_type = st.radio("Hình thức thi:", ["Trắc nghiệm", "Tự luận", "Kết hợp cả hai"])
    mc_ratio = st.slider("Tỉ lệ Trắc nghiệm (%)", 0, 100, 70) if test_type == "Kết hợp cả hai" else 70
    duration = st.number_input("Thời gian (phút):", 15, 180, 45, 5)

with tab_create:
    generate_btn = st.button("🚀 Tạo đề từ ngân hàng", use_container_width=True)
    if generate_btn:
        mc_qs, essay_qs = generate_test(subject, grade, test_type, mc_ratio, duration)
        pdf_data, pdf_name = export_pdf(subject, grade, semester, test_type, duration, mc_qs, essay_qs)
        st.session_state['current_test'] = {"subject": subject, "grade": grade, "semester": semester, "mc": mc_qs, "essay": essay_qs, "pdf_data": pdf_data, "pdf_name": pdf_name}
        st.success("Đã tạo đề thi thành công!")

# --- AI CONFIG ---
GEMINI_API_KEY = "AIzaSyBZ-LE1wTgDBiSt7-jDPpUqQaG6yqc_Svw"

with tab_upload:
    st.header("Tải lên đề cương / Tài liệu")
    uploaded_file = st.file_uploader("Chọn file (Docx, PDF, TXT):", type=["docx", "pdf", "txt"])
    st.info("💡 AI đã được cấu hình sẵn. Bạn chỉ cần tải file lên và nhấn nút bên dưới.")
    
    if st.button("🔍 Bóc tách & Tạo đề bằng AI", use_container_width=True):
        if not uploaded_file:
            st.warning("Vui lòng tải file lên.")
        else:
            with st.spinner("AI đang đọc tài liệu và giải đề..."):
                file_text = extract_text_from_file(uploaded_file)
                custom_questions = ai_process_questions(file_text, GEMINI_API_KEY)
                if custom_questions:
                    mc_qs, essay_qs = generate_test(subject, grade, test_type, mc_ratio, duration, custom_db=custom_questions)
                    pdf_data, pdf_name = export_pdf(f"Custom_{subject}", grade, semester, test_type, duration, mc_qs, essay_qs)
                    st.session_state['current_test'] = {
                        "subject": f"Tùy chỉnh ({subject})",
                        "grade": grade,
                        "semester": semester,
                        "mc": mc_qs,
                        "essay": essay_qs,
                        "pdf_data": pdf_data,
                        "pdf_name": pdf_name
                    }
                    st.success("AI đã bóc tách và tạo đề thành công!")

# --- DISPLAY AREA ---
if 'current_test' in st.session_state:
    test = st.session_state['current_test']
    st.divider()
    st.header(f"📝 {test['subject']} - {test['grade']} - {test['semester']}")
    col1, col2 = st.columns([3, 1])
    with col1:
        if test['mc']:
            st.write("### Phần I: Trắc nghiệm")
            for i, q in enumerate(test['mc']):
                st.write(f"**Câu {i+1}:** {q['question']}")
                for idx, opt in enumerate(q['options']): st.write(f"&nbsp;&nbsp;&nbsp;&nbsp;[ ] {chr(65+idx)}. {opt}")
        if test['essay']:
            st.write("### Phần II: Tự luận")
            for i, q in enumerate(test['essay']): st.write(f"**Câu {len(test['mc']) + i + 1}:** {q['question']}")
        st.markdown("---")
        st.markdown("**Bản quyền thuộc về: Tô Hoàng Long_PC**")
    with col2:
        st.write("### Tùy chọn")
        st.download_button("📥 Tải PDF ngay", test['pdf_data'], test['pdf_name'], "application/pdf", use_container_width=True)
        with st.expander("👁️ Xem đáp án (Giáo viên)"):
            for i, q in enumerate(test['mc']):
                txt = f"**Câu {i+1}:** {get_answer_letter(q)}"
                if "translation" in q and q["translation"]: txt += f"  \n*(Dịch: {q['translation']})*"
                st.write(txt); st.write("")
            for i, q in enumerate(test['essay']):
                st.write(f"**Câu {len(test['mc'])+i+1}:** {q['answer']}")
                if "translation" in q and q["translation"]: st.caption(f"Dịch: {q['translation']}")
                st.write("")

with tab_history:
    st.header("Lịch sử các đề thi đã tạo")
    pdf_files = sorted(glob.glob(os.path.join(EXPORT_DIR, "*.pdf")), key=os.path.getmtime, reverse=True)
    for f_path in pdf_files:
        f_name = os.path.basename(f_path)
        col_i, col_d = st.columns([3, 1])
        with col_i: st.write(f"📄 **{f_name}**"); st.caption(f"Ngày: {datetime.fromtimestamp(os.path.getmtime(f_path))}")
        with col_d:
            with open(f_path, "rb") as f: st.download_button("Tải lại", f, f_name, "application/pdf", key=f"h_{f_name}")
        st.markdown("---")

st.markdown("""
    <style>.footer {position: fixed; left: 0; bottom: 0; width: 100%; background-color: #f0f2f6; text-align: center; padding: 10px; font-size: 14px; border-top: 1px solid #e6e9ef;}</style>
    <div class="footer"><p>Phát triển bởi <b>Tô Hoàng Long_PC</b> | © 2024 AI Test Generator Pro</p></div>
    """, unsafe_allow_html=True)
