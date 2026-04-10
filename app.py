import streamlit as st
import pandas as pd
import os
import sqlite3
import time
from Bio import Entrez, SeqIO
from datetime import datetime
import plotly.graph_objects as go
import streamlit.components.v1 as components
from fpdf import FPDF

# --- CORE BIOLOGICAL LOGIC (FIXED) ---
CODON_TABLE = {
    'AUA':'I', 'AUC':'I', 'AUU':'I', 'AUG':'M', 'ACA':'T', 'ACC':'T', 'ACG':'T', 'ACU':'T',
    'AAC':'N', 'AAU':'N', 'AAA':'K', 'AAG':'K', 'AGC':'S', 'AGU':'S', 'AGA':'R', 'AGG':'R',
    'CUA':'L', 'CUC':'L', 'CUG':'L', 'CUU':'L', 'CCA':'P', 'CCC':'P', 'CCG':'P', 'CCU':'P',
    'CAC':'H', 'CAU':'H', 'CAA':'Q', 'CAG':'Q', 'CGA':'R', 'CGC':'R', 'CGG':'R', 'CGU':'R',
    'GUA':'V', 'GUC':'V', 'GUG':'V', 'GUU':'V', 'GCA':'A', 'GCC':'A', 'GCG':'A', 'GCU':'A',
    'GAC':'D', 'GAU':'D', 'GAA':'E', 'GAG':'E', 'GGA':'G', 'GGC':'G', 'GGG':'G', 'GGU':'G',
    'UCA':'S', 'UCC':'S', 'UCG':'S', 'UCU':'S', 'UUC':'F', 'UUU':'F', 'UUA':'L', 'UUG':'L',
    'UAC':'Y', 'UAU':'Y', 'UAA':'_', 'UAG':'_', 'UGC':'C', 'UGU':'C', 'UGA':'_', 'UGG':'W',
}

def dna_to_rna(dna): return dna.replace('T', 'U')

def rna_to_protein(rna):
    # ORF Finder: Finds the first Start Codon (AUG)
    start_index = rna.find('AUG')
    
    # --- FIXED LOGIC ---
    # Agar AUG nahi mila, toh error dene ke bajaye shuruat se translate karo!
    if start_index == -1:
        coding_rna = rna
    else:
        coding_rna = rna[start_index:]
        
    protein = ""
    for i in range(0, len(coding_rna) - (len(coding_rna) % 3), 3):
        codon = coding_rna[i:i+3]
        amino_acid = CODON_TABLE.get(codon, '?')
        if amino_acid == '_': # Stop Codon
            break
        protein += amino_acid
        
    # Agar translation ke baad bhi blank hai, tab error do
    if not protein:
        return "ERROR: Invalid sequence for translation."
        
    return protein
# --- DATABASE ENGINE ---
# --- STEP 1: INITIALIZE DATABASE ---

    # --- STEP 1: DATABASE INITIALIZATION ---
def init_db():
    conn = sqlite3.connect('krishnova.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT, full_name TEXT, profession TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS history 
                 (id INTEGER PRIMARY KEY, name TEXT, gene TEXT, score REAL, date TEXT, result TEXT, role TEXT, drug TEXT)''')
    conn.commit()
    conn.close()

# --- DATABASE SAVE FUNCTION (FIXED) ---
def save_to_db(name, gene, score, result, role="CEO", drug="N/A"):
    try:
        conn = sqlite3.connect('krishnova.db')
        c = conn.cursor()
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Hum 'result' column mein hi result aur sequence dono save kar rahe hain
        c.execute('''INSERT INTO history (name, gene, score, date, result, role, drug) 
                     VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                  (name, gene, score, now, result, role, drug))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Database Error: {e}")
        return False

# --- 2. GET FULL HISTORY (Ye wala missing tha) ---
def get_full_history():
    try:
        conn = sqlite3.connect('krishnova.db')
        import pandas as pd
        query = "SELECT * FROM history ORDER BY id DESC"
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        import pandas as pd
        # Agar table khali ho toh structure return karega
        return pd.DataFrame(columns=['id', 'name', 'gene', 'score', 'date', 'result', 'role', 'drug'])
