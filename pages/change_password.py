from nicegui import ui
from services.auth_service import update_password, is_strong_password


def show_change_password_page(email):
    ui.add_head_html('<script>document.body.classList.add("no-scroll");</script>')

    with ui.column().classes('w-full h-screen items-center justify-center bg-slate-50 overflow-hidden p-4'):
        
        with ui.card().classes('w-full max-w-md p-8 bg-white rounded-2xl shadow-xl border-none'):
            
            # Header Section
            with ui.column().classes('w-full items-center mb-6'):
                ui.icon('lock_reset').classes('text-5xl text-blue-600 mb-2')
                ui.label('Change Password').classes('text-2xl font-black text-slate-900 tracking-tight')
                ui.label("Enter a new password to secure your account.").classes('text-slate-500 text-center text-sm mt-1')

            # Input Fields with password visibility toggle
            with ui.column().classes('w-full gap-4'):
                # New Password field with visibility toggle
                new_pwd_visible = {'value': False}
                with ui.input(label='New Password', password=True).classes('w-full') as new_pwd:
                    def toggle_new_pwd_visibility():
                        new_pwd_visible['value'] = not new_pwd_visible['value']
                        new_pwd.password = not new_pwd_visible['value']
                        new_eye_icon.set_text('visibility' if new_pwd_visible['value'] else 'visibility_off')
                    
                    with new_pwd.add_slot('append'):
                        new_eye_icon = ui.icon('visibility_off').classes('cursor-pointer text-slate-400 hover:text-slate-600').on('click', toggle_new_pwd_visibility)
                
                # Confirm Password field with visibility toggle
                confirm_pwd_visible = {'value': False}
                with ui.input(label='Confirm New Password', password=True).classes('w-full mb-2') as confirm_pwd:
                    def toggle_confirm_pwd_visibility():
                        confirm_pwd_visible['value'] = not confirm_pwd_visible['value']
                        confirm_pwd.password = not confirm_pwd_visible['value']
                        confirm_eye_icon.set_text('visibility' if confirm_pwd_visible['value'] else 'visibility_off')
                    
                    with confirm_pwd.add_slot('append'):
                        confirm_eye_icon = ui.icon('visibility_off').classes('cursor-pointer text-slate-400 hover:text-slate-600').on('click', toggle_confirm_pwd_visibility)

            # Save button
            def save_click():
                if new_pwd.value != confirm_pwd.value:
                    ui.notify('Passwords do not match', color='red')
                    return

                if not is_strong_password(new_pwd.value):
                    ui.notify('Password must be at least 8 characters with letters and numbers', color='red')
                    return

                # Password will be hashed in auth_service before storing
                update_password(email, new_pwd.value)
                ui.notify('Password updated successfully', color='green')
                ui.navigate.to('/overview')

            # Primary Action Button
            ui.button('Update Password', on_click=save_click) \
                .props('elevated') \
                .classes('w-full py-3 bg-blue-600 text-white rounded-xl font-bold hover:scale-[1.01] transition-transform')

            # Back to Login Footer
            with ui.row().classes('w-full justify-center mt-6 pt-4 border-t border-slate-100'):
                ui.link('← Back to Login', '/login').classes('text-sm text-slate-500 hover:text-blue-600 font-medium no-underline')