# Rika Firenet & Open Firenet Integration for Home Assistant

Custom component for Home Assistant to integrate and control RIKA pellet and combi stoves via the official **Rika Firenet Cloud** service or 100% locally using an **Open Firenet** ESP32 bridge.

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=antibill51&repository=rika-firenet-custom-component)

---

## 🌐 Language / Langue

- [🇬🇧 English Documentation](#-english-documentation)
  - [Overview & Philosophy](#overview--philosophy)
  - [Key Features](#key-features)
  - [Installation](#installation)
  - [Configuration & Setup](#configuration--setup)
  - [Switching Cloud / Local (Seamless Migration)](#switching-cloud--local-seamless-migration)
  - [Events & Notifications](#events--notifications)
  - [Lovelace Dashboard Examples](#lovelace-dashboard-examples)
  - [Acknowledgments & Credits](#acknowledgments--credits)
- [🇫🇷 Documentation en Français](#-documentation-en-français)
  - [Présentation & Philosophie](#présentation--philosophie)
  - [Fonctionnalités Clés](#fonctionnalités-clés)
  - [Installation](#installation-1)
  - [Configuration](#configuration-1)
  - [Basculer Cloud / Local (Transition transparente)](#basculer-cloud--local-transition-transparente)
  - [Événements et Notifications](#événements-et-notifications)
  - [Exemples de Cartes Lovelace](#exemples-de-cartes-lovelace)
  - [Remerciements & Crédits](#remerciements--crédits)

---

# 🇬🇧 English Documentation

## Overview & Philosophy

This integration provides a seamless bridge between your RIKA stove and Home Assistant. It supports two operating modes:
1. **Rika Firenet Cloud**: Connects to the official cloud portal ([rika-firenet.com](https://www.rika-firenet.com)) with your user account.
2. **Open Firenet Local HTTP**: Connects directly and 100% locally to an [Open Firenet](https://github.com/openfirenet/open-firenet) ESP32 bridge over your local network using direct HTTP REST calls (`/api/state` and `/api/controls`), without any cloud dependency and without MQTT entity duplicates.

> [!IMPORTANT]
> **Safety Disclaimer**: This integration does not alter the underlying stove firmware, safety limits, or internal mechanics. All operating modes, power levels, convection fan steps, and combustion cycles (ignition, heating, cleaning, burn-off, shutdown) follow the stove's native electronic board specifications.

## Key Features

- **Dual-Mode Connectivity**: Choose between official Cloud or local Open Firenet HTTP bridge.
- **Persistent Entity Identity**: Seamless transition between Cloud and Local modes without renaming entities or breaking dashboards/automations.
- **Thermostat & Climate Control**: Full control over HVAC modes (Off, Heat/Manual, Auto) and presets (Normal/Power %, Comfort/Target Temperature).
- **Comprehensive Sensors**: Room temperature, flame/combustion status, pellet consumption, runtime statistics, error and diagnostic codes.
- **Heating Schedule Synchronization**:
  - View and edit stove heating time slots directly with native HA `time` entities.
  - One-click synchronization from a native Home Assistant `schedule` helper entity to the stove.
- **Command Timeout Detection**: Automatic event firing (`rika_firenet_command_timeout`) and persistent notifications when a command cannot be confirmed by the stove.

## Installation

### Method 1: HACS (Recommended)

1. Open **HACS** in your Home Assistant instance.
2. Search for `Rika Firenet`. If not present in the default store, add this repository as a **Custom Repository** (Category: `Integration`).
3. Click **Download**, then restart Home Assistant.

### Method 2: Manual Installation

1. Browse to your Home Assistant configuration directory (where `configuration.yaml` is located).
2. Create the folder `custom_components/rika_firenet` if it does not already exist.
3. Copy all files from `custom_components/rika_firenet/` of this repository into that folder.
4. Restart Home Assistant.

## Configuration & Setup

Configuration is performed entirely via the Home Assistant user interface:

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **Rika Firenet**.
3. Choose your **Connection Type**:
   - **Rika Firenet Cloud**: Enter your email address and password for [rika-firenet.com](https://www.rika-firenet.com).
   - **Open Firenet Local HTTP**: Enter the IP address or hostname of your ESP32 bridge (e.g. `open-firenet.local` or `192.168.1.50`).

### Integration Options

Click **Configure** on the integration card to adjust runtime parameters:
- **Default temperature**: Fallback target temperature (°C).
- **Scan interval**: Polling interval in seconds (default: `15`).
- **Command confirmation timeout**: Maximum wait time before flagging an unconfirmed command (default: `300` seconds).
- **Heating schedule entity**: Optional link to a native HA `schedule.*` helper for one-click schedule pushing.
- **Platform toggles**: Enable or disable climate, sensors, binary sensors, switches, numbers, buttons, or time entities.

## Switching Cloud / Local (Seamless Migration)

If you already use the Cloud integration and want to switch to a local Open Firenet bridge (or vice-versa):
- The `stove_id` (stove serial number / fabrication number) remains the unique reference key.
- All entities (`climate.*`, `sensor.*`, `number.*`, etc.) keep their exact same `unique_id` and history in Home Assistant.
- To migrate an existing stove:
  - If you reconfigure the entry, the unique entity identifiers remain identical.
  - Dashboards, statistics, and automations continue to operate without any reconfiguration needed.

## Events & Notifications

When controls sent to the stove are not confirmed within the configured timeout window, the integration:
1. Raises a persistent notification in Home Assistant.
2. Dispatches a `rika_firenet_command_timeout` event on the bus (`stove_id`, `stove_name`, `elapsed_seconds`, `timeout_seconds`).

### Example Automation: Mobile Notification

```yaml
alias: "Rika Firenet - Command Timeout Alert"
trigger:
  - trigger: event
    event_type: rika_firenet_command_timeout
action:
  - action: notify.notify
    data:
      title: "Rika Firenet - Command Not Confirmed"
      message: >-
        Controls sent to stove {{ trigger.event.data.stove_name }}
        were not confirmed after {{ trigger.event.data.elapsed_seconds }} seconds.
```

## Lovelace Dashboard Examples

![Lovelace Example](https://raw.githubusercontent.com/antibill51/rika-firenet-custom-component/main/Screenshot/capture.png)

### Recommended Community Cards
- `custom:config-template-card`
- `custom:stack-in-card`
- `custom:simple-thermostat`

### Example Card (Manual / Power Mode %)
```yaml
type: custom:config-template-card
variables:
  IMG: states['climate.rika_domo'].attributes.entity_picture
  POWER: |
    { (states['number.rika_domo_heating_power'].state)*1 }
  STEP: states['number.rika_domo_heating_power'].attributes.step
entities:
  - climate.rika_domo
  - number.rika_domo_heating_power
card:
  type: custom:stack-in-card
  cards:
    - type: picture-elements
      image: https://upload.wikimedia.org/wikipedia/commons/5/59/Empty.png
      elements:
        - type: image
          entity: climate.rika_domo
          image: ${IMG}
          filter: none
          style:
            top: 42%
            left: 50%
            width: 30%
        - type: state-label
          entity: sensor.rika_domo_stove_status
          style:
            top: 17%
            left: 50%
            font-size: 15px
        - type: state-label
          entity: sensor.stove_activity
          prefix: 'Heating power: '
          style:
            top: 97%
            left: 50%
            font-size: 15px
            color: red
        - type: state-label
          entity: climate.rika_domo
          attribute: current_temperature
          suffix: °C
          style:
            color: '#3498db'
            top: 88%
            left: 50%
            font-size: 27px
        - type: state-label
          entity: number.rika_domo_heating_power
          style:
            top: 42%
            left: 85%
            font-size: 35px
            color: orange
    - type: custom:simple-thermostat
      entity: climate.rika_domo
      show_header: false
      decimals: '1'
      control:
        hvac:
          'off':
            name: Off
          'heat':
            name: Manual
          'auto':
            name: Auto
        preset:
          'comfort': 
            name: Comfort
          'none':
            name: Normal
```

## Acknowledgments & Credits

Special thanks to the author and contributors of the **[Open Firenet](https://github.com/openfirenet/open-firenet)** project for developing the ESP32 hardware/firmware bridge and local REST API, making 100% local, cloud-free control of RIKA stoves possible in Home Assistant.

---

# 🇫🇷 Documentation en Français

## Présentation & Philosophie

Cette intégration assure une passerelle complète entre votre poêle à granulés/mixte RIKA et Home Assistant. Elle prend en charge deux modes d'exploitation :
1. **Rika Firenet Cloud** : Connexion au portail officiel ([rika-firenet.com](https://www.rika-firenet.com)) avec vos identifiants utilisateur.
2. **Open Firenet Local HTTP** : Connexion 100% locale à une passerelle ESP32 [Open Firenet](https://github.com/openfirenet/open-firenet) via son API REST HTTP locale (`/api/state` et `/api/controls`), sans dépendance envers le cloud Rika et sans doublon d'entités MQTT.

> [!IMPORTANT]
> **Avertissement & Sécurité** : Cette intégration ne modifie ni les sécurités matérielles, ni les seuils critiques du poêle. Les modes de fonctionnement, puissances, vitesses de convection et cycles de combustion (allumage, régulation, extinction, nettoyage) demeurent strictement régis par la carte électronique d'origine Rika.

## Fonctionnalités Clés

- **Double mode de fonctionnement** : Choisissez entre le cloud officiel et la passerelle locale HTTP Open Firenet.
- **Stabilité et unicité des entités** : Transition transparente Cloud ↔ Local sans modification des identifiants d'entités, préservant vos historiques et vos cartes.
- **Contrôle climatique complet** : Gestion des modes HVAC (Arrêt, Manuel/Chauffe, Automatique) et des presets (Normal / Puissance %, Confort / Température de consigne).
- **Capteurs et diagnostics riches** : Température de pièce, état de la flamme, consommation estimée de granulés, heures de fonctionnement, codes d'erreur et alertes d'entretien.
- **Gestion des plages horaires de chauffe** :
  - Visualisation et ajustement des heures de chauffe via des entités `time` natives Home Assistant.
  - Synchronisation en 1 clic d'un helper natif `schedule` Home Assistant vers le poêle grâce à un bouton dédié.
- **Surveillance des ordres de commande** : Déclenchement automatique d'un événement `rika_firenet_command_timeout` et d'une notification persistante si un ordre envoyé n'est pas acquitté dans le délai imparti.

## Installation

### Méthode 1 : HACS (Recommandée)

1. Ouvrez **HACS** dans votre instance Home Assistant.
2. Recherchez `Rika Firenet`. Si le dépôt n'apparaît pas dans la liste officielle, ajoutez ce dépôt dans **Dépôts personnalisés** (Catégorie : `Intégration`).
3. Cliquez sur **Télécharger**, puis redémarrez Home Assistant.

### Méthode 2 : Installation Manuelle

1. Accédez au répertoire de configuration de votre Home Assistant (dossier contenant `configuration.yaml`).
2. Créez le dossier `custom_components/rika_firenet` s'il n'existe pas.
3. Copiez l'ensemble des fichiers du dossier `custom_components/rika_firenet/` de ce dépôt dans ce nouveau dossier.
4. Redémarrez Home Assistant.

## Configuration

La configuration s'effectue directement depuis l'interface utilisateur de Home Assistant :

1. Rendez-vous dans **Paramètres → Appareils et services → Ajouter une intégration**.
2. Recherchez **Rika Firenet**.
3. Sélectionnez le **Type de connexion** souhaité :
   - **Rika Firenet Cloud** : Renseignez votre adresse email et votre mot de passe [rika-firenet.com](https://www.rika-firenet.com).
   - **Open Firenet Local HTTP** : Renseignez le nom d'hôte ou l'adresse IP de votre passerelle ESP32 (ex. `open-firenet.local` ou `192.168.1.50`).

### Options de l'Intégration

Cliquez sur le bouton **Configurer** sur la carte de l'intégration pour ajuster les paramètres suivants :
- **Température par défaut** : Température cible de secours (°C).
- **Intervalle de rafraîchissement** : Fréquence d'interrogation en secondes (par défaut : `15`).
- **Délai d'expiration des commandes** : Durée maximale d'attente de confirmation d'un ordre avant alerte (par défaut : `300` secondes / 5 minutes).
- **Entité planning de chauffe** : Sélection d'une entité planificateur `schedule.*` de Home Assistant pour la recopie vers le poêle.
- **Activation des plateformes** : Activation ou désactivation sélective des entités (climatisation, capteurs, capteurs binaires, commutateurs, nombres, boutons, horaires).

## Basculer Cloud / Local (Transition transparente)

Pour les utilisateurs disposant déjà de l'intégration en mode Cloud et souhaitant basculer sur une clé locale Open Firenet (ou inversement) :
- L'identifiant unique du poêle (`stove_id` / numéro de fabrication) reste la référence maîtresse.
- Toutes vos entités (`climate.*`, `sensor.*`, `number.*`, etc.) conservent exactement le même `unique_id` dans la base de données Home Assistant.
- Vos automatisations, tableaux de bord Lovelace et historiques de consommation continuent de fonctionner sans aucune coupure ni doublon.

## Événements et Notifications

Si une commande envoyée au poêle ne reçoit pas de confirmation dans le délai configuré (par défaut 5 minutes), l'intégration :
1. Crée une notification persistante dans Home Assistant (`persistent_notification`).
2. Émet l'événement `rika_firenet_command_timeout` sur le bus d'événements (`stove_id`, `stove_name`, `elapsed_seconds`, `timeout_seconds`).

### Exemple d'Automatisation : Notification Mobile (HA Companion)

```yaml
alias: "Rika Firenet - Alerte échec de commande (Mobile)"
trigger:
  - trigger: event
    event_type: rika_firenet_command_timeout
action:
  - action: notify.notify
    data:
      title: "Rika Firenet - Commande non confirmée"
      message: >-
        Les réglages envoyés au poêle {{ trigger.event.data.stove_name }}
        n'ont pas pu être confirmés après {{ trigger.event.data.elapsed_seconds }} secondes.
```

### Exemple d'Automatisation : Notification Telegram

```yaml
alias: "Rika Firenet - Alerte échec de commande (Telegram)"
trigger:
  - trigger: event
    event_type: rika_firenet_command_timeout
action:
  - action: notify.telegram
    data:
      title: "⚠️ Rika Firenet - Commande non confirmée"
      message: >-
        Les réglages envoyés au poêle {{ trigger.event.data.stove_name }}
        n'ont pas pu être confirmés par le poêle après {{ trigger.event.data.elapsed_seconds }} secondes.
```

## Exemples de Cartes Lovelace

![Capture Lovelace](https://raw.githubusercontent.com/antibill51/rika-firenet-custom-component/main/Screenshot/capture.png)

### Cartes communautaires recommandées
- `custom:config-template-card`
- `custom:stack-in-card`
- `custom:simple-thermostat`

### Carte Lovelace : Mode Puissance % (Manuel)
```yaml
type: custom:config-template-card
variables:
  IMG: states['climate.rika_domo'].attributes.entity_picture
  POWER: |
    { (states['number.rika_domo_heating_power'].state)*1 }
  STEP: states['number.rika_domo_heating_power'].attributes.step
entities:
  - climate.rika_domo
  - number.rika_domo_heating_power
card:
  type: custom:stack-in-card
  cards:
    - type: picture-elements
      image: https://upload.wikimedia.org/wikipedia/commons/5/59/Empty.png
      elements:
        - type: image
          entity: climate.rika_domo
          image: ${IMG}
          filter: none
          style:
            top: 42%
            left: 50%
            width: 30%
        - type: state-label
          entity: sensor.rika_domo_stove_status
          style:
            top: 17%
            left: 50%
            font-size: 15px
        - type: state-label
          entity: sensor.stove_activity
          prefix: 'Puissance de chauffe : '
          style:
            top: 97%
            left: 50%
            font-size: 15px
            color: red
        - type: state-label
          entity: sensor.rika_domo_pellets_before_service
          prefix: 'Service : '
          style:
            top: 97%
            left: 90%
            font-size: 11px
        - type: state-label
          entity: climate.rika_domo
          attribute: current_temperature
          suffix: °C
          style:
            color: '#3498db'
            top: 88%
            left: 50%
            font-size: 27px
        - type: state-label
          entity: number.rika_domo_heating_power
          style:
            top: 42%
            left: 85%
            font-size: 35px
            color: orange
    - type: custom:simple-thermostat
      entity: climate.rika_domo
      show_header: false
      decimals: '1'
      unit: °c
      step_size: '0.5'
      control:
        hvac:
          'off':
            name: Arrêt
          'heat':
            name: Manuel
          'auto':
            name: Automatique
        preset:
          'comfort': 
            name: Confort
          'none':
            name: Normal
```

---

## Contributions

Les contributions, signalements de bugs et suggestions sont les bienvenus via les [Issues GitHub](https://github.com/antibill51/rika-firenet-custom-component/issues) et [Pull Requests](https://github.com/antibill51/rika-firenet-custom-component/pulls).
Veuillez vous référer au fichier [CONTRIBUTING.md](CONTRIBUTING.md).

## Remerciements & Crédits

Un grand merci à l'auteur et aux contributeurs du projet **[Open Firenet](https://github.com/openfirenet/open-firenet)** pour la conception et le développement de la passerelle matérielle/logicielle ESP32 et de son API REST locale, rendant possible le pilotage 100% local et indépendant du cloud de nos poêles RIKA sous Home Assistant.
