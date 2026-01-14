"""
LLM Provider abstraktioner for at understøtte flere AI-modeller med automatisk fallback.

Supporterer:
- Google Gemini API - Primær
- OpenAI GPT-4 - Fallback
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
try:
    from langchain_core.language_models import BaseLanguageModel
except ImportError:
    from langchain.schema.language_model import BaseLanguageModel
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
import requests
import json
from config import (
    OPENAI_API_KEY, OPENAI_ORG_ID,
    GOOGLE_API_KEY,
    LLM_PROVIDER_PRIORITY
)


class BaseLLMProvider(ABC):
    """Abstrakt base klasse for LLM providers"""

    def __init__(self, api_key: str, model_name: str = None):
        self.api_key = api_key
        self.model_name = model_name or self.get_default_model()

    @abstractmethod
    def get_langchain_llm(self, temperature: float = 0.7, **kwargs) -> BaseLanguageModel:
        """Returner en LangChain-kompatibel LLM instance"""
        pass

    @abstractmethod
    def get_default_model(self) -> str:
        """Returner standard model-navnet for denne provider"""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Returner provider-navnet"""
        pass

    def is_available(self) -> bool:
        """Tjek om denne provider er tilgængelig (har API-nøgle)"""
        return bool(self.api_key and self.api_key.strip())

    def test_connection(self) -> bool:
        """Test om forbindelsen til provideren virker"""
        try:
            llm = self.get_langchain_llm(temperature=0.0)
            # Simpel test-prompt
            response = llm.invoke("Svar kun med ordet 'OK'")
            return bool(response)
        except Exception as e:
            print(f"Forbindelsestest fejlede for {self.get_name()}: {str(e)}")
            return False


