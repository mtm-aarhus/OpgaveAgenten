
import streamlit as st
import openai
from datetime import datetime, timedelta, date
import requests
import json
import os
import uuid
import base64  # Tilføjet for base64-kodning af vedhæftninger
import smtplib
import socket  # Tilføjet for at håndtere netværksfejl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import Dict, Any, Optional, List
from config import SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, RECIPIENT_EMAIL
from prompt_handlers import FieldHandlerFactory
from llm_providers import get_llm_manager
from dotenv import load_dotenv

SETTINGS_FILE = "settings.json"

def load_settings():
    """Indlæser indstillinger fra JSON-fil eller returnerer standardværdier."""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Fejl ved indlæsning af indstillinger: {e}")
    
    # Fallback standardværdier hvis filen ikke findes eller er korrupt
    return {
        "task_sizes": {
            "Lille": {"max_lines": 5, "hours": 5.0, "max_days": 7, "icon": "☕", "desc": "Hurtige ting, rettelser eller små tilføjelser."},
            "Mellem stor": {"max_lines": 10, "hours": 8.0, "max_days": 15, "icon": "🍱", "desc": "Standard opgaver, nye features eller analyser."},
            "Stor": {"max_lines": 15, "hours": 12.0, "max_days": 20, "icon": "🏗️", "desc": "Større projekter, komplekse integrationer eller nye moduler."}
        },
        "defaults": {
            "tovholdere": ["Bruger 1"],
            "afdeling": "Digitalisering",
            "statuser": ["Ikke startet", "I gang", "Venter", "Færdig"],
            "afdelinger": ["Vand", "Natur", "Jord og Grundvand", "Systemer", "Digitalisering"]
        },
        "custom_save_path": ""
    }

def save_settings(settings):
    """Gemmer indstillinger til JSON-fil."""
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"Fejl ved gemning af indstillinger: {e}")
        return False

def update_env_file(updates: Dict[str, str]):
    """Opdaterer .env filen med nye værdier permanent."""
    env_path = ".env"
    lines = []
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except:
            lines = []
    
    # Lav en kopi for at holde styr på hvad der er opdateret
    to_update = updates.copy()
    new_lines = []
    
    # Opdater eksisterende linjer
    for line in lines:
        matched = False
        for key in list(to_update.keys()):
            if line.strip().startswith(f"{key}="):
                new_lines.append(f"{key}={to_update[key]}\n")
                del to_update[key]
                matched = True
                break
        if not matched:
            new_lines.append(line)
            
    # Tilføj nye hvis de ikke fandtes
    for key, value in to_update.items():
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines.append("\n")
        new_lines.append(f"{key}={value}\n")
        
    try:
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        return True
    except Exception as e:
        st.error(f"Kunne ikke gemme til .env: {e}")
        return False

