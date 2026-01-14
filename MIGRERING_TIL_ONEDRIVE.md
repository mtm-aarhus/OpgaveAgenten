# 🚚 Guide: Flyt OpgaveAgenten til OneDrive

For at sikre dine data og gøre det nemt at dele værktøjet, anbefaler vi at køre det fra dit OneDrive. Her er de 4 enkle trin:

---

### Trin 1: Stop programmet
Hvis du har OpgaveAgenten kørende (det sorte vindue er åbent), så luk det ved at trykke på krydset i hjørnet.

### Trin 2: Kopiér mappen
Højreklik på mappen `opgavegenerator_docker` (eller hvad du har kaldt projektmappen) og vælg **Kopiér**.

### Trin 3: Sæt ind på OneDrive
Gå til dit Aarhus Kommune OneDrive (f.eks. mappen `Værktøjer` eller `Projekter`) og vælg **Sæt ind**.
*   *Vi foreslår at omdøbe mappen til `OpgaveAgenten` efter du har sat den ind.*

### Trin 4: Slet den gamle 'venv' (Valgfrit men anbefales)
Inde i den nye mappe på OneDrive:
1. Find mappen `venv` og **slet den**.
2. Dobbeltklik på `start.bat`.
3. Systemet vil nu automatisk genopbygge det virtuelle miljø, så det passer perfekt til den nye placering.

---

**Nu er du kørende!** 🚀  
Alle dine opgaver i mappen `data` vil nu automatisk blive synkroniseret og sikkerhedskopieret af OneDrive.
