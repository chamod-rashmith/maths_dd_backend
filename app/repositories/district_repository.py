"""
District Repository with Persistent Redis / In-Memory Caching (0 TTL).
Provides high-performance, zero-DB-overhead lookup for Sri Lankan Administrative Districts.
Supports querying by Integer ID (1-25) and Unique String Code (e.g. 'COLOMBO').
"""

import logging
from typing import Any, Dict, List, Optional, Union
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import districts_cache
from app.domain.exceptions import DatabaseOperationError
from app.models.district import District

logger = logging.getLogger("maths_dd.district_repo")

DISTRICT_CACHE_KEY = "districts:all"
DISTRICTS_CACHE_KEY = DISTRICT_CACHE_KEY

# Standard 3-letter Sri Lankan district abbreviations -> canonical District.code
DISTRICT_CODE_ALIASES: Dict[str, str] = {
    "CMB": "COLOMBO",
    "COL": "COLOMBO",
    "GMP": "GAMPAHA",
    "GAM": "GAMPAHA",
    "KLT": "KALUTARA",
    "KAL": "KALUTARA",
    "KDY": "KANDY",
    "KAN": "KANDY",
    "MTL": "MATALE",
    "NWE": "NUWARA_ELIYA",
    "NUW": "NUWARA_ELIYA",
    "NUWARAELIYA": "NUWARA_ELIYA",
    "NUWARA ELIYA": "NUWARA_ELIYA",
    "GLE": "GALLE",
    "GAL": "GALLE",
    "MTR": "MATARA",
    "MAT": "MATARA",
    "HMB": "HAMBANTOTA",
    "HAM": "HAMBANTOTA",
    "JFN": "JAFFNA",
    "JAF": "JAFFNA",
    "KLN": "KILINOCHCHI",
    "KIL": "KILINOCHCHI",
    "MNR": "MANNAR",
    "MAN": "MANNAR",
    "VAV": "VAVUNIYA",
    "VNI": "VAVUNIYA",
    "MUL": "MULLAITIVU",
    "MLT": "MULLAITIVU",
    "BTC": "BATTICALOA",
    "BAT": "BATTICALOA",
    "AMP": "AMPARA",
    "APR": "AMPARA",
    "TRN": "TRINCOMALEE",
    "TRI": "TRINCOMALEE",
    "KUR": "KURUNEGALA",
    "KRN": "KURUNEGALA",
    "PUT": "PUTTALAM",
    "PTL": "PUTTALAM",
    "ANU": "ANURADHAPURA",
    "ADP": "ANURADHAPURA",
    "POL": "POLONNARUWA",
    "PLN": "POLONNARUWA",
    "BAD": "BADULLA",
    "BDL": "BADULLA",
    "MON": "MONARAGALA",
    "MNRG": "MONARAGALA",
    "RAT": "RATNAPURA",
    "RTP": "RATNAPURA",
    "KEG": "KEGALLE",
    "KGL": "KEGALLE",
}


class DistrictRepository:
    """Repository for querying Sri Lankan Administrative Districts with persistent Redis caching."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_all(self) -> List[Dict[str, Any]]:
        """
        Returns all 25 Sri Lankan districts ordered by display_order.
        Serves from Upstash Serverless Redis / In-Memory cache without TTL if available.
        """
        # 1. Attempt persistent cache lookup
        cached = districts_cache.get(DISTRICTS_CACHE_KEY)
        if cached is not None and isinstance(cached, list):
            logger.debug("Serving %d districts directly from cache.", len(cached))
            return cached

        # 2. Cache miss -> query PostgreSQL database
        try:
            stmt = select(District).order_by(District.display_order.asc(), District.id.asc())
            result = await self._session.execute(stmt)
            districts = result.scalars().all()

            if not districts:
                logger.info("Districts table is empty. Auto-seeding 25 Sri Lankan districts...")
                from app.core.seed import DISTRICTS_SEED
                for d in DISTRICTS_SEED:
                    self._session.add(District(**d))
                await self._session.commit()
                result = await self._session.execute(stmt)
                districts = result.scalars().all()

            data = [
                {
                    "id": d.id,
                    "code": d.code,
                    "name_en": d.name_en,
                    "name_si": d.name_si,
                    "name_ta": d.name_ta,
                    "province": d.province,
                }
                for d in districts
            ]

            # 3. Store in Redis / In-Memory cache with ttl_seconds=0 (no expiration)
            if data:
                districts_cache.set(DISTRICTS_CACHE_KEY, data, ttl_seconds=0)
                logger.info("Cached %d districts indefinitely in Redis/Memory.", len(data))

            return data
        except Exception as exc:
            logger.error("Failed to fetch districts from database: %s", exc)
            raise DatabaseOperationError(str(exc)) from exc

    async def get_by_id(self, district_id: int) -> Optional[Dict[str, Any]]:
        """Finds a single district by its integer ID (1-25)."""
        all_districts = await self.get_all()
        for d in all_districts:
            if d.get("id") == district_id:
                return d
        return None

    async def get_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Finds a single district by its string code (e.g. 'COLOMBO') or 3-letter alias (e.g. 'CMB')."""
        all_districts = await self.get_all()
        raw_target = code.strip().upper()
        canonical_target = DISTRICT_CODE_ALIASES.get(raw_target, raw_target)
        for d in all_districts:
            if str(d.get("code", "")).upper() in (raw_target, canonical_target):
                return d
            if str(d.get("name_en", "")).upper() == raw_target:
                return d
        return None

    async def resolve_district(self, identifier: Union[int, str]) -> Optional[Dict[str, Any]]:
        """Resolves an integer ID (1-25), numeric string ('1'), code ('COLOMBO'), or abbreviation ('CMB') to a district dict."""
        if isinstance(identifier, int):
            return await self.get_by_id(identifier)
        if isinstance(identifier, str):
            cleaned = identifier.strip()
            if not cleaned:
                return None
            if cleaned.isdigit():
                return await self.get_by_id(int(cleaned))
            return await self.get_by_code(cleaned)
        return None

    async def resolve_district_id(self, identifier: Union[int, str]) -> Optional[int]:
        """Resolves an integer ID or string code/abbreviation into a valid district integer ID."""
        d = await self.resolve_district(identifier)
        return int(d["id"]) if d and d.get("id") is not None else None

    @staticmethod
    def invalidate_cache() -> None:
        """Evicts districts cache across Redis and In-Memory."""
        districts_cache.invalidate_prefix("districts:")
        logger.info("Districts cache successfully invalidated.")
