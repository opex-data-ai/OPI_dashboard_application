from nicegui import ui
import config   # import the whole module, not THEME

def primary_button(label: str, on_click):
    """Reusable primary button following theme."""
    return ui.button(label, on_click=on_click)\
        .props('color=None')\
        .classes(
        f'{config.THEME["input_width"]} '
        f'bg-{config.THEME["primary_color"]} '
        f'text-white hover:bg-{config.THEME["primary_hover"]} '
        f'rounded-md {config.THEME["button_height"]} font-medium shadow-sm'
    )

def secondary_button(label: str, on_click):
    """Reusable secondary button with accent color."""
    return ui.button(label, on_click=on_click)\
        .props('color=None')\
        .classes(
        f'{config.THEME["input_width"]} '
        f'bg-{config.THEME["secondary_color"]} '
        f'text-white hover:bg-{config.THEME["secondary_hover"]} '
        f'rounded-md {config.THEME["button_height"]} font-medium shadow-sm'
    )
