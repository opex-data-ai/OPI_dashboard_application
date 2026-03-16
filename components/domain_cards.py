from nicegui import ui
from config import THEME
from components.button import primary_button

def domain_card(name):
    """Clickable domain entry card"""
    def click():
        print(f"{name} domain clicked")
        ui.notify(f"{name} clicked (test)")
    
    with ui.card().classes(f'p-6 {THEME["card_shadow"]} {THEME["card_radius"]} mb-4 w-64 cursor-pointer bg-white hover:shadow-xl transition-shadow'):
        ui.label(name).classes(f'{THEME["font_heading"]} text-center')
        primary_button(f"Go to {name}", on_click=click).classes('mt-2')
