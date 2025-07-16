import random
from concurrent.futures import ThreadPoolExecutor

from app.database import db_session
from app.llm_clients import get_available_models, get_translation_client
from app.models import Query, Translation
from app.repositories.query_repository import QueryRepository
from app.repositories.translation_repository import TranslationRepository
from app.repositories.user_repository import UserRepository
from app.repositories.vote_repository import VoteRepository


def get_translations(source_text, username="Guest", selected_models=None):
    """
    Gets translations for the given source text from a selected subset of models.
    Returns query_id and list of translation results.
    """
    models_to_use = selected_models or list(get_available_models().keys())

    random.shuffle(models_to_use)

    query_repo = QueryRepository(db_session)
    translation_repo = TranslationRepository(db_session)
    user_repo = UserRepository(db_session)
    vote_repo = VoteRepository(db_session)

    query = query_repo.get_by_source_text(source_text)
    if not query:
        query = Query(source_text=source_text)
        query = query_repo.add(query)

    translations = []

    def get_translation(model, position):
        """Fetch translation from DB or API."""
        existing = translation_repo.get_by_query_and_model(query.id, model)
        if existing:
            return {
                "id": existing.id,
                "model": model,
                "position": position,
                "translation": existing.translation,
                "cost": existing.cost,
            }

        client = get_translation_client(model)
        try:
            result, cost = client.translate(source_text)
            if "Error:" in result:
                return None
        except Exception:
            return None

        translation = Translation(
            query_id=query.id,
            model=model,
            translation=result,
            system_prompt=client.SYSTEM_PROMPT,
            position=position,
            cost=cost,
        )

        try:
            translation = translation_repo.add(translation)
            return {
                "id": translation.id,
                "model": model,
                "position": position,
                "translation": result,
                "cost": cost,
            }
        except Exception:
            return None

    with ThreadPoolExecutor() as executor:
        future_to_model = {
            executor.submit(get_translation, model, i): model
            for i, model in enumerate(models_to_use, 1)
        }
        for future in future_to_model:
            try:
                result = future.result()
                if result:
                    translations.append(result)
            except Exception:
                continue

    translations = sorted([t for t in translations if t], key=lambda x: x["position"])

    voted_translation = None
    if username != "Guest":
        user_obj = user_repo.get_by_username(username)
        if user_obj:
            votes = vote_repo.get_by_user_and_query(user_obj.id, query.id)
            if votes:
                # Find a valid vote to get the translation ID
                for vote in votes:
                    if vote.translation_id:
                        voted_translation = vote.translation_id
                        break

    return {
        "query_id": query.id,
        "translations": translations,
        "voted_translation": voted_translation,
    }