# Opsætning
st.set_page_config(
    page_title="OA - OpgaveAgenten",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for a professional enterprise UI
# Custom CSS for a professional enterprise UI
st.markdown("""
<style>
    /* 1. Global App & Typography */
    .stApp {
        background-color: #FFFFFF !important;
        color: #334155 !important;
        font-family: 'Inter', -apple-system, sans-serif !important;
    }
    
    /* Global text contrast enforcement */
    p, span, label, .stMarkdown, div[data-testid="stMarkdownContainer"] p, .stAlert p {
        color: #334155 !important;
    }

    h1, h2, h3, h4, h5 {
        color: #003E5C !important;
        font-weight: 700 !important;
        margin-bottom: 1rem !important;
        letter-spacing: -0.01em !important;
    }

    /* 2. Containers, Cards & Metrics */
    div[data-testid="stExpander"], .stAlert {
        background-color: #FAFAFA !important;
        border: 1px solid #EDF2F7 !important;
        border-radius: 12px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
    }

    div[data-testid="stMetric"] {
        background-color: #FFFFFF !important;
        border: 1px solid #EDF2F7 !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.02) !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
        padding: 1rem !important;
    }

    div[data-testid="stMetricLabel"] { 
        color: #64748B !important; 
        justify-content: center !important;
    }
    div[data-testid="stMetricValue"] { 
        color: #003E5C !important; 
    }

    /* Streamlit structure for metrics often needs more specificity for alignment */
    div[data-testid="stMetricValue"] > div {
        display: flex !important;
        justify-content: center !important;
    }
    div[data-testid="stMetricLabel"] > div {
        display: flex !important;
        justify-content: center !important;
    }

    /* 3. Navigation & Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #F8FAFC !important;
        border-right: 1px solid #E2E8F0 !important;
    }

    section[data-testid="stSidebar"] .stRadio label {
        color: #1E293B !important;
        font-weight: 500 !important;
    }

    /* 4. Inputs & Forms */
    .stTextInput input, .stTextArea textarea, .stSelectbox [data-baseweb="select"], .stDateInput input, .stNumberInput input {
        background-color: #FFFFFF !important;
        border: 1px solid #D1D5DB !important;
        border-radius: 8px !important;
        color: #1E293B !important;
    }

    .stTextInput label, .stTextArea label, .stSelectbox label, .stDateInput label, .stNumberInput label {
        color: #475569 !important;
        font-weight: 600 !important;
    }

    /* 5. Buttons - Aarhus Blue (Zen Primary) */
    .stButton > button {
        background-color: #003E5C !important;
        color: #FFFFFF !important;
        border-radius: 8px !important;
        padding: 0.6rem 1.25rem !important;
        font-weight: 600 !important;
        border: none !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1) !important;
        transition: all 0.2s ease !important;
    }

    /* Target PRIMARY button text - FORCE WHITE */
    .stButton > button[kind="primary"] p, 
    .stButton > button[kind="primary"] span, 
    .stButton > button[kind="primary"] label,
    .stButton > button[kind="primary"] div {
        color: #FFFFFF !important;
    }

    /* Target SECONDARY button style and text */
    .stButton > button[kind="secondary"] {
        background-color: transparent !important;
        color: #003E5C !important;
        border: 1px solid #003E5C !important;
    }

    .stButton > button[kind="secondary"] p, 
    .stButton > button[kind="secondary"] span, 
    .stButton > button[kind="secondary"] label {
        color: #003E5C !important;
    }

    .stButton > button:hover {
        background-color: #004d73 !important;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.12) !important;
        transform: translateY(-1px);
    }
    
    .stButton > button[kind="secondary"]:hover {
        background-color: #F8FAFC !important;
        color: #004d73 !important;
    }

    /* 6. Special Components (Selection Cards) */
    .selection-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 16px;
        padding: 2rem;
        text-align: center;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        cursor: pointer;
        height: 100%;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }

    .selection-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 20px 25px -5px rgba(0,0,0,0.05);
        border-color: #003E5C;
    }

    .card-icon { font-size: 3rem; margin-bottom: 1rem; }
    .card-title { font-size: 1.25rem; font-weight: 700; color: #003E5C; }
    .card-text { color: #64748B; font-size: 0.95rem; margin-top: 0.5rem; }

    /* 7. File Uploader - Zen Design (CLEAN WHITE) */
    [data-testid="stFileUpload"], .stFileUploader {
        background-color: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 12px !important;
        padding: 30px !important;
    }

    /* Hide the default dotted border from Streamlit if possible */
    [data-testid="stFileUploadDropzone"] {
        border: 2px dashed #003E5C !important;
        background-color: #FFFFFF !important;
        border-radius: 8px !important;
        padding: 2rem !important;
    }
    
    /* Force all text in dropzone to be dark */
    [data-testid="stFileUploadDropzone"] * {
        color: #003E5C !important;
    }

    /* Target Uploader Buttons to be Neutral with DARK TEXT */
    [data-testid="stFileUpload"] button {
        background-color: #003E5C !important;
        color: #FFFFFF !important;
        border: 1px solid #003E5C !important;
        font-weight: 600 !important;
    }

    [data-testid="stFileUpload"] button p, 
    [data-testid="stFileUpload"] button span,
    [data-testid="stFileUpload"] button div {
        color: #FFFFFF !important;
    }

    /* File uploader text - FORCE DARK COLOR */
    [data-testid="stFileUpload"] p, 
    [data-testid="stFileUpload"] span,
    [data-testid="stFileUpload"] label,
    [data-testid="stFileUploadDropzone"] p,
    [data-testid="stFileUploadDropzone"] span,
    [data-testid="stFileUploadDropzone"] small {
        color: #1E293B !important;
        font-weight: 500 !important;
    }
    
    /* Extra specificity for drag and drop text */
    [data-testid="stFileUploadDropzone"] > div,
    [data-testid="stFileUploadDropzone"] > div > div,
    [data-testid="stFileUploadDropzone"] > div > div > span,
    [data-testid="stFileUploadDropzone"] section,
    [data-testid="stFileUploadDropzone"] section span,
    [data-testid="stFileUploadDropzone"] section small {
        color: #1E293B !important;
    }

    /* 8. Guide and Utils */
    .guide-box {
        background-color: #F0F9FF;
        border-radius: 12px;
        padding: 1.5rem;
        border: 1px solid #E0F2FE;
    }

    .guide-step { display: flex; align-items: flex-start; margin-bottom: 0.8rem; }
    .step-number {
        background-color: #003E5C;
        color: white;
        width: 24px;
        height: 24px;
        border-radius: 50%;
        display: flex;
        justify-content: center;
        align-items: center;
        margin-right: 12px;
        font-size: 0.8rem;
        flex-shrink: 0;
        margin-top: 3px;
    }

    .upload-label {
        color: #003E5C;
        font-weight: 700;
        display: flex;
        align-items: center;
        margin-bottom: 0.5rem;
    }

    .upload-label i { margin-right: 8px; }

    /* 9. Danger / Destructive Actions */
    .danger-container .stButton > button {
        background-color: #DC2626 !important;
        color: #FFFFFF !important;
        border: none !important;
    }
    .danger-container .stButton > button:hover {
        background-color: #B91C1C !important;
    }
    .danger-container .stButton > button p, 
    .danger-container .stButton > button span, 
    .danger-container .stButton > button label {
        color: #FFFFFF !important;
    }
</style>
""", unsafe_allow_html=True)

# Session state initialisering
if 'data' not in st.session_state:
    st.session_state.data = {}
if 'tasks' not in st.session_state:
    st.session_state.tasks = []
if 'local_tasks' not in st.session_state:
    st.session_state.local_tasks = []
if 'attachments' not in st.session_state:
    st.session_state.attachments = []
if 'custom_fields' not in st.session_state:
    st.session_state.custom_fields = {}
if 'custom_api_keys' not in st.session_state:
    st.session_state.custom_api_keys = {"google": "", "openai": ""}
if 'settings' not in st.session_state:
    st.session_state.settings = load_settings()
if 'nav_page' not in st.session_state:
    st.session_state.nav_page = "Opgaver"
if 'settings_tab' not in st.session_state:
    st.session_state.settings_tab = "🔑 API & AI"

# Definer opgavestørrelser og deres egenskaber
TASK_SIZES = {
    "Lille": {
        "max_lines": 5,
        "hours": 5,
        "max_days": 7
    },
    "Mellem stor": {
        "max_lines": 10,
        "hours": 8,
        "max_days": 15
    },
    "Stor": {
        "max_lines": 15,
        "hours": 12,
        "max_days": 20
    }
}

def convert_dates(obj):
    """Hjælpefunktion til at konvertere datoer til strenge"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: convert_dates(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_dates(item) for item in obj]
    return obj

def save_task_locally(task_data):
    """Gemmer opgaven lokalt i en JSON-fil"""
    try:
        # Opret en kopi af data for at sikre, at vi ikke ændrer originalen
        task_data_copy = task_data.copy()
        
        # Konverter datoer til strenge
        task_data_copy = convert_dates(task_data_copy)
        
        # Opret en struktureret beskrivelse med underopgaver, hvis de findes
        beskrivelse = task_data_copy.get('Beskrivelse', '')
        if 'underopgaver' in task_data_copy and task_data_copy['underopgaver']:
            beskrivelse += "\n\nUnderopgaver:\n"
            for i, opg in enumerate(task_data_copy['underopgaver'], 1):
                beskrivelse += f"{i}. {opg}\n"
        
        # Opret et struktureret JSON-objekt
        task_json = {
            "Titel": task_data_copy.get('Titel', ''),
            "Afdeling": task_data_copy.get('Afdeling', ''),
            "Beskrivelse": beskrivelse,
            "EstimeretTid": task_data_copy.get('EstimeretTid', ''),
            "Status": task_data_copy.get('Status', 'Igang'),
            "Tovholder": task_data_copy.get('Tovholder', ''),
            "Startdato": task_data_copy.get('Startdato', ''),
            "Slutdato": task_data_copy.get('Forventet afslutning', ''),
            "Opgavestørrelse": task_data_copy.get('Opgavestørrelse', 'Mellem'),
            "Oprettet": datetime.now().isoformat(),
            "Version": "1.4"
        }
        
        # Brug custom mappe hvis sat, ellers brug data-mappen lokalt
        settings = st.session_state.get('settings', load_settings())
        custom_path = settings.get('custom_save_path', '')
        
        if custom_path and os.path.exists(custom_path):
            data_dir = custom_path
        else:
            data_dir = os.path.join(os.getcwd(), 'data')
        
        # Opret data-mappen hvis den ikke findes
        os.makedirs(data_dir, exist_ok=True)
        
        # Generer et unikt filnavn baseret på tidsstempel
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"opgave_{timestamp}.json"
        filepath = os.path.join(data_dir, filename)
        
        # Gem opgaven i en JSON-fil lokalt
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(task_json, f, indent=2, ensure_ascii=False, default=str)
        
        st.success(f"Opgaven er gemt lokalt som {filepath}")
        # Opdater lokal cache hvis den findes
        if 'local_tasks' in st.session_state:
            st.session_state.local_tasks.append(task_json)
        return True
        
    except Exception as e:
        st.error(f"Fejl under lagring af opgave: {str(e)}")
        import traceback
        st.text(traceback.format_exc())
        return False

    # Prøv forskellige SMTP-konfigurationer
    smtp_servers = [
        {'server': SMTP_SERVER, 'port': SMTP_PORT, 'use_tls': True},  # Standard Office 365
        {'server': 'smtp.office365.com', 'port': 587, 'use_tls': True},  # Standard Office 365 alternativ
        {'server': 'smtp.office365.com', 'port': 25, 'use_tls': False},  # Alternativ port uden TLS
        {'server': 'smtp.gmail.com', 'port': 587, 'use_tls': True},  # Gmail SMTP
        {'server': 'smtp.gmail.com', 'port': 465, 'use_ssl': True}  # Gmail med SSL
    ]
    
    for config in smtp_servers:
        try:
            server = None
            st.write(f"\nForsøger at sende via {config['server']}:{config['port']}...")
            
            # Opret forbindelse
            if config.get('use_ssl', False):
                server = smtplib.SMTP_SSL(config['server'], config['port'], timeout=30)
            else:
                server = smtplib.SMTP(config['server'], config['port'], timeout=30)
            
            # Vis forbindelsesoplysninger
            server.set_debuglevel(1)  # Aktiver debug output
            
            # Start TLS hvis nødvendigt
            if config.get('use_tls', False) and not config.get('use_ssl', False):
                server.starttls()
            
            # Log ind
            st.write(f"Logger ind som {SMTP_USERNAME}...")
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            
            # Send besked
            st.write("Afsender besked...")
            server.send_message(msg)
            
            # Hvis vi når hertil, er alt gået godt
            server.quit()
            st.success(f"Opgaven er sendt korrekt via {config['server']}.")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            st.error(f"Login fejlede til {config['server']}. Tjek brugernavn/adgangskode.")
            if server:
                server.quit()
            continue
            
        except smtplib.SMTPException as e:
            st.error(f"SMTP-fejl med {config['server']}: {str(e)}")
            if hasattr(e, 'smtp_error'):
                st.error(f"Server svar: {e.smtp_error.decode()}")
            if server:
                server.quit()
            continue
            
        except socket.error as e:
            st.error(f"Kunne ikke oprette forbindelse til {config['server']}:{config['port']} - {str(e)}")
            if server:
                server.quit()
            continue
            
        except Exception as e:
            st.error(f"Uventet fejl med {config['server']}: {str(e)}")
            import traceback
            st.text(traceback.format_exc())
            if server:
                server.quit()
            continue
    
    # Hvis vi når hertil, har alle servere fejlet
    st.error("Kunne ikke sende e-mail via nogen af de tilgængelige SMTP-servere.")
    st.error("Tjek dine internetindstillinger og kontakt din IT-afdeling for at sikre, at udgående e-mail er tilladt.")
    return False

def get_local_task_files():
    """Henter alle lokale opgave-filer fra den relative data-mappe eller custom mappe"""
    # Brug custom mappe hvis sat, ellers brug data-mappen lokalt
    settings = st.session_state.get('settings', load_settings())
    custom_path = settings.get('custom_save_path', '')
    
    if custom_path and os.path.exists(custom_path):
        data_dir = custom_path
    else:
        data_dir = os.path.join(os.getcwd(), 'data')
    
    tasks = []
    
    if not os.path.exists(data_dir):
        return []
        
    for filename in os.listdir(data_dir):
        if filename.endswith(".json") and filename.startswith("opgave_"):
            try:
                with open(os.path.join(data_dir, filename), 'r', encoding='utf-8') as f:
                    tasks.append(json.load(f))
            except Exception:
                continue
    
    # Sortér efter dato (nyeste først)
    tasks.sort(key=lambda x: x.get('Oprettet', ''), reverse=True)
    return tasks

# Hjælpefunktioner
# Importer de nødvendige handlers direkte
from prompt_handlers import (
    FieldHandlerFactory,
    TitleHandler,
    DescriptionHandler,
    ResponsiblePersonHandler
)

def validate_fields(data: Dict[str, Any]) -> bool:
    """Validerer at alle påkrævede felter er udfyldt."""
    required = ["Titel", "Beskrivelse", "Tovholder"]
    return all(data.get(field) and str(data.get(field)).strip() for field in required)

def extract_task_info(text: str, task_size: str = "Mellem stor", context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Bruger specialiserede prompt handlers til at ekstrahere struktureret 
    opgaveinformation fra tekst. Returnerer et dictionary med udtrukne felter.
    
    Args:
        text: Teksten der skal analyseres
        task_size: Den valgte opgavestørrelse (Lille, Mellem, Stor)
        context: Ekstra kontekst (f.eks. afdelingsliste)
    """
    # Initialiser et tomt dictionary til at gemme de udtrukne data
    extracted_data = {}
    
    try:
        # Opret en ny instans af FieldHandlerFactory
        factory = FieldHandlerFactory()
        
        # Opret/opdater kontekst
        if context is None:
            context = {}
        context["Opgavestørrelse"] = task_size
        
        # Debug: Vis input og kontekst
        print(f"Debug - Input tekst: {text}")
        print(f"Debug - Kontekst: {context}")
        
        # Hent titel
        try:
            title_handler = TitleHandler()
            extracted_data['title'] = title_handler.process(text, context=context)
            print(f"Debug - Genereret titel: {extracted_data['title']}")
        except Exception as e:
            st.error(f"Fejl under generering af titel: {str(e)}")
            extracted_data['title'] = text[:50] + ('...' if len(text) > 50 else '') if text else 'Ny opgave'
        
        # Hent beskrivelse
        try:
            description_handler = DescriptionHandler()
            # Opret en kopi af context for at sikre, at vi ikke ændrer den originale
            description_context = context.copy()
            # Sørg for at bruge den korrekte nøgle for opgavestørrelsen
            if 'Opgavestørrelse' in description_context and description_context['Opgavestørrelse'] == 'Mellem stor':
                description_context['Opgavestørrelse'] = 'Mellem stor'
            elif 'Opgavestørrelse' in description_context and description_context['Opgavestørrelse'] == 'Mellem':
                description_context['Opgavestørrelse'] = 'Mellem stor'  # Omdiriger 'Mellem' til 'Mellem stor'
                
            description_result = description_handler.process(text, description_context)
            if isinstance(description_result, dict) and 'beskrivelse' in description_result:
                extracted_data['description'] = description_result['beskrivelse']
                extracted_data['beskrivelse_data'] = description_result  # Gem hele beskrivelsesdata
            else:
                extracted_data['description'] = str(description_result)
                
            print(f"Debug - Genereret beskrivelse: {extracted_data['description'][:100]}...")
        except Exception as e:
            st.error(f"Fejl under generering af beskrivelse: {str(e)}")
            extracted_data['description'] = text if text else 'Ingen beskrivelse angivet'
            extracted_data['beskrivelse_data'] = {
                'beskrivelse': extracted_data['description'],
                'estimeret_tid': 8,  # Standardværdi
                'max_dage': 15  # Standardværdi
            }
        
        # Hent afdeling
        try:
            department_handler = DepartmentHandler()
            department_result = department_handler.process(text, context=context)
            if isinstance(department_result, dict) and 'afdeling' in department_result:
                extracted_data['afdeling'] = department_result['afdeling']
            else:
                extracted_data['afdeling'] = 'Digitalisering'
            print(f"Debug - Genereret afdeling: {extracted_data['afdeling']}")
        except Exception as e:
            st.error(f"Fejl under afdelingsextrahering: {str(e)}")
            extracted_data['afdeling'] = 'Digitalisering'
        
        # Sæt standard tovholder
        extracted_data['responsible_person'] = 'Bruger 1'
        
        # Definer standardværdier baseret på opgavestørrelse
        size_constraints = {
            "Lille": {"hours": 5, "max_days": 7},
            "Mellem stor": {"hours": 8, "max_days": 15},
            "Stor": {"hours": 12, "max_days": 20}
        }
        
        # Hent tidsestimater baseret på opgavestørrelse
        size_info = size_constraints.get(task_size, size_constraints["Mellem stor"])
        
        # Opret opgave med de udtrukne data
        task_data = {
            "Titel": extracted_data.get('title', '').strip(),
            "Beskrivelse": extracted_data.get('description', '').strip(),
            "Tovholder": extracted_data.get('responsible_person', 'Bruger 1'),
            "Afdeling": extracted_data.get('afdeling', 'Digitalisering'),
            "Startdato": datetime.now().date(),
            "Forventet afslutning": (datetime.now() + timedelta(days=size_info["max_days"])).date(),
            "EstimeretTid": size_info["hours"],
            "Status": "Igang",
            "Opgavestørrelse": task_size
        }
        
        # Debug: Vis det endelige task_data
        print(f"Debug - Færdig task_data: {task_data}")
        
        # Opdater baseret på opgavestørrelse hvis den er kendt
        if 'beskrivelse' in extracted_data and isinstance(extracted_data['beskrivelse'], dict):
            desc_data = extracted_data['beskrivelse']
            if 'estimeret_tid' in desc_data:
                task_data['EstimeretTid'] = desc_data['estimeret_tid']
            if 'max_dage' in desc_data:
                task_data['Forventet afslutning'] = (datetime.now() + timedelta(days=desc_data['max_dage'])).date()
        
        return task_data
        
    except Exception as e:
        st.error(f"Fejl under ekstrahering af opgaveinformation: {str(e)}")
        
        # Opret et nyt task_data dictionary med standardværdier
        task_data = {
            "Titel": text[:50] + ('...' if len(text) > 50 else '') if text and len(text.strip()) > 10 else 'Ny opgave',
            "Beskrivelse": text if text and len(text.strip()) > 10 else '',
            "Tovholder": "",
            "Afdeling": "Digitalisering",
            "Startdato": datetime.now().date(),
            "Forventet afslutning": (datetime.now() + timedelta(days=15)).date(),
            "EstimeretTid": 8,
            "Status": "Igang",
            "Opgavestørrelse": task_size if task_size in ["Lille", "Mellem stor", "Stor"] else "Mellem stor"
        }
        
        return task_data

    st.error("Kunne ikke sende e-mail via nogen af de tilgængelige SMTP-servere.")
    st.error("Tjek dine internetindstillinger og kontakt din IT-afdeling for at sikre, at udgående e-mail er tilladt.")
    return False

def create_task(data: Dict[str, Any], attachments: List[Any] = None) -> tuple[bool, Dict[str, Any]]:
    """Opretter og gemmer en ny opgave lokalt. Returnerer (success, task_data)"""
    try:
        # Opret en kopi af data for at undgå at ændre den originale
        task_data = data.copy()
        
        # Fjern eventuelle midlertidige felter før afsendelse
        task_data.pop('underopgaver', None)
        
        # Gem opgaven lokalt
        if save_task_locally(task_data):
            return True, task_data
        else:
            return False, {}
            
    except Exception as e:
        st.error(f"Fejl ved oprettelse af opgave: {str(e)}")
        return False, {}

def test_llm_connections():
    """
    Tester forbindelsen til alle konfigurerede LLM providers.
    Returnerer status for alle providers.
    """
    llm_manager = get_llm_manager()

    # Vis status-oversigt
    status_summary = llm_manager.get_status_summary()

    # Test alle providers
    test_results = llm_manager.test_all_providers()

    # Tjek om mindst én provider virker
    any_working = any(test_results.values())

    return any_working, status_summary, test_results

# Sidebjælke med navigation
st.sidebar.title("🤖 OA - OpgaveAgenten")
st.sidebar.write("Din intelligente opgave-makker")

pages = ["Opgaver", "Opret opgave", "Test LLM-forbindelser", "Indstillinger"]
# Sikr at nav_page er i pages
if st.session_state.get('nav_page') not in pages:
    st.session_state.nav_page = "Opgaver"

# Brug session state til at styre hvilken side der vises
# Radio uden key så vi kan styre den programmatisk via index
selected_page = st.sidebar.radio(
    "Menu",
    pages,
    index=pages.index(st.session_state.nav_page)
)

# Opdater nav_page hvis bruger vælger en anden side via radio
if selected_page != st.session_state.nav_page:
    st.session_state.nav_page = selected_page
    st.rerun()

page = st.session_state.nav_page

# Side: Opgaver
if page == "Opgaver":
    # Header med logo
    col_title, col_logo = st.columns([3, 1])
    with col_title:
        st.title("📊 OA Dashboard")
        st.write("Få overblik over dine igangværende opgaver.")
    with col_logo:
        logo_path = os.path.join(os.path.dirname(__file__), "images", "mtm-logo.png")
        if os.path.exists(logo_path):
            st.image(logo_path, width=150)
        else:
            st.write("")  # Tom placeholder hvis logo ikke findes
    
    with st.spinner("Indlæser statistik..."):
        local_tasks = get_local_task_files()
        st.session_state.local_tasks = local_tasks
        
        if not local_tasks:
            st.info("Ingen lokale opgaver fundet endnu. Opret din første opgave for at se statistik her!")
        else:
            # Overordnede tal
            col1, col2, col3, col4 = st.columns(4)
            
            total_tasks = len(local_tasks)
            sizes = [t.get('Opgavestørrelse', 'Ukendt') for t in local_tasks]
            depts = [t.get('Afdeling', 'Digitalisering') for t in local_tasks]
            
            with col1:
                st.metric("Total antal opgaver", total_tasks)
            with col2:
                # Beregn antal pr. størrelse (simple tælning)
                mellem = sizes.count('Mellem stor') + sizes.count('Mellem')
                st.metric("Mellem stor", mellem)
            with col3:
                stor = sizes.count('Stor')
                st.metric("Store opgaver", stor)
            with col4:
                lille = sizes.count('Lille')
                st.metric("Små opgaver", lille)
                
            st.divider()
            
            # To kolonner til detaljer
            d_col1, d_col2 = st.columns([2, 1])
            
            with d_col1:
                st.subheader("Seneste oprettede opgaver")
                search_dash = st.text_input("Søg i dine opgaver...", placeholder="Søg på titel eller afdeling", key="dash_search")
                
                filtered_dash = local_tasks
                if search_dash:
                    search_dash = search_dash.lower()
                    filtered_dash = [t for t in local_tasks if search_dash in t.get('Titel', '').lower() or search_dash in t.get('Afdeling', '').lower()]
                
                for i, task in enumerate(filtered_dash[:10]): # Vis kun de 10 nyeste eller søgeresultater
                    with st.expander(f"{task.get('Titel', 'Uden titel')} - {task.get('Afdeling', 'Ingen afdeling')}"):
                        st.write(f"**Oprettet:** {task.get('Oprettet', 'Ukendt')[:16].replace('T', ' ')}")
                        st.write(f"**Størrelse:** {task.get('Opgavestørrelse', 'Ukendt')}")
                        st.write(f"**Estimeret tid:** {task.get('EstimeretTid', 0)} timer")
                        st.write(f"**Tovholder:** {task.get('Tovholder', 'Ikke angivet')}")
                        st.markdown(f"**Beskrivelse:**\n{task.get('Beskrivelse', '')}")
            
            with d_col2:
                st.subheader("Top Afdelinger")
                # Enkel statistik over afdelinger
                dept_counts = {}
                for d in depts:
                    dept_counts[d] = dept_counts.get(d, 0) + 1
                
                # Sortér og vis
                sorted_depts = sorted(dept_counts.items(), key=lambda x: x[1], reverse=True)
                for dept, count in sorted_depts:
                    st.write(f"- **{dept}:** {count} opgaver")
                
                st.divider()
                st.subheader("Hurtig handling")
                if st.button("➕ Opret ny opgave", key="quick_new_task", use_container_width=True):
                    st.session_state.nav_page = "Opret opgave"
                    st.rerun()

                if st.button("📏 Konfigurer størrelser", key="quick_config_sizes", use_container_width=True):
                    st.session_state.nav_page = "Indstillinger"
                    st.session_state.settings_tab = "📏 Opgavestørrelser"
                    st.rerun()

                if st.button("📝 Ret standardværdier", key="quick_edit_defaults", use_container_width=True):
                    st.session_state.nav_page = "Indstillinger"
                    st.session_state.settings_tab = "📝 Standardværdier"
                    st.rerun()

# Side: Opret opgave
elif page == "Opret opgave":
    st.title("📝 Opret ny opgave")
    
    # Fase 1: Vælg opgavestørrelse
    if 'task_size' not in st.session_state:
        st.header("1. Hvor stor er opgaven?")
        st.write("Vælg den størrelse, der passer bedst til dit behov:")
        
        col1, col2, col3 = st.columns(3)
        
        # Hent indstillinger fra session state
        settings = st.session_state.settings
        
        for i, (size, info) in enumerate(settings["task_sizes"].items()):
            size_info = info
            with [col1, col2, col3][i]:
                # Vi bruger en kombination af markdown til looket og en skjult knap til funktionalitet
                st.markdown(f"""
                <div class="selection-card">
                    <div>
                        <div class="card-icon">{info['icon']}</div>
                        <div class="card-title">{size}</div>
                        <div class="card-text">
                            {info['desc']}<br><br>
                            <b>⏱️ Estimeret:</b> {size_info['hours']} timer<br>
                            <b>📅 Maks tid:</b> {size_info['max_days']} dage
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Knappen placeres lige under kortet
                if st.button(f"Vælg {size}", key=f"btn_{size}", use_container_width=True, type="primary"):
                    st.session_state.task_size = size
                    st.session_state.step = "input"
                    st.rerun()
    
    # Fase 2: Indtast oplysninger og generer opgave
    elif 'task_size' in st.session_state and st.session_state.get('step') == "input":
        # To kolonner for bedre layout
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.header(f"2. Indtast oplysninger")
            st.write(f"Du er ved at oprette en **{st.session_state.task_size.lower()}** opgave.")
            
            tekst = st.text_area("Hvad skal opgaven handle om?", height=250, 
                                placeholder="Indsæt e-mail korrespondance, mødereferat eller din egen beskrivelse her...", 
                                key="input_text")
            
            # Filupload
            uploaded_files = st.file_uploader(
                "📁 Vedhæft relevante bilag (valgfrit) - Træk og slip filer her eller klik for at gennemsøge", 
                accept_multiple_files=True, 
                type=['pdf', 'docx', 'xlsx', 'jpg', 'png', 'jpeg'],
                help="Understøtter PDF, Word, Excel og billeder"
            )
            
            if uploaded_files:
                st.session_state.attachments = uploaded_files
                cols = st.columns(2)
                for i, file in enumerate(uploaded_files):
                    with cols[i % 2]:
                        st.markdown(f"""
                        <div style="background-color: #FFFFFF; padding: 10px; border-radius: 8px; margin-bottom: 8px; border: 1px solid #E5E7EB; border-left: 4px solid #BEE3F8; font-size: 0.85rem; box-shadow: 0 2px 4px rgba(0,0,0,0.02);">
                            <span style="color: #003E5C; font-weight: 600;">📎 {file.name}</span> <br>
                            <span style="color: #9CA3AF; font-size: 0.75rem;">Størrelse: {file.size / 1024:.1f} KB</span>
                        </div>
                        """, unsafe_allow_html=True)
            
            st.divider()
            
            # Knapper i bunden
            b_col1, b_col2 = st.columns([1, 2])
            with b_col1:
                if st.button("← Tilbage", use_container_width=True):
                    del st.session_state.task_size
                    if 'data' in st.session_state:
                        del st.session_state.data
                    st.rerun()
            with b_col2:
                if st.button("🔍 Analyser og generer opgaveforslag", type="primary", use_container_width=True):
                    if not tekst.strip():
                        st.warning("Indtast venligst en tekst at analysere")
                    else:
                        with st.spinner("AI analyserer din tekst..."):
                            try:
                                settings = st.session_state.settings
                                context = {
                                    "Opgavestørrelse": st.session_state.task_size,
                                    "afdelinger_liste": "\n".join([f"- {d}" for d in settings["defaults"]["afdelinger"]])
                                }
                                result = extract_task_info(tekst, task_size=st.session_state.task_size, context=context)
                                result["Opgavestørrelse"] = st.session_state.task_size
                                st.session_state.data = result
                                st.session_state.step = "preview"
                                st.rerun()
                            except Exception as e:
                                st.error(f"Fejl ved generering af opgave: {str(e)}")
        
        # Højre kolonne med vejledning
        with col2:
            st.markdown(f"""
            <div class="guide-box">
                <h4>🚀 Sådan gør du</h4>
                <p>For at få det skarpeste resultat, anbefaler vi at følge disse trin:</p>
                <div class="guide-step">
                    <div class="step-number">1</div>
                    <div><b>Indsæt kildetekst:</b> Kopier en hel mail-tråd eller projektbeskrivelse ind i feltet. Jo mere kontekst, jo bedre forstår AI'en opgaven.</div>
                </div>
                <div class="guide-step">
                    <div class="step-number">2</div>
                    <div><b>Tilføj filer:</b> Har du specifikationsdokumenter eller billeder? Vedhæft dem som ekstra reference.</div>
                </div>
                <div class="guide-step">
                    <div class="step-number">3</div>
                    <div><b>Kør analysen:</b> Klik på knappen for at lade AI'en udtrække titler, ansvarlige og oprette forslag til underopgaver.</div>
                </div>
                <p style="font-size: 0.85rem; margin-top: 1rem; font-style: italic;">
                    💡 <b>Tip:</b> Du kan altid rette i detaljerne på næste side, før opgaven gemmes endeligt.
                </p>
            </div>
            """, unsafe_allow_html=True)
    
    # Fase 3: Forhåndsvisning og redigering
    elif 'data' in st.session_state and st.session_state.get('step') == "preview":
        data = st.session_state.data
        
        # Header område
        col_h1, col_h2 = st.columns([3, 1])
        with col_h1:
            st.header("3. Gennemse og færdiggør")
            st.write("Her er AI'ens forslag til opgaven. Du kan rette i alt inden du gemmer.")
        with col_h2:
             if st.button("← Tilbage", use_container_width=True):
                st.session_state.step = "input"
                st.rerun()
                
        st.divider()
        
        # To kolonner for redigering
        col1, col2 = st.columns([2, 1])
        
        settings = st.session_state.settings
        
        with col1:
            st.subheader("Opgave detaljer")
            
            data["Titel"] = st.text_input("Titel*", value=data.get("Titel", ""), 
                                        help="Hvad skal opgaven hedde?")
            
            data["Beskrivelse"] = st.text_area("Beskrivelse*", 
                                           value=data.get("Beskrivelse", ""),
                                           height=250,
                                           help="Uddybende forklaring af opgaven")
            
            # Underopgaver hvis de findes
            if data.get("underopgaver"):
                with st.expander("Underopgaver (forslag)", expanded=False):
                    for i, opgave in enumerate(data["underopgaver"], 1):
                        st.markdown(f"**{i}.** {opgave}")
                    st.caption("Underopgaver bliver gemt som en del af beskrivelsen.")

            st.divider()
            st.subheader("Ansvar og Tid")
            
            c1, c2 = st.columns(2)
            with c1:
                tovholdere = settings["defaults"].get("tovholdere", [])
                current_tov = data.get("Tovholder") or settings["defaults"].get("selected_tovholder", settings["defaults"].get("tovholder", ""))
                
                # Sikr at den nuværende værdi findes i listen, ellers tilføj den midlertidigt
                tov_options = list(tovholdere)
                if current_tov and current_tov not in tov_options:
                    tov_options.insert(0, current_tov)
                
                data["Tovholder"] = st.selectbox("Tovholder*", options=tov_options, 
                                              index=tov_options.index(current_tov) if current_tov in tov_options else 0,
                                              key="tovholder_select")
                
                today = datetime.today().date()
                start_val = data.get("Startdato", today)
                if isinstance(start_val, str):
                    try: start_val = datetime.strptime(start_val, '%Y-%m-%d').date()
                    except: start_val = today
                
                data["Startdato"] = st.date_input("Startdato*", value=start_val, min_value=today)
                
            with c2:
                departments = settings["defaults"].get("afdelinger", [])
                current_dept = data.get("Afdeling") or settings["defaults"].get("afdeling", "")
                
                dept_options = list(departments)
                if current_dept and current_dept not in dept_options:
                    dept_options.insert(0, current_dept)

                data["Afdeling"] = st.selectbox("Afdeling", options=dept_options,
                                              index=dept_options.index(current_dept) if current_dept in dept_options else 0,
                                              key="dept_select")
                
                # Slutdato håndtering
                size_info = settings["task_sizes"].get(st.session_state.task_size, settings["task_sizes"]["Mellem stor"])
                slut_val = data.get("Slutdato") or data.get("Forventet afslutning") or (today + timedelta(days=size_info['max_days']))
                if isinstance(slut_val, str):
                    try: slut_val = datetime.strptime(slut_val, '%Y-%m-%d').date()
                    except: slut_val = today + timedelta(days=size_info['max_days'])
                
                data["Slutdato"] = st.date_input("Forventet Slutdato*", value=slut_val, min_value=start_val)

            data["EstimeretTid"] = st.number_input("Estimeret tid (timer)*", 
                                                min_value=0.5, value=float(data.get("EstimeretTid", size_info["hours"])), step=0.5)

            status_options = settings["defaults"]["statuser"]
            current_status = data.get("Opgavestatus") or data.get("Status", "I gang")
            if current_status not in status_options: current_status = status_options[0] if status_options else "I gang"
            
            data["Opgavestatus"] = st.selectbox("Status", status_options, index=status_options.index(current_status))

        with col2:
            # Info om opgavestørrelsen valgt i trin 1
            st.markdown(f"""
            <div class="guide-box">
                <h4>{size_info.get('icon', '📊')} Opgavetype: {st.session_state.task_size}</h4>
                <p>Baseret på dit valg i trin 1, har vi sat følgende rammer:</p>
                <ul style="font-size: 0.9rem; margin-top: 10px;">
                    <li><b>Max tid:</b> {size_info['hours']} timer</li>
                    <li><b>Tidsramme:</b> {size_info['max_days']} dage</li>
                </ul>
                <p style="font-size: 0.85rem; font-style: italic; margin-top: 15px;">
                    💡 Du kan altid overskride disse rammer i felterne til venstre hvis nødvendigt.
                </p>
            </div>
            """, unsafe_allow_html=True)
        
        st.write("")
        
        if not validate_fields(data):
            st.warning("⚠️ Husk at udfylde de påkrævede felter (*)")
        
        if st.button("🚀 Opret opgave nu", type="primary", use_container_width=True):
            if validate_fields(data):
                with st.spinner("Gemmer opgaven..."):
                    success, task_data = create_task(data, st.session_state.attachments)
                    if success:
                        # Vis moderne success besked med opgavedetaljer
                        st.markdown("""
                        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                    padding: 2rem; 
                                    border-radius: 15px; 
                                    color: white; 
                                    box-shadow: 0 10px 25px rgba(0,0,0,0.2);
                                    margin: 1rem 0;">
                            <h2 style="margin: 0 0 1rem 0; color: white;">✅ Opgave oprettet!</h2>
                            <p style="font-size: 1.1rem; margin: 0; opacity: 0.95;">Din opgave er nu gemt og klar til brug.</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Vis opgavedetaljer i et pænt kort
                        st.markdown("### 📋 Opgavedetaljer")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown(f"""
                            <div style="background-color: #f8f9fa; padding: 1.5rem; border-radius: 10px; border-left: 4px solid #667eea; margin-bottom: 1rem;">
                                <p style="margin: 0; color: #6c757d; font-size: 0.85rem; font-weight: 600;">TITEL</p>
                                <p style="margin: 0.5rem 0 0 0; color: #212529; font-size: 1.1rem; font-weight: 500;">{task_data.get('Titel', 'N/A')}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            st.markdown(f"""
                            <div style="background-color: #f8f9fa; padding: 1.5rem; border-radius: 10px; border-left: 4px solid #28a745; margin-bottom: 1rem;">
                                <p style="margin: 0; color: #6c757d; font-size: 0.85rem; font-weight: 600;">TOVHOLDER</p>
                                <p style="margin: 0.5rem 0 0 0; color: #212529; font-size: 1.1rem; font-weight: 500;">👤 {task_data.get('Tovholder', 'N/A')}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            st.markdown(f"""
                            <div style="background-color: #f8f9fa; padding: 1.5rem; border-radius: 10px; border-left: 4px solid #ffc107; margin-bottom: 1rem;">
                                <p style="margin: 0; color: #6c757d; font-size: 0.85rem; font-weight: 600;">ESTIMERET TID</p>
                                <p style="margin: 0.5rem 0 0 0; color: #212529; font-size: 1.1rem; font-weight: 500;">⏱️ {task_data.get('EstimeretTid', 'N/A')} timer</p>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with col2:
                            st.markdown(f"""
                            <div style="background-color: #f8f9fa; padding: 1.5rem; border-radius: 10px; border-left: 4px solid #17a2b8; margin-bottom: 1rem;">
                                <p style="margin: 0; color: #6c757d; font-size: 0.85rem; font-weight: 600;">AFDELING</p>
                                <p style="margin: 0.5rem 0 0 0; color: #212529; font-size: 1.1rem; font-weight: 500;">🏢 {task_data.get('Afdeling', 'N/A')}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            st.markdown(f"""
                            <div style="background-color: #f8f9fa; padding: 1.5rem; border-radius: 10px; border-left: 4px solid #dc3545; margin-bottom: 1rem;">
                                <p style="margin: 0; color: #6c757d; font-size: 0.85rem; font-weight: 600;">STATUS</p>
                                <p style="margin: 0.5rem 0 0 0; color: #212529; font-size: 1.1rem; font-weight: 500;">🚦 {task_data.get('Opgavestatus', task_data.get('Status', 'N/A'))}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            st.markdown(f"""
                            <div style="background-color: #f8f9fa; padding: 1.5rem; border-radius: 10px; border-left: 4px solid #6610f2; margin-bottom: 1rem;">
                                <p style="margin: 0; color: #6c757d; font-size: 0.85rem; font-weight: 600;">OPGAVESTØRRELSE</p>
                                <p style="margin: 0.5rem 0 0 0; color: #212529; font-size: 1.1rem; font-weight: 500;">📊 {task_data.get('Opgavestørrelse', 'N/A')}</p>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        # Vis datoer
                        st.markdown("### 📅 Tidsplan")
                        date_col1, date_col2 = st.columns(2)
                        with date_col1:
                            st.info(f"**Startdato:** {task_data.get('Startdato', 'N/A')}")
                        with date_col2:
                            st.info(f"**Slutdato:** {task_data.get('Slutdato', task_data.get('Forventet afslutning', 'N/A'))}")
                        
                        st.divider()
                        
                        # Handlingsknapper
                        action_col1, action_col2, action_col3 = st.columns(3)
                        with action_col1:
                            if st.button("📊 Gå til Dashboard", type="primary", use_container_width=True, key="goto_dashboard"):
                                for key in ['data', 'task_size', 'step', 'attachments']:
                                    if key in st.session_state: del st.session_state[key]
                                st.session_state.nav_page = "Opgaver"
                                st.rerun()
                        with action_col2:
                            if st.button("➕ Opret ny opgave", use_container_width=True, key="create_new_task"):
                                for key in ['data', 'task_size', 'step', 'attachments']:
                                    if key in st.session_state: del st.session_state[key]
                                st.rerun()
                        with action_col3:
                            if st.button("⚙️ Indstillinger", use_container_width=True, key="goto_settings"):
                                for key in ['data', 'task_size', 'step', 'attachments']:
                                    if key in st.session_state: del st.session_state[key]
                                st.session_state.nav_page = "Indstillinger"
                                st.rerun()
            else:
                st.error("Udfyld venligst Titel, Beskrivelse og Tovholder.")

        if st.button("🗑️ Nulstil alt", use_container_width=True):
            for key in ['data', 'task_size', 'step', 'attachments']:
                if key in st.session_state: del st.session_state[key]
            st.rerun()

# Side: Test LLM-forbindelser
elif page == "Test LLM-forbindelser":
    st.title("🔌 AI Forbindelsestest")
    
    st.markdown("""
    Denne side hjælper dig med at verificere, at systemet har korrekt adgang til AI-modellerne. 
    Vi tester både om dine **API-nøgler** er indtastet, og om de faktisk kan skabe forbindelse.
    """)

    col_btn, _ = st.columns([1, 2])
    with col_btn:
        run_test = st.button("Kør komplet systemtest", type="primary", use_container_width=True)

    if run_test:
        with st.status("Analyserer AI-forbindelser...", expanded=True) as status:
            any_working, status_summary, test_results = test_llm_connections()
            
            st.write("---")
            for provider_name, is_working in test_results.items():
                llm_manager = get_llm_manager()
                provider = llm_manager.providers.get(provider_name)
                if not provider: continue
                
                # Bestem status og ikon
                if is_working:
                    icon = "✅"
                    label = "Aktiv / Forbundet"
                    msg = f"Forbindelse til {provider.get_name()} er etableret korrekt."
                    color_box = "success"
                elif not provider.is_available():
                    icon = "⚠️"
                    label = "Mangler Konfiguration"
                    msg = f"Ingen API-nøgle fundet for {provider.get_name()}."
                    color_box = "warning"
                else:
                    icon = "❌"
                    label = "Forbindelsesfejl"
                    msg = f"Kunne ikke oprette forbindelse til {provider.get_name()} (tjek din API-nøgle)."
                    color_box = "error"

                # Vis i en container
                with st.container():
                    c1, c2 = st.columns([1, 4])
                    with c1:
                        st.markdown(f"### {icon}")
                    with c2:
                        st.markdown(f"**{provider.get_name()}**")
                        st.caption(f"Status: {label} | Model: {provider.model_name}")
                        
                        if color_box == "success": st.success(msg)
                        elif color_box == "warning": st.warning(msg)
                        else: st.error(msg)
            
            status.update(label="Test fuldført!", state="complete", expanded=False)

        # Samlet konklusion
        st.divider()
        if any_working:
            st.balloons()
            st.success("### ✅ Systemet er klar!")
            st.markdown("""
            Mindst én AI-model er korrekt konfigureret og klar til brug. 
            Du kan nu gå til **Opret opgave** og begynde at bruge generatoren.
            """)
        else:
            st.error("### ❌ Ingen aktive forbindelser")
            st.markdown("""
            Systemet kan ikke få kontakt til nogen AI-modeller. 
            Gå venligst til **Indstillinger** og tjek at dine API-nøgler er korrekte.
            """)
            with st.expander("Se tekniske detaljer"):
                st.code(status_summary)

# Side: Indstillinger
elif page == "Indstillinger":
    st.title("⚙️ Indstillinger")
    
    # Vi bruger en radio-baseret tab-løsning for at kunne styre den programmatisk
    tabs = ["🔑 API & AI", "📏 Opgavestørrelser", "📝 Standardværdier", "📂 Gem-mappe"]
    # Tjek om vi er kommet fra dashboardet med et ønske om en specifik tab
    current_tab = st.session_state.get('settings_tab', tabs[0])
    if current_tab not in tabs: current_tab = tabs[0]
    
    active_tab = st.radio("Vælg område", tabs, index=tabs.index(current_tab), horizontal=True, label_visibility="collapsed")
    # Opdater session state så vi husker valget (men også så dashboard-links virker)
    st.session_state.settings_tab = active_tab
    
    st.write("") # Margin
    
    if active_tab == "🔑 API & AI":
        st.subheader("API-indstillinger")
        st.info("Her kan du overskrive de system-definerede API-nøgler for denne session.")
        
        col_api1, col_api2 = st.columns(2)
        with col_api1:
            custom_google = st.text_input("Custom Google Gemini API Key", 
                                        value=st.session_state.custom_api_keys["google"],
                                        type="password")
        with col_api2:
            custom_openai = st.text_input("Custom OpenAI API Key", 
                                        value=st.session_state.custom_api_keys["openai"],
                                        type="password")
            
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("Anvend (kun denne session)", type="secondary", use_container_width=True):
                st.session_state.custom_api_keys["google"] = custom_google
                st.session_state.custom_api_keys["openai"] = custom_openai
                llm_manager = get_llm_manager()
                llm_manager.update_api_keys(
                    google_key=custom_google if custom_google else None,
                    openai_key=custom_openai if custom_openai else None
                )
                st.success("API-nøgler anvendt i hukommelsen!")
                st.rerun()
        
        with col_btn2:
            if st.button("💾 Gem permanent", type="primary", use_container_width=True):
                # Opdater filen
                success = update_env_file({
                    "GOOGLE_API_KEY": custom_google,
                    "OPENAI_API_KEY": custom_openai
                })
                
                if success:
                    # Opdater også den nuværende session
                    st.session_state.custom_api_keys["google"] = custom_google
                    st.session_state.custom_api_keys["openai"] = custom_openai
                    llm_manager = get_llm_manager()
                    llm_manager.update_api_keys(
                        google_key=custom_google if custom_google else None,
                        openai_key=custom_openai if custom_openai else None
                    )
                    st.success("✅ API-nøgler gemt permanent i .env filen!")
                    st.rerun()

    elif active_tab == "📏 Opgavestørrelser":
        st.subheader("Konfigurer Opgavestørrelser")
        st.write("Her kan du definere rammerne for de tre opgavetyper.")
        
        settings = st.session_state.settings
        
        for size in ["Lille", "Mellem stor", "Stor"]:
            with st.expander(f"Indstillinger for: {size}", expanded=(size=="Lille")):
                c1, c2, c3 = st.columns([1,1,2])
                with c1:
                    settings["task_sizes"][size]["hours"] = st.number_input(f"Timer ({size})", 
                                                                        value=float(settings["task_sizes"][size]["hours"]), 
                                                                        step=0.5, key=f"h_{size}")
                with c2:
                    settings["task_sizes"][size]["max_days"] = st.number_input(f"Max dage ({size})", 
                                                                            value=int(settings["task_sizes"][size]["max_days"]), 
                                                                            step=1, key=f"d_{size}")
                with c3:
                    settings["task_sizes"][size]["icon"] = st.text_input(f"Ikon ({size})", 
                                                                      value=settings["task_sizes"][size]["icon"], 
                                                                      key=f"i_{size}")
                
                settings["task_sizes"][size]["desc"] = st.text_area(f"Beskrivelse ({size})", 
                                                                 value=settings["task_sizes"][size]["desc"], 
                                                                 key=f"desc_{size}", height=80)
        
        if st.button("Gem opgaveindstillinger", type="primary"):
            if save_settings(settings):
                st.session_state.settings = settings
                st.success("Opgaveindstillinger gemt!")
                st.rerun()

    elif active_tab == "📝 Standardværdier":
        st.subheader("Standardværdier for nye opgaver")
        st.write("Disse værdier vil automatisk blive foreslået i trin 3.")
        
        settings = st.session_state.settings
        
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.write("#### 👥 Tovholdere")
            tov_str = st.text_area("Liste over tovholdere (kommasepareret)", 
                                 value=", ".join(settings["defaults"].get("tovholdere", [settings["defaults"].get("tovholder", "Bruger 1")])), 
                                 help="Adskil navne med komma")
            settings["defaults"]["tovholdere"] = [t.strip() for t in tov_str.split(",") if t.strip()]
            
        with col_d2:
            st.write("#### 🏢 Afdelinger")
            dept_str = st.text_area("Liste over afdelinger (kommasepareret)", 
                                   value=", ".join(settings["defaults"]["afdelinger"]), 
                                   help="Adskil med komma")
            settings["defaults"]["afdelinger"] = [d.strip() for d in dept_str.split(",") if d.strip()]
            
        st.divider()
        st.write("#### 🚦 Statuser")
        status_str = st.text_area("Mulige statuser (kommasepareret)", value=", ".join(settings["defaults"]["statuser"]), 
                                 help="Adskil med komma")
        settings["defaults"]["statuser"] = [s.strip() for s in status_str.split(",") if s.strip()]
        
        st.write("#### 📍 Standardvalg")
        c1, c2 = st.columns(2)
        with c1:
            # Sikr at vi har en liste at vælge fra
            tov_list = settings["defaults"]["tovholdere"]
            settings["defaults"]["selected_tovholder"] = st.selectbox("Standard Tovholder", options=tov_list, 
                                                                    index=0 if tov_list else None)
        with c2:
            dept_list = settings["defaults"]["afdelinger"]
            settings["defaults"]["afdeling"] = st.selectbox("Standard Afdeling", options=dept_list,
                                                          index=dept_list.index(settings["defaults"]["afdeling"]) if settings["defaults"]["afdeling"] in dept_list else 0)
        
        if st.button("Gem standardværdier", type="primary"):
            if save_settings(settings):
                st.session_state.settings = settings
                st.success("Standardværdier gemt!")
                st.rerun()

        st.divider()
        st.subheader("🛠️ Avancerede indstillinger")

        # Brugerdefinerede felter (legacy) rykket op
        with st.expander("Brugerdefinerede felter (legacy)", expanded=False):
            st.write("Tilføj standardfelter, der skal være tilgængelige i alle nye opgaver:")
            new_field = st.text_input("Nyt feltnavn")
            if st.button("Tilføj felt"):
                if new_field and new_field not in st.session_state.custom_fields:
                    st.session_state.custom_fields[new_field] = ""
                    st.rerun()
            
            if st.session_state.custom_fields:
                st.write("**Eksisterende brugerdefinerede felter:**")
                for field in list(st.session_state.custom_fields.keys()):
                    col1, col2 = st.columns([4, 1])
                    with col1: st.code(field)
                    with col2:
                        if st.button("🗑️", key=f"del_custom_{field}"):
                            del st.session_state.custom_fields[field]
                            st.rerun()

        st.write("") # Margin
        
        # Nulstil placeret som det sidste element
        st.warning("⚠️ **Farezone:** Knappen herunder nulstiller alle dine midlertidige data og indstillinger i denne session.")
        if st.button("🔄 Nulstil alt data nu", type="primary", use_container_width=True, help="Rydder alt midlertidigt data"):
            st.session_state.data = {}
            st.session_state.attachments = []
            st.session_state.custom_fields = {}
            st.rerun()

    elif active_tab == "📂 Gem-mappe":
        st.subheader("Vælg mappe til at gemme opgaver")
        st.write("Her kan du vælge en brugerdefineret mappe hvor dine opgaver skal gemmes.")
        
        settings = st.session_state.settings
        
        st.info("💡 **Tip:** Vælg en mappe i din OneDrive for at kunne oprette automatiseringer med Power Automate.")
        
        current_path = settings.get("custom_save_path", "")
        
        st.write("#### 📁 Nuværende indstilling")
        if current_path:
            st.success(f"Opgaver gemmes i: `{current_path}`")
        else:
            st.info("Opgaver gemmes i standard-mappen: `data/` i applikationens rodmappe")
        
        st.write("#### 🔧 Konfigurer ny mappe")
        st.markdown("""
        Indtast den fulde sti til den mappe hvor du vil gemme opgaver.
        
        **Eksempler:**
        - `C:\\Users\\DitNavn\\OneDrive\\Opgaver`
        - `C:\\Users\\DitNavn\\Documents\\MinOpgaver`
        - `D:\\Projekter\\Opgaver`
        """)
        
        new_path = st.text_input(
            "Sti til gem-mappe", 
            value=current_path,
            placeholder="C:\\Users\\DitNavn\\OneDrive\\Opgaver",
            help="Indtast den fulde sti til mappen hvor opgaver skal gemmes"
        )
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("✅ Gem indstilling", type="primary", use_container_width=True):
                if new_path:
                    if os.path.exists(new_path):
                        settings["custom_save_path"] = new_path
                        if save_settings(settings):
                            st.session_state.settings = settings
                            st.success(f"✅ Gem-mappe opdateret til: `{new_path}`")
                            st.rerun()
                    else:
                        try:
                            os.makedirs(new_path, exist_ok=True)
                            settings["custom_save_path"] = new_path
                            if save_settings(settings):
                                st.session_state.settings = settings
                                st.success(f"✅ Mappe oprettet og gemt: `{new_path}`")
                                st.rerun()
                        except Exception as e:
                            st.error(f"❌ Kunne ikke oprette mappen: {str(e)}")
                else:
                    settings["custom_save_path"] = ""
                    if save_settings(settings):
                        st.session_state.settings = settings
                        st.success("✅ Nulstillet til standard-mappe")
                        st.rerun()
        
        with col2:
            if st.button("🔄 Nulstil til standard", use_container_width=True):
                settings["custom_save_path"] = ""
                if save_settings(settings):
                    st.session_state.settings = settings
                    st.success("✅ Nulstillet til standard-mappe")
                    st.rerun()
        
        st.divider()
        st.write("#### 🔄 Power Automate Integration - Trin-for-trin vejledning")
        
        with st.expander("📖 Komplet vejledning til automatisk SharePoint integration", expanded=False):
            st.markdown("""
            ### 🎯 Hvad opnår du?
            Med denne automatisering vil hver ny opgave automatisk blive:
            - ✅ Oprettet som et element i dit SharePoint Dashboard
            - ✅ Alle felter udfyldes automatisk fra opgave-filen
            - ✅ Klar til at blive administreret og sporet i SharePoint
            
            ---
            
            ### 📋 Trin 1: Forbered din OneDrive mappe
            
            1. **Opret en mappe i OneDrive:**
               - Åbn OneDrive (via Stifinder eller browser)
               - Opret en ny mappe, f.eks. `Opgaver` eller `TaskGenerator`
               - Kopier den fulde sti (f.eks. `C:\\Users\\DitNavn\\OneDrive\\Opgaver`)
            
            2. **Gem stien i OpgaveAgenten:**
               - Indsæt stien i feltet ovenfor
               - Klik "Gem indstilling"
               - Test ved at oprette en opgave
            
            ---
            
            ### 🔧 Trin 2: Opret Power Automate Flow
            
            1. **Gå til Power Automate:**
               - Åbn [https://make.powerautomate.com](https://make.powerautomate.com)
               - Klik på "Create" → "Automated cloud flow"
            
            2. **Navngiv dit flow:**
               - Navn: "Opgave til SharePoint Dashboard"
               - Klik "Skip" for at vælge trigger manuelt
            
            ---
            
            ### ⚡ Trin 3: Tilføj Trigger
            
            **Action:** "When a file is created" (OneDrive for Business)
            
            **Indstillinger:**
            - **Folder:** Vælg din opgave-mappe (f.eks. `/Opgaver`)
            - **Include subfolders:** No
            - **Infer Content Type:** A boolean value true, false to infer content type based on extension
            
            💡 **Tip:** Klik på mappeikonet for at browse til den korrekte mappe
            
            ---
            
            ### 📄 Trin 4: Hent filindhold
            
            **Action:** "Get file content" (OneDrive for Business)
            
            **Indstillinger:**
            - **File:** Vælg "File identifier" fra dynamisk indhold (fra forrige trin)
            - **Infer Content Type:** A boolean value true, false to infer content type based on extension
            
            ---
            
            ### 🔍 Trin 5: Parse JSON data
            
            **Action:** "Parse JSON" (Data Operations)
            
            **Indstillinger:**
            - **Content:** Vælg "File content" fra dynamisk indhold
            - **Schema:** Klik "Generate from sample" og indsæt:
            
            ```json
            {
              "Titel": "Eksempel opgave",
              "Afdeling": "Digitalisering",
              "Beskrivelse": "Dette er en beskrivelse",
              "EstimeretTid": 8.5,
              "Status": "I gang",
              "Tovholder": "Navn Navnesen",
              "Startdato": "2026-01-14",
              "Slutdato": "2026-01-28",
              "Opgavestørrelse": "Mellem stor",
              "Oprettet": "2026-01-14T13:15:00",
              "Version": "1.4"
            }
            ```
            
            **Vigtigt:** Når schema genereres, skal `EstimeretTid` være type `number` (ikke `integer`)
            
            Klik "Done" - schema genereres automatisk
            
            ---
            
            ### 📊 Trin 6: Opret SharePoint element
            
            **Action:** "Create item" (SharePoint)
            
            **Indstillinger:**
            - **Site Address:** Vælg dit SharePoint site (f.eks. "Digitalisering Dashboard")
            - **List Name:** Vælg din liste (f.eks. "Hovedopgaver")
            
            **Map felter fra JSON til SharePoint:**
            
            | SharePoint felt | Dynamisk indhold | Beskrivelse |
            |----------------|------------------|-------------|
            | **Title** | `Titel` | Fra Parse JSON |
            | **Beskrivelse af opgaven** | `Beskrivelse` | Fra Parse JSON |
            | **Afdeling** | `Afdeling` | Fra Parse JSON |
            | **EstimeretTid** | `EstimeretTid` | Fra Parse JSON |
            | **Status** | `Status` | Fra Parse JSON |
            | **Tovholder Value** | `Tovholder` | Fra Parse JSON |
            | **Startdato** | `Startdato` | Fra Parse JSON |
            | **Slutdato** | `Slutdato` | Fra Parse JSON |
            | **Opgavestatus Value** | `Status` | Fra Parse JSON |
            | **Indholdstype Id** | (valgfri) | Hvis du bruger content types |
            
            💡 **Vigtigt:** 
            - Felter med "Value" i navnet er lookup/person felter
            - Datofelter skal være i formatet YYYY-MM-DD
            - Hvis et felt ikke findes i SharePoint, opret det først
            
            ---
            
            ### ✅ Trin 7: Test dit flow
            
            1. **Gem flowet:** Klik "Save" øverst til højre
            
            2. **Test flowet:**
               - Klik "Test" → "Manually" → "Test"
               - Gå til OpgaveAgenten og opret en test-opgave
               - Vent 1-2 minutter
               - Tjek dit SharePoint Dashboard
            
            3. **Verificer:**
               - ✅ Opgaven vises i SharePoint
               - ✅ Alle felter er udfyldt korrekt
               - ✅ Datoer er formateret rigtigt
            
            ---
            
            ### 🔧 Fejlfinding
            
            **Problem:** Flow trigger ikke
            - ✅ Kontroller at mappen er i OneDrive (ikke lokal)
            - ✅ Verificer at OneDrive synkroniserer
            - ✅ Tjek at flow'et er aktiveret (toggle øverst)
            
            **Problem:** "Invalid JSON"
            - ✅ Kontroller at schema matcher opgave-strukturen
            - ✅ Brug "Generate from sample" igen
            - ✅ Tjek at filen er en .json fil
            
            **Problem:** SharePoint felter mangler
            - ✅ Opret manglende felter i SharePoint listen
            - ✅ Tjek at feltnavne matcher præcist
            - ✅ Verificer felttyper (tekst, dato, tal, osv.)
            
            **Problem:** Person/Tovholder felt virker ikke
            - ✅ Brug "Tovholder Value" i stedet for "Tovholder"
            - ✅ Kontroller at personen findes i SharePoint
            - ✅ Brug email i stedet for navn hvis nødvendigt
            
            ---
            
            ### 🎓 Avancerede muligheder
            
            **Tilføj email notifikation:**
            - Efter "Create item", tilføj "Send an email (V2)"
            - Send til tovholder når opgave oprettes
            
            **Tilføj til Microsoft Planner:**
            - Tilføj "Create a task" (Planner)
            - Synkroniser opgaver til Planner boards
            
            **Tilføj betingelser:**
            - Tilføj "Condition" efter Parse JSON
            - Håndter forskellige opgavestørrelser forskelligt
            - Send kun email for "Stor" opgaver
            
            **Arkiver originale filer:**
            - Tilføj "Move file" efter Create item
            - Flyt til en "Arkiv" mappe i OneDrive
            
            ---
            
            ### 💡 Hjælp til fejlfinding
            
            Hvis du oplever problemer:
            1. Tjek flow'ets "Run history" for fejlmeddelelser
            2. Verificer at alle SharePoint felter eksisterer
            3. Test med en simpel opgave først
            """)
        
        st.divider()
        st.write("#### 💡 Hurtig start")
        st.markdown("""
        **Kom hurtigt i gang:**
        
        1. **Vælg OneDrive mappe** ovenfor og gem indstillingen
        2. **Opret en test-opgave** for at generere en JSON-fil
        3. **Følg Power Automate vejledningen** ovenfor (klik for at udvide)
        4. **Test dit flow** og juster efter behov
        """)

# Tilføj en footer med version og links
st.sidebar.markdown("---")
st.sidebar.markdown("### Om")
st.sidebar.info(
    "OA - OpgaveAgenten v1.1\n\n"
    "Et smart værktøj til at oprette og administrere opgaver\n\n"
)
