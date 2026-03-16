from nicegui import ui

def project_sidebar():
    ui.label('Projects').classes('text-lg font-semibold mb-4')

    ui.link('Projects', '/project?tab=projects')
    ui.link('Tasks', '/project?tab=tasks')
    ui.link('Staff', '/project?tab=staff')
