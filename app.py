import os
import json
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.utils import format_currency
from core.data_processing import process_data
from core.email_sender import create_smtp_connection, send_single_email
from core.email_templates import generate_email_body

# ==========================================
# CẤU HÌNH GIAO DIỆN TRANG WEB STREAMLIT
# ==========================================
st.set_page_config(page_title="App Gửi Email Công Nợ", page_icon="📧", layout="wide")

# ──────────────────────────────────────────────────────────────────────────────
# PRESET: thông số sẵn cho từng provider
# ──────────────────────────────────────────────────────────────────────────────
SMTP_PRESETS = {
    "Gmail": {
        "server": "smtp.gmail.com",
        "port": 587,
        "note": (
            "Gmail yêu cầu **App Password** (không phải mật khẩu thường).\n\n"
            "1. Bật xác thực 2 bước: [myaccount.google.com/security](https://myaccount.google.com/security)\n"
            "2. Tạo App Password: [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) "
            "→ chọn *Mail* + *Other* → copy 16 ký tự.\n"
            "3. Dán vào ô **Mật khẩu / App Password** bên dưới."
        ),
    },
    "Mail Server riêng": {
        "server": "",
        "port": 587,
        "note": (
            "Nhập thông tin SMTP do bộ phận IT cung cấp.\n\n"
            "Cổng phổ biến:\n"
            "- **Port 587** + STARTTLS ✅ (khuyến nghị)\n"
            "- **Port 465** + SSL\n"
            "- **Port 25** + không mã hoá (chỉ dùng nội bộ)"
        ),
    },
}


# ──────────────────────────────────────────────────────────────────────────────
# HELPER: đọc giá trị mặc định từ .env (nếu có)
# ──────────────────────────────────────────────────────────────────────────────
def _load_env_defaults() -> dict:
    load_dotenv()
    return {
        "server":   os.getenv("SMTP_SERVER", ""),
        "port":     int(os.getenv("SMTP_PORT", 587)),
        "email":    os.getenv("SENDER_EMAIL", ""),
        "password": os.getenv("SENDER_PASSWORD", ""),
    }


# ──────────────────────────────────────────────────────────────────────────────
# SIDEBAR: chọn provider + nhập thông tin SMTP
# ──────────────────────────────────────────────────────────────────────────────
def render_smtp_sidebar() -> dict | None:
    """
    Hiển thị phần cài đặt SMTP trong sidebar.
    Trả về dict {server, port, email, password, use_tls, provider}
    hoặc None nếu còn thiếu thông tin bắt buộc.
    """
    st.sidebar.subheader("⚙️ Cấu hình gửi email")

    env = _load_env_defaults()

    # ── Chọn provider ──────────────────────────────────────────────────────
    provider = st.sidebar.radio(
        "Loại mail server",
        list(SMTP_PRESETS.keys()),
        horizontal=True,
        help="Gmail nếu dùng @gmail.com · 'Mail Server riêng' nếu dùng SMTP công ty",
    )
    preset = SMTP_PRESETS[provider]

    with st.sidebar.expander("ℹ️ Hướng dẫn cấu hình", expanded=False):
        st.markdown(preset["note"])

    st.sidebar.divider()

    # ── SMTP Server ────────────────────────────────────────────────────────
    if provider == "Gmail":
        smtp_server = preset["server"]
        st.sidebar.caption(f"🔒 SMTP Server: `{smtp_server}` (cố định)")
    else:
        smtp_server = st.sidebar.text_input(
            "SMTP Server",
            value=env["server"] or preset["server"],
            placeholder="vd: mail.yourcompany.com",
        ).strip()

    # ── Port & TLS ─────────────────────────────────────────────────────────
    col_port, col_tls = st.sidebar.columns([1, 1])

    port_options = [587, 465, 25]
    default_port = env["port"] if env["port"] in port_options else preset["port"]
    smtp_port = col_port.selectbox("Port", port_options, index=port_options.index(default_port))

    # TLS mặc định bật trừ port 25
    use_tls = col_tls.checkbox("Dùng TLS/SSL", value=(smtp_port != 25))

    st.sidebar.divider()

    # ── Tài khoản ──────────────────────────────────────────────────────────
    sender_email = st.sidebar.text_input(
        "Email gửi",
        value=env["email"],
        placeholder="vd: accounting@yourcompany.com",
    ).strip()

    sender_password = st.sidebar.text_input(
        "Mật khẩu / App Password",
        value=env["password"],
        type="password",
        placeholder="Mật khẩu hoặc App Password 16 ký tự",
    )

    # ── Nút Test kết nối ───────────────────────────────────────────────────
    if st.sidebar.button("🔌 Kiểm tra kết nối SMTP", use_container_width=True):
        if not all([smtp_server, smtp_port, sender_email, sender_password]):
            st.sidebar.error("Vui lòng điền đầy đủ thông tin trước khi kiểm tra.")
        else:
            with st.sidebar.status("Đang kết nối...", expanded=True) as s:
                try:
                    conn = create_smtp_connection(
                        smtp_server, smtp_port, sender_email, sender_password, use_tls=use_tls
                    )
                    conn.quit()
                    s.update(label="✅ Kết nối thành công!", state="complete")
                    st.session_state["smtp_verified"] = True
                except Exception as e:
                    s.update(label=f"❌ Lỗi: {e}", state="error")
                    st.session_state["smtp_verified"] = False

    if st.session_state.get("smtp_verified"):
        st.sidebar.success(f"Đã xác minh: **{sender_email}**")

    # Trả về None nếu thiếu field bắt buộc
    if not all([smtp_server, sender_email, sender_password]):
        return None

    return {
        "server":   smtp_server,
        "port":     smtp_port,
        "email":    sender_email,
        "password": sender_password,
        "use_tls":  use_tls,
        "provider": provider,
    }


