# Journal de Bord — rika-firenet-openfirenet-dev

## 2026-10-30 - Importation du projet dans Temps Perdu
- Importation du dépôt réel depuis `/home/sandbox/github/rika-firenet-openfirenet-dev`.
- Création de `PROJET.md`, `PLAN.md` et `JOURNAL.md`.
- Désactivation du projet générique `open-firenet` et passage de `rika-firenet-openfirenet-dev` en Priorité 1 dans `PRIORITES.md`.

## 2026-10-30 - Exécution Complète (Phases 1, 2, 3 & Optimisations)
- **Modèle** : Gemini 4 Argon (Low)
- **Phase 1 (Audit & Cadrage)** :
  - Audit complet de `custom_components/rika_firenet` (`__init__.py`, `config_flow.py`, `const.py`, `core.py`, `entity.py`, `climate.py`, `sensor.py`, `binary_sensor.py`, `switch.py`, `number.py`) face au firmware ESP32-S3 `open-firenet.ino`.
  - Validation des correctifs d'audit existants (`target_temperature: null` en mode manuel, séparation `RoomPowerRequest` vs `power_percent`, repli des binary_sensors sur `sensors.*`, état `offline` via `lastSeenMinutes = 99` quand `version_ack == False`).
- **Phase 2 (Intégration Locale OpenFirenet & Optimisations)** :
  - Enrichissement de `RikaFirenetCoordinator._normalize_openfirenet_state()` dans `custom_components/rika_firenet/core.py` :
    - Alignement strict des `stoveFeatures` sur `open-firenet.ino::mqttDiscoveryStep` : exclusion de `ecoModePossible` sur les poêles en profil `V28` (INDUO II 2.28), prise en compte de `air_flaps_target_percent` / `airFlapsTarget`, et repli sur `controls_pos` (`len > 23` / `len > 26`) pour `multiAir1` et `multiAir2`.
    - Normalisation additionnelle de `inputBoardTemperature` (`board_temperature` / `boardSensor`), `outputAirFlapsTargetPosition` (`air_flaps_target_percent`) et `bakeTemperature` (`bake_target_temperature`).
  - Amélioration de `set_stove_controls()` en mode local : prise en charge de `bakeTemperature` (`bake_target_temperature`), des 14 plages horaires `heatTime*`, et journalisation dédiée lors d'une réponse HTTP `503 stove_not_ready`.
- **Phase 3 (Tests, Rechargement, Conformité HACS & Documentation)** :
  - Extension de `test_openfirenet_compat.py` (6 suites de tests unitaires et d'intégration couvrant : normalisation DOMO, cas limites manuel/hors-ligne, découverte locale, envoi de commandes REST, exclusion `ecoModePossible` en profil `V28`, instanciation de toutes les plateformes `climate`/`sensor`/`binary_sensor`/`switch`/`number`, `ConfigFlow`, cycle `async_setup_entry` / `async_unload_entry`, et validation `hacs.json` + `manifest.json` + 4 fichiers de traduction `fr`/`en`/`de`/`nl`).
  - Mise à jour de `README.md` et `info.md` pour documenter le mode **Open Firenet Local HTTP**.
