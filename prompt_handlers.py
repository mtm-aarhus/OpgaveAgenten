from langchain_core.prompts import PromptTemplate
from typing import Dict, Any, Optional
import os
from llm_providers import get_llm_manager

class FieldHandler:
    """Basisklasse for felt-håndteringsklasser"""
    def __init__(self, field_name: str, description: str):
        self.field_name = field_name
        self.description = description
        # Gem reference til LLM manager for fallback-funktionalitet
        self.llm_manager = get_llm_manager()

    def get_prompt_template(self) -> str:
        """Returnerer prompt-skabelonen for dette felt"""
        raise NotImplementedError("Denne metode bør implementeres i underklasser")

    def process(self, input_text: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Processerer input og returnerer det behandlede felt med automatisk fallback"""
        print(f"Debug - FieldHandler.process kaldt med input: {input_text[:100]}...")

        template = self.get_prompt_template()

        # Opret en ordbog med standard input_variables
        input_vars = {"input_text": input_text}

        # Tilføj eventuelle yderligere variabler fra context
        if context:
            input_vars.update(context)

        # Opret prompt-skabelonen med de nødvendige variabler
        prompt = PromptTemplate(
            input_variables=list(input_vars.keys()),
            template=template
        )

        # Forsøg alle tilgængelige providers i prioriteret rækkefølge
        available_providers = self.llm_manager.get_available_providers()

        if not available_providers:
            print("⚠️ ADVARSEL: Ingen LLM providers tilgængelige! Returnerer original input.")
            return input_text

        last_error = None

        for provider_name in available_providers:
            try:
                print(f"🔄 Forsøger {provider_name}...")

                # Hent LLM for denne provider
                llm = self.llm_manager.get_langchain_llm(
                    temperature=0.7,
                    force_provider=provider_name
                )

                # Kør LLM chain (using new RunnableSequence syntax)
                chain = prompt | llm
                result = chain.invoke(input_vars)

                # Extract content from AIMessage object
                response = result.content if hasattr(result, 'content') else str(result)

                print(f"✅ {provider_name} lykkedes! Modtaget svar: {response[:200]}...")
                return response.strip()

            except Exception as e:
                last_error = e
                error_msg = str(e)
                print(f"❌ {provider_name} fejlede: {error_msg}")

                # Tjek om det er en rate limit / balance fejl
                if "429" in error_msg or "limit brugt" in error_msg or "insufficient" in error_msg.lower():
                    print(f"   ↳ {provider_name} har ingen midler eller rate limit - prøver næste provider...")
                else:
                    print(f"   ↳ Uventet fejl - prøver næste provider...")

                # Fortsæt til næste provider
                continue

        # Hvis alle providers fejlede
        print(f"❌ Alle providers fejlede! Sidste fejl: {last_error}")
        print(f"⚠️ Returnerer original input som fallback.")
        return input_text

class TitleHandler(FieldHandler):
    def __init__(self):
        super().__init__("title", "Generer en kort og prægnant titel for opgaven")
    
    def get_prompt_template(self) -> str:
        return """
        Du er en ekspert i at skrive præcise og informative titler til opgaver.
        Lav en kort og prægnant titel baseret på følgende beskrivelse:
        
        {input_text}
        
        VIGTIGT:
        - Titlen skal være maksimalt 10-12 ord
        - Fange essensen af opgaven
        - INGEN anførselstegn (" eller ')
        - INGEN punktum i slutningen
        - Returner KUN titlen, ingen yderligere tekst
        
        Eksempler på gode titler:
        - Implementering af brugerregistrering
        - Opdatering af dokumentationssystem
        - Fejlrettelse i login-flow
        """
    
    def process(self, input_text: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Processerer input og fjerner anførselstegn fra resultatet"""
        result = super().process(input_text, context)
        # Fjern anførselstegn og trim whitespace
        if isinstance(result, str):
            result = result.strip('"\'').strip()
            # Fjern eventuelle punktummer i starten
            if result and result[0].isdigit() and '. ' in result[:5]:
                result = result.split('. ', 1)[1]
        return result

class DescriptionHandler(FieldHandler):
    def __init__(self):
        super().__init__("description", "Generer en detaljeret beskrivelse af opgaven")
        self.size_constraints = {
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
    
    def get_prompt_template(self) -> str:
        return """
        Du er en ekspert i at skrive præcise og faktuelle opgavebeskrivelser.
        Lav en direkte og konkret beskrivelse baseret på følgende information:
        
        {input_text}
        
        Beskrivelsens længde skal afspejle opgavestørrelsen:
        - Lille opgave: Maksimalt {max_lines} linjer
        - Mellem stor opgave: Mellem 6-10 linjer
        - Stor opgave: Mellem 10-15 linjer
        
        Beskrivelsen skal være faktuel og direkte og indeholde:
        - Hvad der skal gøres (konkret handling)
        - Hvilke specifikke resultater der forventes
        - Eventuelle tekniske krav eller begrænsninger
        
        Undgå:
        - Udtryk som "kunne", "måske", "muligvis" eller anden usikkerhed
        - Generelle vendinger om formål eller gevinster
        - Unødvendige forklaringer eller begrundelser
        - At skrive "Underopgaver:" - brug i stedet en nummeret liste direkte
        
        Skriv første en kort beskrivele af opgaven og efterfulgt af underopogaver.

        Eksempler på underopgaver (antag max_lines={max_lines}):
        
        Lille opgave (op til 5 linjer):
        1. Opret testdata for brugerregistrering
        2. Udfør test af login-funktionalitet
        
        Mellem stor opgave (op til 10 linjer):
        1. Implementer brugerregistrering med validering
        2. Opret database-skema for brugere
        3. Udfør enheds- og integrationstest
        
        Stor opgave (op til 15 linjer):
        1. Design og implementer brugerstyringssystem
        2. Implementer adgangskontrol og sikkerhedsforanstaltninger
        3. Opret API-endepunkter til brugeradministration
        4. Implementer logging og overvågning
        5. Udfør omfattende testning og dokumentation
        
        Returner KUN den færdige beskrivelse uden yderligere kommentarer eller overskrifter.
        """
    
    def process(self, input_text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Processerer beskrivelsen og returnerer et dictionary med opgaveoplysninger
        """
        try:
            print(f"Debug - DescriptionHandler modtog input: {input_text[:200]}...")
            
            if not context or 'Opgavestørrelse' not in context:
                return {
                    "beskrivelse": input_text,
                    "estimeret_tid": 0,
                    "max_dage": 7
                }
                
            size = context["Opgavestørrelse"]
            if size not in self.size_constraints:
                size = "Lille"  # Default hvis ukendt størrelse
                
            constraints = self.size_constraints[size]
            max_lines = constraints["max_lines"]
            
            # Tilføj max_lines til context, så den kan bruges i prompten
            if context is None:
                context = {}
            context["max_lines"] = max_lines
            
            # Kald den overordnede process-metode med både input_text og context
            description = super().process(input_text, context)
            
            # Fjern eventuelle anførselstegn og trim
            if isinstance(description, str):
                description = description.strip('\"\'').strip()
            else:
                description = str(description).strip()
            
            print(f"Debug - Modtog beskrivelse fra LLM: {description[:200]}...")
            
            # Fjern tomme linjer og trim hver linje
            lines = [line.strip() for line in description.split('\n') if line.strip()]
            
            # Hvis der stadig er for mange linjer, trim til max_lines
            if len(lines) > max_lines:
                lines = lines[:max_lines]
            
            return {
                "beskrivelse": '\n'.join(lines),
                "estimeret_tid": constraints["hours"],
                "max_dage": constraints["max_days"]
            }
            
        except Exception as e:
            print(f"Fejl i DescriptionHandler.process: {str(e)}")
            return {
                "beskrivelse": input_text,
                "estimeret_tid": 8,  # Standardværdi
                "max_dage": 15  # Standardværdi
            }

class ResponsiblePersonHandler(FieldHandler):
    def __init__(self):
        super().__init__("responsible_person", "Angiv den ansvarlige person")
    
    def get_prompt_template(self) -> str:
        return """
        Returner altid 'Bruger 1' som den ansvarlige person uanset input.
        
        {input_text}
        
        Returner kun 'Bruger 1' uden yderligere tekst.
        """
        
    def process(self, input_text: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Overskriver process-metoden for altid at returnere 'Bruger 1'"""
        return "Bruger 1"

class DepartmentHandler(FieldHandler):
    def __init__(self):
        super().__init__("department", "Vurder den mest relevante afdeling for opgaven")
    
    def get_prompt_template(self) -> str:
        return """
        Du er en ekspert i at kategorisere opgaver til forskellige afdelinger.
        
        Baseret på følgende opgavetekst, vurder hvilken af disse afdelinger der bedst passer til opgaven:
        {afdelinger_liste}
        
        Overvej opgavens indhold, fagområde og hvilken afdeling der typisk håndterer lignende opgaver.
        Returner KUN navnet på den mest passende afdeling, intet andet.
        
        Opgavetekst:
        {input_text}
        """
    
    def process(self, input_text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Overskriver process-metoden for at sikre korrekt returtype"""
        result = super().process(input_text, context)
        # Returner altid et dictionary med en 'afdeling' nøgle
        if isinstance(result, dict):
            return result
        return {'afdeling': str(result) if result else 'Digitalisering'}
        return {"afdeling": result}

class FieldHandlerFactory:
    """Factory til at oprette de korrekte felt-håndteringsklasser"""
    
    @staticmethod
    def get_handler(field_name: str) -> FieldHandler:
        """Returner den korrekte handler for det angivne felt"""
        handlers = {
            "title": TitleHandler(),
            "description": DescriptionHandler(),
            "responsible_person": ResponsiblePersonHandler(),
            "department": DepartmentHandler(),
        }
        
        handler = handlers.get(field_name)
        if not handler:
            raise ValueError(f"Ingen handler fundet for felt: {field_name}")
            
        return handler
