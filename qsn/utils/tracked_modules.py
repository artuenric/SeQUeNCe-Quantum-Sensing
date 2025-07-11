# tracked_modules.py
# Lista de todos os nossos módulos customizados que queremos observar.
# O sistema de log irá automaticamente filtrar e mostrar apenas os que forem executados na simulação atual.
# Sempre adicionar novos módulos aqui quando forem criados ou modificados.

TRACKED_MODULES = [
    "hub_ghz_active_app",
    "sensor_ghz_active_app",
    "message_ghz_active",
    "sensor_ghz_active_fallback_app"
]