class GoogleProvider(BaseLLMProvider):
    """
    Google Gemini API Provider
    https://ai.google.dev/
    """

    def get_name(self) -> str:
        return "Google Gemini"

    def get_default_model(self) -> str:
        # Use latest stable models - LangChain will add "models/" prefix automatically
        return "gemini-2.5-flash"  # Fast and efficient, or use "gemini-2.5-pro" for better quality

    def get_langchain_llm(self, temperature: float = 0.7, **kwargs) -> BaseLanguageModel:
        """Returner LangChain LLM for Google Gemini"""
        return ChatGoogleGenerativeAI(
            model=self.model_name,
            temperature=temperature,
            google_api_key=self.api_key,
            **kwargs
        )


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI GPT Provider
    https://platform.openai.com/
    """

    def __init__(self, api_key: str, model_name: str = None, org_id: str = None):
        super().__init__(api_key, model_name)
        self.org_id = org_id

    def get_name(self) -> str:
        return "OpenAI GPT-4"

    def get_default_model(self) -> str:
        return "gpt-4"

    def get_langchain_llm(self, temperature: float = 0.7, **kwargs) -> BaseLanguageModel:
        """Returner LangChain LLM for OpenAI"""
        return ChatOpenAI(
            model_name=self.model_name,
            temperature=temperature,
            openai_api_key=self.api_key,
            openai_organization=self.org_id if self.org_id else None,
            **kwargs
        )


class LLMProviderManager:
    """
    Manager for LLM providers med automatisk fallback.
    Prioritet: Google -> OpenAI (kan konfigureres)
    """

    def __init__(self, priority_list: List[str] = None):
        """
        Initialiser manager med provider-prioritet.

        Args:
            priority_list: Liste af provider-navne i prioriteret rækkefølge.
                          Standardværdi: ["zai", "google", "openai"]
        """
        self.priority_list = priority_list or LLM_PROVIDER_PRIORITY

        # Initialiser alle providers
        self.providers: Dict[str, BaseLLMProvider] = {
            "google": GoogleProvider(GOOGLE_API_KEY),
            "openai": OpenAIProvider(OPENAI_API_KEY, org_id=OPENAI_ORG_ID)
        }

        # Cache den aktive provider
        self._active_provider: Optional[BaseLLMProvider] = None
        self._last_error: Optional[str] = None

    def update_api_keys(self, google_key: str = None, openai_key: str = None):
        """
        Opdater API-nøgler for de specifikke providers dynamisk.
        Dette bruges hvis brugeren indtaster egne nøgler i UI.
        """
        if google_key and "google" in self.providers:
            self.providers["google"].api_key = google_key
            print("Info: Google API-nøgle opdateret dynamisk")
            
        if openai_key and "openai" in self.providers:
            self.providers["openai"].api_key = openai_key
            print("Info: OpenAI API-nøgle opdateret dynamisk")
            
        # Nulstil aktiv provider så den gen-evalueres med de nye nøgler
        self._active_provider = None

    def get_available_providers(self) -> List[str]:
        """Returner liste over tilgængelige providers (med API-nøgler)"""
        return [
            name for name in self.priority_list
            if name in self.providers and self.providers[name].is_available()
        ]

    def get_provider(self, force_provider: str = None) -> BaseLLMProvider:
        """
        Hent den bedst tilgængelige provider baseret på prioritet.

        Args:
            force_provider: Tving brug af specifik provider (ignorerer prioritet)

        Returns:
            BaseLLMProvider instance

        Raises:
            RuntimeError: Hvis ingen providers er tilgængelige
        """
        # Hvis en specifik provider er anmodet, brug den
        if force_provider:
            if force_provider in self.providers and self.providers[force_provider].is_available():
                self._active_provider = self.providers[force_provider]
                return self._active_provider
            else:
                raise RuntimeError(f"Provider '{force_provider}' er ikke tilgængelig")

        # Brug cached provider hvis tilgængelig
        if self._active_provider and self._active_provider.is_available():
            return self._active_provider

        # Find første tilgængelige provider baseret på prioritet
        available = self.get_available_providers()

        if not available:
            raise RuntimeError(
                "Ingen LLM providers tilgængelige! "
                "Kontroller at mindst én API-nøgle er sat i .env-filen: "
                "GOOGLE_API_KEY eller OPENAI_API_KEY"
            )

        # Vælg første tilgængelige provider
        provider_name = available[0]
        self._active_provider = self.providers[provider_name]

        print(f"Info: Bruger {self._active_provider.get_name()} som LLM provider")
        return self._active_provider

    def get_langchain_llm(self, temperature: float = 0.7, force_provider: str = None, **kwargs) -> BaseLanguageModel:
        """
        Hent en LangChain-kompatibel LLM med automatisk fallback.

        Args:
            temperature: Model temperature (0.0-1.0)
            force_provider: Tving brug af specifik provider
            **kwargs: Yderligere argumenter til LLM

        Returns:
            LangChain BaseLanguageModel instance
        """
        provider = self.get_provider(force_provider)
        return provider.get_langchain_llm(temperature=temperature, **kwargs)

    def test_all_providers(self) -> Dict[str, bool]:
        """
        Test alle providers og returner deres status.

        Returns:
            Dict med provider-navn som nøgle og forbindelsesstatus som værdi
        """
        results = {}

        for name, provider in self.providers.items():
            if not provider.is_available():
                results[name] = False
                print(f"⚠️  {provider.get_name()}: Ingen API-nøgle")
            else:
                print(f"🔄 Tester {provider.get_name()}...")
                is_working = provider.test_connection()
                results[name] = is_working

                if is_working:
                    print(f"✅ {provider.get_name()}: OK")
                else:
                    print(f"❌ {provider.get_name()}: Fejl")

        return results

    def get_status_summary(self) -> str:
        """Returner en formateret status-oversigt over alle providers"""
        available = self.get_available_providers()

        summary_lines = [
            "\n=== LLM Provider Status ===",
            f"Prioritet: {' -> '.join(self.priority_list)}",
            f"\nTilgængelige providers: {len(available)}/{len(self.providers)}",
        ]

        for name in self.priority_list:
            if name not in self.providers:
                continue

            provider = self.providers[name]
            status = "✅" if provider.is_available() else "❌"
            summary_lines.append(f"  {status} {provider.get_name()}")

        if available:
            active = available[0]
            summary_lines.append(f"\nAktiv provider: {self.providers[active].get_name()}")
        else:
            summary_lines.append("\n⚠️  ADVARSEL: Ingen providers tilgængelige!")

        return "\n".join(summary_lines)


# Singleton instance for global brug
_provider_manager = None

def get_llm_manager() -> LLMProviderManager:
    """Hent den globale LLMProviderManager singleton"""
    global _provider_manager
    if _provider_manager is None:
        _provider_manager = LLMProviderManager()
    return _provider_manager
