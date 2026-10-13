import streamlit as st
import io
import datetime
import os
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from reportlab.pdfgen import canvas
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.pagesizes import A4

# ==========================================
# 0. ระบบจัดการฐานข้อมูล (Google Sheets CRUD)
# ==========================================
def get_all_users():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # แก้ไขตรงนี้: ใส่ ttl=0 เพื่อบังคับให้ดึงข้อมูลใหม่เสมอ ไม่จำแคช
        df = conn.read(worksheet="Sheet1", ttl=0) 
        
        if not df.empty and 'id' in df.columns:
            # ตัดแถวที่ id เป็นค่าว่างออก (ป้องกัน Google Sheets คืนค่าแถวว่างเปล่ามาให้)
            df = df.dropna(subset=['id'])
            df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
            
            # กรองเอาเฉพาะข้อมูลที่มีค่า ID มากกว่า 0
            df = df[df['id'] > 0]
            
            # แปลงข้อมูลบางคอลัมน์ไม่ให้เป็นทศนิยม
            cols_to_int = ['s_day', 's_month', 's_year_be', 'e_day_num', 'e_month_num', 'e_year_num', 'age']
            for col in cols_to_int:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(1).astype(int)
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการดึงข้อมูล: {e}")
        return pd.DataFrame()

def add_user(name, s_day, s_month, s_year_be, e_day_num, e_month_num, e_year_num, age, thai_lunar_text):
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = get_all_users()
    
    # คำนวณ ID ถัดไป
    new_id = 1
    if not df.empty and 'id' in df.columns:
        new_id = int(df['id'].max()) + 1
        
    created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    new_data = pd.DataFrame([{
        "id": new_id, "name": name, "s_day": s_day, "s_month": s_month, "s_year_be": s_year_be,
        "e_day_num": e_day_num, "e_month_num": e_month_num, "e_year_num": e_year_num,
        "age": age, "thai_lunar_text": thai_lunar_text, "created_at": created_at
    }])
    
    updated_df = pd.concat([df, new_data], ignore_index=True)
    # อัปเดตกลับไปที่ Google Sheets
    conn.update(worksheet="Sheet1", data=updated_df)
    # ล้างแคชทั้งหมดหลังบันทึก
    st.cache_data.clear()

def update_user(user_id, name, age, thai_lunar_text):
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = get_all_users()
    if not df.empty:
        idx = df[df['id'] == user_id].index
        if len(idx) > 0:
            df.loc[idx, 'name'] = name
            df.loc[idx, 'age'] = age
            df.loc[idx, 'thai_lunar_text'] = thai_lunar_text
            conn.update(worksheet="Sheet1", data=df)
            st.cache_data.clear()

def delete_user(user_id):
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = get_all_users()
    if not df.empty:
        df = df[df['id'] != user_id]
        conn.update(worksheet="Sheet1", data=df)
        st.cache_data.clear()

