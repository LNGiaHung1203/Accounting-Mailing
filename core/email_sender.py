import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from core.email_templates import generate_email_body, DEFAULT_SENDER


def create_smtp_connection(
    smtp_server: str,
    smtp_port: int,
    sender_email: str,
    sender_password: str,
    use_tls: bool = True,
) -> smtplib.SMTP:
    """
    Tạo và trả về kết nối SMTP đã xác thực.

    Logic chọn phương thức kết nối:
    ┌─────────────┬───────────────────────────────────────────────────┐
    │ Port 465    │ SMTP_SSL  — SSL/TLS ngay từ đầu                   │
    │ Port 587    │ SMTP + STARTTLS  (Gmail mặc định, khuyến nghị)    │
    │ Port 25     │ SMTP plain  (nội bộ, use_tls=False)               │
    │ Cổng khác   │ Thử STARTTLS nếu use_tls=True, plain nếu ngược lại│
    └─────────────┴───────────────────────────────────────────────────┘

    Parameters
    ----------
    smtp_server     : Địa chỉ SMTP (vd: smtp.gmail.com / mail.company.com)
    smtp_port       : Cổng (465 / 587 / 25 / custom)
    sender_email    : Tài khoản đăng nhập
    sender_password : Mật khẩu hoặc App Password (Gmail)
    use_tls         : True  → mã hoá (mặc định)
                      False → plain SMTP, chỉ dùng cho server nội bộ

    Returns
    -------
    smtplib.SMTP hoặc smtplib.SMTP_SSL đã đăng nhập thành công.
    Gọi .quit() sau khi gửi xong.

    Raises
    ------
    smtplib.SMTPAuthenticationError  — sai tài khoản / mật khẩu
    smtplib.SMTPConnectError         — không kết nối được server
    Exception                        — lỗi khác
    """
    port = int(smtp_port)
    context = ssl.create_default_context()

    if port == 465:
        # ── SSL ngay từ đầu (port 465) ─────────────────────────────────
        server = smtplib.SMTP_SSL(smtp_server, port, context=context, timeout=30)

    elif use_tls:
        # ── STARTTLS (port 587 hoặc custom có TLS) ─────────────────────
        server = smtplib.SMTP(smtp_server, port, timeout=30)
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()

    else:
        # ── Plain SMTP, không mã hoá — chỉ dùng server nội bộ ─────────
        server = smtplib.SMTP(smtp_server, port, timeout=30)
        server.ehlo()

    server.login(sender_email, sender_password)
    return server


def send_single_email(
    server,
    customer_name: str,
    customer_email: str,
    customer_cc: str,
    group_df,
    sender_email: str,
    report_date: str,
    mail_lang: str,
    sender: dict = None,
) -> tuple[bool, str]:
    """
    Gửi một email công nợ, tái sử dụng kết nối SMTP `server` đã tạo sẵn.

    Parameters
    ----------
    server         : smtplib.SMTP / SMTP_SSL đã login (từ create_smtp_connection)
    customer_name  : Tên khách hàng — dùng trong subject & body
    customer_email : Địa chỉ To (nhiều địa chỉ cách nhau bởi ; hoặc ,)
    customer_cc    : Địa chỉ CC (tuỳ chọn, cùng định dạng)
    group_df       : DataFrame chứa các hóa đơn của khách hàng này
    sender_email   : Địa chỉ email người gửi (header From)
    report_date    : Ngày báo cáo dạng dd/mm/yyyy
    mail_lang      : "English" hoặc "Tiếng Việt"
    sender         : dict thông tin người ký {name, title, phone, email}

    Returns
    -------
    (True, "")           — gửi thành công
    (False, error_msg)   — gửi thất bại kèm lý do
    """
    try:
        # ── 1. Parse địa chỉ email ─────────────────────────────────────────
        def parse_emails(e_str: str) -> list[str]:
            if not e_str or str(e_str).strip().lower() in ("", "nan"):
                return []
            return [e.strip() for e in str(e_str).replace(",", ";").split(";") if e.strip()]

        to_emails = parse_emails(customer_email)
        cc_emails = parse_emails(customer_cc)

        if not to_emails:
            return False, "Thiếu địa chỉ email người nhận (To)."

        all_recipients = to_emails + cc_emails

        # ── 2. Chuẩn bị nội dung ──────────────────────────────────────────
        total_amount = group_df["Số còn phải thu"].sum()
        _sender      = sender or DEFAULT_SENDER
        DISPLAY_NAME = "GOTCO Accounting"   # tên hiển thị cố định trong hộp thư người nhận

        msg = MIMEMultipart("alternative")
        msg["From"] = formataddr((DISPLAY_NAME, sender_email))
        msg["To"]   = ", ".join(to_emails)
        if cc_emails:
            msg["Cc"] = ", ".join(cc_emails)

        clean_name   = str(customer_name).strip().title()
        subject_map  = {
            "English":    f"[Reminder for Outstanding Payment] - {clean_name}",
            "Tiếng Việt": f"[Thông báo công nợ quá hạn] - {clean_name}",
        }
        msg["Subject"] = subject_map.get(mail_lang, subject_map["Tiếng Việt"])

        html_content = generate_email_body(
            customer_name, group_df, total_amount, report_date, mail_lang, _sender
        )
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        # ── 3. Gửi ────────────────────────────────────────────────────────
        server.sendmail(sender_email, all_recipients, msg.as_string())
        return True, ""

    except smtplib.SMTPException as e:
        return False, f"Lỗi SMTP: {e}"
    except Exception as e:
        return False, f"Lỗi hệ thống: {e}"