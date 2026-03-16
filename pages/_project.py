'''from nicegui import ui
from config import THEME


def show_project_page():
    with ui.column().classes('w-full'):
        ui.label('Project & Staff Performance').classes(
            f'{THEME["font_heading"]} mb-2'
        )
        ui.label(
            'Track projects, tasks, and staff productivity.'
        ).classes(f'{THEME["font_body"]} mb-6')

        with ui.card().classes(
            f'p-6 {THEME["card_shadow"]} {THEME["card_radius"]}'
        ):
            ui.label('Project dashboards will appear here').classes(
                THEME["font_body"]
            )
'''