# ==========================================
# 1. ฟังก์ชันแปลงปฏิทินสากลเป็นจันทรคติไทย
# ==========================================
def convert_to_thai_lunar(solar_date):
    day_map = {7: (1, "อาทิตย์"), 1: (2, "จันทร์"), 2: (3, "อังคาร"), 
               3: (4, "พุธ"), 4: (5, "พฤหัสบดี"), 5: (6, "ศุกร์"), 6: (7, "เสาร์")}
    d_num, d_name = day_map[solar_date.isoweekday()]

    y = solar_date.year
    if solar_date.month < 4 or (solar_date.month == 4 and solar_date.day < 13): y -= 1
        
    zodiac_map = {4: (1, "ชวด"), 5: (2, "ฉลู"), 6: (3, "ขาล"), 7: (4, "เถาะ"), 8: (5, "มะโรง"), 9: (6, "มะเส็ง"), 10: (7, "มะเมีย"), 11: (8, "มะแม"), 0: (9, "วอก"), 1: (10, "ระกา"), 2: (11, "จอ"), 3: (12, "กุน")}
    y_num, y_name = zodiac_map[y % 12]

    ref_date = datetime.date(2000, 1, 1)
    days_diff = (solar_date - ref_date).days
    lunar_days = (days_diff + 25.5) % 29.530588
    
    if lunar_days < 14.76:
        phase = "ขึ้น"
        phase_day = int(lunar_days) + 1
    else:
        phase = "แรม"
        phase_day = int(lunar_days - 14.76) + 1
        
    if phase_day > 15: phase_day = 15

    m_num = solar_date.month + 1 
    if m_num > 12: m_num -= 12
    thai_months = {1: "อ้าย (๑)", 2: "ยี่ (๒)", 3: "สาม (๓)", 4: "สี่ (๔)", 5: "ห้า (๕)", 6: "หก (๖)", 7: "เจ็ด (๗)", 8: "แปด (๘)", 9: "เก้า (๙)", 10: "สิบ (๑๐)", 11: "สิบเอ็ด (๑๑)", 12: "สิบสอง (๑๒)"}
    m_name = thai_months.get(m_num, str(m_num))

    return {"day_num": d_num, "day_name": d_name, "month_num": m_num, "month_name": m_name, "year_num": y_num, "year_name": y_name, "phase": phase, "phase_day": phase_day}

# ==========================================
# 2. ฟังก์ชันคำนวณฐานดวง
# ==========================================
def get_month_base(month_num, solar_date):
    mapping = {1: 2, 2: 3, 3: 4, 4: 5, 6: 2, 7: 3, 8: 4, 9: 5, 10: 6, 11: 7, 12: 1}
    if month_num == 5:
        if solar_date.month < 4 or (solar_date.month == 4 and solar_date.day < 13): return 5 
        else: return 1 
    return mapping.get(month_num, 1)

def calculate_7_base(day_num, month_num, year_num, solar_date):
    m_base = get_month_base(month_num, solar_date)
    y_base = (year_num % 7) if (year_num % 7) != 0 else 7
    
    row1 = [(day_num - 1 + i) % 7 + 1 for i in range(7)]
    row2 = [(m_base - 1 + i) % 7 + 1 for i in range(7)]
    row3 = [(y_base - 1 + i) % 7 + 1 for i in range(7)]
    row4 = [row1[i] + row2[i] + row3[i] for i in range(7)]
    row5 = [(val - 1) % 7 + 1 for val in row4]
    
    extended_rows = []
    for i in range(7):
        start_val = row5[i]
        current_row = [(start_val - 1 + j) % 7 + 1 for j in range(7)]
        extended_rows.append(current_row)
        
    chart_data = [row1, row2, row3, row4, row5] + extended_rows

    age_vals = [row1[0], row2[0], row3[0]]
    for i in range(3): age_vals.append((age_vals[i] + 2 - 1) % 7 + 1)
    for i in range(3, 9): age_vals.append((age_vals[i] + 3 - 1) % 7 + 1)

    return chart_data, age_vals

