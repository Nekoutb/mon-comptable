# Architecture technique

Mon Comptable est structuré comme un monorepo avec une interface Next.js et une API FastAPI. PostgreSQL est la base de production, Redis est prévu pour les tâches asynchrones et le développement local peut utiliser SQLite.

Les données métier portent systématiquement une frontière `tenant_id`; les requêtes API filtrent par le locataire issu du jeton signé. Les écritures comptables passent par des validations déterministes après les recommandations. Les montants utilisent `Decimal`/`Numeric`, jamais des nombres flottants.

Les adaptateurs `ERPAdapter` et `OCRAdapter` isolent les fournisseurs externes. La version locale utilise uniquement `MockERPAdapter` et `MockOCRAdapter`, identifiés comme tels dans les réponses de santé et de comptabilisation.

Les traitements longs passent par des jobs suivis en base (`background_jobs`). En mode `inline` (défaut), le job s'exécute dans la requête; en mode `rq`, il est confié au worker Redis/RQ (`python -m app.worker`). L'OCR des factures est le premier traitement câblé sur ce mécanisme. Chaque requête porte un identifiant de corrélation (`X-Correlation-ID`) propagé jusqu'aux journaux d'audit et aux jobs.

Le cycle de vie d'une facture est verrouillé après soumission : les statuts `pending_approval`, `approved`, `erp_draft` et `posted` bloquent l'édition, le rapprochement et la régénération de proposition. Toute modification de montant invalide la proposition validée. Les clés d'idempotence ERP sont uniques par locataire.

## Modules

- Accounts Payable : dépôt, OCR, rapprochement fournisseur, doublons (exact et probable), proposition, approbation à quatre yeux, brouillon ERP et comptabilisation.
- Treasury : dépôt CSV/MT940/CAMT.053, parsing, contrôle des lignes, équilibre du relevé et import ERP idempotent.
- Socle : authentification (avec désambiguïsation par code locataire), rôles, isolation locataire, stockage documentaire, audit et jobs.
