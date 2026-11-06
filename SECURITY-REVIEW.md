# ආරක්ෂක සමාලෝචන වාර්තාව

සමාලෝචනය කළේ: 2026-11-06  
සමාලෝචන පරාසය: සම්පූර්ණ backend codebase, configuration, migrations, Dockerfile, dependencies සහ tests.

## සොයාගත් අවදානම්

| # | Severity | File | Lines | Vulnerability | Confidence |
|---|----------|------|-------|---------------|------------|
| 1 | 🟠 HIGH | `app/api/v1/endpoints/subscriptions.py` | 254-261 | `REVENUECAT_WEBHOOK_AUTH_TOKEN` හිස් නම් RevenueCat webhook authentication සම්පූර්ණයෙන්ම මඟහැරේ. එමඟින් attacker කෙනෙකුට වලංගු ආකාරයේ payload යවා ඕනෑම user කෙනෙකුට premium subscription ලබාදිය හැක. | 10/10 |
| 2 | 🟡 MEDIUM | `app/api/v1/endpoints/health.py` | 89-101 | `/db-seed` GET සහ POST endpoints authentication/authorization නොමැතිව public වේ. ඒවා database writes සිදු කර default `ADMIN` user එක නැවත seed කරයි. | 9/10 |

## නිර්දේශිත විසඳුම්

1. Production environment තුළ RevenueCat webhook secret එක අනිවාර්ය කර, secret එක නොමැති විට request එක fail closed ලෙස reject කරන්න. RevenueCat හි signed webhook verification ක්‍රමය භාවිතා කරන්න.
2. `/db-seed` HTTP endpoints ඉවත් කරන්න. අවශ්‍ය නම් දැඩි admin authorization එකක් සහ internal-only network restriction එකක් යොදන්න.

## අවදානම් නොසොයා සමාලෝචනය කළ ප්‍රදේශ

- Firebase ID-token verification සහ authenticated user scoping
- Admin/editor RBAC සහ protected CRUD routes
- Student progress, bookmarks, XP history සහ question ownership queries
- Premium study-note access gating
- SQLAlchemy repository queries සහ parameterization
- Docker non-root execution සහ container configuration
- Migration සහ schema code
- Storage URL generation සහ signed upload/download flows
- Dependency lockfile සහ committed secrets පරීක්ෂාව
