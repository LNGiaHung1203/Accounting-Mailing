import pandas as pd
from datetime import datetime, timedelta
from core.utils import format_currency, format_currency_usd, get_debt_group

# ============================================================
# SHARED HELPERS
# ============================================================

DEFAULT_SENDER = {
    "name": "Huynh Thi Ngoc Lien",
    "title": "Receivable Accountant / Accounting Dept.",
    "phone": "+84 93 303 5860",
    "email": "accounting@gotco.com.vn"
}

def _signature_html(sender):
    return f"""
      <table width="500" border="0" cellspacing="0" cellpadding="0" style="border-collapse: collapse; line-height: 1.4; margin-top: 15px;">
        <tbody>
            <tr>
                <td style="padding-bottom: 5px;">
                    <span style="font-size: 10pt; color: #008000; font-weight: bold;">{sender['name']}</span><br>
                    <span style="font-size: 9pt; color: #000000; font-weight: bold;">{sender['title']}</span>
                </td>
            </tr>
            <tr>
                <td style="padding-bottom: 5px;">
                    <b style="color: #008000;">M:</b> {sender['phone']} | 
                    <b style="color: #008000;">E:</b> 
                    <a href="mailto:{sender['email']}" style="color: #1155cc; text-decoration: none;">{sender['email']}</a>
                </td>
            </tr>
            <tr>
                <td style="padding-bottom: 0px; color: #538135;">
                    -------------------------------------------------------------------------------------
                </td>
            </tr>
            <tr>
                <td style="padding-bottom: 5px;">
                    <span style="font-size: 9pt; color: #008000; font-weight: bold;">GREEN OCEAN TECHNOLOGY AND SERVICE COMPANY (GOTCO)</span><br>
                    <span style="font-size: 9pt; color: #008000; font-weight: bold;">CÔNG TY TNHH DỊCH VỤ VÀ KỸ THUẬT BIỂN XANH</span>
                </td>
            </tr>
            <tr>
                <td style="padding-bottom: 5px;">
                    <b style="color: #008000;">P:</b> +84 90 183 7775 | 
                    <b style="color: #008000;">E:</b> <a href="mailto:info@gotco.com.vn" style="color: #1155cc; text-decoration: none;">info@gotco.com.vn</a> | 
                    <b style="color: #008000;">W:</b> <a href="https://www.gotco.com.vn" target="_blank" style="color: #1155cc; text-decoration: none;">https://www.gotco.com.vn</a>
                </td>
            </tr>
            <tr>
                <td style="padding-bottom: 5px;">
                    <b style="color: #008000;">HQ:</b> 183C/5P Ton That Thuyet Street, Vinh Hoi Ward, HCMC, Viet Nam. Zip: 700000
                </td>
            </tr>
            <tr>
                <td style="padding-bottom: 5px;">
                    <u><b>Workplace</b></u>:
                </td>
            </tr>
            <tr>
                <td>
                    <table width="100%" border="0" cellspacing="0" cellpadding="0">
                        <tr>
                            <td width="33%" valign="top" style="padding-right: 10px; border-right: 1px solid #000; font-size: 9pt;">
                                389 (12/1F) Dao Tri Street, Phu Thuan Ward, HCMC, Viet Nam
                            </td>
                            <td width="33%" valign="top" style="padding-left: 10px; padding-right: 10px; border-right: 1px solid #000; font-size: 9pt;">
                                239 National Route 1A, Binh Son Village, Quang Ngai, Viet Nam
                            </td>
                            <td width="33%" valign="top" style="padding-left: 10px; font-size: 9pt;">
                                1423 Ngo Gia Tu Street, Hai An Ward, Hai Phong, Viet Nam
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </tbody>
      </table>
    """

