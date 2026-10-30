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

## 2026-10-30 - passe d'optimisation & factorisation supplémentaire
- **Modèle** : Gemini 4 Argon (Low)
- **Factorisation & Entités** :
  - `custom_components/rika_firenet/__init__.py` : remplacement des chaînes littérales `"connection_type"` / `"cloud"` / `"host"` par les constantes `CONF_CONNECTION_TYPE`, `CONNECTION_TYPE_CLOUD` et `CONF_HOST` de `const.py`.
  - `custom_components/rika_firenet/core.py` : ajout des méthodes `get_board_temperature()`, `get_outputAirFlapsTargetPosition()`, `get_bake_temperature()` et `set_bake_temperature()` sur `RikaFirenetStove` ; contextualisation du message de notification `_notify_command_timeout()` ("le pont local Open Firenet" vs "le cloud").
  - `custom_components/rika_firenet/sensor.py` : exposition des capteurs diagnostics `board temperature` (°C) et `airflaps target` (%) lorsqu'ils sont disponibles sur le poêle, en parité avec `firenet_mqtt.h`.
  - `test_openfirenet_compat.py` : ajout des assertions sur `board temperature`, `airflaps target`, `bakeTemperature` et `_notify_command_timeout()`.

## 2026-10-30 - Intégration de la gestion des plages horaires de chauffe (Schedule & Buttons)
- **Modèle** : Gemini 3.8 Flash (Low)
- **Objectif** : Conserver l'intégralité du design et des entités existantes de `rika_firenet`, tout en offrant la possibilité de synchroniser et régler les plages de chauffe depuis Home Assistant (parité avec le composant dédié `open-firenet-ha`).
- **Nouveaux modules & fonctionnalités** :
  - `custom_components/rika_firenet/schedule.py` : portage de l'algorithme d'encodage/décodage des plages hebdomadaires (7 jours, 2 créneaux/jour sous format `HHMMHHMM` ou `0` pour désactivé) et conversion depuis les grilles HA Schedule Helpers (`schedule_entity`).
  - `custom_components/rika_firenet/button.py` : ajout de la plateforme `button` avec `schedule_copy` (copie le helper HA sélectionné vers le poêle), `schedule_send` (envoie les créneaux modifiés) et `schedule_discard` (annule les modifications en attente).
  - `custom_components/rika_firenet/time.py` : ajout de la plateforme `time` (28 entités désactivées par défaut pour ajuster manuellement chaque début/fin de plage si souhaité).
  - `custom_components/rika_firenet/binary_sensor.py` : ajout du binary sensor diagnostic `schedule pending` reflétant si des plages sont en attente d'envoi.
  - `custom_components/rika_firenet/config_flow.py` & `const.py` : ajout de l'option `CONF_SCHEDULE_ENTITY` avec sélecteur d'entité `schedule` et ajout des plateformes `Platform.BUTTON` et `Platform.TIME`.
  - `custom_components/rika_firenet/translations/` : mise à jour des traductions `fr.json` et `en.json` pour tous les nouveaux boutons, entités horaires et options.
- **Tests & Validation** :
  - `test_openfirenet_compat.py` : ajout du test `test_schedule_and_buttons` vérifiant l'encodage, le décodage, la validation des plages, la détection des dépassements (> 2 plages), l'interaction du coordinateur, l'instanciation des boutons et des entités `time`. 100% des tests validés (7 tests avec succès).
