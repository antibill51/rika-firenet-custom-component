# Projet : rika-firenet-openfirenet-dev

## 🎯 Contexte & Objectif
Composant d'intégration Home Assistant unifié pour poêles à granulés RIKA, basé sur [`antibill51/rika-firenet-custom-component`](https://github.com/antibill51/rika-firenet-custom-component) et adapté pour supporter la clé locale ESP32 OpenFirenet ([`open-firenet-ha`](https://github.com/openfirenet/open-firenet-ha)) en **HTTP REST direct**.

## 📌 Directives Clés
1. **Pas de MQTT** : La clé ESP32 dispose d'un serveur HTTP REST complet (`/api/...`). Utiliser exclusivement les appels HTTP REST locaux afin d'éviter tout doublon d'entités avec la découverte MQTT native Home Assistant.
2. **Dual-Mode Cloud / Clé locale** : Possibilité de configurer ou faire basculer le poêle entre Rika Firenet Cloud et la clé locale ESP32 à chaud.
3. **Stabilité des Entités** : Les `unique_id` et noms d'entités doivent rester strictement identiques lors d'un basculement de mode (pas de duplication ni d'entités orphelines dans Home Assistant).
4. **Gestion des Horaires de Chauffe** : Permettre la visualisation et l'édition des plages horaires de fonctionnement depuis l'interface Home Assistant.
5. **Résilience et Évolutivité Firmware** : Architecture découplée pour intégrer sans friction les mises à jour futures du firmware OpenFirenet ESP32.

## 📂 Architecture
- `custom_components/rika_firenet/` : code source du composant HA.
- `HA config/` : exemples de dashboards Lovelace et automatisations.
- `tests/` : tests unitaires d'intégration (REST local + Cloud).