# 3. Functions ko call karna
init_db()
# --- STEP 2: SESSION STATE ---
# --- INITIALIZATION (Ye line Error fix karegi) ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# --- LOGIN PAGE UI ---
if not st.session_state['logged_in']:
    # Centering the layout
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        # --- LOGO ONLY SECTION ---
        try:
            # Apni file ka sahi naam yahan check kar lena (logo.png)
            st.image("logo.png", use_container_width=True)
        except:
            # Agar logo file nahi milti toh ye icon dikhega
            st.markdown("<h1 style='text-align: center; font-size: 100px;'>🧬</h1>", unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True) # Logo ke niche thoda gap
        
        # --- LOGIN CARD ---
        with st.container(border=True):
            auth_choice = st.radio("SELECT ACTION", ["LOGIN", "REGISTER"], horizontal=True, label_visibility="collapsed")
            st.markdown("---")

            if auth_choice == "REGISTER":
                st.subheader("📝 Create New Account")
                reg_user = st.text_input("User ID / Email ID", key="reg_id")
                reg_pass = st.text_input("Password", type='password', key="reg_p")
                reg_name = st.text_input("Full Name", key="reg_n")
                reg_role = st.selectbox("Role", ["Researcher", "Student", "CEO"], key="reg_r")
                
                ceo_authorized = True
                if reg_role == "CEO":
                    master_key = st.text_input("Master Authorization Key", type='password', key="m_key")
                    if master_key != "TEJAS_CEO_2026":
                        ceo_authorized = False

                if st.button("SIGN UP", key="signup_btn", use_container_width=True):
                    if not ceo_authorized:
                        st.error("❌ Unauthorized! Key required for CEO role.")
                    elif reg_user and reg_pass and reg_name:
                        conn = sqlite3.connect('krishnova.db')
                        c = conn.cursor()
                        try:
                            c.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (reg_user, reg_pass, reg_name, reg_role))
                            conn.commit()
                            st.success("✅ Account Created! Now switch to LOGIN.")
                        except sqlite3.IntegrityError:
                            st.error("❌ User ID already exists!")
                        finally:
                            conn.close()
                    else:
                        st.warning("Please fill all details.")

            else:
                st.subheader("🔑 Secure Access")
                l_user = st.text_input("User ID / Email ID", key="l_id")
                l_pass = st.text_input("Password", type='password', key="l_p")
                
                if st.button("LOGIN", key="login_btn", use_container_width=True):
                    if l_user == "tejas@ceo.com" and l_pass == "admin123":
                        st.session_state['logged_in'] = True
                        st.session_state['user_name'] = "Tejas Parmar"
                        st.session_state['user_role'] = "CEO"
                        st.rerun()
                    else:
                        conn = sqlite3.connect('krishnova.db')
                        c = conn.cursor()
                        c.execute("SELECT * FROM users WHERE username=? AND password=?", (l_user, l_pass))
                        result = c.fetchone()
                        if result:
                            st.session_state['logged_in'] = True
                            st.session_state['user_name'] = result[2]
                            st.session_state['user_role'] = result[3]
                            st.rerun()
                        else:
                            st.error("❌ Invalid ID or Password")
                        conn.close()

    st.stop()
        
    with col2:
            st.info("Don't have an account? Select REGISTER above.")
    
    # --- IMPORTANT: Stops everything else if not logged in ---
    st.stop()

# --- STEP 4: POST-LOGIN NAVIGATION (Everything below this only runs if logged_in is True) ---
st.sidebar.success(f"👤 Logged in: {st.session_state['user_name']} ({st.session_state['user_role']})")
if st.sidebar.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

# [Yahan se aapka Home, Molecular, History wala puraana code start hoga]
    # --- AB AAPKA PURANA NAVIGATION CODE (Home, Molecular, etc.) YAHAN AAYEGA ---
if 'page' not in st.session_state:
    st.session_state['page'] = 'register'

