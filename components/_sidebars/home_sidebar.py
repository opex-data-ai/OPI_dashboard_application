from nicegui import ui

def home_sidebar():
    ui.label('Home').classes('text-lg font-semibold mb-4')

    ui.link('Overview', '/home')
    ui.link('Quick Insights', '/home')
