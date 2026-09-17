# === TAB 1: UPSERT (D365 Template Matching) ===
with tab1:
    st.subheader("Form Input / Update Customer (D365 Standard)")
    gsheet_url = st.text_input("URL atau Nama File Google Sheet:", value="")
    
    with st.form("upsert_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            company = st.text_input("Company (dataAreaId)", value="BFI")
            cust_id = st.text_input("Customer Account / ID *")
            cust_name = st.text_input("Organization Name (Customer Name) *")
            cust_group = st.text_input("Customer Group ID (e.g. GT_RETAIL)")
        with col2:
            phone = st.text_input("Primary Phone")
            segment = st.text_input("Sales Segment ID (Channel)")
            address = st.text_area("Address Street")
            
        submitted = st.form_submit_button("🚀 Submit Upsert to Queue")
        
        if submitted:
            if not cust_id or not cust_name or not gsheet_url:
                st.error("Customer ID, Name, dan URL Google Sheet wajib diisi!")
            else:
                try:
                    gc = get_gsheet_client()
                    sh = gc.open_by_url(gsheet_url) if "docs.google.com" in gsheet_url else gc.open(gsheet_url)
                    worksheet = sh.worksheet(SHEET_NAME)
                    
                    # Cek apakah Customer ID sudah ada untuk Upsert
                    cell = worksheet.find(cust_id)
                    if cell:
                        row = cell.row
                        # Update baris eksisting (A:J)
                        worksheet.update(f"A{row}:J{row}", [[company, cust_id, cust_name, cust_group, address, phone, segment, "UPSERT", "PENDING", "Updated via Web UI"]])
                        st.success(f"Data Customer **{cust_id}** diperbarui di baris {row} dengan status **PENDING**!")
                    else:
                        # Append baris baru
                        worksheet.append_row([company, cust_id, cust_name, cust_group, address, phone, segment, "UPSERT", "PENDING", "Inserted via Web UI"])
                        st.success(f"Customer **{cust_id}** ditambahkan ke antrean **UPSERT**!")
                except Exception as e:
                    st.error(f"Gagal terhubung ke Google Sheet: {str(e)}")