# ==========================================
# 3. ฟังก์ชันวาด PDF
# ==========================================
def generate_pdf(name, dob_text, thai_lunar_date, chart_data, age_vals, age, month_num):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    if os.path.exists("bg.jpg"): c.drawImage("bg.jpg", 0, 0, width=A4[0], height=A4[1])
    
    try:
        pdfmetrics.registerFont(TTFont('THSarabun', 'THSarabunNew.ttf'))
        c.setFont("THSarabun", 28) 
    except:
        c.setFont("Helvetica", 20)
        name += " (Font THSarabunNew.ttf not found)"

    c.setFillColorRGB(0, 0, 0)
    c.drawString(50, 800, f"ชื่อ-นามสกุล: {name}")
    c.setFont("THSarabun", 24)
    c.drawString(50, 775, f"วัน-เดือน-ปีเกิด: {dob_text}")
    c.drawString(50, 750, f"จันทรคติ: {thai_lunar_date}")
    
    col_width = 45 
    row_height = 25
    start_x = 140 
    
    # === 1. ตารางที่ 1 (เฉพาะท่อนบน แถว 1 ถึง 5) ===
    start_y_part1 = 710
    
    for row_idx in range(5):
        row = chart_data[row_idx]
        y_pos = start_y_part1 - (row_idx * row_height)
        
        for col_idx, value in enumerate(row):
            x = start_x + (col_idx * col_width)
            
            if col_idx == 3:
                c.setFillColorRGB(0.85, 0.93, 1.0) 
                c.rect(x, y_pos, col_width, row_height, stroke=1, fill=1)
            else:
                c.setStrokeColorRGB(0, 0, 0)
                c.rect(x, y_pos, col_width, row_height)
            
            c.setFillColorRGB(0, 0, 0) 
            c.setFont("THSarabun", 22) 
            c.drawCentredString(x + col_width / 2.0, y_pos + 6, str(value))
            
            small_num = None
            if row_idx == 0: small_num = 1 + col_idx
            elif row_idx == 1: small_num = 8 + col_idx
            elif row_idx == 2: small_num = 15 + col_idx
                
            if small_num is not None:
                c.setFont("THSarabun", 12) 
                c.drawString(x + col_width - 13, y_pos + 2, str(small_num))

    # เส้นหนาระหว่างแถว 3 และ 4 ของตารางแรก
    c.setLineWidth(3)
    thick_line_y = start_y_part1 - (2 * row_height) 
    c.line(start_x, thick_line_y, start_x + (7 * col_width), thick_line_y)
    c.setLineWidth(1)

    # --- คำนวณตัวเลขสำหรับตารางดวงจร ---
    start1 = 1
    if 1 <= age <= 7: start1 = chart_data[0][age - 1]
    elif 8 <= age <= 14: start1 = chart_data[1][age - 8]
    elif 15 <= age <= 21: start1 = chart_data[2][age - 15]
    elif age >= 22:
        r_idx = 5 + (age - 22) // 7
        c_idx = (age - 22) % 7
        if r_idx < len(chart_data): start1 = chart_data[r_idx][c_idx]
        else: start1 = 1
        
    start2 = age_vals[(age - 1) % 12]
    start3 = month_num

    seq1 = [(start1 - 1 + i) % 7 + 1 for i in range(7)]
    seq2 = [(start2 - 1 + i) % 7 + 1 for i in range(7)]
    seq3_4 = [(start3 - 1 + i) % 12 + 1 for i in range(12)]
    seq3 = seq3_4[0:7]
    seq4 = seq3_4[7:12]

    # === 2. ตารางดวงจร (แทรกกลาง ระหว่างแถว 5 กับ 6 และ ชิดซ้าย) ===
    pred_chart_x = 50 
    pred_title_y = 560
    pred_chart_y = 530
    
    c.setFont("THSarabun", 24)
    c.drawCentredString(pred_chart_x + (col_width * 3.5), pred_title_y, f"ตอนนี้อายุ    {age} ปี")

    table_top = pred_chart_y + row_height
    table_bottom = table_top - 4 * row_height
    table_left = pred_chart_x
    table_right = pred_chart_x + 7 * col_width
    
    # เส้นกริด
    c.setStrokeColorRGB(0.85, 0.85, 0.85)
    c.setLineWidth(1)
    for i in range(5):
        y = table_top - i * row_height
        c.line(table_left, y, table_right, y)
    for i in range(8):
        x = table_left + i * col_width
        c.line(x, table_top, x, table_bottom)

    # เส้นหนาสีดำ แบ่งระหว่างแถว 2 (เลขดวง) และ แถว 3 (เดือน) ของดวงจร
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(3)
    thick_y = table_top - 2 * row_height
    c.line(table_left, thick_y, table_right, thick_y)
    c.setLineWidth(1)

    def draw_centered_large(canvas, text, x, y, color):
        canvas.setFillColorRGB(*color)
        canvas.drawCentredString(x + col_width/2.0, y + 6, text)

    c.setFont("THSarabun", 22) 
    for i, val in enumerate(seq1): draw_centered_large(c, str(val), pred_chart_x + i * col_width, pred_chart_y, (0, 0, 1) if i == 0 else (0, 0, 0))
    for i, val in enumerate(seq2): draw_centered_large(c, str(val), pred_chart_x + i * col_width, pred_chart_y - row_height, (0, 0, 1) if i == 0 else (0, 0, 0))
    for i, val in enumerate(seq3): draw_centered_large(c, str(val), pred_chart_x + i * col_width, pred_chart_y - 2 * row_height, (0, 0, 1) if i == 0 else (0, 0, 0))
    for i, val in enumerate(seq4): draw_centered_large(c, str(val), pred_chart_x + i * col_width, pred_chart_y - 3 * row_height, (0, 0, 0))

    # === 3. ตารางที่ 1 (ท่อนล่าง แถว 6 ถึง 12) ===
    start_y_part2 = 405
    for row_idx in range(5, len(chart_data)):
        row = chart_data[row_idx]
        display_idx = row_idx - 5
        y_pos = start_y_part2 - (display_idx * row_height)
        
        for col_idx, value in enumerate(row):
            x = start_x + (col_idx * col_width)
            
            c.setStrokeColorRGB(0, 0, 0)
            c.rect(x, y_pos, col_width, row_height)
            
            c.setFillColorRGB(0, 0, 0) 
            c.setFont("THSarabun", 22) 
            c.drawCentredString(x + col_width / 2.0, y_pos + 6, str(value))
            
            # เลขดวงเล็กมุมขวาล่าง
            small_num = 22 + (display_idx * 7) + col_idx
            c.setFont("THSarabun", 12) 
            c.drawString(x + col_width - 13, y_pos + 2, str(small_num))

    # === 4. ตารางอายุ (อยู่ล่างสุด) ===
    age_start_x = 214
    age_start_y = 205
    age_row_height = 16
    main_col_width = 35
    small_col_width = 22
    
    for i in range(12):
        y = age_start_y - (i * age_row_height)
        c.setStrokeColorRGB(0, 0, 0)
        c.rect(age_start_x, y, main_col_width, age_row_height)
        c.setFillColorRGB(0, 0, 1)
        c.setFont("THSarabun", 20) 
        c.drawCentredString(age_start_x + main_col_width / 2.0, y + 4, str(age_vals[i]))
        
        for j in range(6):
            sx = age_start_x + main_col_width + (j * small_col_width)
            c.setStrokeColorRGB(0.7, 0.7, 0.7)
            c.rect(sx, y, small_col_width, age_row_height)
            age_num = (i + 1) + (j * 12)
            c.setFillColorRGB(0.4, 0.4, 0.4)
            c.setFont("THSarabun", 14) 
            c.drawCentredString(sx + small_col_width / 2.0, y + 4, str(age_num))

    c.setFillColorRGB(0, 0, 0)
    c.setFont("THSarabun", 16)
    c.drawString(40, 20, "* เอกสารนี้สร้างขึ้นจากระบบผูกดวงอัตโนมัติ")

    if os.path.exists("qr.png"):
        c.drawImage("qr.png", 480, 25, width=70, height=70, mask='auto')
        c.setFont("THSarabun", 14)
        c.drawString(470, 10, "สแกนรับคำทำนายเพิ่มเติม")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# ==========================================
