"""Serie de numeración de un equipo de mostrador (RN-11, ADR-0003, research R3).

El contador `device_series` da números 1, 2, 3…; cada uno se convierte en letras como las
columnas de una hoja de cálculo: 1 → `A`, 26 → `Z`, 27 → `AA`, 702 → `ZZ`, 703 → `AAA`.
Como el contador solo avanza, una serie nunca se reutiliza.
"""

MAX_LETTERS = 3


def series_for(number: int) -> str:
    """Letras de la serie número `number` (desde 1), hasta 3 letras."""
    if number < 1:
        raise ValueError("El número de serie empieza en 1")
    letters = ""
    rest = number
    while rest > 0:
        rest, remainder = divmod(rest - 1, 26)
        letters = chr(ord("A") + remainder) + letters
    if len(letters) > MAX_LETTERS:
        raise ValueError("No quedan series disponibles para nuevos equipos")
    return letters
