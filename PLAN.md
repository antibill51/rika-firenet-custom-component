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
- [x] **Optimisations complémentaires** : alignement des `FeatureFlags` avec `open-firenet.ino::mqttDiscoveryStep` (exclusion de `ecoModePossible` sur profil `V28`, détection MultiAir via `controls_pos`, mapping de `board_temperature`, `air_flaps_target_percent`, `bakeTemperature` et créneaux `heatTime*`), exposition des capteurs diagnostics (`board temperature`, `airflaps target`), accesseurs `get_board_temperature()` / `get_outputAirFlapsTargetPosition()` / `get_bake_temperature()` / `set_bake_temperature()`, notification de timeout contextualisée local vs cloud, gestion explicite de `503 stove_not_ready`, et documentation (`README.md`, `info.md`).
- [x] **Phase 4 : Gestion des plages horaires de chauffe (Schedule & Buttons)** :
  - Portage de la logique de planification hebdomadaire (`schedule.py`) compatible OpenFirenet et Rika Cloud.
  - Support de synchronisation directe depuis un helper HA (`schedule_entity`) via le bouton `schedule_copy`.
  - Exposition des plateformes `button` (copier, envoyer, annuler) et `time` (réglage fin des plages par jour).
  - Ajout du binary sensor diagnostique `schedule_pending` pour refléter les modifications en attente.
  - Tests unitaires complets et validation sans régression.
