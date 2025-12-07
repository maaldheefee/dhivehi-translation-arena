import hashlib

from sqlalchemy.orm import Session

from app.database import SessionFactory
from app.llm_clients import get_translation_client
from app.models import Query, Translation
from app.repositories.query_repository import QueryRepository
from app.repositories.translation_repository import TranslationRepository


def get_translation_for_model(source_text: str, model: str, position: int) -> dict:
    """
    Retrieves or creates a translation for a given source text and model.

    This function first checks the database for an existing translation.
    If found, it returns the cached translation. Otherwise, it calls the
    external translation API, stores the new translation in the database,
    and then returns it.

    A new database session is created and managed within this function to ensure
    thread safety when handling concurrent translation requests.

    Args:
        source_text: The text to be translated.
        model: The identifier for the translation model to use.
        position: The display order for the translation in the UI.

    Returns:
        A dictionary containing the translation details.
    """
    session: Session = SessionFactory()
    try:
        query_repo = QueryRepository(session)
        translation_repo = TranslationRepository(session)

        query = query_repo.get_by_source_text(source_text)
        if not query:
            session.rollback()
            query = query_repo.get_by_source_text(source_text)
            if not query:
                query = Query(source_text=source_text)
                query = query_repo.add(query)

        existing = translation_repo.get_by_query_and_model(query.id, model)  # ty: ignore [invalid-argument-type]
        if existing:
            return {
                "query_id": existing.query_id,
                "id": existing.id,
                "model": model,
                "position": position,
                "translation": existing.translation,
                "cost": existing.cost,
                "response_hash": existing.response_hash,
            }

        client = get_translation_client(model)
        try:
            result_text, cost = client.translate(source_text)
            if "Error:" in result_text or "Rate limit" in result_text:
                raise ConnectionError(result_text)
        except Exception as e:
            msg = f"API call failed for {model}: {e!s}"
            raise ConnectionError(msg) from e

        # Calculate hash
        response_hash = hashlib.sha256(result_text.encode("utf-8")).hexdigest()

        translation = Translation(
            query_id=query.id,
            model=model,
            translation=result_text,
            system_prompt=client.SYSTEM_PROMPT,
            position=position,
            cost=cost,
            response_hash=response_hash,
        )
        new_translation = translation_repo.add(translation)

    except Exception:
        session.rollback()
        raise

    else:
        return {
            "query_id": new_translation.query_id,
            "id": new_translation.id,
            "model": model,
            "position": position,
            "translation": result_text,
            "cost": cost,
            "response_hash": response_hash,
        }

    finally:
        session.close()