def _sort_df(df_group):
    """Sort rows by debt group (heaviest first)."""
    def _key(d):
        try: d = float(d)
        except: d = 0
        if d < 0:    return 0
        elif d == 0: return 1
        elif d <= 15: return 2
        elif d <= 30: return 3
        elif d <= 60: return 4
        elif d <= 90: return 5
        else:         return 6
    df = df_group.copy()
    df['_sort_key'] = df['Số ngày quá hạn'].apply(_key)
    return df.sort_values('_sort_key', ascending=False).reset_index(drop=True)

def _parse_report_date_vn(report_date):
    """Ensure report_date is in dd/mm/yyyy string format."""
    try:
        for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%m/%d/%Y'):
            try:
                return datetime.strptime(str(report_date).strip(), fmt).strftime('%d/%m/%Y')
            except ValueError:
                continue
    except:
        pass
    return str(report_date).strip().split(' ')[0]

def _parse_report_date_en(report_date):
    """Return report_date as 'Month DD, YYYY' English format."""
    try:
        for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%m/%d/%Y'):
            try:
                return datetime.strptime(str(report_date).strip(), fmt).strftime('%B %d, %Y')
            except ValueError:
                continue
    except:
        pass
    return str(report_date).strip()


# ============================================================
# TEMPLATE 1 — ENGLISH
# ============================================================

def _build_en(customer_name, df_group, report_date, sender):
    report_date_str = _parse_report_date_en(report_date)
    df_sorted = _sort_df(df_group)

    sum_ngoai_te = 0
    rows_html = ""
    for idx, row in enumerate(df_sorted.to_dict('records'), 1):
        try: val_ngoai_te = float(row.get('Ngoại tệ', 0))
        except: val_ngoai_te = 0
        sum_ngoai_te += val_ngoai_te
        rows_html += f"""
          <tr>
            <td style="border: 1px solid #000; padding: 5px; width: 30px; text-align: center;">{idx}</td>
            <td style="border: 1px solid #000; padding: 5px; text-align: left; max-width: 250px; word-wrap: break-word;">{row.get('Diễn giải', '')}</td>
            <td style="border: 1px solid #000; padding: 5px; text-align: right; white-space: nowrap;">{format_currency_usd(val_ngoai_te)}</td>
          </tr>
        """

    # ── INTRO ──────────────────────────────────────────────
    intro_html = f"""
      <p style="margin-bottom: 5px;"><strong style="font-size: 1.1em;">Dear {customer_name},</strong></p>
      <p>I hope you are doing well.</p>
      <p>This is a friendly reminder regarding the outstanding payment as {report_date_str}, The details are as follows:</p>
    """

    # ── TABLE ──────────────────────────────────────────────
    table_html = f"""
      <table style="border-collapse: collapse; width: 900px; text-align: center; margin-top: 15px;">
        <thead>
          <tr><td style="padding: 4px;"></td><td style="padding: 4px;"></td><td style="padding: 4px; text-align: right; font-style: italic; color: #555;">Currency: USD</td></tr>
          <tr style="background-color: #f2f2f2;">
            <th style="border: 1px solid #000; padding: 5px;">No.</th>
            <th style="border: 1px solid #000; padding: 5px;">Description</th>
            <th style="border: 1px solid #000; padding: 5px;">Amount</th>
          </tr>
        </thead>
        <tbody>
          {rows_html}
          <tr style="font-weight: bold;">
            <td colspan="2" style="border: 1px solid #000; padding: 5px; text-align: right;">Total</td>
            <td style="border: 1px solid #000; padding: 5px; text-align: right;">{format_currency_usd(sum_ngoai_te)}</td>
          </tr>
        </tbody>
      </table>
    """

    # ── FOOTER ─────────────────────────────────────────────
    footer_html = f"""
      <p>Could you please check and arrange the payment at your earliest convenience?</p>
      <p>Please transfer the payment to the following bank account:</p>
      <div style="margin-left: 0px; margin-top: 15px;">
          <table style="border-collapse: collapse; font-size: 1em;">
              <tr>
                  <td style="padding-bottom: 5px;">Beneficiary</td>
                  <td style="padding-bottom: 5px; padding-left: 5px;">: <strong style="color: #2c5d97; text-transform: uppercase;">GREEN OCEAN TECHNOLOGY AND SERVICE COMPANY LIMITED</strong></td>
              </tr>
              <tr>
                  <td style="padding-bottom: 5px;">Account Number (USD)</td>
                  <td style="padding-bottom: 5px; padding-left: 5px;">: <strong style="font-size: 1.1em;">160 713 679</strong></td>
              </tr>
              <tr>
                  <td style="padding-bottom: 5px;">SWIFTCODE</td>
                  <td style="padding-bottom: 5px; padding-left: 5px;">: <strong style="font-size: 1.1em;">ASCBVNVXXXX</strong></td>
              </tr>
              <tr>
                  <td style="padding-bottom: 5px;">Bank Name</td>
                  <td style="padding-bottom: 5px; padding-left: 5px;">: Asia Commercial Bank, Ho Chi Minh City, Viet Nam.</td>
              </tr>
              <tr>
                  <td style="padding-bottom: 5px;">Bank Address</td>
                  <td style="padding-bottom: 5px; padding-left: 5px;">: 442 Nguyen Thi Minh Khai Street, Ban Co Ward, Ho Chi Minh City, VietNam.</td>
              </tr>
          </table>
      </div>
      <p>If the payment has already been made, kindly disregard this message and please send us the payment confirmation for our reference.</p>
      <p>Should you need any further information, please feel free to contact us.<br><br>Thank you for your cooperation.</p>
      <p style="font-style: italic; color: #555;"> - Thanks, and Best Regards - </p>
    """

    return intro_html, table_html, footer_html


