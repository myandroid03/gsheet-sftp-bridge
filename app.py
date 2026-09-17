import streamlit as st
import gspread
import os
import json
from cryptography.fernet import Fernet

# --- CONFIG & INITIALIZATION ---
CREDENTIALS_FILE = "credentials.json"
KEY_FILE = "secret.key"
D365_CRED_FILE = "d365_credentials.enc"
SHEET_NAME = "C3.5"  # Sesuaikan dengan nama sheet/tab di Google Sheet Anda

st.set_page_config(page_title="D365 Customer Portal", page_icon="📦", layout="wide")

# --- HELPER ENCRYPTION ---
def generate_key():
    if not os.path.exists(KEY_FILE):
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as f:
            f.write(key)

def load_key():
    return open(KEY_FILE, "rb").read()

def save_d365_credentials(username, password):
    generate_key()
    f = Fernet(load_key())
    data = json.dumps({"username": username, "password": password}).encode()
    encrypted = f.encrypt(data)
    with open(D365_CRED_FILE, "wb") as file:
        file.write(encrypted)

def get_d365_credentials():
    if not os.path.exists(D365_CRED_FILE):
        return None, None
    try:
        f = Fernet(load_key())
        encrypted = open(D365_CRED_FILE, "rb").read()
        decrypted = f.decrypt(encrypted)
        data = json.loads(decrypted.decode())
        return data["username"], data["password"]
    except Exception:
        return None, None

# --- GSHEET CLIENT ---
@st.cache_resource
def get_gsheet_client():
    return gspread.service_account(filename=CREDENTIALS_FILE)

# --- UI LAYOUT ---
st.title("📦 D365 Customer Management Portal")

tab1, tab2, tab3 = st.tabs(["📝 Upsert Customer", "🗑️ Delete Customer", "🔑 Settings D365 Account"])

