import os
from dotenv import load_dotenv

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.utils import format_currency
from core.data_processing import process_data
from core.email_sender import send_single_email

def main():
    # 1. Load các biến môi trường từ file .env
    load_dotenv()
    
    SMTP_SERVER = os.getenv("SMTP_SERVER")
    SMTP_PORT = os.getenv("SMTP_PORT")
    SENDER_EMAIL = os.getenv("SENDER_EMAIL")
    SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
    MAIL_LANGUAGE = os.getenv("MAIL_LANGUAGE", "Tiếng Việt") # Lấy config ngôn ngữ từ file env hoặc mặc định
    
    if not all([SMTP_SERVER, SMTP_PORT, SENDER_EMAIL, SENDER_PASSWORD]):
        print("Lỗi: Thiếu thông tin kết nối SMTP trong file .env!")
        return

    # Đường dẫn file đầu vào
    data_file = 'tracking_cong_no.xlsx'
    
    # Kiểm tra xem file có tồn tại không
    if not os.path.exists(data_file):
        print(f"Lỗi: Không tìm thấy file dữ liệu '{data_file}'.")
        return

    print("Đang đọc và xử lý dữ liệu từ Excel...")
    df_merged, report_date, err_msg = process_data(data_file)
    
    if err_msg:
        prefix = "Cảnh báo" if "CẢNH BÁO" in err_msg else "Lỗi"
        print(f"\n[{prefix}] {err_msg}")
    
    if df_merged is None or df_merged.empty:
        print("Dừng tiến trình gửi email.")
        return

    print("\nBắt đầu gửi email...")
    grouped = df_merged.groupby(['Tên khách hàng', 'Email'])
    
    for (customer_name, customer_email), group_df in grouped:
        total_amount = group_df['Số còn phải thu'].sum()
        success, error_msg = send_single_email(
            customer_name, 
            customer_email, 
            group_df, 
            SMTP_SERVER, 
            SMTP_PORT, 
            SENDER_EMAIL, 
            SENDER_PASSWORD, 
            report_date, 
            MAIL_LANGUAGE
        )
        if success:
            print(f"Sent to {customer_name} - {format_currency(total_amount)} VND.")
        else:
            print(f"Failed to send to {customer_name} ({customer_email}). Lỗi: {error_msg}")

    print("\nQuá trình hoàn tất!")

if __name__ == "__main__":
    main()
