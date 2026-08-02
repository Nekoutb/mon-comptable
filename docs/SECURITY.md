# Notes de sécurité

- Remplacer `MC_JWT_SECRET` avant tout déploiement.
- Terminer TLS au niveau du proxy ou de la plateforme cloud.
- Stocker les secrets ERP dans un gestionnaire de secrets; aucun secret ERP n'est implémenté en clair.
- Le stockage local est réservé au développement. Utiliser un adaptateur S3/Blob/MinIO avec chiffrement en production.
- Brancher un antivirus avant d'accepter des documents de production.
- Configurer CORS avec les origines réelles via `MC_CORS_ORIGINS` (liste séparée par des virgules) et appliquer une limitation de débit au proxy/API gateway.
- Les journaux d'audit sont append-only au niveau applicatif; une politique WORM ou une réplication séparée est recommandée en production.
- Les adaptateurs ERP et OCR actuels sont simulés et n'envoient aucune donnée à un tiers.
