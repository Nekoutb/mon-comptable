# Architecture technique

Mon Comptable est structuré comme un monorepo avec une interface Next.js et une API FastAPI. PostgreSQL est la base de production, Redis est prévu pour les tâches asynchrones et le développement local peut utiliser SQLite.

Les données métier portent systématiquement une frontière `tenant_id`; les requêtes API filtrent par le locataire issu du jeton signé. Les écritures comptables passent par des validations déterministes après les recommandations. Les montants utilisent `Decimal`/`Numeric`, jamais des nombres flottants.

Les adaptateurs `ERPAdapter` et `OCRAdapter` isolent les fournisseurs externes. La version locale utilise uniquement `MockERPAdapter` et `MockOCRAdapter`, identifiés comme tels dans les réponses de santé et de comptabilisation.

## Modules

- Accounts Payable : dépôt, OCR, rapprochement fournisseur, doublons, proposition, approbation, brouillon ERP et comptabilisation.
- Treasury : dépôt CSV, parsing, contrôle des lignes, équilibre du relevé et import ERP.
- Socle : authentification, rôles, isolation locataire, stockage documentaire et audit.
