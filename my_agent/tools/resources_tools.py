"""
resources_tools.py
------------------
Tools custom pour l'assistant d'aide aux déplacés au Liban.

Ces tools lisent une base JSON locale et retournent des données structurées.
Ils sont conçus pour être simples, robustes et faciles à exploiter par les agents ADK.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional


_DATA_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "data",
    "lebanon_resources.json",
)


def _load_data() -> Dict[str, Any]:
    """
    Charge le fichier JSON local contenant les ressources.

    Returns:
        dict: contenu JSON chargé.

    Raises:
        FileNotFoundError: si le fichier n'existe pas.
        ValueError: si le JSON est invalide.
    """
    if not os.path.exists(_DATA_PATH):
        raise FileNotFoundError(f"Resource file not found: {_DATA_PATH}")

    try:
        with open(_DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {_DATA_PATH}: {exc}") from exc


def _normalize_text(value: Optional[str]) -> str:
    """Normalise un texte pour comparaison simple."""
    return (value or "").strip().lower()


def _matches_location(location: str, *fields: Optional[str]) -> bool:
    """
    Vérifie si la location demandée apparaît dans au moins un champ.
    Matching volontairement simple pour la démo.
    """
    location_norm = _normalize_text(location)
    if not location_norm:
        return False

    for field in fields:
        if location_norm in _normalize_text(field):
            return True
    return False


def _safe_list(value: Any) -> List[Any]:
    """Garantit qu'une valeur est toujours une liste."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parse une date YYYY-MM-DD si possible."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return None


def verify_resource(resource: Dict[str, Any]) -> Dict[str, Any]:
    """
    Évalue le statut de vérification d'une ressource.

    Rules:
    - verified=True + last_updated <= 30 jours => Confirmed
    - verified=True + old date => To reconfirm
    - verified=False + contact => Unverified
    - sinon => No direct contact / To confirm

    Args:
        resource: dictionnaire représentant une ressource.

    Returns:
        dict: résumé de vérification.
    """
    verified = bool(resource.get("verified", False))
    last_updated = _parse_date(resource.get("last_updated"))
    has_contact = bool(
        resource.get("contact")
        or resource.get("contact_phone")
        or resource.get("numbers")
    )

    now = datetime.now()
    days_old: Optional[int] = None
    if last_updated is not None:
        days_old = (now - last_updated).days

    if verified and days_old is not None and days_old <= 30:
        label = "✅ Confirmed"
        action = "Safe to use"
    elif verified:
        label = "⚠️ To reconfirm"
        action = "Call before going"
    elif has_contact:
        label = "⚠️ Unverified"
        action = "Call and confirm before going"
    else:
        label = "❓ No direct contact"
        action = "Use with caution and confirm through official channels"

    return {
        "label": label,
        "action": action,
        "verified": verified,
        "last_updated": resource.get("last_updated"),
        "days_old": days_old,
    }


def get_shelters_by_location(location: str, limit: int = 5) -> Dict[str, Any]:
    """
    Retourne des shelters correspondant à une ville/région/district.

    Args:
        location: ville, district ou governorate à chercher.
        limit: nombre max de résultats.

    Returns:
        dict: résultats de shelters structurés.
    """
    try:
        data = _load_data()
        shelters = data.get("shelters", [])

        matches: List[Dict[str, Any]] = []
        for shelter in shelters:
            if _matches_location(
                location,
                shelter.get("governorate"),
                shelter.get("district"),
                shelter.get("address"),
                shelter.get("name"),
                shelter.get("name_ar"),
            ):
                verification = verify_resource(shelter)
                matches.append(
                    {
                        "id": shelter.get("id"),
                        "type": "shelter",
                        "name": shelter.get("name"),
                        "name_ar": shelter.get("name_ar"),
                        "governorate": shelter.get("governorate"),
                        "district": shelter.get("district"),
                        "address": shelter.get("address"),
                        "contact": shelter.get("contact"),
                        "status": shelter.get("status"),
                        "notes": shelter.get("notes"),
                        "verification": verification,
                    }
                )

        return {
            "query_location": location,
            "count": len(matches),
            "results": matches[:limit],
            "warning": (
                "Always call before going. Availability and capacity may change."
            ),
        }
    except Exception as exc:
        return {
            "query_location": location,
            "count": 0,
            "results": [],
            "error": str(exc),
        }


