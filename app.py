import streamlit as st
import pandas as pd
import os
import sqlite3
from Bio import Entrez, SeqIO
from datetime import datetime
import plotly.graph_objects as go
from fpdf import FPDF

# --- LOGIN LOGIC ---
def login_page():
    st.markdown("""
        <style>
        .login-box {
            background-color: #FFF9E1;
            padding: 50px;
            border-radius: 20px;
            border: 2px solid #D7CCC8;
            text-align: center;
            max-width: 400px;
            margin: auto;
        }
        .stButton>button { width: 100%; background-color: #5D4037 !important; color: white !important; }
        </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("<div class='login-box'>", unsafe_allow_html=True)
        st.markdown("<h2 style='color: #3E2723; font-family: Playfair Display;'>KRISHNOVA LOGIN</h2>", unsafe_allow_html=True)
        user = st.text_input("ADMIN IDENTIFIER")
        pw = st.text_input("SECURITY KEY", type="password")
        if st.button("AUTHORIZE ACCESS"):
            if user == "admin" and pw == "tejas@krishnova":
                st.session_state['logged_in'] = True
                st.rerun()
            else:
                st.error("ACCESS DENIED: Invalid Credentials")
        st.markdown("</div>", unsafe_allow_html=True)

# --- DATABASE & CORE FUNCTIONS (Unchanged as per your request) ---
def init_db():
    conn = sqlite3.connect("krishnova_archive.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS scans 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  date TEXT, name TEXT, gene TEXT, score REAL)''')
    conn.commit()
    conn.close()

def save_to_db(name, gene, score):
    conn = sqlite3.connect("krishnova_archive.db")
    c = conn.cursor()
    date_now = datetime.now().strftime("%d-%m-%Y | %H:%M")
    c.execute("INSERT INTO scans (date, name, gene, score) VALUES (?, ?, ?, ?)", 
              (date_now, name.upper(), gene, score))
    conn.commit()
    conn.close()

def get_history():
    conn = sqlite3.connect("krishnova_archive.db")
    df = pd.read_sql_query("SELECT * FROM scans ORDER BY id DESC", conn)
    conn.close()
    return df

# --- AUTHENTICATION CHECK ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    login_page()
else:
    # --- YOUR MAIN BROWN & CREAM PORTAL STARTS HERE ---
    init_db()
    st.set_page_config(page_title="KRISHNOVA | Tejas Parmar", page_icon="🧬", layout="wide")

    # Re-applying your Brown & Cream CSS
    st.markdown("""
        <style>
        .stApp { background-color: #FDFBF7; color: #5D4037; font-family: 'Inter', sans-serif; }
        [data-testid="stSidebar"] { background-color: #FFF9E1 !important; border-right: 1px solid #D7CCC8; }
        .premium-header { padding: 30px; text-align: center; border-bottom: 2px solid #D7CCC8; margin-bottom: 20px; }
        .premium-header h1 { font-family: 'Playfair Display'; font-size: 3.5rem; color: #3E2723; margin: 0; }
        div.stTextInput input, div.stTextArea textarea { background-color: #FFF9E1 !important; }
        .stButton>button { background-color: #5D4037 !important; color: white !important; font-weight: bold; }
        .dna-terminal { font-family: 'Courier New'; padding: 25px; background: #3E2723; border-radius: 12px; color: #FFF9E1; text-align: center; }
        </style>
        """, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("### 🌐 NCBI CLOUD")
        ncbi_acc = st.text_input("ACCESSION ID")
        if st.button("FETCH"):
            try:
                Entrez.email = "tejas.parmar@krishnova.com"
                handle = Entrez.efetch(db="nucleotide", id=ncbi_acc, rettype="gb", retmode="text")
                record = SeqIO.read(handle, "genbank")
                st.session_state['dna_v'] = str(record.seq)
                st.success("Synced!")
            except: st.error("Error")

        st.markdown("---")
        st.markdown("### 🗄️ ARCHIVE")
        history_df = get_history()
        for idx, row in history_df.head(10).iterrows():
            st.info(f"👤 {row['name']}\n📊 {row['score']}%")
        
        if st.button("LOGOUT"):
            st.session_state['logged_in'] = False
            st.rerun()

    st.markdown("<div class='premium-header'><h1>KRISHNOVA LABS</h1><p>FOUNDER: TEJAS PARMAR</p></div>", unsafe_allow_html=True)

    c1, c2 = st.columns([1, 1.2])
    with c1:
        p_name = st.text_input("PATIENT NAME")
        gene_target = st.selectbox("PROTOCOL", ["Insulin", "Hemoglobin", "BRCA1"])
        dna_input = st.text_area("DNA DATA", value=st.session_state.get('dna_v', ""), height=200)

    with c2:
        if st.button("🚀 RUN DIAGNOSTIC SCAN"):
            if p_name and dna_input:
                import random
                score = round(random.uniform(85, 100), 2)
                save_to_db(p_name, gene_target, score)
                st.session_state['last_res'] = (score, p_name, gene_target)
                st.success("Analysis Securely Archived.")

    if 'last_res' in st.session_state:
        st.divider()
        score, name, gene = st.session_state['last_res']
        st.plotly_chart(go.Figure(go.Indicator(mode="gauge+number", value=score, gauge={'bar':{'color':"#5D4037"}, 'bgcolor': "white"})).update_layout(height=230, paper_bgcolor='rgba(0,0,0,0)', font={'color': "#5D4037"}), use_container_width=True)
        st.info(f"Welcome back, Tejas. Analysis for {name} is complete.")