# --- CSS ---
# --- PREMIUM CSS & 
st.markdown("""
    <style>
    /* 🌐 Import Premium Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Poppins:wght@400;600&display=swap');

    /* 🎨 Main App Background */
    .stApp {
        background-color: #050a15 !important; /* Extremely dark blue/black */
        color: #e2e8f0 !important; /* Soft white text */
    }

    /* 🚀 Main Page Headers (H1, H2, H3) */
    .stApp h1, .stApp h2, .stApp h3 {
        font-family: 'Orbitron', sans-serif !important;
        color: #00BFFF !important;
        letter-spacing: 1.5px;
    }

    /* 💡 H1 Glowing Underline Effect */
    .stApp h1 {
        text-shadow: 0px 0px 15px rgba(0, 191, 255, 0.4);
        border-bottom: 2px solid rgba(0, 191, 255, 0.2);
        padding-bottom: 15px;
        margin-bottom: 30px;
    }

    /* 🏷️ Input Box Labels (FULL NAME, BIRTH DATE, etc.) */
    .stTextInput label p, .stDateInput label p, .stSelectbox label p, .stTextArea label p {
        color: #00BFFF !important; /* Premium Blue Color */
        font-family: 'Poppins', sans-serif !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        letter-spacing: 0.5px;
        margin-bottom: 5px !important;
    }

    /* ⌨️ Input Fields & Text Areas (WHITE BACKGROUND) */
    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"], .stDateInput input {
        background-color: #FFFFFF !important; /* Pure White Box */
        border: 1px solid rgba(0, 191, 255, 0.5) !important;
        border-radius: 8px !important;
        font-family: 'Poppins', sans-serif !important;
        transition: all 0.3s ease;
    }

    /* ✨ Input Field Glowing on Click */
    .stTextInput input:focus, .stTextArea textarea:focus, .stSelectbox div[data-baseweb="select"]:focus-within {
        border: 2px solid #00BFFF !important;
        box-shadow: 0px 0px 12px rgba(0, 191, 255, 0.5) !important;
        background-color: #FFFFFF !important; /* Keep it white */
    }

    /* =========================================
       🖋️ TYPING TEXT COLOR FIX (BLACK TEXT)
       ========================================= */
       
    /* 1. Jo text aap type kar rahe ho (Black Color) */
    div[data-baseweb="input"] input, 
    div[data-baseweb="textarea"] textarea, 
    div[data-baseweb="select"] div,
    input[type="text"], input[type="password"] {
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important; /* Browser override */
        font-size: 15px !important;
        font-weight: 600 !important; /* Thoda bold taaki clear dikhe */
    }

    /* 2. Placeholder Text (Halka Grey) */
    div[data-baseweb="input"] input::placeholder, 
    div[data-baseweb="textarea"] textarea::placeholder {
        color: #666666 !important; 
        -webkit-text-fill-color: #666666 !important;
        opacity: 1 !important;
    }

    /* 🗂️ DataFrames & Tables (History Page) */
    [data-testid="stDataFrame"] {
        border: 1px solid rgba(0, 191, 255, 0.2) !important;
        border-radius: 10px;
        background-color: rgba(255, 255, 255, 0.01);
    }

    /* 🚨 Alert & Info Boxes (st.success, st.warning, st.info) */
    .stAlert {
        background-color: rgba(0, 191, 255, 0.08) !important;
        border: 1px solid rgba(0, 191, 255, 0.4) !important;
        color: #ffffff !important;
        border-radius: 8px !important;
        backdrop-filter: blur(5px);
    }
    
    /* 🗄️ Sidebar Premium Background */
    section[data-testid="stSidebar"] { 
        background-color: #0b132b !important; /* Deep Tech Blue */
        border-right: 2px solid #00BFFF;
    }

    /* 🚀 Sidebar Title (KRISHNOVA) */
    section[data-testid="stSidebar"] h2 {
        font-family: 'Orbitron', sans-serif !important;
        color: #00BFFF !important;
        text-align: center;
        letter-spacing: 3px;
        text-shadow: 0px 4px 15px rgba(0, 191, 255, 0.6);
        margin-bottom: 20px;
    }

    /* 🔘 INACTIVE BUTTONS (Dimmed out) */
    [data-testid="stSidebar"] button[kind="secondary"] {
        background-color: transparent !important;
        color: #8892b0 !important;
        border: 1px solid rgba(255,255,255,0.05) !important;
        border-radius: 8px !important;
        height: 45px !important;
        text-align: left !important;
        padding-left: 15px !important;
        font-weight: 400 !important;
        transition: all 0.3s ease;
    }

    /* 🔵 ACTIVE BUTTONS (Glowing indicator) */
    [data-testid="stSidebar"] button[kind="primary"] {
        background-color: rgba(0, 191, 255, 0.1) !important;
        color: #00BFFF !important;
        border: 1px solid #00BFFF !important;
        border-radius: 8px !important;
        height: 45px !important;
        text-align: left !important;
        padding-left: 15px !important;
        font-weight: 600 !important;
        box-shadow: 0px 0px 15px rgba(0, 191, 255, 0.2);
    }

    /* ✨ HOVER EFFECT (For both) */
    [data-testid="stSidebar"] button:hover {
        border: 1px solid #00BFFF !important;
        color: #ffffff !important;
        background-color: rgba(0, 191, 255, 0.3) !important;
        transform: translateX(5px);
    }
    
    /* 👨‍💻 Developer Text Format */
    .dev-credit {
        text-align: center; 
        font-family: 'Poppins', sans-serif;
        font-size: 13px; 
        color: #8892b0;
        margin-top: 30px;
    }
    .dev-name {
        color: #00BFFF;
        font-family: 'Orbitron', sans-serif;
        letter-spacing: 1px;
    }
    </style>
""", unsafe_allow_html=True)
st.markdown("<hr><div class='dev-credit'>Developed by<br><span class='dev-name'>TEJASKUMAR PARMAR</span></div>", unsafe_allow_html=True)
# --- SIDEBAR NAVIGATION ---
# --- SIDEBAR NAVIGATION (PROFESSIONAL V2.0) ---
with st.sidebar:
    # Logo & Branding
    if os.path.exists("logo.png"): 
        st.image("logo.png", use_container_width=True)
    else:
        st.markdown("<h1 style='text-align: center;'>🧬</h1>", unsafe_allow_html=True)
        
    st.markdown("<h2 style='text-align: center; color: #00BFFF; font-family: Orbitron; margin-bottom: 0px;'>KRISHNOVA</h2>", unsafe_allow_html=True)
    st.markdown("<div style='text-align: center; color: #8892b0; font-size: 11px; letter-spacing: 1px; margin-bottom: 25px;'>BIO-IT DIAGNOSTIC ENGINE</div>", unsafe_allow_html=True)
    
    st.markdown("<div style='color: #ffffff; font-size: 12px; font-weight: bold; margin-bottom: 10px; padding-left: 5px;'>📌 MAIN MENU</div>", unsafe_allow_html=True)
    
    # --- SMART NAVIGATION BUTTONS ---
    # Logic: Agar current page wahi hai, toh type="primary" (glow karega), warna "secondary" (dim rahega)
    
    if st.button("📑 ADMISSION DESK", use_container_width=True, type="primary" if st.session_state.get('page') == 'register' else "secondary"):
        st.session_state['page'] = 'register'
        st.rerun()
        
    if st.button("🧬 GENOMIC SCAN", use_container_width=True, type="primary" if st.session_state.get('page') == 'genomic' else "secondary"):
        st.session_state['page'] = 'genomic'
        st.rerun()
        
    if st.button("🧪 MOLECULAR LAB", use_container_width=True, type="primary" if st.session_state.get('page') == 'molecular' else "secondary"):
        st.session_state['page'] = 'molecular'
        st.rerun()
        
    if st.button("📂 MEDICAL ARCHIVES", use_container_width=True, type="primary" if st.session_state.get('page') == 'history' else "secondary"):
        st.session_state['page'] = 'history'
        st.rerun()
        
    # Developer Credit (Aligned to bottom)
    st.markdown("<div style='margin-top: 50px;'><hr></div>", unsafe_allow_html=True)
    st.markdown("<div class='dev-credit'>Developed by<br><span class='dev-name'>TEJASKUMAR PARMAR</span></div>", unsafe_allow_html=True)
