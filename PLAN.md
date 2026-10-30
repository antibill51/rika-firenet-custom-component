# Plan de Travail — rika-firenet-openfirenet-dev

## Phase 1 : Audit et Cadrage
- [x] Analyser l'état actuel de `custom_components/rika_firenet` et des adaptations OpenFirenet existantes.
- [x] Exécuter et valider la suite de tests de compatibilité `test_openfirenet_compat.py`.
- [x] Définir les écarts entre les payloads attendus par OpenFirenet et le composant actuel.

## Phase 2 : Intégration Locale OpenFirenet
- [x] Adapter la couche de communication pour gérer la communication locale directe (HTTP/WebSocket/MQTT selon spécification OpenFirenet).
- [x] Supporter le basculement local vs cloud (ou mode 100% autonome OpenFirenet).
- [x] Valider la gestion des entités (températures, consigne, statut flamme, ventilation, mode de fonctionnement).

## Phase 3 : Tests & Validation
- [x] Écrire les tests unitaires et d'intégration automatisés.
- [x] Vérifier la rétrocompatibilité et l'absence de régression.
- [x] Tester le rechargement et la conformité HACS.
- [x] **Optimisations complémentaires** : alignement des `FeatureFlags` avec `open-firenet.ino::mqttDiscoveryStep` (exclusion de `ecoModePossible` sur profil `V28`, détection MultiAir via `controls_pos`, mapping de `board_temperature`, `air_flaps_target_percent`, `bakeTemperature` et créneaux `heatTime*`), gestion explicite de `503 stove_not_ready`, et documentation (`README.md`, `info.md`).
