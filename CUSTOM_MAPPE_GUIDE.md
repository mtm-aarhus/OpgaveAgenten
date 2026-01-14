# Guide til Custom Gem-mappe

## Oversigt
OpgaveAgenten understøtter nu brugerdefinerede gem-mapper, så du kan vælge præcis hvor dine opgave-filer skal gemmes. Dette gør det muligt at integrere med OneDrive, SharePoint og Power Automate.

## Sådan bruger du funktionen

### 1. Åbn Indstillinger
- Klik på **"Indstillinger"** i sidemenuen
- Vælg fanen **"📂 Gem-mappe"**

### 2. Vælg din mappe
Du kan indtaste stien til din ønskede mappe på to måder:

**Metode 1: Kopier fra Stifinder**
1. Åbn Stifinder (Windows Explorer)
2. Naviger til den mappe du vil bruge
3. Klik i adresselinjen øverst
4. Kopier hele stien (Ctrl+C)
5. Indsæt stien i feltet i OpgaveAgenten

**Metode 2: Indtast manuelt**
Indtast den fulde sti direkte, f.eks.:
- `C:\Users\DitNavn\OneDrive\Opgaver`
- `C:\Users\DitNavn\Documents\MinOpgaver`
- `D:\Projekter\Opgaver`

### 3. Gem indstillingen
- Klik på **"✅ Gem indstilling"**
- Hvis mappen ikke findes, vil den automatisk blive oprettet
- Alle fremtidige opgaver gemmes nu i denne mappe

## OneDrive Integration

### Fordele ved at bruge OneDrive
- **Automatisk backup**: Dine opgaver synkroniseres automatisk til skyen
- **Tilgængelig overalt**: Adgang til opgaver fra alle dine enheder
- **Power Automate**: Opret automatiseringer baseret på nye opgave-filer

### Anbefalet OneDrive sti
```
C:\Users\[DitBrugernavn]\OneDrive\Opgaver
```

## Power Automate Integration

### Eksempel: Automatisk email ved ny opgave

1. **Opret et Flow i Power Automate**
   - Trigger: "When a file is created" (OneDrive)
   - Mappe: Din valgte opgave-mappe
   - Filtype filter: `.json`

2. **Tilføj handlinger**
   - Parse JSON: Læs opgave-data
   - Send email: Send notifikation til tovholder
   - Opret Planner task: Opret opgave i Microsoft Planner

### Eksempel: Gem til SharePoint

1. **Opret et Flow**
   - Trigger: "When a file is created" (OneDrive)
   - Action: "Copy file" til SharePoint dokumentbibliotek
   - Action: "Create item" i SharePoint liste med opgave-data

## Nulstil til standard

Hvis du vil vende tilbage til standard-mappen:
1. Gå til **Indstillinger** → **📂 Gem-mappe**
2. Klik på **"🔄 Nulstil til standard"**
3. Opgaver gemmes nu igen i `data/` mappen i applikationens rodmappe

## Tekniske detaljer

### Filformat
Opgaver gemmes som JSON-filer med følgende navneformat:
```
opgave_YYYYMMDD_HHMMSS.json
```

Eksempel: `opgave_20260114_131500.json`

### JSON struktur
```json
{
  "Titel": "Opgavens titel",
  "Afdeling": "Digitalisering",
  "Beskrivelse": "Detaljeret beskrivelse...",
  "EstimeretTid": 8.0,
  "Status": "I gang",
  "Tovholder": "Navn Navnesen",
  "Startdato": "2026-01-14",
  "Slutdato": "2026-01-28",
  "Opgavestørrelse": "Mellem stor",
  "Oprettet": "2026-01-14T13:15:00",
  "Version": "1.4"
}
```

## Fejlfinding

### Problem: Mappen kan ikke oprettes
**Løsning**: Kontroller at:
- Stien er korrekt indtastet
- Du har skrivetilladelser til placeringen
- Drevet eksisterer og er tilgængeligt

### Problem: Opgaver gemmes stadig i data/
**Løsning**: 
- Kontroller at indstillingen er gemt korrekt
- Genstart applikationen
- Verificer at stien eksisterer

### Problem: Power Automate trigger ikke
**Løsning**:
- Kontroller at mappen er i OneDrive (ikke lokal)
- Verificer at OneDrive synkroniserer korrekt
- Tjek Flow'ets trigger-indstillinger

## Support

Hvis du oplever problemer med den brugerdefinerede mappe-funktion, kontakt IT-support eller tjek applikationens logfiler.