# 4. ฟังก์ชันสำหรับสร้าง Preview บนหน้าเว็บ (HTML/CSS)
# ==========================================
def render_html_preview(chart_data, age_vals, age, month_num):
    html_str = """
    <style>
    .preview-container { background: #fafafa; padding: 25px; border-radius: 12px; margin: 20px 0; color: black; font-family: 'Sarabun', sans-serif; box-shadow: 0px 4px 10px rgba(0,0,0,0.1); }
    .astro-table { margin: 0 auto 0 auto; border-collapse: collapse; }
    .astro-table td { position: relative; width: 45px; height: 45px; text-align: center; vertical-align: middle; font-size: 22px; border: 1px solid #333; background: #fff; color: #000; }
    .astro-col-highlight { background: #d9edf7 !important; } 
    .astro-small { position: absolute; bottom: 2px; right: 4px; font-size: 11px; color: #666; }
    
    .tables-wrapper { display: flex; flex-direction: column; align-items: center; gap: 25px; margin-top: 10px; }
    
    .age-table { border-collapse: collapse; margin: 0 auto; }
    .age-table td { border: 1px solid #ccc; width: 25px; height: 25px; text-align: center; font-size: 13px; background: #fff; color: #555; }
    .age-main { border: 1px solid #333 !important; color: blue !important; font-weight: bold; width: 32px !important; font-size: 16px !important; }
    
    .pred-table { border-collapse: collapse; background: #fff;}
    .pred-table td { border: 1px solid #e0e0e0; padding: 6px 14px; text-align: center; font-size: 22px; color: #000; width: 45px; height: 40px;}
    .pred-blue { color: blue !important; }
    .pred-border-b td { border-bottom: 3px solid #000 !important; } 
    </style>
    <div class="preview-container"><h3 style="text-align: center; color: #333; margin-bottom: 25px;">📄 แผ่นดวงชะตา</h3>
    <div class="tables-wrapper">
    """
    
    # --- 1. ตารางที่ 1 (ท่อนบน แถว 1 ถึง 5) ---
    html_str += "<table class='astro-table'>"
    for row_idx in range(5):
        row = chart_data[row_idx]
        tr_style = " style='border-bottom: 3px solid #000;'" if row_idx == 2 else ""
        html_str += f"<tr{tr_style}>"
        
        for col_idx, val in enumerate(row):
            small_num = ""
            if row_idx == 0: small_num = 1 + col_idx
            elif row_idx == 1: small_num = 8 + col_idx
            elif row_idx == 2: small_num = 15 + col_idx
            
            highlight_class = " astro-col-highlight" if col_idx == 3 else ""
            td_style = " style='border-bottom: 3px solid #000;'" if row_idx == 2 else ""
            
            html_str += f"<td class='{highlight_class.strip()}'{td_style}>{val}<span class='astro-small'>{small_num if small_num else ''}</span></td>"
        html_str += "</tr>"
    html_str += "</table>"
    
    # --- คำนวณดวงจร ---
    start1 = 1
    if 1 <= age <= 7: start1 = chart_data[0][age - 1]
    elif 8 <= age <= 14: start1 = chart_data[1][age - 8]
    elif 15 <= age <= 21: start1 = chart_data[2][age - 15]
    elif age >= 22:
        r_idx = 5 + (age - 22) // 7
        c_idx = (age - 22) % 7
        if r_idx < len(chart_data): start1 = chart_data[r_idx][c_idx]
        
    start2 = age_vals[(age - 1) % 12]
    start3 = month_num

    seq1 = [(start1 - 1 + i) % 7 + 1 for i in range(7)]
    seq2 = [(start2 - 1 + i) % 7 + 1 for i in range(7)]
    seq3_4 = [(start3 - 1 + i) % 12 + 1 for i in range(12)]
    seq3 = seq3_4[0:7]
    seq4 = seq3_4[7:12]
    
    # --- 2. ตารางดวงจร (แทรกกลาง และ ชิดซ้าย) ---
    html_str += f"<div style='align-self: flex-start; padding-left: 20px;'><div style='text-align: center; margin-bottom: 10px; font-size: 18px; font-weight: bold; color: #000;'>ตอนนี้อายุ {age} ปี</div><table class='pred-table' style='margin: 0;'>"
    for r_idx, seq in enumerate([seq1, seq2, seq3, seq4]):
        row_class = "pred-border-b" if r_idx == 1 else ""
        html_str += f"<tr class='{row_class}'>"
        for c_idx in range(7):
            val = seq[c_idx] if c_idx < len(seq) else ""
            cls = []
            if c_idx == 0 and r_idx < 3: cls.append("pred-blue")
            html_str += f"<td class='{' '.join(cls)}'>{val}</td>"
        html_str += "</tr>"
    html_str += "</table></div>"
    
    # --- 3. ตารางที่ 1 (ท่อนล่าง แถว 6 ถึง 12) ---
    html_str += "<table class='astro-table'>"
    for row_idx in range(5, len(chart_data)):
        row = chart_data[row_idx]
        html_str += "<tr>"
        
        for col_idx, val in enumerate(row):
            small_num = 22 + ((row_idx - 5) * 7) + col_idx
            html_str += f"<td>{val}<span class='astro-small'>{small_num}</span></td>"
        html_str += "</tr>"
    html_str += "</table>"
    
    # --- 4. ตารางอายุ (อยู่ล่างสุด) ---
    html_str += "<div><table class='age-table'>"
    for i in range(12):
        html_str += f"<tr><td class='age-main'>{age_vals[i]}</td>"
        for j in range(6): html_str += f"<td>{(i + 1) + (j * 12)}</td>"
        html_str += "</tr>"
    html_str += "</table></div>"
    
    html_str += "</div></div>"
    
    st.markdown(html_str, unsafe_allow_html=True)

