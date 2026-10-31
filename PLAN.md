# Plan d'Exécution — rika-firenet-openfirenet-dev

Intégration hybride Open-Firenet / Rika Firenet Cloud basée sur [`antibill51/rika-firenet-custom-component`](https://github.com/antibill51/rika-firenet-custom-component) et l'architecture locale de [`open-firenet-ha`](https://github.com/openfirenet/open-firenet-ha).

## Objectifs Clés
- **Source de base** : fork/adaptation propre de `antibill51/rika-firenet-custom-component`.
- **Zéro MQTT pour l'intégration HA** : communication 100% directe en HTTP REST local avec la clé ESP32 OpenFirenet (`http://<ip_ou_mdns>/api/...`) pour éviter les doublons d'entités avec MQTT Discovery.
- **Rétrocompatibilité Cloud intégrale** : fonctionnement Cloud Rika Firenet inchangé.
- **Bascule Cloud <-> Clé ESP32 sans rupture** : permutation possible dans les options/reconfiguration du même poêle sans recréer ni renommer les entités existantes (`unique_id` stables).
- **Entités spécifiques & Plages horaires** : gestion complète des schedules/plages de chauffe depuis HA et exposition des métriques étendues (températures, cartes, ventilateurs, diagnostiques).
- **Pérennité firmware** : parsing et schémas modulaires pour absorber facilement les futures versions du firmware OpenFirenet ESP32.

---

## Phase 1 : Cadrage du Config Flow & Architecture Hybride
- [ ] **1.1. Modèle de configuration & Options Flow** :
  - Ajouter dans le Config Flow (`config_flow.py`) et l'Options Flow le choix de liaison : `Rika Firenet Cloud` ou `Clé locale OpenFirenet (ESP32)`.
  - Permettre de modifier l'adresse IP / hôte mDNS de l'ESP32 et de rebasculer sur le cloud (ou inversement) sans modifier l'ID de l'appareil ni les `unique_id` des entités.
  - Définition d'un schéma d'identification unifié basé sur le numéro de série / identifiant matériel du poêle.

## Phase 2 : Couche de Transport & Client HTTP Local OpenFirenet
- [ ] **2.1. Client HTTP REST Local Asynchrone (`openfirenet_client.py`)** :
  - Implémenter le client aiohttp interrogeant directement l'API REST de l'ESP32 (`/api/status`, `/api/controls`, `/api/schedule`, `/api/reboot`).
  - Gérer la résilience locale (timeouts, retry, gestion des états transitoires poêle débranché / `503 stove_not_ready`).
  - Éviter rigoureusement toute dépendance ou connexion MQTT dans cette intégration.
- [ ] **2.2. Normalisation des données & Rétrocompatibilité Rika Core** :
  - Normaliser le dictionnaire de statut local OpenFirenet pour qu'il alimente le même `RikaFirenetCoordinator` / objets d'état que le cloud.
  - Préserver l'ensemble des entités standard (`climate`, `sensor`, `binary_sensor`, `switch`, `number`).

## Phase 3 : Gestion Avancée des Plages Horaires & Entités Étendues
- [ ] **3.1. Gestion des plages horaires de chauffe depuis Home Assistant** :
  - Implémenter la lecture et l'écriture des créneaux de chauffe hebdomadaires (`schedule.py` / `/api/schedule`).
  - Exposer des entités `time` / boutons de synchronisation ou service de programmation sans dépendre du cloud Rika.
- [ ] **3.2. Entités spécifiques OpenFirenet** :
  - Exposer les métriques exclusives du firmware (température de carte mère, statut convection/air flaps réels, compteurs détaillés) sous forme d'entités HA diagnostiques.

## Phase 4 : Modularité & Pérennité Firmware
- [ ] **4.1. Adaptabilité aux évolutions firmware ESP32** :
  - Isoler le mapping des registres et payloads dans un module de spécification de versions (`firmware_specs.py`).
  - Tolérance aux champs manquants ou nouveaux attributs renvoyés par l'ESP32.

## Phase 5 : Tests Automatisés & Validation
- [ ] **5.1. Suite de tests unitaires et mocks** :
  - Écrire les tests simulant l'API REST locale OpenFirenet et le Cloud Rika.
  - Vérifier la non-régression du Config Flow, de la bascule de source et de la stabilité des `unique_id`.
  - Vérification de conformité HACS et rechargement sans redémarrage HA.
