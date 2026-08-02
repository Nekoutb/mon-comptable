# Limitations connues

- ERP, OCR, e-mail, antivirus et stockage objet sont simulés ou représentés par des points d'extension. Aucune connexion externe n'est présentée comme active.
- Les parseurs bancaires couvrent CSV, MT940 et CAMT.053; le format est détecté par l'extension du fichier (.csv, .txt, .sta, .mt940, .xml, .camt).
- Le worker asynchrone (Redis/RQ) exécute l'OCR des factures lorsque `MC_BACKGROUND_MODE=rq`; le mode par défaut `inline` traite le job dans la requête. Le traitement des e-mails entrants reste un point d'extension (les pièces jointes ne sont pas encore converties en factures).
- L'interface importe les factures; l'import de relevés bancaires passe par l'API `/api/v1/bank-statements/upload` (interface à venir).
- Les règles fiscales fournies sont des données fictives de démonstration et ne constituent pas un conseil fiscal camerounais.
- La plateforme doit faire l'objet d'une revue de sécurité, d'une validation comptable et de tests de charge avant toute utilisation avec des données réelles.
