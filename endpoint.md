============================================================
1. ACCOUNTS
============================================================

POST   /api/accounts/register/                    ✅
POST   /api/accounts/login/                       ✅
GET    /api/accounts/me/                          ✅
POST   /api/accounts/verification/                ✅

GET    /api/accounts/users/                        ✅
POST   /api/accounts/users/                        ✅
GET    /api/accounts/users/<id>/                   ✅
PUT    /api/accounts/users/<id>/                   ✅
PATCH  /api/accounts/users/<id>/                   ✅
DELETE /api/accounts/users/<id>/                   ✅

POST   /api/accounts/users/<id>/role/              ✅
POST   /api/accounts/users/<id>/status/            ✅

GET    /api/accounts/verifications/                ✅
POST   /api/accounts/verifications/<id>/approve/   ✅
POST   /api/accounts/verifications/<id>/reject/    ✅


============================================================
2. CASES
============================================================

GET    /api/cases/                                 ✅
POST   /api/cases/                                 ✅
GET    /api/cases/<id>/                            ✅
PUT    /api/cases/<id>/                            ✅
PATCH  /api/cases/<id>/                            ✅
DELETE /api/cases/<id>/                            ✅


============================================================
3. COMPLAINTS
============================================================

GET    /api/complaints/                            ✅
POST   /api/complaints/                            ✅
GET    /api/complaints/<id>/                       ✅
PUT    /api/complaints/<id>/                       ✅
PATCH  /api/complaints/<id>/                       ✅
DELETE /api/complaints/<id>/                       ✅


============================================================
4. DOCUMENTS
============================================================

GET    /api/documents/documents/                   ✅
POST   /api/documents/documents/                   ✅
GET    /api/documents/documents/<id>/              ✅
PUT    /api/documents/documents/<id>/              ✅
PATCH  /api/documents/documents/<id>/              ✅
DELETE /api/documents/documents/<id>/              ✅

GET    /api/documents/documents/<id>/download/     ✅
GET    /api/documents/documents/<id>/versions/     ✅
POST   /api/documents/documents/<id>/new-version/  ✅
GET    /api/documents/documents/<id>/verify-integrity/ ✅

POST   /api/documents/documents/<id>/share/        ✅
GET    /api/documents/documents/shared-with-me/    ✅
POST   /api/documents/documents/<id>/archive/      ✅

POST   /api/documents/documents/<id>/sign/         ✅
POST   /api/documents/documents/<id>/verify-signature/ ✅


============================================================
5. EVIDENCE
============================================================

GET    /api/evidence/                             ✅
POST   /api/evidence/                             ✅
GET    /api/evidence/<id>/                        ✅
PUT    /api/evidence/<id>/                        ✅
PATCH  /api/evidence/<id>/                        ✅
DELETE /api/evidence/<id>/                        ✅

❌ /api/evidence/<id>/download/
❌ /api/evidence/<id>/verify-integrity/


============================================================
6. WITNESS STATEMENTS
============================================================

GET    /api/investigations/witness-statements/             ✅
POST   /api/investigations/witness-statements/             ✅
GET    /api/investigations/witness-statements/<id>/        ✅
PUT    /api/investigations/witness-statements/<id>/        ✅
PATCH  /api/investigations/witness-statements/<id>/        ✅
DELETE /api/investigations/witness-statements/<id>/        ✅


============================================================
7. LEGAL REVIEWS
============================================================

GET    /api/legal/reviews/                         ✅
POST   /api/legal/reviews/                         ✅
GET    /api/legal/reviews/<id>/                    ✅
PUT    /api/legal/reviews/<id>/                    ✅
PATCH  /api/legal/reviews/<id>/                   ✅
DELETE /api/legal/reviews/<id>/                   ✅

❌ /api/legal/reviews/<id>/approve/
❌ /api/legal/reviews/<id>/reject/


============================================================
8. COURT HEARINGS
============================================================

GET    /api/legal/hearings/                        ✅
POST   /api/legal/hearings/                        ✅
GET    /api/legal/hearings/<id>/                   ✅
PUT    /api/legal/hearings/<id>/                   ✅
PATCH  /api/legal/hearings/<id>/                  ✅
DELETE /api/legal/hearings/<id>/                  ✅

❌ /api/legal/hearings/<id>/complete/
============================================================
9. AUDIT
============================================================

GET    /api/audit/logs/                            ✅
GET    /api/audit/logs/<id>/                       ✅
GET    /api/audit/logs/verify-integrity/           ✅

============================================================
11. DIGITAL SIGNATURE
============================================================

POST   /api/documents/documents/<id>/sign/             ✅
POST   /api/documents/documents/<id>/verify-signature/ ✅

❌ /api/documents/documents/<id>/signature/


============================================================
12. AI
============================================================

POST   /api/ai/analyze/                           ✅
POST   /api/ai/summarize/                         ✅
POST   /api/ai/classify/                          ✅
POST   /api/ai/extract/                           ✅

❌ /api/ai/


=========================================
2nd verstion 
====================================