# === TAB 1: UPSERT (LABEL CUSTOMIZE D365) ===
with tab1:
    st.subheader("Form Input / Update Customer (Mandatory & Core Fields)")
    gsheet_url = st.text_input("URL atau Nama File Google Sheet:", value="")
    
    with st.form("upsert_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            site = st.text_input("Site", value="Site")
            company = st.text_input("Company (dataAreaId) *", value="BFI")
            cust_id = st.text_input("Customer ID (CustomerAccount) *")
            cust_name = st.text_input("Customer Name (OrganizationName) *")
            cust_group = st.text_input("Customer Group (CustomerGroupId) *", value="GT_RETAIL")
            currency = st.text_input("Currency (SalesCurrencyCode)", value="IDR")
            
        with col2:
            street = st.text_area("Street (AddressStreet) *")
            city = st.text_input("City (AddressCity)")
            country = st.text_input("Country/Region (AddressCountryRegionId)", value="IDN")
            phone = st.text_input("Primary Phone (PrimaryContactPhone)")
            email = st.text_input("Primary Email (PrimaryContactEmail)")
            
        with col3:
            sales_group = st.text_input("SALES GROUP (CommissionSalesGroupId)")
            emp_resp = st.text_input("EMPLOYEE RESPONSIBLE (EmployeeResponsibleNumber)")
            market = st.text_input("MARKET (LineOfBusinessId)")
            channel = st.text_input("CHANNEL (SalesSegmentId)")
            warehouse = st.text_input("WAREHOUSE ID (WarehouseId)")
            status_outlet = st.text_input("STATUS OUTLET (OnHoldStatus)", value="No")

        submitted = st.form_submit_button("🚀 Submit Upsert to Queue")
        
        if submitted:
            if not cust_id or not cust_name or not company or not gsheet_url:
                st.error("Company, Customer ID, Customer Name, dan URL Google Sheet wajib diisi!")
            else:
                try:
                    gc = get_gsheet_client()
                    sh = gc.open_by_url(gsheet_url) if "docs.google.com" in gsheet_url else gc.open(gsheet_url)
                    worksheet = sh.worksheet(SHEET_NAME)
                    
                    # Pemetaan data lengkap ke 45 kolom D365 + 3 kolom Bot Control (Action, Status, Message)
                    row_data = [
                        site, company, "", "Organization", cust_id, cust_name, "", "", cust_id, cust_group,
                        currency, cust_name, street, city, country, "", "No", "0", "", "Net 30",
                        "TRANSFER", "", "MOTOR", phone, "", email, "No", "PPN", "", "",
                        "", "", "", "", "", sales_group, emp_resp, "", market, channel,
                        "", "", "", warehouse, status_outlet,
                        "UPSERT", "PENDING", "Inserted via Web UI"
                    ]
                    
                    # Cek apakah Customer ID sudah ada untuk Upsert
                    cell = worksheet.find(cust_id)
                    if cell:
                        row = cell.row
                        row_data[-1] = "Updated via Web UI"  # Message
                        worksheet.update(f"A{row}:AV{row}", [row_data])
                        st.success(f"Data Customer **{cust_id}** diperbarui di baris {row} dengan status **PENDING**!")
                    else:
                        worksheet.append_row(row_data)
                        st.success(f"Customer **{cust_id}** berhasil dimasukkan ke antrean **UPSERT**!")
                except Exception as e:
                    st.error(f"Gagal terhubung ke Google Sheet: {str(e)}")

# === TAB 2: DELETE ===
with tab2:
    st.subheader("Form Hapus / Deaktivasi Customer")
    gsheet_url_del = st.text_input("URL atau Nama File Google Sheet (Delete):", value="", key="del_url")
    
    with st.form("delete_form", clear_on_submit=True):
        del_cust_id = st.text_input("Customer ID (CustomerAccount) yang ingin dihapus *")
        confirm = st.checkbox("Saya konfirmasi ingin menghapus / menonaktifkan customer ini dari D365")
        
        del_submitted = st.form_submit_button("⚠️ Process Delete Request")
        
        if del_submitted:
            if not del_cust_id or not confirm or not gsheet_url_del:
                st.error("Isi Customer ID, centang konfirmasi, dan URL Google Sheet!")
            else:
                try:
                    gc = get_gsheet_client()
                    sh = gc.open_by_url(gsheet_url_del) if "docs.google.com" in gsheet_url_del else gc.open(gsheet_url_del)
                    worksheet = sh.worksheet(SHEET_NAME)
                    
                    cell = worksheet.find(del_cust_id)
                    if cell:
                        row = cell.row
                        worksheet.update_cell(row, 46, "DELETE")  # Col 46 (AT): Action
                        worksheet.update_cell(row, 47, "PENDING") # Col 47 (AU): Status
                        worksheet.update_cell(row, 48, "Delete requested via Web UI") # Col 48 (AV): Message
                        st.warning(f"Customer **{del_cust_id}** pada baris {row} ditandai untuk **DELETE** (PENDING).")
                    else:
                        st.error(f"Customer ID **{del_cust_id}** tidak ditemukan di Google Sheet!")
                except Exception as e:
                    st.error(f"Gagal terhubung ke Google Sheet: {str(e)}")

# === TAB 3: SETTINGS ===
with tab3:
    st.subheader("🔑 Manajemen Kredensial Akun D365")
    saved_user, _ = get_d365_credentials()
    if saved_user:
        st.success(f"Kredensial tersimpan untuk User: **{saved_user}**")
    else:
        st.warning("Kredensial D365 belum tersimpan di komputer lokal.")
        
    with st.form("cred_form"):
        d365_user = st.text_input("Username / Email D365", value=saved_user if saved_user else "")
        d365_pass = st.text_input("Password D365 Baru", type="password")
        
        save_btn = st.form_submit_button("🔒 Simpan Kredensial Terenkripsi")
        if save_btn:
            if d365_user and d365_pass:
                save_d365_credentials(d365_user, d365_pass)
                st.success("Kredensial D365 berhasil disandikan dan disimpan secara aman!")
                st.rerun()
            else:
                st.error("Username dan Password wajib diisi!")
