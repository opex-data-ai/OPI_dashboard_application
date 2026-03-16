from nicegui import ui

def settings_sidebar():
    ui.label('Settings').classes('text-lg font-semibold mb-4')

    ui.link('Profile', '/settings?tab=profile')
    ui.link('Notifications', '/settings?tab=notifications')
    ui.link('Security', '/settings?tab=security')
