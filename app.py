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
        html, body, [data-testid="stWidgetLabel"], .stText, p, span:not(.material-icons) { 
            font-family: 'Roboto', sans-serif !important; 
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

# --- MOCK DATA ---
GRADES = [f"Lớp {i}" for i in range(1, 13)]
SEMESTERS = ["Học kỳ 1", "Học kỳ 2"]
SUBJECTS = ["Tiếng Anh", "Toán", "Ngữ văn"]

# Ngân hàng câu hỏi mẫu đầy đủ
QUESTIONS_DB = {
    "Tiếng Anh": {
        f"Lớp {i}": {
            "Multiple Choice": [
                {"question": "Choose the word that has a different stress pattern.", "translation": "Chọn từ có trọng âm khác.", "options": ["Doctor", "Student", "Advice", "Teacher"], "answer": "Advice"},
                {"question": "I ______ a student in this school last year.", "translation": "Tôi là học sinh năm ngoái.", "options": ["am", "is", "was", "were"], "answer": "was"},
                {"question": "What is the synonym of 'beautiful'?", "translation": "Từ đồng nghĩa của 'beautiful'?", "options": ["Ugly", "Pretty", "Bad", "Smart"], "answer": "Pretty"},
                {"question": "She ______ to school by bus every day.", "translation": "Cô ấy đi học bằng xe buýt.", "options": ["go", "goes", "going", "went"], "answer": "goes"},
                {"question": "Which one is a fruit?", "translation": "Cái nào là trái cây?", "options": ["Carrot", "Potato", "Apple", "Onion"], "answer": "Apple"},
                {"question": "They ______ dinner when the phone rang.", "translation": "Họ đang ăn tối thì điện thoại reo.", "options": ["eat", "ate", "were eating", "are eating"], "answer": "were eating"},
                {"question": "How ______ oranges are there?", "translation": "Có bao nhiêu quả cam?", "options": ["many", "much", "long", "far"], "answer": "many"},
                {"question": "The sun ______ in the East.", "translation": "Mặt trời mọc ở hướng Đông.", "options": ["rise", "rises", "rising", "rose"], "answer": "rises"},
                {"question": "If it rains, we ______ at home.", "translation": "Nếu trời mưa, chúng tôi sẽ ở nhà.", "options": ["stay", "will stay", "stayed", "would stay"], "answer": "will stay"},
                {"question": "This is the ______ book I have read.", "translation": "Đây là cuốn sách hay nhất tôi từng đọc.", "options": ["good", "better", "best", "goodest"], "answer": "best"}
            ],
            "Essay": [
                {"question": "Write 50 words about your family.", "translation": "Viết 50 từ về gia đình.", "answer": "Suggested family essay..."},
                {"question": "Benefits of learning English?", "translation": "Lợi ích học tiếng Anh?", "answer": "Communication, career..."},
                {"question": "Describe your favorite hobby.", "translation": "Kể về sở thích của bạn.", "answer": "Reading, sports, etc."},
                {"question": "What is your dream job?", "translation": "Công việc mơ ước của bạn là gì?", "answer": "Doctor, teacher, engineer..."},
                {"question": "Talk about your best friend.", "translation": "Kể về người bạn thân nhất.", "answer": "Name, appearance, personality..."}
            ]
        } for i in range(1, 13)
    },
    "Toán": {
        f"Lớp {i}": {
            "Multiple Choice": [
                {"question": "25 + 75 = ?", "options": ["90", "100", "110", "120"], "answer": "100"},
                {"question": "x - 15 = 20. Tìm x?", "options": ["5", "25", "35", "45"], "answer": "35"},
                {"question": "Số nào là số nguyên tố?", "options": ["4", "6", "8", "7"], "answer": "7"},
                {"question": "Diện tích hình chữ nhật (5m x 3m)?", "options": ["8", "15", "20", "25"], "answer": "15"},
                {"question": "1 giờ có bao nhiêu giây?", "options": ["60", "360", "3600", "120"], "answer": "3600"},
                {"question": "Số lớn nhất có 2 chữ số?", "options": ["10", "90", "99", "100"], "answer": "99"},
                {"question": "Căn bậc hai của 144?", "options": ["10", "11", "12", "13"], "answer": "12"},
                {"question": "Số 0 là số chẵn hay số lẻ?", "options": ["Chẵn", "Lẻ", "Cả hai", "Không phải"], "answer": "Chẵn"},
                {"question": "1km bằng bao nhiêu mét?", "options": ["10", "100", "1000", "10000"], "answer": "1000"},
                {"question": "Hình nào có 4 cạnh bằng nhau?", "options": ["Tam giác", "Tròn", "Vuông", "Thang"], "answer": "Vuông"}
            ],
            "Essay": [
                {"question": "Tính 2/5 của 100kg gạo.", "answer": "40kg"},
                {"question": "Chứng minh tổng 3 góc tam giác = 180.", "answer": "Dựa trên tính chất song song..."},
                {"question": "Giải hệ phương trình bậc nhất 2 ẩn.", "answer": "Sử dụng phương pháp thế hoặc cộng..."},
                {"question": "Tính thể tích hình lập phương cạnh 3cm.", "answer": "3^3 = 27 cm3"},
                {"question": "Phân tích số 120 ra thừa số nguyên tố.", "answer": "2^3 * 3 * 5"}
            ]
        } for i in range(1, 13)
    },
    "Ngữ văn": {
        f"Lớp {i}": {
            "Multiple Choice": [
                {"question": "Tác giả Truyện Kiều?", "options": ["Nguyễn Khuyến", "Nguyễn Du", "Nguyễn Trãi", "Chu Văn An"], "answer": "Nguyễn Du"},
                {"question": "Biện pháp: 'Lá ơi! Hãy về với đất'?", "options": ["So sánh", "Ẩn dụ", "Nhân hóa", "Hoán dụ"], "answer": "Nhân hóa"},
                {"question": "Thể loại của 'Lão Hạc'?", "options": ["Tiểu thuyết", "Truyện ngắn", "Tùy bút", "Hồi ký"], "answer": "Truyện ngắn"},
                {"question": "Tác giả bài 'Đoàn thuyền đánh cá'?", "options": ["Huy Cận", "Xuân Diệu", "Chế Lan Viên", "Tố Hữu"], "answer": "Huy Cận"},
                {"question": "Thành ngữ 'Học đi đôi với hành'?", "options": ["Lý thuyết", "Thực tế", "Áp dụng", "Bỏ học"], "answer": "Áp dụng"},
                {"question": "Sông Hương nằm ở tỉnh nào?", "options": ["Quảng Bình", "Quảng Trị", "Thừa Thiên Huế", "Đà Nẵng"], "answer": "Thừa Thiên Huế"},
                {"question": "Nhân vật chính trong 'Dế Mèn phiêu lưu ký'?", "options": ["Dế Choắt", "Dế Mèn", "Chị Cốc", "Dế Trũi"], "answer": "Dế Mèn"},
                {"question": "Từ nào viết đúng chính tả?", "options": ["Xắp sếp", "Sắp sếp", "Sắp xếp", "Xắp xếp"], "answer": "Sắp xếp"},
                {"question": "Bài thơ 'Viếng Lăng Bác' của ai?", "options": ["Viễn Phương", "Thanh Hải", "Hữu Thỉnh", "Phạm Tiến Duật"], "answer": "Viễn Phương"},
                {"question": "Tác phẩm 'Tắt đèn' của tác giả nào?", "options": ["Nam Cao", "Ngô Tất Tố", "Vũ Trọng Phụng", "Nguyên Hồng"], "answer": "Ngô Tất Tố"}
            ],
            "Essay": [
                {"question": "Phân tích nhân vật Lão Hạc.", "answer": "Lòng tự trọng, tình cha con..."},
                {"question": "Nêu cảm nghĩ về tình mẫu tử.", "answer": "Tình yêu bao la, sự hy sinh..."},
                {"question": "Phân tích bài thơ 'Đồng chí'.", "answer": "Tình đồng đội, hoàn cảnh khó khăn..."},
                {"question": "Ý nghĩa của truyện 'Vợ nhặt'.", "answer": "Sức sống mãnh liệt của con người..."},
                {"question": "Bàn về đức tính khiêm tốn.", "answer": "Sự học hỏi, tôn trọng người khác..."}
            ]
        } for i in range(1, 13)
    }
}

# --- FUNCTIONS ---
def extract_text_from_file(uploaded_file):
    if uploaded_file.name.endswith(".docx"):
        doc = docx.Document(uploaded_file)
        return "\n".join([p.text for p in doc.paragraphs])
    elif uploaded_file.name.endswith(".pdf"):
        with pdfplumber.open(uploaded_file) as pdf:
            return "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
    return uploaded_file.read().decode("utf-8")

def ai_process_questions(text, api_key):
    try:
        genai.configure(api_key=api_key)
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        target_model = "models/gemini-1.5-flash" if "models/gemini-1.5-flash" in available_models else available_models[0]
        model = genai.GenerativeModel(target_model)
        prompt = f"Extract 10 MCQs and 5 Essays from this text and return ONLY JSON:\n{text}"
        response = model.generate_content(prompt)
        return json.loads(response.text.strip().replace("```json", "").replace("```", ""))
    except Exception as e:
        st.error(f"Lỗi AI: {str(e)}"); return None

def generate_test(subject, grade, test_type, mc_ratio, duration, custom_db=None):
    db = custom_db if custom_db else QUESTIONS_DB[subject][grade]
    mc_pool, essay_pool = db["Multiple Choice"], db["Essay"]
    num_mc_q = 10 if test_type == "Trắc nghiệm" else (0 if test_type == "Tự luận" else int(10 * (mc_ratio/100)))
    num_essay_q = 5 if test_type == "Tự luận" else (0 if test_type == "Trắc nghiệm" else 10 - num_mc_q)
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
            for idx, opt in enumerate(q['options']): p.drawString(ml+0.5*cm, y, f"[ ] {chr(65+idx)}. {opt}"); y -= 0.5*cm
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
    with col2:
        semester = st.selectbox("Học kỳ:", SEMESTERS)
        duration = st.number_input("Thời gian (phút):", 15, 180, 45, 5)
    with col3:
        test_type = st.radio("Hình thức:", ["Trắc nghiệm", "Tự luận", "Kết hợp"], horizontal=True)
        mc_ratio = st.slider("Tỉ lệ Trắc nghiệm (%)", 0, 100, 70) if test_type == "Kết hợp" else 70

tab_bank, tab_ai, tab_history = st.tabs(["📄 Tạo từ ngân hàng", "📁 Tạo từ đề cương (AI)", "📜 Lịch sử file"])

with tab_bank:
    if st.button("🚀 TẠO ĐỀ THI NGAY", use_container_width=True):
        mc, es = generate_test(subject, grade, test_type, mc_ratio, duration)
        pdf, name = export_pdf(subject, grade, semester, test_type, duration, mc, es)
        st.session_state['test'] = {"sub": subject, "gr": grade, "sem": semester, "mc": mc, "es": es, "pdf": pdf, "name": name}
        st.success("Đã tạo đề thành công!")

with tab_ai:
    st.write("Tải file lên để AI bóc tách câu hỏi và tạo đề.")
    up_file = st.file_uploader("Chọn file Word/PDF/TXT:", type=["docx", "pdf", "txt"])
    if st.button("🔍 AI Bóc tách & Tạo đề", use_container_width=True):
        if up_file:
            with st.spinner("AI đang xử lý..."):
                txt = extract_text_from_file(up_file)
                custom = ai_process_questions(txt, GEMINI_API_KEY)
                if custom:
                    mc, es = generate_test(subject, grade, test_type, mc_ratio, duration, custom_db=custom)
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