# ──────────────────────────────────────────────────────────────────────────────
# SIDEBAR: chọn người ký tên trong email
# ──────────────────────────────────────────────────────────────────────────────
def render_sender_sidebar() -> dict:
    st.sidebar.divider()
    st.sidebar.subheader("👤 Người gửi / Sender")
    st.sidebar.info(
        "🌐 Ngôn ngữ email tự động theo cột **Nhóm khách hàng** "
        "(domestic → 🇻🇳 VN, global → 🇬🇧 EN)"
    )

    senders_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "senders.json")
    try:
        with open(senders_path, "r", encoding="utf-8") as f:
            senders = json.load(f)
    except Exception:
        senders = [{
            "name": "Huynh Thi Ngoc Lien",
            "title": "Receivable Accountant / Accounting Dept.",
            "phone": "+84 93 303 5860",
            "email": "accounting@gotco.com.vn",
        }]

    selected_name = st.sidebar.selectbox("Chọn người ký email", [s["name"] for s in senders])
    selected = next((s for s in senders if s["name"] == selected_name), senders[0])
    st.sidebar.caption(f"📞 {selected['phone']}  |  ✉️ {selected['email']}")
    return selected


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────
def main():
    st.title("📧 Phần Mềm Quản Lý Gửi Email Công Nợ")

    smtp_cfg        = render_smtp_sidebar()
    selected_sender = render_sender_sidebar()

    # ── Banner trạng thái cấu hình ─────────────────────────────────────────
    if smtp_cfg:
        badge = "🟢 Gmail" if smtp_cfg["provider"] == "Gmail" else "🔵 Mail Server riêng"
        st.success(
            f"{badge} · `{smtp_cfg['email']}` · "
            f"{smtp_cfg['server']}:{smtp_cfg['port']} · "
            f"{'TLS/SSL ✅' if smtp_cfg['use_tls'] else 'Không mã hoá ⚠️'}"
        )
    else:
        st.warning("⚠️ Chưa điền đầy đủ cấu hình SMTP ở sidebar bên trái.")

    st.write("---")

    # ── 1. Upload File ─────────────────────────────────────────────────────
    st.subheader("1. Tải lên dữ liệu")
    uploaded_file = st.file_uploader(
        "Vui lòng tải lên file Excel (chứa sheet 'Báo cáo-GIAO BAN' và 'KHACHHANG')",
        type=["xlsx"],
    )

    if uploaded_file is not None:
        if st.button("⚙️ Trích Xuất Dữ Liệu Công Nợ"):
            with st.spinner("Đang tính toán..."):
                processed_df, report_date, err_msg = process_data(uploaded_file)
                if err_msg:
                    st.warning(err_msg) if "CẢNH BÁO" in err_msg else st.error(err_msg)
                if processed_df is not None:
                    st.session_state["processed_df"] = processed_df
                    st.session_state["report_date"]  = report_date
                    st.success("Đã phân tích xong dữ liệu!")

    # ── 2. Bảng tổng quan ─────────────────────────────────────────────────
    if "processed_df" not in st.session_state:
        return

    st.write("---")
    st.subheader("2. Kiểm tra danh sách chuẩn bị gửi (Trang Chờ)")

    df_all      = st.session_state["processed_df"] if st.session_state["processed_df"] is not None else pd.DataFrame(columns=["Khách hàng", "Email"])
    report_date = st.session_state.get("report_date", "")
    df_valid    = df_all.dropna(subset=["Email"])
    df_missing  = df_all[df_all["Email"].isna()]

    summary_table = []
    for (cus, email, cc, nhom), grp in df_valid.groupby(
        ["Khách hàng", "Email", "CC", "Nhóm khách hàng"]
    ):
        mail_lang = "English" if str(nhom).lower() == "global" else "Tiếng Việt"
        summary_table.append({
            "Khách hàng":    cus,
            "Nhóm":          nhom,
            "Ngôn ngữ":      "🇬🇧 EN" if mail_lang == "English" else "🇻🇳 VN",
            "Email (To)":    email,
            "CC":            cc or "",
            "Số lượng HĐ":   len(grp),
            "Tổng nợ (VND)": format_currency(grp["Số còn phải thu"].sum()),
        })

    st.write(f"Tìm thấy **{len(summary_table)}** khách hàng có báo nợ đủ điều kiện gửi email.")
    if not summary_table:
        return

    st.dataframe(pd.DataFrame(summary_table), use_container_width=True)

    # ── 3. Preview & Gửi từng người ───────────────────────────────────────
    st.write("---")
    st.subheader("3. Xem trước và Gửi Email từng Khách Hàng")

    for (cus, email, cc, nhom), grp in df_valid.groupby(
        ["Khách hàng", "Email", "CC", "Nhóm khách hàng"]
    ):
        mail_lang    = "English" if str(nhom).lower() == "global" else "Tiếng Việt"
        is_sent      = st.session_state.get(f"sent_{cus}_{email}", False)
        status_emoji = "✅ ĐÃ GỬI" if is_sent else "⏳ CHỜ GỬI"
        lang_badge   = "🇬🇧 EN" if mail_lang == "English" else "🇻🇳 VN"
        total_debt   = format_currency(grp["Số còn phải thu"].sum())
        cc_str       = cc or ""

        with st.expander(
            f"[{status_emoji}] {lang_badge} {cus} ({len(grp)} hóa đơn, Tổng nợ: {total_debt} VND)"
        ):
            col1, col2 = st.columns(2)
            col1.markdown(f"📧 **To:** `{email}`")
            col2.markdown(f"📋 **CC:** `{cc_str}`" if cc_str else "📋 **CC:** _(không có)_")

            html_preview = generate_email_body(
                cus, grp, grp["Số còn phải thu"].sum(), report_date, mail_lang, selected_sender
            )
            st.components.v1.html(html_preview, height=500, scrolling=True)

            if not is_sent:
                if st.button(f"📤 Xác nhận gửi email cho {cus}", key=f"btn_send_{cus}_{email}"):
                    if not smtp_cfg:
                        st.error("⚠️ Vui lòng điền đầy đủ cấu hình SMTP ở sidebar trước khi gửi!")
                    else:
                        with st.spinner(f"Đang gửi email cho {cus}..."):
                            try:
                                smtp_conn = create_smtp_connection(
                                    smtp_cfg["server"],
                                    smtp_cfg["port"],
                                    smtp_cfg["email"],
                                    smtp_cfg["password"],
                                    use_tls=smtp_cfg["use_tls"],
                                )
                                success, error_msg = send_single_email(
                                    server=smtp_conn,
                                    customer_name=cus,
                                    customer_email=email,
                                    customer_cc=cc_str,
                                    group_df=grp,
                                    sender_email=smtp_cfg["email"],
                                    report_date=report_date,
                                    mail_lang=mail_lang,
                                    sender=selected_sender,
                                )
                                smtp_conn.quit()
                            except Exception as conn_err:
                                success   = False
                                error_msg = f"Không thể kết nối SMTP: {conn_err}"

                        if success:
                            st.session_state[f"sent_{cus}_{email}"] = True
                            st.rerun()
                        else:
                            st.error(f"Lỗi gửi email cho {cus}: {error_msg}")
            else:
                st.success("Email này đã được gửi thành công.")

    # ── Cảnh báo thiếu email ───────────────────────────────────────────────
    if not df_missing.empty:
        st.write("---")
        st.error(
            f"Cảnh báo: Có {df_missing['Khách hàng'].nunique()} khách hàng có nợ nhưng "
            "KHÔNG TÌM THẤY EMAIL trong Mapping:"
        )
        st.dataframe(
            df_missing[["Khách hàng", "Số còn phải thu", "Số hóa đơn"]].copy(),
            use_container_width=True,
        )


if __name__ == "__main__":
    main()