if st.session_state['page'] == 'register':
    st.markdown("<h1>ADMISSION DESK</h1>", unsafe_allow_html=True)
    df_h = get_full_history()
    auto_id = f"KR-{(len(df_h) + 1):04d}"
    c1, c2 = st.columns(2)
    with c1:
        name = st.text_input("FULL NAME")
        dob = st.date_input("BIRTH DATE", min_value=datetime(1920, 1, 1))
    with c2:
        city = st.text_input("CITY")
        st.info(f"Assigned ID: {auto_id}")
    if st.button("CONFIRM REGISTRATION"):
        if name and city:
            st.session_state.update({'patient_name': name.upper(), 'patient_id': auto_id, 'patient_dob': str(dob), 'patient_city': city.upper(), 'page': 'genomic'})
            st.rerun()
        else: st.error("Fill all details.")

if st.session_state['page'] == 'genomic':
    st.markdown("<h1>GENOMIC SCAN CENTER</h1>", unsafe_allow_html=True)
    acc_id = st.text_input("ENTER ACCESSION ID", placeholder="NM_000518")
    
    if st.button("FETCH FROM NCBI"):
        try:
            Entrez.email = "tejas.biotech@example.com"
            handle = Entrez.efetch(db="nucleotide", id=acc_id, rettype="fasta", retmode="text")
            record = SeqIO.read(handle, "fasta")
            st.session_state['ncbi_dna'] = str(record.seq).upper()
            st.success("DNA Fetched!")
        except Exception as e: 
            st.error(f"Error: {e}")
    
    col1, col2 = st.columns(2)
    with col1: 
        ref_dna = st.text_area("REFERENCE", value=st.session_state.get('ncbi_dna', ""), height=150).upper().strip()
    with col2: 
        pat_dna = st.text_area("PATIENT SAMPLE", height=150).upper().strip()
    
    if st.button("ALINE"):
        if ref_dna and pat_dna:
            # 1. Calculation Logic
            # Jitne base match nahi kar rahe, wo mutations hain
            total_bases = len(ref_dna)
            matches = sum(1 for a, b in zip(ref_dna, pat_dna) if a == b)
            mutations = total_bases - matches
            
            score = round((matches / total_bases) * 100, 2)
            mutation_percent = round((mutations / total_bases) * 100, 2)
            
            # 2. Highlight Logic (Sirf Red Highlight ke liye)
            highlighted_dna = ""
            for r, p in zip(ref_dna, pat_dna):
                if r != p:
                    highlighted_dna += f"<span style='color: #ff4b4b; font-weight: bold;'>{p}</span>"
                else:
                    highlighted_dna += p

            # 3. Simple Display Lines (Jo aapne maangi thi)
            st.markdown("---")
            st.markdown(f"### 📊 Analysis Results:")
            st.write(f"✅ **Similarity Score:** {score}%")
            st.write(f"⚠️ **Total Mutations Found:** {mutations} Bases")
            st.write(f"🔬 **Mutation Percentage:** {mutation_percent}%")
            
            # 4. Visual Profile (Red Highlight)
            st.markdown("### 🧬 DNA Profile (Mutated Bases in Red)")
            st.markdown(f"""
                <div style="background-color: #1e1e1e; padding: 15px; border-radius: 8px; font-family: monospace; word-wrap: break-word;">
                    {highlighted_dna}
                </div>
            """, unsafe_allow_html=True)

            # 5. Save to DB (Bina koi change kiye)
            res_summary = f"Mutations: {mutations} ({mutation_percent}%)"
            save_to_db(
                name=st.session_state.get('patient_name', 'Unknown'), 
                gene=f"Align: {acc_id}", 
                score=score, 
                result=res_summary,
                role=st.session_state.get('user_role', 'CEO')
            )
            
        else: 
            st.error("Please provide both sequences.")
