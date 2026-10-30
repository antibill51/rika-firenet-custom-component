# Plan de Travail — rika-firenet-openfirenet-dev

## Phase 1 : Audit et Cadrage
- [ ] Analyser l'état actuel de `custom_components/rika_firenet` et des adaptations OpenFirenet existantes.
- [ ] Exécuter et valider la suite de tests de compatibilité `test_openfirenet_compat.py`.
- [ ] Définir les écarts entre les payloads attendus par OpenFirenet et le composant actuel.

## Phase 2 : Intégration Locale OpenFirenet
- [ ] Adapter la couche de communication pour gérer la communication locale directe (HTTP/WebSocket/MQTT selon spécification OpenFirenet).
- [ ] Supporter le basculement local vs cloud (ou mode 100% autonome OpenFirenet).
- [ ] Valider la gestion des entités (températures, consigne, statut flamme, ventilation, mode de fonctionnement).

## Phase 3 : Tests & Validation
- [ ] Écrire les tests unitaires et d'intégration automatisés.
- [ ] Vérifier la rétrocompatibilité et l'absence de régression.
- [ ] Tester le rechargement et la conformité HACS.