# ==========================================
# 5. ส่วนแสดงผลหน้าเว็บ (Streamlit UI)
# ==========================================
def main():
    st.set_page_config(page_title="โปรแกรมผูกดวงเลข 7 ตัว", layout="centered")
    
    st.title("🔮 ระบบโหราศาสตร์เลข 7 ตัว")

    tab1, tab2 = st.tabs(["🔮 ผูกดวงชะตา", "🗂️ ฐานข้อมูลลูกค้า"])

    # ---------------- TAB 1: ระบบผูกดวง ----------------
    with tab1:
        thai_nums = {1: "๑", 2: "๒", 3: "๓", 4: "๔", 5: "๕", 6: "๖", 7: "๗", 8: "๘", 9: "๙", 10: "๑๐", 11: "๑๑", 12: "๑๒", 13: "๑๓", 14: "๑๔", 15: "๑๕"}
        thai_months = {1: "อ้าย (๑)", 2: "ยี่ (๒)", 3: "สาม (๓)", 4: "สี่ (๔)", 5: "ห้า (๕)", 6: "หก (๖)", 7: "เจ็ด (๗)", 8: "แปด (๘)", 9: "เก้า (๙)", 10: "สิบ (๑๐)", 11: "สิบเอ็ด (๑๑)", 12: "สิบสอง (๑๒)"}
        day_list = ["อาทิตย์", "จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์"]
        month_list = [f"เดือน {i}" for i in range(1, 13)]
        zodiac_list = ["ชวด", "ฉลู", "ขาล", "เถาะ", "มะโรง", "มะเส็ง", "มะเมีย", "มะแม", "วอก", "ระกา", "จอ", "กุน"]

        name = st.text_input("ชื่อ - นามสกุล", placeholder="เช่น นัด")
        st.markdown("---")
        
        st.write("📅 **1. วันเกิด (ปฏิทินสากล)**")
        col_d, col_m, col_y = st.columns(3)
        with col_d: s_day = st.number_input("วันที่", min_value=1, max_value=31, value=21)
        with col_m:
            solar_months = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
            s_month_name = st.selectbox("เดือน", solar_months, index=2) 
            s_month = solar_months.index(s_month_name) + 1
        with col_y: s_year_be = st.number_input("ปี พ.ศ.", min_value=2400, max_value=2600, value=2529)

        s_year_ce = s_year_be - 543
        today = datetime.date.today()
        try:
            solar_date = datetime.date(s_year_ce, s_month, s_day)
            calculated_age = today.year - solar_date.year - ((today.month, today.day) < (solar_date.month, solar_date.day))
        except ValueError:
            st.error("⚠️ วันที่ไม่ถูกต้อง")
            solar_date = datetime.date(s_year_ce, s_month, 1)
            calculated_age = today.year - solar_date.year
            
        calculated_age = max(1, calculated_age)
        auto_lunar = convert_to_thai_lunar(solar_date)

        st.markdown("---")
        st.write("⏳ **2. อายุ (ระบบคำนวณให้อัตโนมัติ สามารถแก้ไขได้)**")
        age = st.number_input("อายุปัจจุบัน (ปี)", min_value=1, max_value=120, value=calculated_age)
        
        st.markdown("---")
        st.write("🌙 **3. ข้อมูลจันทรคติ (ระบบแปลงให้อัตโนมัติ สามารถแก้ไขได้)**")
        st.markdown("💡 *คุณสามารถตรวจสอบความถูกต้องของ ปฏิทินจันทรคติ (ข้างขึ้น/ข้างแรม) ได้ที่นี่:* [ปฏิทินโหราศาสตร์ไทย (MyHora)](https://myhora.com/calendar/thai-astro.aspx)")
        
        c1, c2, c3 = st.columns(3)
        with c1: edit_day = st.selectbox("วันเกิด", day_list, index=day_list.index(auto_lunar["day_name"]))
        with c2: edit_month = st.selectbox("เดือนเกิด", month_list, index=auto_lunar["month_num"] - 1)
        with c3: edit_year = st.selectbox("ปีนักษัตร", zodiac_list, index=zodiac_list.index(auto_lunar["year_name"]))

        c4, c5 = st.columns(2)
        with c4: edit_phase = st.radio("ข้างขึ้น / ข้างแรม", ["ขึ้น", "แรม"], index=0 if auto_lunar["phase"] == "ขึ้น" else 1, horizontal=True)
        with c5: edit_phase_day = st.selectbox("ดิถี (ค่ำ)", list(range(1, 16)), index=auto_lunar["phase_day"] - 1)

        e_month_num = int(edit_month.split()[1])
        e_day_num = day_list.index(edit_day) + 1
        e_year_num = zodiac_list.index(edit_year) + 1

        t_day = thai_nums.get(edit_phase_day, str(edit_phase_day))
        t_month = thai_months.get(e_month_num, str(e_month_num))
        display_thai_text = f"เกิดวัน{edit_day} {edit_phase} {t_day} ค่ำ เดือน{t_month} ปี{edit_year}"
        
        st.info(f"✨ ข้อมูลที่จะนำไปผูกดวง: **{display_thai_text}**")
        st.markdown("---")

        save_to_db = st.checkbox("💾 บันทึกข้อมูลลูกค้ารายนี้ลงในระบบฐานข้อมูล", value=True)

        if st.button("ดำเนินการผูกดวงและสร้าง PDF"):
            if not name.strip():
                st.warning("⚠️ กรุณากรอกชื่อ-นามสกุลก่อนทำรายการ")
            else:
                if save_to_db:
                    add_user(name, s_day, s_month, s_year_be, e_day_num, e_month_num, e_year_num, age, display_thai_text)
                    st.toast(f"บันทึกข้อมูลคุณ {name} ลงฐานข้อมูลเรียบร้อยแล้ว!")
                    st.cache_data.clear()

                chart_data, age_vals = calculate_7_base(e_day_num, e_month_num, e_year_num, solar_date)
                st.success(f"✅ ผูกดวงสำหรับคุณ {name} สำเร็จแล้ว!")
                
                render_html_preview(chart_data, age_vals, age, e_month_num)
                
                solar_months_list = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
                s_month_str = solar_months_list[s_month - 1]
                dob_text = f"วันที่ {s_day} {s_month_str} พ.ศ. {s_year_be}"
                pdf_buffer = generate_pdf(name, dob_text, display_thai_text, chart_data, age_vals, age, e_month_num)

                st.download_button(
                    label="📥 คลิกที่นี่เพื่อดาวน์โหลดแผ่นดวง (PDF)",
                    data=pdf_buffer,
                    file_name=f"Chart_{name}.pdf",
                    mime="application/pdf"
                )

    # ---------------- TAB 2: ฐานข้อมูลลูกค้า ----------------
    with tab2:
        col_title, col_refresh = st.columns([0.8, 0.2])
        with col_title:
            st.subheader("🗂️ รายชื่อลูกค้าทั้งหมดในระบบ")
        with col_refresh:
            if st.button("🔄 รีเฟรช"):
                st.cache_data.clear()
                st.rerun()
                
        df = get_all_users()
        
        if df.empty:
            st.info("ยังไม่มีข้อมูลลูกค้าในระบบ")
        else:
            display_df = df[['id', 'name', 'age', 'thai_lunar_text', 'created_at']].copy()
            display_df.columns = ["ID", "ชื่อ-นามสกุล", "อายุ", "ข้อมูลจันทรคติ", "วันที่บันทึก"]
            st.dataframe(display_df, hide_index=True, use_container_width=True)

            st.markdown("---")
            st.subheader("⚙️ จัดการข้อมูล และ ดาวน์โหลด PDF ดวงชะตา")
            
            user_options = df['id'].astype(str) + " - " + df['name']
            selected_option = st.selectbox("เลือกลูกค้าที่ต้องการ", ["-- กรุณาเลือก --"] + user_options.tolist())

            if selected_option != "-- กรุณาเลือก --":
                sel_id = int(selected_option.split(" - ")[0])
                user_row = df[df['id'] == sel_id].iloc[0]

                e_d = int(user_row['e_day_num']) if pd.notna(user_row['e_day_num']) else 1
                e_m = int(user_row['e_month_num']) if pd.notna(user_row['e_month_num']) else 1
                e_y = int(user_row['e_year_num']) if pd.notna(user_row['e_year_num']) else 1
                u_age = int(user_row['age']) if pd.notna(user_row['age']) else 1
                
                s_y_ce = int(user_row['s_year_be']) - 543 if pd.notna(user_row['s_year_be']) else 2000
                s_m = int(user_row['s_month']) if pd.notna(user_row['s_month']) else 1
                s_d = int(user_row['s_day']) if pd.notna(user_row['s_day']) else 1
                
                try:
                    db_solar_date = datetime.date(s_y_ce, s_m, s_d)
                except:
                    db_solar_date = datetime.date(s_y_ce, s_m, 1)
                    
                solar_months_list = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
                s_month_str = solar_months_list[s_m - 1]
                dob_text_db = f"วันที่ {s_d} {s_month_str} พ.ศ. {user_row['s_year_be']}"

                db_chart_data, db_age_vals = calculate_7_base(e_d, e_m, e_y, db_solar_date)

                pdf_bytes_db = generate_pdf(
                    user_row['name'], 
                    dob_text_db, 
                    user_row['thai_lunar_text'], 
                    db_chart_data, 
                    db_age_vals, 
                    u_age, 
                    e_m
                )
                
                st.download_button(
                    label=f"📥 ดาวน์โหลด PDF แผ่นดวงของ {user_row['name']}",
                    data=pdf_bytes_db,
                    file_name=f"Chart_{user_row['name']}.pdf",
                    mime="application/pdf",
                    key=f"dl_btn_{sel_id}"
                )

                with st.expander(f"👁️ ดูตัวอย่างแผ่นดวงชะตาของคุณ {user_row['name']}", expanded=True):
                    render_html_preview(db_chart_data, db_age_vals, u_age, e_m)

                st.markdown("<br>", unsafe_allow_html=True)
                
                new_name = st.text_input("อัปเดต ชื่อ-นามสกุล", user_row['name'])
                new_age = st.number_input("อัปเดต อายุ", value=int(user_row['age']), min_value=1)
                new_thai_text = st.text_input("อัปเดต ข้อมูลจันทรคติ", user_row['thai_lunar_text'])

                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("💾 บันทึกการแก้ไข", key="edit_btn"):
                        update_user(sel_id, new_name, new_age, new_thai_text)
                        st.success("อัปเดตข้อมูลสำเร็จ! ระบบจะทำการรีเฟรช...")
                        st.rerun() 
                with col_b:
                    if st.button("🗑️ ลบข้อมูลลูกค้ารายนี้", key="del_btn"):
                        delete_user(sel_id)
                        st.error("ลบข้อมูลออกจากระบบเรียบร้อยแล้ว!")
                        st.rerun() 

if __name__ == "__main__":
    main()
