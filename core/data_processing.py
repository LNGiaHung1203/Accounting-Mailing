import pandas as pd

def process_data(data_source):
    """
    Hàm đọc và xử lý Excel.
    Trả về bộ ba (dataframe_valid_email, report_date, error_message).
    Nếu có lỗi nghiêm trọng, dataframe_valid_email = None.
    data_source có thể là filepath (dùng cho backend) hoặc file payload (Streamlit).
    """
    try:
        # Lấy ngày báo cáo từ ô dòng 2, cột 2 (B2) trong Excel gốc
        df_raw = pd.read_excel(data_source, sheet_name='Báo cáo-GIAO BAN', header=None, nrows=2)
        report_date_raw = df_raw.iloc[1, 1] if len(df_raw) > 1 and len(df_raw.columns) > 1 else ""
        try:
            if isinstance(report_date_raw, pd.Timestamp):
                # Already a proper datetime - just format it directly
                report_date = report_date_raw.strftime('%d/%m/%Y')
            else:
                # It's a string - parse with explicit dd/mm/yyyy format
                report_date = pd.to_datetime(str(report_date_raw).strip(), format='%d/%m/%Y').strftime('%d/%m/%Y')
        except:
            try:
                # Last resort: use dayfirst=True inference
                report_date = pd.to_datetime(report_date_raw, dayfirst=True).strftime('%d/%m/%Y')
            except:
                report_date = str(report_date_raw).strip().split(' ')[0]
        
        # Reset con trỏ file upload trước khi đọc tiếp
        if hasattr(data_source, 'seek'):
            data_source.seek(0)
        
        # Đọc dữ liệu từ file Upload
        df_cong_no = pd.read_excel(data_source, sheet_name='Báo cáo-GIAO BAN', header=2)
        
        # Reset con trỏ file upload trước khi đọc tiếp
        if hasattr(data_source, 'seek'):
            data_source.seek(0)
        df_mapping = pd.read_excel(data_source, sheet_name='KHACHHANG', header=1)
        
        # Chuẩn hóa tên cột
        df_cong_no.columns = df_cong_no.columns.astype(str).str.strip().str.replace('\n', ' ')
        df_mapping.columns = df_mapping.columns.astype(str).str.strip().str.replace('\n', ' ')

        # Kiểm tra cột bắt buộc
        if 'Số còn phải thu' not in df_cong_no.columns or 'Khách hàng' not in df_cong_no.columns:
            return None, "", "LỖI: Chưa tìm thấy cột 'Số còn phải thu' hoặc 'Khách hàng' trong sheet Báo cáo-GIAO BAN."
            
        if 'Số ngày quá hạn' not in df_cong_no.columns:
            return None, "", "LỖI: Chưa tìm thấy cột 'Số ngày quá hạn' trong file."

        if 'Tên khách hàng' not in df_mapping.columns or 'Email' not in df_mapping.columns:
            return None, "", "LỖI: Chưa tìm thấy cột 'Tên khách hàng' hoặc 'Email' trong sheet KHACHHANG."

        # Chuyển đổi dữ liệu và Lọc
        df_cong_no['Số còn phải thu'] = pd.to_numeric(df_cong_no['Số còn phải thu'], errors='coerce').fillna(0)
        df_cong_no['Số ngày quá hạn'] = pd.to_numeric(df_cong_no['Số ngày quá hạn'], errors='coerce').fillna(0)
        
        # Lọc danh sách nợ
        df_filtered = df_cong_no[(df_cong_no['Số còn phải thu'] > 0)].copy()

        if df_filtered.empty:
            return None, report_date, "CẢNH BÁO: Không có hóa đơn nào thỏa mãn: Số phải thu > 0."

        # Chuẩn hóa tên khách hàng
        df_filtered['Khách hàng'] = df_filtered['Khách hàng'].astype(str).str.strip()
        df_mapping['Tên khách hàng'] = df_mapping['Tên khách hàng'].astype(str).str.strip()

        # Xác định các cột mapping cần lấy (CC và Nhóm KH là tuỳ chọn)
        mapping_cols = ['Tên khách hàng', 'Email']
        if 'CC' in df_mapping.columns:
            df_mapping['CC'] = df_mapping['CC'].fillna('').astype(str).str.strip()
            mapping_cols.append('CC')
        if 'Nhóm khách hàng' in df_mapping.columns:
            df_mapping['Nhóm khách hàng'] = df_mapping['Nhóm khách hàng'].fillna('domestic').astype(str).str.strip().str.lower()
            mapping_cols.append('Nhóm khách hàng')
        
        # Merge Email + CC (dựa trên 'Khách hàng' và 'Tên khách hàng')
        df_merged = pd.merge(df_filtered, df_mapping[mapping_cols], left_on='Khách hàng', right_on='Tên khách hàng', how='left')
        
        if 'CC' not in df_merged.columns:
            df_merged['CC'] = ''
        else:
            df_merged['CC'] = df_merged['CC'].fillna('')
        
        if 'Nhóm khách hàng' not in df_merged.columns:
            df_merged['Nhóm khách hàng'] = 'domestic'
        else:
            df_merged['Nhóm khách hàng'] = df_merged['Nhóm khách hàng'].fillna('domestic')
        
        return df_merged, report_date, ""
        
    except Exception as e:
        return None, "", f"Lỗi khi đọc và xử lý file Excel: {e}"