def get_hotline_by_region(region: str) -> Dict[str, Any]:
    """
    Retourne la hotline principale de shelter referral pour une région donnée.

    Args:
        region: région / governorate recherchée.

    Returns:
        dict: hotline(s) correspondante(s).
    """
    try:
        data = _load_data()
        hotlines = data.get("hotlines", [])

        matches: List[Dict[str, Any]] = []
        for hotline in hotlines:
            if _matches_location(region, hotline.get("region"), hotline.get("region_ar")):
                matches.append(
                    {
                        "id": hotline.get("id"),
                        "type": "hotline",
                        "region": hotline.get("region"),
                        "service": hotline.get("service"),
                        "numbers": hotline.get("numbers", []),
                        "available_24h": hotline.get("available_24h"),
                        "languages": hotline.get("languages", []),
                        "verified": hotline.get("verified", False),
                    }
                )

        return {
            "query_region": region,
            "count": len(matches),
            "results": matches,
        }
    except Exception as exc:
        return {
            "query_region": region,
            "count": 0,
            "results": [],
            "error": str(exc),
        }


def get_medical_resources() -> Dict[str, Any]:
    """
    Retourne les lignes médicales nationales.

    Returns:
        dict: ressources médicales nationales.
    """
    try:
        data = _load_data()
        medical = data.get("medical", {})
        lines = medical.get("national_lines", [])

        results = []
        for line in lines:
            results.append(
                {
                    "id": line.get("id"),
                    "type": "medical_hotline",
                    "number": line.get("number"),
                    "service": line.get("service"),
                    "description": line.get("description"),
                    "available_24h": line.get("available_24h"),
                    "free": line.get("free"),
                    "verified": line.get("verified"),
                }
            )

        return {
            "coverage_note": medical.get("coverage_note"),
            "count": len(results),
            "results": results,
        }
    except Exception as exc:
        return {
            "count": 0,
            "results": [],
            "error": str(exc),
        }


def get_food_and_aid(location: str, limit: int = 6) -> Dict[str, Any]:
    """
    Retourne les initiatives food aid + ONG pertinentes pour une zone donnée.

    Args:
        location: ville / région recherchée.
        limit: nombre max de résultats.

    Returns:
        dict: résultats d'aide alimentaire et ONG.
    """
    try:
        data = _load_data()

        food_items = data.get("food_aid", [])
        org_items = data.get("organizations", [])

        matches: List[Dict[str, Any]] = []

        for item in food_items:
            areas = _safe_list(item.get("areas"))
            if any(_matches_location(location, area) for area in areas):
                verification = verify_resource(item)
                matches.append(
                    {
                        "id": item.get("id"),
                        "type": "food_aid",
                        "name": item.get("name"),
                        "description": item.get("description"),
                        "areas": areas,
                        "services": _safe_list(item.get("services")),
                        "contact": item.get("contact_phone"),
                        "notes": item.get("notes"),
                        "verification": verification,
                    }
                )

        for item in org_items:
            areas = _safe_list(item.get("areas"))
            services = [str(s).lower() for s in _safe_list(item.get("services"))]
            if any(_matches_location(location, area) for area in areas) and (
                "food" in services or "medicine" in services or "clothing" in services
            ):
                verification = verify_resource(item)
                matches.append(
                    {
                        "id": item.get("id"),
                        "type": "organization",
                        "name": item.get("name"),
                        "description": item.get("description"),
                        "areas": areas,
                        "services": _safe_list(item.get("services")),
                        "contact": item.get("contact_phone"),
                        "contact_note": item.get("contact_note"),
                        "verification": verification,
                    }
                )

        return {
            "query_location": location,
            "count": len(matches),
            "results": matches[:limit],
            "warning": "Please confirm availability before going.",
        }
    except Exception as exc:
        return {
            "query_location": location,
            "count": 0,
            "results": [],
            "error": str(exc),
        }


def get_emergency_summary(location: str) -> Dict[str, Any]:
    """
    Retourne un résumé global pour une zone donnée.

    Args:
        location: ville / région recherchée.

    Returns:
        dict: résumé shelters + hotlines + medical + food aid.
    """
    try:
        shelters = get_shelters_by_location(location, limit=3)
        hotlines = get_hotline_by_region(location)
        medical = get_medical_resources()
        food = get_food_and_aid(location, limit=3)

        return {
            "query_location": location,
            "summary": {
                "shelters": shelters.get("results", []),
                "regional_hotlines": hotlines.get("results", []),
                "medical_lines": medical.get("results", []),
                "food_and_aid": food.get("results", []),
            },
            "meta": {
                "shelter_count": shelters.get("count", 0),
                "hotline_count": hotlines.get("count", 0),
                "medical_count": medical.get("count", 0),
                "food_count": food.get("count", 0),
            },
            "disclaimer": (
                "These data are partially verified. Always call before going."
            ),
        }
    except Exception as exc:
        return {
            "query_location": location,
            "summary": {},
            "meta": {},
            "error": str(exc),
        }