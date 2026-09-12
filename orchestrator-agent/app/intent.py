CLASS_KEYWORDS = ["yoga", "spinning", "crossfit", "pilates"]

BOOKING_KEYWORDS = ["reserva", "resérvame", "reservame", "inscríbeme", "inscribeme", "apúntame", "apuntame"]
NOTIFICATION_KEYWORDS = ["notif", "avísame", "avisame", "notifica", "avisa"]


def parse_instruction(text: str) -> dict:
    """Interpretación basada en reglas (no es un LLM real) de una
    instrucción como 'Reserva yoga para el viernes y avísame por
    notificación'. Suficiente para el propósito de este demo: identificar
    qué agentes hay que involucrar y con qué datos."""
    text_lower = text.lower()

    wants_booking = any(k in text_lower for k in BOOKING_KEYWORDS)
    wants_notification = any(k in text_lower for k in NOTIFICATION_KEYWORDS)
    class_name = next((c for c in CLASS_KEYWORDS if c in text_lower), None)

    return {
        "wants_booking": wants_booking,
        "wants_notification": wants_notification,
        "class_name": class_name,
    }
