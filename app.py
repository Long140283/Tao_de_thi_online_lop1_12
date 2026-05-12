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
            .stMainBlockContainer { padding-top: 1rem !important; }
        }
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

# Hàm tạo ngân hàng câu hỏi thật (tránh chung chung)
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

def ai_process_questions(text, api_key, num_q):
    try:
        genai.configure(api_key=api_key)
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        target_model = "models/gemini-1.5-flash" if "models/gemini-1.5-flash" in available_models else available_models[0]
        model = genai.GenerativeModel(target_model)
        prompt = f"Bóc tách đúng {num_q} câu trắc nghiệm và 2 câu tự luận từ văn bản này. Trả về JSON duy nhất (question, options, answer):\n{text}"
        response = model.generate_content(prompt)
        return json.loads(response.text.strip().replace("```json", "").replace("```", ""))
    except Exception as e:
        st.error(f"Lỗi AI: {str(e)}"); return None

def generate_test(subject, grade, test_type, mc_ratio, duration, total_q, custom_db=None):
    db = custom_db if custom_db else QUESTIONS_DB[subject][grade]
    mc_pool, essay_pool = db["Multiple Choice"], db["Essay"]
    num_mc_q = total_q if test_type == "Trắc nghiệm" else (0 if test_type == "Tự luận" else int(total_q * (mc_ratio/100)))
    num_essay_q = total_q - num_mc_q if test_type == "Kết hợp" else (0 if test_type == "Trắc nghiệm" else min(total_q, len(essay_pool)))
    return random.sample(mc_pool, min(len(mc_pool), num_mc_q)), random.sample(essay_pool, min(len(essay_pool), num_essay_q))

def export_pdf(subject, grade, semester, test_type, duration, mc_qs, essay_qs):
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
    p.setFont(PDF_FONT, 10); p.drawString(ml, mb-0.5*cm, "Bản quyền: Tô Hoàng Long_PC")
    p.showPage(); header(p, "ĐÁP ÁN")
    p.save(); f = open(filepath, "wb"); f.write(buffer.getvalue()); f.close(); buffer.seek(0); return buffer, filename

# --- MAIN UI ---
st.title("🎓 Hệ Thống Tạo Đề Thi Thông Minh")

with st.expander("⚙️ CẤU HÌNH ĐỀ THI (Nhấn để mở/đóng)", expanded=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        subject = st.selectbox("Môn học:", SUBJECTS)
        grade = st.selectbox("Khối lớp:", GRADES)
        total_q = st.number_input("Số lượng câu hỏi:", 5, 50, 10, 5)
    with col2:
        semester = st.selectbox("Học kỳ:", SEMESTERS)
        duration = st.number_input("Thời gian (phút):", 15, 180, 45, 5)
    with col3:
        test_type = st.radio("Hình thức:", ["Trắc nghiệm", "Tự luận", "Kết hợp"], horizontal=True)
        mc_ratio = st.slider("Tỉ lệ Trắc nghiệm (%)", 0, 100, 70) if test_type == "Kết hợp" else 70

tab_bank, tab_ai, tab_history = st.tabs(["📄 Tạo từ ngân hàng", "📁 Tạo từ đề cương (AI)", "📜 Lịch sử file"])

if st.button("🚀 TẠO ĐỀ THI NGAY", use_container_width=True, key="main_gen_btn"):
    if st.session_state.get('active_tab') == "📁 Tạo từ đề cương (AI)":
        # Handled inside tab_ai if necessary
        pass
    else:
        mc, es = generate_test(subject, grade, test_type, mc_ratio, duration, total_q)
        pdf, name = export_pdf(subject, grade, semester, test_type, duration, mc, es)
        st.session_state['test'] = {"sub": subject, "gr": grade, "sem": semester, "mc": mc, "es": es, "pdf": pdf, "name": name}
        st.success(f"Đã tạo đề thi thành công!")

with tab_ai:
    st.write("Tải file lên để AI bóc tách câu hỏi và tạo đề.")
    up_file = st.file_uploader("Chọn file Word/PDF/TXT:", type=["docx", "pdf", "txt"])
    if st.button("🔍 AI Bóc tách & Tạo đề", use_container_width=True):
        if up_file:
            with st.spinner("AI đang xử lý..."):
                txt = extract_text_from_file(up_file)
                custom = ai_process_questions(txt, GEMINI_API_KEY, total_q)
                if custom:
                    mc, es = generate_test(subject, grade, test_type, mc_ratio, duration, total_q, custom_db=custom)
                    pdf, name = export_pdf(f"AI_{subject}", grade, semester, test_type, duration, mc, es)
                    st.session_state['test'] = {"sub": f"AI ({subject})", "gr": grade, "sem": semester, "mc": mc, "es": es, "pdf": pdf, "name": name}
                    st.success("AI đã tạo đề xong!")

if 'test' in st.session_state:
    t = st.session_state['test']
    st.divider()
    st.header(f"📝 {t['sub']} - {t['gr']} - {t['sem']}")
    c1, c2 = st.columns([2, 1])
    with c1:
        if t['mc']:
            st.write("### I. Trắc nghiệm")
            for i, q in enumerate(t['mc']): st.write(f"**Câu {i+1}:** {q['question']}")
        if t['es']:
            st.write("### II. Tự luận")
            for i, q in enumerate(t['es']): st.write(f"**Câu {len(t['mc'])+i+1}:** {q['question']}")
    with c2:
        st.download_button("📥 Tải PDF", t['pdf'], t['name'], "application/pdf", use_container_width=True)
        with st.expander("👁️ Xem đáp án"):
            for i, q in enumerate(t['mc']): st.write(f"Câu {i+1}: {q['answer']}")
            for i, q in enumerate(t['es']): st.write(f"Câu {len(t['mc'])+i+1}: {q['answer']}")

with tab_history:
    st.header("Lịch sử")
    pdfs = sorted(glob.glob("exports/*.pdf"), key=os.path.getmtime, reverse=True)
    for f in pdfs:
        n = os.path.basename(f)
        col_i, col_d = st.columns([3, 1])
        with col_i: st.write(f"📄 {n}")
        with col_d:
            with open(f, "rb") as rb: st.download_button("Tải lại", rb, n, "application/pdf", key=f"h_{n}")

st.markdown("<div style='text-align:center; padding:20px; color:gray;'>Phát triển bởi Tô Hoàng Long_PC | © 2024</div>", unsafe_allow_html=True)