elif st.session_state['page'] == 'molecular':
    st.markdown("<div class='premium-header'><h1>GLOBAL MOLECULAR ANALYZER & DIAGNOSTICS</h1></div>", unsafe_allow_html=True)
    
    # --- UPGRADED UNIVERSAL PROTEIN DICTIONARY (Multi-Drug AI) ---
    # --- KRISHNOVA GLOBAL MEGA DATABASE (V2.0) ---
    PROTEIN_MAP = {
        # 🟢 1. METABOLIC & LIFESTYLE
        "MALWMR": {
            "name": "Human Preproinsulin", "pdb": "1ZNI", 
            "role": "Glucose metabolism and energy storage.", 
            "drug": "- 💉 Recombinant Insulin Therapy\n- 🥗 Low GI Diet Monitoring\n- 🏃‍♂️ Regular Cardio Exercise"
        },
        
        # 🔴 2. GENETIC BLOOD DISORDERS
        "VHLTPE": {
            "name": "Hemoglobin Beta (Normal)", "pdb": "1HBB", 
            "role": "Healthy Oxygen transport in Red Blood Cells.", 
            "drug": "✅ No medication required.\n- 🍎 Maintain Iron-rich diet\n- 💧 Stay hydrated"
        },
        "VHLTPV": {
            "name": "Hemoglobin Beta (Sickle Cell)", "pdb": "1HBB", 
            "role": "Mutated Oxygen transport protein.", 
            "drug": "- 💊 Primary: Hydroxyurea\n- 🩸 Secondary: Blood Transfusion\n- 🧬 Future: CRISPR Gene Editing"
        },
        "IIGVS": {
            "name": "CFTR Mutant (Cystic Fibrosis)", "pdb": "1XMI", 
            "role": "Defective Chloride channel transport in lungs.", 
            "drug": "- 💊 Trikafta (CFTR Modulator)\n- 🫁 Chest Physiotherapy\n- 🌬️ Inhaled Mucolytics"
        },

        # 🧠 3. NEUROLOGICAL DISORDERS
        "DAEFRH": {
            "name": "Amyloid Beta (Aβ42)", "pdb": "1IYT", 
            "role": "Neuro-signaling; forms plaques in Alzheimer's.", 
            "drug": "- 💊 Lecanemab (Anti-amyloid)\n- 🧠 Cognitive Behavioral Therapy\n- 🧬 Cholinesterase Inhibitors"
        },
        "QQQQQQ": {
            "name": "Mutant Huntingtin (Huntington's Disease)", "pdb": "3IOW", 
            "role": "Toxic polyglutamine aggregation in neurons.", 
            "drug": "- 💊 Tetrabenazine (Symptom management)\n- 🧬 RNA-lowering therapies (Trials)\n- 🧠 Neurological rehab"
        },

        # 🦠 4. VIRAL INFECTIONS (PANDEMICS)
        "MFVFLV": {
            "name": "SARS-CoV-2 Spike Protein (COVID-19)", "pdb": "6VXX", 
            "role": "Viral attachment and entry into host lung cells.", 
            "drug": "- 💊 Paxlovid (Antiviral)\n- 💉 mRNA Vaccine Booster\n- 🛏️ Supportive Oxygen Therapy"
        },
        "PQITLW": {
            "name": "HIV-1 Protease", "pdb": "1HIV", 
            "role": "Viral maturation and cleavage for HIV replication.", 
            "drug": "- 💊 Ritonavir (Protease Inhibitor)\n- 💊 Tenofovir (ART Therapy)\n- 🩸 Viral Load Monitoring"
        },
        "IPPNWH": {
            "name": "Ebola Virus Glycoprotein", "pdb": "5JQ3", 
            "role": "Viral membrane fusion causing hemorrhagic fever.", 
            "drug": "- 💊 Inmazeb (Monoclonal Antibodies)\n- 💉 Ervebo Vaccine\n- 🩸 Intensive IV Fluid Therapy"
        },

        # 🔬 5. BACTERIAL & PARASITIC INFECTIONS
        "MKALIV": {
            "name": "Human Lysozyme (Innate Immunity)", "pdb": "1LZ1", 
            "role": "Antibacterial enzyme fighting local infections.", 
            "drug": "- 💊 Probiotic Supplements\n- 🧴 Topical Antimicrobials\n- 🦷 Enhanced Oral Hygiene"
        },
        "FSRPGL": {
            "name": "Mycobacterium Antigen 85B (Tuberculosis)", "pdb": "1F0N", 
            "role": "Cell wall synthesis in TB bacteria.", 
            "drug": "- 💊 Isoniazid & Rifampin (6 Months)\n- 💊 Pyrazinamide\n- 💉 BCG Vaccine"
        },
        "NKKNDQ": {
            "name": "Plasmodium PfEMP1 (Malaria)", "pdb": "3C2L", 
            "role": "Erythrocyte membrane adherence by parasite.", 
            "drug": "- 💊 Artemisinin Combination Therapy (ACT)\n- 💊 Chloroquine\n- 🦟 Vector Control"
        },

        # 🎗️ 6. ONCOLOGY (CANCER RESEARCH)
        "MEQPQS": {
            "name": "p53 Tumor Suppressor (General Cancer)", "pdb": "1P51", 
            "role": "DNA repair failure leading to uncontrolled growth.", 
            "drug": "- 💊 Nutlin-3A (MDM2 Inhibitor)\n- ☢️ Targeted Radiotherapy\n- 🔬 Routine Biopsy Monitoring"
        },
        "CPICLE": {
            "name": "BRCA1 Mutant Motif (Breast Cancer)", "pdb": "1JM7", 
            "role": "Defective DNA double-strand break repair.", 
            "drug": "- 💊 Olaparib (PARP Inhibitor)\n- ☢️ Targeted Radiation\n- 🧬 Genetic Counseling"
        }
    }

    # --- NCBI LOADER ---
    st.markdown("### 🌐 Step 1: Load Sequence from NCBI (Optional)")
    m_col1, m_col2 = st.columns([3, 1])
    with m_col1:
        m_acc = st.text_input("LOAD FROM NCBI", placeholder="Example: NM_000518", key="mol_acc")
    with m_col2:
        st.write(" ")
        if st.button("FETCH & AUTO-FILL"):
            try:
                Entrez.email = "tejas.biotech@example.com"
                handle = Entrez.efetch(db="nucleotide", id=m_acc, rettype="fasta", retmode="text")
                record = SeqIO.read(handle, "fasta")
                st.session_state['mol_dna'] = str(record.seq).upper()
                st.success("DNA Loaded!")
            except: st.error("Fetch Failed")

    st.markdown("---")
    
    # --- ANALYSIS SECTION ---
    st.markdown("### 🔬 Step 2: Biological Process & AI Diagnostics")
    
    # IMPORTANT: 'option' must be defined before the button logic
    option = st.selectbox("CHOOSE PROCESS", ["Transcription (DNA -> RNA)", "Translation (RNA -> Protein)"])
    
    default_input = st.session_state.get('mol_dna', "")
    input_seq = st.text_area("INPUT SEQUENCE", value=default_input, height=100).upper().strip()
    
    if st.button("RUN GLOBAL ANALYSIS"):
        if input_seq:
            with st.spinner('Analyzing Structural Data...'):
                # Always generate RNA first
                rna_seq = dna_to_rna(input_seq)
                
                if "Translation" in option:
                    # Execute Translation Logic
                    protein = rna_to_protein(rna_seq)
                    
                    if "ERROR" in protein:
                        st.error(protein)
                    else:
                        st.success(f"**Generated Protein Sequence:** {protein[:100]}...")
                        
                        # --- UNIVERSAL SEARCH & DIAGNOSTICS ---
                        found = False
                        p_name, pdb_id, p_role, p_analysis, ai_drug = "", "", "", "", ""
                        
                        for pattern, data in PROTEIN_MAP.items():
                            if pattern in protein:
                                p_name = data["name"]
                                pdb_id = data["pdb"]
                                p_role = data["role"]
                                p_analysis = "✅ Target Identified & Analyzed."
                                ai_drug = data["drug"]
                                found = True
                                break
                        
                        # Fallback for unknown proteins
                        if not found:
                            p_name = f"Peptide-{len(protein)}"
                            pdb_id = "1ZNI" if len(protein) < 150 else "6VSB"
                            p_role = "Uncharacterized cellular protein or structural peptide."
                            p_analysis = "🔍 STABLE: Novel sequence identified (No known mutations)."
                            ai_drug = "Routine Genomic Screening"

                        # --- SAVE TO DATABASE ---
                        patient_name = st.session_state.get('patient_name', 'GUEST_USER')
                        # Purani line hata kar ye dalo:
                        save_to_db(patient_name, p_name, 100.0, result=f"{p_analysis} | Seq: {input_seq[:30]}...", role=p_role, drug=ai_drug)
                        st.markdown("---")
                        st.markdown("### 🔍 Live Molecular Analysis")
                        ca, cb = st.columns(2)
                        with ca:
                            st.info(f"**Target Protein:** {p_name}")
                            st.markdown(f"**🧬 Biological Role:** {p_role}")
                            st.write(f"**Diagnostic Result:** {p_analysis}")
                        with cb: 
    # Dono cheezon ko ek hi warning box ke andar f-string se merge kar diya
   
                         st.warning(f"**🤖 AI Treatment Protocol:**\n\n{ai_drug}")
    
                         
                        st.markdown("---")
                        st.markdown(f"### 🧬 3D Structural Projection (PDB: {pdb_id})")
                        components.iframe(f"https://www.rcsb.org/3d-view/{pdb_id}?preset=viewer", height=600, scrolling=True)
                
                else:
                    # Display Transcription Result
                    st.info(f"**Transcribed mRNA:** {rna_seq}")
        else:
            st.error("Please enter a sequence!")

    st.markdown("---")
    st.caption("Connected to Krishnova Bio-IT Engine | Data Source: RCSB PDB & NCBI")