# ============================================================
# TEMPLATE 2 — VIETNAMESE LIGHT (max overdue ≤ 30 days)
# ============================================================

def _build_vn_light(customer_name, df_group, report_date, sender):
    report_date_str = _parse_report_date_vn(report_date)
    df_sorted = _sort_df(df_group)

    sum_tong_tt = sum_da_tt = sum_con_lai = sum_den_han = sum_chua_den_han = 0
    rows_html = ""
    for idx, row in enumerate(df_sorted.to_dict('records'), 1):
        try: val_tong_tt = float(row.get('Giá trị hóa đơn', row.get('Tổng thanh toán', 0)))
        except: val_tong_tt = 0
        try: val_da_tt = float(row.get('Số đã thu', row.get('Đã thanh toán/ cấn trừ', 0)))
        except: val_da_tt = 0
        try: val_con_lai = float(row.get('Số còn phải thu', row.get('Số còn lại phải thanh toán', 0)))
        except: val_con_lai = 0
        try: d = float(row.get('Số ngày quá hạn', 0))
        except: d = 0

        sum_tong_tt += val_tong_tt
        sum_da_tt += val_da_tt
        sum_con_lai += val_con_lai
        if d >= 1: sum_den_han += val_con_lai
        else: sum_chua_den_han += val_con_lai

        ngay_hd = row.get('Ngày hóa đơn', '')
        if isinstance(ngay_hd, pd.Timestamp):
            ngay_hd = ngay_hd.strftime('%d/%m/%Y')
        nhom = get_debt_group(d, 'Tiếng Việt')

        rows_html += f"""
          <tr>
            <td style="border: 1px solid #000; padding: 5px;">{idx}</td>
            <td style="border: 1px solid #000; padding: 5px;">{row.get('Số hóa đơn', '')}</td>
            <td style="border: 1px solid #000; padding: 5px;">{ngay_hd}</td>
            <td style="border: 1px solid #000; padding: 5px; text-align: left;">{row.get('Diễn giải', '')}</td>
            <td style="border: 1px solid #000; padding: 5px; text-align: right;">{format_currency(val_tong_tt)}</td>
            <td style="border: 1px solid #000; padding: 5px; text-align: right;">{format_currency(val_da_tt)}</td>
            <td style="border: 1px solid #000; padding: 5px; text-align: right;">{format_currency(val_con_lai)}</td>
            <td style="border: 1px solid #000; padding: 5px;">{nhom}</td>
          </tr>
        """

    # ── INTRO ──────────────────────────────────────────────
    intro_html = f"""
      <p style="margin-bottom: 5px;">Kính gửi: <strong style="font-size: 1.1em;">Quý khách hàng, {customer_name}</strong></p>
      <p>Căn cứ vào hợp đồng/báo giá cung cấp dịch vụ và các biên bản Nghiệm thu/giao nhận hàng hóa giữa CÔNG TY TNHH DỊCH VỤ VÀ KỸ THUẬT BIỂN XANH và Quý khách hàng.</p>
      <p>Tính đến ngày {report_date_str}, qua đối soát dữ liệu kế toán, chúng tôi nhận thấy Quý khách hàng vẫn chưa hoàn tất thanh toán các khoản công nợ đã quá hạn. Chi tiết như sau:</p>
    """

    # ── TABLE ──────────────────────────────────────────────
    table_html = f"""
      <table style="border-collapse: collapse; width: 900px; text-align: center; margin-top: 15px;">
        <thead>
          <tr style="background-color: #f2f2f2;">
            <th style="border: 1px solid #000; padding: 5px;">STT</th>
            <th style="border: 1px solid #000; padding: 5px;">Số hóa đơn</th>
            <th style="border: 1px solid #000; padding: 5px;">Ngày hóa đơn</th>
            <th style="border: 1px solid #000; padding: 5px;">Diễn giải</th>
            <th style="border: 1px solid #000; padding: 5px;">Tổng thanh toán</th>
            <th style="border: 1px solid #000; padding: 5px;">Đã thanh toán/ cấn trừ</th>
            <th style="border: 1px solid #000; padding: 5px;">Số còn lại phải thanh toán</th>
            <th style="border: 1px solid #000; padding: 5px; color: red;">Nhóm nợ</th>
          </tr>
        </thead>
        <tbody>
          {rows_html}
          <tr style="font-weight: bold;">
            <td colspan="4" style="border: 1px solid #000; padding: 5px; text-align: right;">Tổng cộng:</td>
            <td style="border: 1px solid #000; padding: 5px; text-align: right;">{format_currency(sum_tong_tt)}</td>
            <td style="border: 1px solid #000; padding: 5px; text-align: right;">{format_currency(sum_da_tt)}</td>
            <td style="border: 1px solid #000; padding: 5px; text-align: right;">{format_currency(sum_con_lai)}</td>
            <td style="border: 1px solid #000; padding: 5px;"></td>
          </tr>
          <tr>
            <td colspan="4" style="border: 1px solid #000; padding: 5px;"></td>
            <td style="border: 1px solid #000; padding: 5px; text-align: right; font-style: italic;">Trong đó:</td>
            <td style="border: 1px solid #000; padding: 5px; text-align: left;">Đến hạn/quá hạn thanh toán</td>
            <td style="border: 1px solid #000; padding: 5px; text-align: right; font-weight: bold; color: red;">{format_currency(sum_den_han)}</td>
            <td style="border: 1px solid #000; padding: 5px;"></td>
          </tr>
          <tr>
            <td colspan="5" style="border: 1px solid #000; padding: 5px;"></td>
            <td style="border: 1px solid #000; padding: 5px; text-align: left;">Chưa/sắp đến hạn</td>
            <td style="border: 1px solid #000; padding: 5px; text-align: right; font-weight: bold;">{format_currency(sum_chua_den_han)}</td>
            <td style="border: 1px solid #000; padding: 5px;"></td>
          </tr>
        </tbody>
      </table>
    """

    # ── FOOTER ─────────────────────────────────────────────
    footer_html = f"""
      <p>Quý khách hàng vui lòng kiểm tra và sắp xếp lịch thanh toán cho chúng tôi khoản công nợ đã đến hạn/quá hạn thanh toán theo các điều khoản thanh toán được thỏa thuận giữa hai bên bằng hình thức chuyển khoản theo thông tin chi tiết:</p>
      <div style="margin-left: 0px; margin-top: 15px;">
          <table style="border-collapse: collapse; font-size: 1em;">
              <tr>
                  <td style="padding-bottom: 5px;">Chủ tài khoản</td>
                  <td style="padding-bottom: 5px; padding-left: 5px;">: <strong style="color: #2c5d97; text-transform: uppercase;">CÔNG TY TNHH DỊCH VỤ VÀ KỸ THUẬT BIỂN XANH</strong></td>
              </tr>
              <tr>
                  <td style="padding-bottom: 5px;">Số tài khoản</td>
                  <td style="padding-bottom: 5px; padding-left: 5px;">: <strong style="font-size: 1.1em;">200114851214544 (VND)</strong></td>
              </tr>
              <tr>
                  <td style="padding-bottom: 5px;">Tại</td>
                  <td style="padding-bottom: 5px; padding-left: 5px;">: Ngân Hàng Eximbank, Tp. HCM</td>
              </tr>
          </table>
      </div>
      <p>Nếu Quý khách hàng đã thanh toán vui lòng bỏ qua email này và gửi lại cho chúng tôi thông tin để đối chiếu,</p>
      <p>Công Ty chúng tôi chân thành cảm ơn sự quan tâm hợp tác tốt đẹp của Quý khách hàng trong thời gian qua.</p>
      <p style="font-style: italic; color: #555;">Trân Trọng!</p>
    """

    return intro_html, table_html, footer_html


