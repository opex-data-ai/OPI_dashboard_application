from nicegui import ui
from config import THEME

def app_card(title: str, content_callback):
    """
    Reusable card for login, KPI cards, domain cards.
    """
    with ui.card().classes(f'p-6 {THEME["card_shadow"]} {THEME["card_radius"]} mb-4 w-96 bg-white'):
        ui.label(title).classes(f'{THEME["font_heading"]} mb-4 text-center')
        content_callback()