elif st.session_state['page'] == 'history':
    st.markdown("<h1>MEDICAL ARCHIVES</h1>", unsafe_allow_html=True)
    df = get_full_history()
    
    if not df.empty:
        # Display the full database table
        st.dataframe(df, use_container_width=True)
        
        st.markdown("---")
        st.markdown("### 📥 Generate Patient Report")
        
        # Selection logic
        sel_p = st.selectbox("Select Patient Name for Report", df['name'].unique())
        p_row = df[df['name'] == sel_p].iloc[0]
        
        # Proper button alignment
        if st.button("PREPARE PDF REPORT"):
            try:
                # 🛡️ THE BULLETPROOF EMOJI FILTER
                def safe_text(text):
                    if text is None: return "N/A"
                    return str(text).encode('ascii', 'ignore').decode('ascii').strip()

                pdf = FPDF()
                pdf.add_page()
                
                # ==========================================
                # 1. PREMIUM TOP BANNER (Dark Navy Blue)
                # ==========================================
                pdf.set_fill_color(11, 19, 43) # Krishnova Dark Navy
                pdf.rect(0, 0, 210, 20, 'F')
                
                pdf.set_y(5)
                pdf.set_font("Arial", 'B', 18)
                pdf.set_text_color(0, 191, 255) # Neon Blue Text
                pdf.cell(110, 8, " KRISHNOVA GENOMICS", ln=0)
                
                pdf.set_font("Arial", 'B', 10)
                pdf.set_text_color(255, 255, 255) # White Text
                pdf.cell(80, 8, f"REPORT ID: KR-RPT-{p_row.get('id', 0):04d}", ln=1, align='R')
                
                pdf.set_font("Arial", 'I', 9)
                pdf.set_text_color(200, 200, 200)
                pdf.cell(110, 5, "   Advanced Bio-IT Diagnostic Dashboard", ln=0)
                pdf.cell(80, 5, f"DATE: {datetime.now().strftime('%d-%m-%Y %H:%M')}", ln=1, align='R')
                pdf.ln(8)
                
                # ==========================================
                # 2. PATIENT DEMOGRAPHICS (Compact Grid)
                # ==========================================
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Arial", 'B', 12)
                pdf.set_fill_color(240, 240, 240) # Light Grey
                pdf.cell(190, 8, "  1. PATIENT DEMOGRAPHICS", ln=1, fill=True, border=1)
                
                pdf.set_font("Arial", 'B', 10)
                pdf.cell(30, 7, "  Name:", border='L')
                pdf.set_font("Arial", '', 10)
                pdf.cell(65, 7, f"{safe_text(p_row['name'])}")
                
                pdf.set_font("Arial", 'B', 10)
                pdf.cell(30, 7, "Patient ID:")
                pdf.set_font("Arial", '', 10)
                pdf.cell(65, 7, f"KR-{p_row.get('id', 0):04d}", border='R', ln=1)
                
                pdf.set_font("Arial", 'B', 10)
                pdf.cell(30, 7, "  Age/DOB:", border='L')
                pdf.set_font("Arial", '', 10)
                pdf.cell(65, 7, f"{safe_text(p_row.get('dob', 'N/A'))}")
                
                pdf.set_font("Arial", 'B', 10)
                pdf.cell(30, 7, "City/Location:")
                pdf.set_font("Arial", '', 10)
                pdf.cell(65, 7, f"{safe_text(p_row.get('city', 'N/A'))}", border='R', ln=1)
                pdf.cell(190, 1, "", border='T', ln=1) # Bottom border
                pdf.ln(4)
                
                # ==========================================
                # 3. MOLECULAR ANALYSIS (Split Design)
                # ==========================================
                pdf.set_font("Arial", 'B', 12)
                pdf.set_fill_color(230, 245, 255) # Light Blue
                pdf.cell(190, 8, "  2. GENOMIC TARGET & ANALYSIS", ln=1, fill=True, border=1)
                
                pdf.set_font("Arial", 'B', 10)
                pdf.cell(190, 7, f"  Target Protein/Gene:  {safe_text(p_row['gene'])}", border='L, R', ln=1)
                
                # --- Dynamic Score & Risk Alert ---
                try:
                    score_val = float(p_row.get('score', 100))
                    if score_val < 99:
                        status = "MUTATION DETECTED (HIGH RISK)"
                        s_color = (200, 0, 0) # Red
                    else:
                        status = "NORMAL (HEALTHY)"
                        s_color = (0, 150, 0) # Green
                except:
                    score_val = 100
                    status = "UNKNOWN"
                    s_color = (0, 0, 0)
                
                pdf.cell(40, 10, "  Alignment Score: ", border='L')
                pdf.set_font("Arial", 'B', 16) # Bada Font Score ke liye
                pdf.set_text_color(s_color[0], s_color[1], s_color[2])
                pdf.cell(40, 10, f"{score_val}%", align='L')
                
                pdf.set_font("Arial", 'B', 10)
                pdf.cell(110, 10, f"STATUS: {status}", border='R', ln=1, align='R')
                pdf.set_text_color(0, 0, 0) # Reset Color
                
                # Clinical Observation
                pdf.set_font("Arial", 'B', 10)
                pdf.cell(40, 7, "  Clinical Findings: ", border='L')
                pdf.set_font("Arial", '', 10)
                pdf.multi_cell(150, 7, f"{safe_text(p_row.get('result'))}", border='R')
                pdf.cell(190, 1, "", border='T', ln=1)
                pdf.ln(4)
                
                # ==========================================
                # 4. AI TREATMENT PROTOCOL (Compact List)
                # ==========================================
                pdf.set_font("Arial", 'B', 12)
                pdf.set_fill_color(255, 240, 240) # Light Red
                pdf.cell(190, 8, "  3. AI DRUG RECOMMENDATION & PROTOCOL", ln=1, fill=True, border=1)
                
                pdf.set_font("Arial", '', 11)
                # Convert dash to bullet points and spacing
                drug_text = safe_text(p_row.get('drug')).replace('- ', '  • ')
                pdf.multi_cell(190, 8, f"\n{drug_text}\n", border=1)
                
                # ==========================================
                # 5. FOOTER (Strictly at Bottom, 1-Page Lock)
                # ==========================================
                pdf.set_y(260) # Lock to bottom of the 1st page
                pdf.set_draw_color(0, 191, 255)
                pdf.set_line_width(0.5)
                pdf.line(10, 258, 200, 258) # Blue Footer Line
                
                pdf.set_font("Arial", 'B', 10)
                pdf.set_text_color(0, 31, 63)
                pdf.cell(0, 6, "AUTHORIZED TECH LEAD: TEJASKUMAR PARMAR", ln=1, align='L')
                
                pdf.set_font("Arial", 'I', 8)
                pdf.set_text_color(150, 150, 150)
                pdf.multi_cell(0, 4, "Disclaimer: This is an AI-generated molecular diagnostic report powered by the Krishnova Bio-IT Engine. This document is highly confidential and intended for clinical research, genetic reference, and authorized medical personnel only. Not for direct legal usage without doctor approval.")
                
                # Finalizing PDF
                pdf_output = bytes(pdf.output(dest='S')) 
                
                st.download_button(
                    label="📥 DOWNLOAD 1-PAGE EXECUTIVE REPORT",
                    data=pdf_output,
                    file_name=f"Krishnova_Dashboard_{sel_p}.pdf",
                    mime="application/pdf"
                )
                st.success(f"1-Page Executive Report for {sel_p} is ready!")
                
            except Exception as e:
                st.error(f"PDF Generation Error: {e}")