# pages/settings.py
from nicegui import ui, app, run
from components.dashboard_layout import dashboard_layout
from components.theme_manager import ThemeManager
from services.auth_service import (
    update_user_profile, 
    update_password, 
    verify_password,
    get_user_settings, 
    update_user_settings,
    get_user_notifications, 
    update_user_notifications,
    update_account_status
)

async def show_settings_page():
    # Get user info from session
    email = app.storage.user.get('email', '')
    first_name = app.storage.user.get('first_name', '')
    last_name = app.storage.user.get('last_name', '')
    
    # Fetch settings from storage (populated on login) to avoid API timeout
    notifications = app.storage.user.get('notifications', {}) or {}
    
    # Ensure all keys exist in notifications to avoid UI errors
    default_notifications = {
        'email_notifications': False,
        'weekly_reports': False,
        'kpi_alerts': False,
        'anomaly_detection': False,
        'in-app_notifications': True
    }
    # Merge defaults with stored values
    notifications = {**default_notifications, **notifications}
    

    
    async def content():
        # Header
        ui.label('Settings').classes('text-2xl font-bold text-slate-800 mb-1')
        ui.label('Manage your account preferences and application settings.').classes('text-sm text-slate-500 mb-8')
        
        with ui.column().classes('w-full max-w-5xl gap-8'):
            
            # --------------------
            # Profile Section
            # --------------------
            with ui.card().classes('w-full p-0 shadow-sm border border-slate-200 rounded-lg overflow-hidden'):
                with ui.row().classes('w-full p-6 border-b border-slate-100 items-center justify-between'):
                    with ui.row().classes('items-center gap-4'):
                        with ui.element('div').classes('p-2 bg-slate-50 rounded-lg'):
                            ui.icon('person', color='slate-700').classes('text-xl')
                        with ui.column().classes('gap-0'):
                            ui.label('Personal Information').classes('text-base font-semibold text-slate-800')
                            ui.label('Update your personal details').classes('text-xs text-slate-500')
                
                with ui.column().classes('w-full p-6 gap-6'):
                    with ui.row().classes('w-full gap-6'):
                        fn_input = ui.input('First Name', value=first_name).classes('flex-1')
                        ln_input = ui.input('Last Name', value=last_name).classes('flex-1')
                    
                    ui.input('Email Address', value=email).props('readonly disable').classes('w-full bg-slate-50 rounded')
                    
                    async def save_profile():
                        if not fn_input.value or not ln_input.value:
                            ui.notify('Name fields cannot be empty', type='negative')
                            return
                        success = await run.io_bound(update_user_profile, email, fn_input.value, ln_input.value)
                        if success:
                            app.storage.user['first_name'] = fn_input.value
                            app.storage.user['last_name'] = ln_input.value
                            ui.notify('Profile updated successfully', type='positive')
                        else:
                            ui.notify('Failed to update profile', type='negative')

                    with ui.row().classes('w-full justify-end mt-2'):
                        ui.button('Save Changes', on_click=save_profile).props('unelevated no-caps').classes('bg-indigo-600 text-white px-6 rounded-md')

            # --------------------
            # Authentication Section
            # --------------------
            with ui.card().classes('w-full p-0 shadow-sm border border-slate-200 rounded-lg overflow-hidden'):
                with ui.row().classes('w-full p-6 border-b border-slate-100 items-center justify-between'):
                    with ui.row().classes('items-center gap-4'):
                        with ui.element('div').classes('p-2 bg-slate-50 rounded-lg'):
                            ui.icon('lock', color='slate-700').classes('text-xl')
                        with ui.column().classes('gap-0'):
                            ui.label('Security').classes('text-base font-semibold text-slate-800')
                            ui.label('Manage password and security settings').classes('text-xs text-slate-500')
                
                with ui.column().classes('w-full p-6'):
                    with ui.row().classes('w-full items-center justify-between'):
                        with ui.column().classes('gap-1'):
                            ui.label('Password').classes('text-sm font-medium text-slate-700')
                            ui.label('Last changed recently').classes('text-xs text-slate-400')
                        
                        def open_password_dialog():
                            with ui.dialog() as dialog, ui.card().classes('p-6 w-full max-w-sm rounded-lg shadow-xl'):
                                ui.label('Change Password').classes('text-lg font-bold text-slate-800 mb-6')
                                curr_pwd = ui.input('Current Password', password=True).classes('w-full mb-3')
                                new_pwd = ui.input('New Password', password=True).classes('w-full mb-3')
                                conf_pwd = ui.input('Confirm New Password', password=True).classes('w-full mb-6')
                                
                                async def perform_change():
                                    if new_pwd.value != conf_pwd.value:
                                        ui.notify('New passwords do not match', type='negative')
                                        return
                                    
                                    from services.auth_service import validate_login
                                    login_check = await run.io_bound(validate_login, email, curr_pwd.value)
                                    if not login_check:
                                        ui.notify('Incorrect current password', type='negative')
                                        return
                                    
                                    success = await run.io_bound(update_password, email, new_pwd.value)
                                    if success:
                                        ui.notify('Password changed successfully', type='positive')
                                        dialog.close()
                                    else:
                                        ui.notify('Failed to update password', type='negative')

                                with ui.row().classes('w-full justify-end gap-3'):
                                    ui.button('Cancel', on_click=dialog.close).props('flat no-caps text-slate-600')
                                    ui.button('Update Password', on_click=perform_change).props('unelevated no-caps').classes('bg-indigo-600 text-white')
                            
                            dialog.open()

                        ui.button('Change Password', on_click=open_password_dialog).props('outline no-caps').classes('text-slate-700 border-slate-300')

            # --------------------
            # Preferences & Notifications Section (Grouped)
            # --------------------
            with ui.card().classes('w-full p-0 shadow-sm border border-slate-200 rounded-lg overflow-hidden'):
                with ui.row().classes('w-full p-6 border-b border-slate-100 items-center justify-between'):
                    with ui.row().classes('items-center gap-4'):
                        with ui.element('div').classes('p-2 bg-slate-50 rounded-lg'):
                            ui.icon('tune', color='slate-700').classes('text-xl')
                        with ui.column().classes('gap-0'):
                            ui.label('Preferences & Notifications').classes('text-base font-semibold text-slate-800')
                            ui.label('Customize your experience and alerts').classes('text-xs text-slate-500')

                with ui.column().classes('w-full p-6 gap-8'):

                    # Notifications
                    with ui.column().classes('w-full gap-2'):
                        ui.label('Notification Settings').classes('text-sm font-semibold text-slate-700 uppercase tracking-wider mb-2')
                        
                        toggle_data = notifications # Initial data from DB
                        
                        def create_toggle(label, description, key):
                            with ui.row().classes('w-full items-start justify-between py-3'):
                                with ui.column().classes('gap-0'):
                                    ui.label(label).classes('text-sm font-medium text-slate-800')
                                    ui.label(description).classes('text-xs text-slate-400')
                                
                                s = ui.switch(value=toggle_data.get(key, False)).props('color=indigo-600')
                                async def on_toggle():
                                    toggle_data[key] = s.value
                                    await run.io_bound(update_user_notifications, email, toggle_data)
                                    # Silent update or subtle toast
                                s.on('change', on_toggle)
                        
                        create_toggle('Email Alerts', 'Receive important updates via email', 'email_notifications')
                        create_toggle('Weekly Reports', 'Get a summary of your performance every Monday', 'weekly_reports')
                        create_toggle('KPI Alerts', 'Notify when metrics cross defined thresholds', 'kpi_alerts')
                        create_toggle('Anomaly Detection', 'Alert when unusual patterns are detected', 'anomaly_detection')
                        create_toggle('In-App Notifications', 'Show notifications within the dashboard', 'in-app_notifications')

            # --------------------
            # Danger Zone
            # --------------------
            with ui.column().classes('w-full mt-4 bg-red-50/30 border border-red-100 rounded-lg p-6'):
                with ui.row().classes('items-center justify-between w-full'):
                    with ui.row().classes('items-center gap-4'):
                        ui.icon('warning', color='red-400').classes('text-xl')
                        with ui.column().classes('gap-0'):
                            ui.label('Danger Zone').classes('text-sm font-bold text-red-900')
                            ui.label('Irreversible actions').classes('text-xs text-red-700/70')
                    
                    async def handle_deactivate():
                        with ui.dialog() as dialog, ui.card().classes('p-6 w-full max-w-md rounded-lg'):
                            ui.label('Deactivate Account?').classes('text-lg font-bold text-slate-900 mb-2')
                            ui.label('This action cannot be undone. You will lose access to the dashboard immediately.').classes('text-sm text-slate-600 mb-6')
                            
                            with ui.row().classes('w-full justify-end gap-3'):
                                ui.button('Cancel', on_click=dialog.close).props('flat no-caps text-slate-600')
                                async def confirm():
                                    await run.io_bound(update_account_status, email, 'Deactivated')
                                    app.storage.user.clear()
                                    ui.navigate.to('/login')
                                ui.button('Deactivate', on_click=confirm).props('unelevated no-caps').classes('bg-red-600 text-white')
                        dialog.open()

                    ui.button('Deactivate Account', on_click=handle_deactivate).props('flat no-caps dense').classes('text-red-600 hover:bg-red-50')

        with ui.page_scroller(position='bottom-right', x_offset=32, y_offset=32):
            ui.button(icon='arrow_upward').props('fab-mini unelevated color=indigo-600 text-color=white')
    
    await dashboard_layout(content, page_title="Settings", active_page="settings")
