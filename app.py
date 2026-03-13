import os
import json
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.utils import format_currency
from core.data_processing import process_data
from core.email_sender import send_single_email
from core.email_templates import generate_email_body

# ==========================================
# CẤU HÌNH GIAO DIỆN TRANG WEB STREAMLIT
# ==========================================
st.set_page_config(page_title="App Gửi Email Công Nợ", page_icon="📧", layout="wide")

# ==========================================
# MAIN APP GIAO DIỆN
# ==========================================
def main():
    st.title("Phần Mềm Quản Lý Gửi Email Công Nợ")
    
    # 1. Load các biến môi trường
    load_dotenv()
    SMTP_SERVER = os.getenv("SMTP_SERVER")
    SMTP_PORT = os.getenv("SMTP_PORT")
    SENDER_EMAIL = os.getenv("SENDER_EMAIL")
    SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
    
    # Cảnh báo cấu hình
    if all([SMTP_SERVER, SMTP_PORT, SENDER_EMAIL, SENDER_PASSWORD]):
        st.success(f"Đã kết nối cấu hình tài khoản gửi: **{SENDER_EMAIL}**")
    else:
        st.error("Chưa cấu hình tài khoản gửi! Vui lòng kiểm tra lại file .env")

    st.write("---")
    
    st.sidebar.subheader("Cài Đặt / Settings")
    st.sidebar.info("🇺🇳 Ngôn ngữ email tự động theo cột **Nhóm khách hàng** (domestic → TV, global → EN)")
    
    # Load danh sách người gửi tử file JSON
    senders_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'senders.json')
    try:
        with open(senders_path, 'r', encoding='utf-8') as f:
            senders = json.load(f)
    except Exception:
        senders = [{"name": "Huynh Thi Ngoc Lien", "title": "Receivable Accountant / Accounting Dept.", "phone": "+84 93 303 5860", "email": "accounting@gotco.com.vn"}]
    
    sender_names = [s['name'] for s in senders]
    selected_sender_name = st.sidebar.selectbox("👤 Người gửi / Sender", sender_names)
    selected_sender = next((s for s in senders if s['name'] == selected_sender_name), senders[0])
    st.sidebar.caption(f"📞 {selected_sender['phone']}  |  ✉️ {selected_sender['email']}")
    
    # 2. Block Upload File
    st.subheader("1. Tải lên dữ liệu")
    uploaded_file = st.file_uploader("Vui lòng tải lên file Excel (chứa sheet 'Báo cáo-GIAO BAN' và 'KHACHHANG')", type=["xlsx"])
    
    if uploaded_file is not None:
        # Nhấn nút xử lý
        if st.button("Trích Xuất Dữ Liệu Công Nợ"):
            with st.spinner("Đang tính toán..."):
                processed_df, report_date, err_msg = process_data(uploaded_file)
                if err_msg:
                    if "CẢNH BÁO" in err_msg:
                        st.warning(err_msg)
                    else:
                        st.error(err_msg)
                        
                if processed_df is not None:
                    # Lưu dataframe đã tính vào session_state để không bị mất khi giao diện vẽ lại
                    st.session_state['processed_df'] = processed_df
                    st.session_state['report_date'] = report_date
                    st.success("Đã phân tích xong dữ liệu!")

    # 3. Block Hiển thị Báo cáo & Bấm Confirm
    if 'processed_df' in st.session_state:
        st.write("---")
        st.subheader("2. Kiểm tra lại danh sách chuẩn bị gửi (Trang Chờ)")
        
        df_all = st.session_state['processed_df']
        report_date = st.session_state.get('report_date', '')
        
        if df_all is None:
            df_all = pd.DataFrame(columns=['Khách hàng', 'Email'])
        
        # Thống kê tổng quan để Review
        df_valid = df_all.dropna(subset=['Email'])
        df_missing = df_all[df_all['Email'].isna()]
        
        summary_table = []
        for (cus, email, cc, nhom), grp in df_valid.groupby(['Khách hàng', 'Email', 'CC', 'Nhóm khách hàng']):
                mail_lang = 'English' if str(nhom).lower() == 'global' else 'Tiếng Việt'
                summary_table.append({
                    "Khách hàng": cus,
                    "Nhóm": nhom,
                    "Ngôn ngữ": '🇬🇧 EN' if mail_lang == 'English' else '🇻🇳 VN',
                    "Email (To)": email,
                    "CC": cc if cc else '',
                    "Số lượng HĐ": len(grp),
                    "Tổng nợ (VND)": format_currency(grp['Số còn phải thu'].sum())
                })
            
        st.write(f"Tìm thấy **{len(summary_table)}** khách hàng có báo nợ đủ điều kiện gửi email.")
        
        if len(summary_table) > 0:
            st.dataframe(pd.DataFrame(summary_table), use_container_width=True)
            
            st.write("---")
            st.subheader("3. Xem trước và Gửi Email từng Khách Hàng")
            
            # Form xác nhận gửi từng người
            for (cus, email, cc, nhom), grp in df_valid.groupby(['Khách hàng', 'Email', 'CC', 'Nhóm khách hàng']):
                mail_lang = 'English' if str(nhom).lower() == 'global' else 'Tiếng Việt'
                is_sent = st.session_state.get(f"sent_{cus}_{email}", False)
                status_emoji = "✅ ĐÃ GỬI" if is_sent else "⏳ CHỜ GỬI"
                lang_badge = '🇬🇧 EN' if mail_lang == 'English' else '🇻🇳 VN'
                total_debt = format_currency(grp['Số còn phải thu'].sum())
                cc_str = cc if cc else ''
                
                with st.expander(f"[{status_emoji}] {lang_badge} {cus} ({len(grp)} hóa đơn, Tổng nợ: {total_debt} VND)"):
                    col1, col2 = st.columns(2)
                    col1.markdown(f"📧 **To:** `{email}`")
                    col2.markdown(f"📋 **CC:** `{cc_str}`" if cc_str else "📋 **CC:** _(không có)_")
                    
                    # Hiển thị Preview Mail
                    html_preview = generate_email_body(cus, grp, grp['Số còn phải thu'].sum(), report_date, mail_lang, selected_sender)
                    st.components.v1.html(html_preview, height=500, scrolling=True)
                    
                    if not is_sent:
                        if st.button(f"Xác nhận gửi email cho {cus}", key=f"btn_send_{cus}_{email}"):
                            if not all([SMTP_SERVER, SMTP_PORT, SENDER_EMAIL, SENDER_PASSWORD]):
                                st.error("Vui lòng cấu hình file .env trước khi gửi!")
                            else:
                                with st.spinner(f"Đang gửi email cho {cus}..."):
                                    success, error_msg = send_single_email(
                                        cus, 
                                        email,
                                        cc_str,
                                        grp, 
                                        SMTP_SERVER, 
                                        SMTP_PORT, 
                                        SENDER_EMAIL, 
                                        SENDER_PASSWORD, 
                                        report_date, 
                                        mail_lang,
                                        selected_sender
                                    )
                                    if success:
                                        st.session_state[f"sent_{cus}_{email}"] = True
                                        st.rerun()
                                    else:
                                        st.error(f"Lỗi gửi email cho {cus}: {error_msg}")
                    else:
                        st.success(f"Email này đã được gửi thành công.")
                            
        # Hiện cảnh báo thiếu email
        if not df_missing.empty:
            st.write("---")
            st.error(f"Cảnh báo: Có {df_missing['Khách hàng'].nunique()} khách hàng có nợ nhưng KHÔNG TÌM THẤY EMAIL trong Mapping:")
            missing_names = df_missing[['Khách hàng', 'Số còn phải thu', 'Số hóa đơn']].copy()
            st.dataframe(missing_names, use_container_width=True)

if __name__ == "__main__":
    main()