# ============================================================
# TEMPLATE 3 — VIETNAMESE HEAVY (max overdue > 30 days)
# ============================================================

def _build_vn_heavy(customer_name, df_group, report_date, sender):
    report_date_str = _parse_report_date_vn(report_date)
    try:
        deadline_dt = datetime.strptime(report_date_str, '%d/%m/%Y') + timedelta(days=7)
        deadline_str = deadline_dt.strftime('%d/%m/%Y')
    except:
        deadline_str = "..."

    df_sorted = _sort_df(df_group)

    sum_tong_tt = sum_da_tt = sum_con_lai = sum_den_han = sum_chua_den_han = 0
    rows_html = ""
    for idx, row in enumerate(df_sorted.to_dict('records'), 1):
        try: val_tong_tt = float(row.get('Giá trị hóa đơn', row.get('Tổng thanh toán', 0)))
        except: val_tong_tt = 0
        try: val_da_tt = float(row.get('Số đã thu', row.get('Đã thanh toán/ cấn trừ', 0)))
        except: val_da_tt = 0
        try: val_con_lai = float(row.get('Số còn phải thu', row.get('Số còn lại phải thanh toán', 0)))
        except: val_con_lai = 0
        try: d = float(row.get('Số ngày quá hạn', 0))
        except: d = 0

        sum_tong_tt += val_tong_tt
        sum_da_tt += val_da_tt
        sum_con_lai += val_con_lai
        if d >= 1: sum_den_han += val_con_lai
        else: sum_chua_den_han += val_con_lai

        ngay_hd = row.get('Ngày hóa đơn', '')
        if isinstance(ngay_hd, pd.Timestamp):
            ngay_hd = ngay_hd.strftime('%d/%m/%Y')
        nhom = get_debt_group(d, 'Tiếng Việt')

        rows_html += f"""
          <tr>
            <td style="border: 1px solid #000; padding: 5px;">{idx}</td>
            <td style="border: 1px solid #000; padding: 5px;">{row.get('Số hóa đơn', '')}</td>
            <td style="border: 1px solid #000; padding: 5px;">{ngay_hd}</td>
            <td style="border: 1px solid #000; padding: 5px; text-align: left;">{row.get('Diễn giải', '')}</td>
            <td style="border: 1px solid #000; padding: 5px; text-align: right;">{format_currency(val_tong_tt)}</td>
            <td style="border: 1px solid #000; padding: 5px; text-align: right;">{format_currency(val_da_tt)}</td>
            <td style="border: 1px solid #000; padding: 5px; text-align: right;">{format_currency(val_con_lai)}</td>
            <td style="border: 1px solid #000; padding: 5px;">{nhom}</td>
          </tr>
        """

    # ── INTRO ──────────────────────────────────────────────
    intro_html = f"""
      <p style="margin-bottom: 5px;">Kính gửi: <strong style="font-size: 1.1em;">Quý khách hàng, {customer_name}</strong></p>
      <p>Căn cứ vào hợp đồng/báo giá cung cấp dịch vụ và các biên bản Nghiệm thu/giao nhận hàng hóa giữa CÔNG TY TNHH DỊCH VỤ VÀ KỸ THUẬT BIỂN XANH và Quý khách hàng.</p>
      <p>Tính đến ngày {report_date_str}, qua đối soát dữ liệu kế toán, chúng tôi nhận thấy Quý khách hàng vẫn chưa hoàn tất thanh toán các khoản công nợ đã quá hạn. Chi tiết như sau:</p>
    """

    # ── TABLE ──────────────────────────────────────────────
    table_html = f"""
      <table style="border-collapse: collapse; width: 900px; text-align: center; margin-top: 15px;">
        <thead>
          <tr style="background-color: #f2f2f2;">
            <th style="border: 1px solid #000; padding: 5px;">STT</th>
            <th style="border: 1px solid #000; padding: 5px;">Số hóa đơn</th>
            <th style="border: 1px solid #000; padding: 5px;">Ngày hóa đơn</th>
            <th style="border: 1px solid #000; padding: 5px;">Diễn giải</th>
            <th style="border: 1px solid #000; padding: 5px;">Tổng thanh toán</th>
            <th style="border: 1px solid #000; padding: 5px;">Đã thanh toán/ cấn trừ</th>
            <th style="border: 1px solid #000; padding: 5px;">Số còn lại phải thanh toán</th>
            <th style="border: 1px solid #000; padding: 5px; color: red;">Nhóm nợ</th>
          </tr>
        </thead>
        <tbody>
          {rows_html}
          <tr style="font-weight: bold;">
            <td colspan="4" style="border: 1px solid #000; padding: 5px; text-align: right;">Tổng cộng:</td>
            <td style="border: 1px solid #000; padding: 5px; text-align: right;">{format_currency(sum_tong_tt)}</td>
            <td style="border: 1px solid #000; padding: 5px; text-align: right;">{format_currency(sum_da_tt)}</td>
            <td style="border: 1px solid #000; padding: 5px; text-align: right;">{format_currency(sum_con_lai)}</td>
            <td style="border: 1px solid #000; padding: 5px;"></td>
          </tr>
          <tr>
            <td colspan="4" style="border: 1px solid #000; padding: 5px;"></td>
            <td style="border: 1px solid #000; padding: 5px; text-align: right; font-style: italic;">Trong đó:</td>
            <td style="border: 1px solid #000; padding: 5px; text-align: left;">Đến hạn/quá hạn thanh toán</td>
            <td style="border: 1px solid #000; padding: 5px; text-align: right; font-weight: bold; color: red;">{format_currency(sum_den_han)}</td>
            <td style="border: 1px solid #000; padding: 5px;"></td>
          </tr>
          <tr>
            <td colspan="5" style="border: 1px solid #000; padding: 5px;"></td>
            <td style="border: 1px solid #000; padding: 5px; text-align: left;">Chưa/sắp đến hạn</td>
            <td style="border: 1px solid #000; padding: 5px; text-align: right; font-weight: bold;">{format_currency(sum_chua_den_han)}</td>
            <td style="border: 1px solid #000; padding: 5px;"></td>
          </tr>
        </tbody>
      </table>
    """

    # ── FOOTER ─────────────────────────────────────────────
    footer_html = f"""
      <p>Bằng Email này, chúng tôi xin thông báo và yêu cầu Quý khách hàng thực hiện thanh toán các khoản nợ quá hạn trên chậm nhất vào ngày <strong>{deadline_str}</strong> về tài khoản sau:</p>
      <div style="margin-left: 0px; margin-top: 15px;">
          <table style="border-collapse: collapse; font-size: 1em;">
              <tr>
                  <td style="padding-bottom: 5px;">Chủ tài khoản</td>
                  <td style="padding-bottom: 5px; padding-left: 5px;">: <strong style="color: #2c5d97; text-transform: uppercase;">CÔNG TY TNHH DỊCH VỤ VÀ KỸ THUẬT BIỂN XANH</strong></td>
              </tr>
              <tr>
                  <td style="padding-bottom: 5px;">Số tài khoản</td>
                  <td style="padding-bottom: 5px; padding-left: 5px;">: <strong style="font-size: 1.1em;">200114851214544 (VND)</strong></td>
              </tr>
              <tr>
                  <td style="padding-bottom: 5px;">Tại</td>
                  <td style="padding-bottom: 5px; padding-left: 5px;">: Ngân Hàng Eximbank, Tp. HCM</td>
              </tr>
          </table>
      </div>
      <p>Nếu quá thời hạn nêu trên mà chúng tôi vẫn chưa nhận được tiền thanh toán hoặc thông báo xác nhận từ ngân hàng, chúng tôi sẽ buộc phải xem xét thực hiện biện pháp:
        <ul style="margin: 6px 0 6px 20px;"><li>Ngừng cung cấp mọi dịch vụ tiếp theo đối với Quý khách hàng.</li></ul>
      </p>
      <p>Nếu Quý khách hàng đã thanh toán vui lòng bỏ qua email này và gửi lại cho chúng tôi thông tin để đối chiếu,</p>
      <p>Công ty chúng tôi rất mong nhận được sự hợp tác thiện chí từ Quý khách và tiếp tục duy trì mối quan hệ kinh doanh giữa hai bên.</p>
      <p style="font-style: italic; color: #555;">Trân Trọng!</p>
    """

    return intro_html, table_html, footer_html


# ============================================================
# DISPATCHER
# ============================================================

def generate_email_body(customer_name, df_group, total_amount, report_date, lang="Tiếng Việt", sender=None):
    """Chọn đúng template và trả về HTML email hoàn chỉnh."""
    if sender is None:
        sender = DEFAULT_SENDER

    if lang == "English":
        intro_html, table_html, footer_html = _build_en(customer_name, df_group, report_date, sender)
    else:
        # Xác định heavy (>30 ngày) hay light (≤30 ngày)
        try:
            max_days = df_group['Số ngày quá hạn'].apply(
                lambda x: float(x) if str(x).replace('.', '').replace('-', '').isdigit() else 0
            ).max()
        except:
            max_days = 0

        if max_days > 30:
            intro_html, table_html, footer_html = _build_vn_heavy(customer_name, df_group, report_date, sender)
        else:
            intro_html, table_html, footer_html = _build_vn_light(customer_name, df_group, report_date, sender)

    html = f"""
    <html>
    <body style="font-family: Tahoma, sans-serif; font-size: 11pt; line-height: 1.2; color: #333; max-width: 800px; margin: 20px;">
      {intro_html}
      {table_html}
      {footer_html}
      {_signature_html(sender)}
    </body>
    </html>
    """
    return html
