"""
modules/ai/groq_client.py — Client GROQ singleton réel
Modèles: llama3-70b-8192 (principal) · mixtral-8x7b-32768 (analyse)
"""
import logging
from backend.config import groq_client, GROQ_MODEL_MAIN, GROQ_MODEL_ANALYSIS

logger = logging.getLogger(__name__)


async def call_groq(
    system_prompt: str,
    user_content: str,
    model: str = None,
    temperature: float = 0.3,
    max_tokens: int = 2048,
    json_mode: bool = False
) -> str:
    """Appel GROQ réel — retourne le contenu texte de la réponse."""
    if not groq_client:
        raise RuntimeError("GROQ_API_KEY non configuré")

    model = model or GROQ_MODEL_MAIN
    kwargs = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    completion = groq_client.chat.completions.create(**kwargs)
    return completion.choices[0].message.content


async def call_groq_analysis(
    system_prompt: str,
    user_content: str,
    temperature: float = 0.2,
    max_tokens: int = 1500,
    json_mode: bool = True
) -> str:
    """Appel avec le modèle d'analyse (mixtral) — pour talent/turnover/recommandation."""
    return await call_groq(
        system_prompt=system_prompt,
        user_content=user_content,
        model=GROQ_MODEL_ANALYSIS,
        temperature=temperature,
        max_tokens=max_tokens,
        json_mode=json_mode
    )
