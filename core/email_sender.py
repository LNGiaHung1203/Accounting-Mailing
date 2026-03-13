import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from core.email_templates import generate_email_body

def send_single_email(customer_name, customer_email, customer_cc, group_df, smtp_server, smtp_port, sender_email, sender_password, report_date, mail_lang, sender=None):
    """
    Gửi email cho từng khách hàng.
    - customer_email: chuỗi email To (có thể nhiều, phân cách ';')
    - customer_cc: chuỗi email CC (có thể nhiều, phân cách ';'), từ cột CC trong file Excel
    Trả về (success: bool, error_message: str)
    """
    try:
        # Parse To emails
        to_emails = [e.strip() for e in str(customer_email).replace(',', ';').split(';') if e.strip()]
        # Parse CC emails
        cc_emails = [e.strip() for e in str(customer_cc).replace(',', ';').split(';') if e.strip()]

        all_recipients = to_emails + cc_emails

        # Kết nối SMTP — tự động chọn SSL/TLS (port 465) hoặc STARTTLS (587/other)
        port = int(smtp_port)
        if port == 465:
            server = smtplib.SMTP_SSL(smtp_server, port)
        else:
            server = smtplib.SMTP(smtp_server, port)
            server.starttls()
        server.login(sender_email, sender_password)
        
        total_amount = group_df['Số còn phải thu'].sum()
        
        msg = MIMEMultipart("alternative")
        # Tên hiển thị lấy từ sender profile
        display_name = sender.get('display_name', '') if sender else ''
        from core.email_templates import DEFAULT_SENDER
        if not sender:
            display_name = DEFAULT_SENDER.get('display_name', '')
        from email.utils import formataddr
        msg['From'] = formataddr((display_name, sender_email))
        msg['To'] = ', '.join(to_emails)
        if cc_emails:
            msg['Cc'] = ', '.join(cc_emails)
        
        if mail_lang == "English":
            msg['Subject'] = f"[Reminder for Outstanding Payment] - {customer_name}"
        else:
            msg['Subject'] = f"[THÔNG BÁO CÔNG NỢ QUÁ HẠN] - {customer_name}"
        
        html_content = generate_email_body(customer_name, group_df, total_amount, report_date, mail_lang, sender)
        msg.attach(MIMEText(html_content, "html"))
        
        server.sendmail(sender_email, all_recipients, msg.as_string())
        server.quit()
        return True, ""
    except Exception as e:
        return False, str(e)
