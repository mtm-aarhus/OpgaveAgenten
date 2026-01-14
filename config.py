
from dotenv import load_dotenv
import os

# Indlæs miljøvariabler fra .env-fil
load_dotenv()

# Hent miljøvariabler med sikker standardværdi
# OpenAI konfiguration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_ORG_ID = os.getenv("OPENAI_ORG_ID", "")
OPENAI_PROJECT_ID = os.getenv("OPENAI_PROJECT_ID", "")


# Google API konfiguration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# LLM Provider prioritering (1=højest prioritet)
# Hvis ikke sat, bruges: Google -> OpenAI
LLM_PROVIDER_PRIORITY = os.getenv("LLM_PROVIDER_PRIORITY", "google,openai").split(",")

# SMTP konfiguration
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.office365.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "din_email@aarhus.dk")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "din_mail_adgangskode")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL", "modtager@aarhus.dk")

# Valider påkrævede miljøvariabler
required_vars = [
    ("SMTP_SERVER", SMTP_SERVER),
    ("SMTP_USERNAME", SMTP_USERNAME),
    ("SMTP_PASSWORD", SMTP_PASSWORD),
    ("RECIPIENT_EMAIL", RECIPIENT_EMAIL)
]

# LLM API nøgler (mindst én skal være sat)
llm_api_keys = [
    ("GOOGLE_API_KEY", GOOGLE_API_KEY),
    ("OPENAI_API_KEY", OPENAI_API_KEY)
]

# Valgfrie miljøvariabler
optional_vars = [
    ("OPENAI_ORG_ID", OPENAI_ORG_ID),
    ("OPENAI_PROJECT_ID", OPENAI_PROJECT_ID)
]

# Vis advarsler for manglende påkrævede variabler
for var_name, var_value in required_vars:
    if not var_value:
        print(f"Advarsel: {var_name} er ikke sat i .env-filen")

# Tjek at mindst én LLM API-nøgle er sat
if not any(value for _, value in llm_api_keys):
    print("FEJL: Ingen LLM API-nøgler sat! Mindst én af GOOGLE_API_KEY eller OPENAI_API_KEY skal være sat.")
else:
    available_providers = [name.replace("_API_KEY", "").lower() for name, value in llm_api_keys if value]
    print(f"Info: Tilgængelige LLM providers: {', '.join(available_providers)}")

# Vis info om valgfrie variabler
for var_name, var_value in optional_vars:
    if not var_value:
        print(f"Info: {var_name} er ikke sat (valgfri)")
