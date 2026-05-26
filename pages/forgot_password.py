from nicegui import ui
from services.auth_service import forgot_password, send_reset_email
from components.button import primary_button, secondary_button
import config


def show_forgot_page():
    
    ui.add_head_html('<script>document.body.classList.add("no-scroll");</script>')

    with ui.column().classes('w-full h-screen items-center justify-center bg-slate-10 overflow-hidden p-4 bg-slate-50'):
        
        # Compact card width (max-w-md) to keep it focused
        with ui.card().classes('w-full max-w-md p-8 bg-white rounded-2xl shadow-xl border-none'):
            
            # Icon and Header
            with ui.column().classes('w-full items-center mb-6'):
                ui.icon('mail_lock').classes('text-5xl text-indigo-600 mb-2')
                ui.label('Reset Password').classes('text-2xl font-black text-slate-900 tracking-tight')
                ui.label("Enter your email and we'll send you a temporary password.")\
                    .classes('text-slate-500 text-center text-sm mt-1')

            # Email Input: Dense and Outlined for modern feel
            email_input = ui.input(label='Business Email Address') \
                .props('outlined dense rounded item-aligned') \
                .classes('w-full mb-6')


            # Dialog for temporary password
            dialog = ui.dialog()
            with dialog, ui.card().classes('w-80 p-6 bg-white rounded-2xl items-center'):
                ui.label('Temporary Password').classes('text-lg font-bold text-slate-900 mb-2')
                ui.label('Use the temporary password below to log in, then change your password.')\
                    .classes('text-slate-500 text-center text-sm mb-4')
                ui.label('A temporary Password has also been generated for your account.').classes('text-sm text-slate-600 mb-2')
                temp_label = ui.label('').classes('text-2xl font-mono text-indigo-600 bg-indigo-50 px-4 py-2 rounded-lg mb-4')

                def copy_temp_password():
                    ui.run_javascript(f'navigator.clipboard.writeText("{temp_label.text}")')
                    ui.notify('Copied to clipboard!', color='green')

                ui.button('Copy', on_click=copy_temp_password).props('flat').classes('flex-1')

                def close_and_redirect():
                    dialog.close()
                    ui.navigate.to('/login')

                ui.button('Close', on_click=close_and_redirect).props('unelevated').classes('flex-1 bg-indigo-600 text-white rounded-lg').style('background: #4f46e5 !important; color: white !important;')

            #  Reset button
            def reset_click():
                email = email_input.value

                if not email:
                    ui.notify('Please enter your email', color='red')
                    return

                try: 
                    temp_pswd = forgot_password(email)
                    
                    if temp_pswd == 'GOOGLE_AUTH':
                        ui.notify('This account uses Google Sign-In. Please sign in with Google.', color='orange')
                        return
                    
                    if not temp_pswd:
                        raise ValueError("Email not found")
                        
                except Exception as e:
                    ui.notify('Email not found or error occurred', color='red')
                    return
        
                result = send_reset_email(email, temp_pswd)

                if temp_pswd:
                    if result:
                        ui.notify('A reset link has been sent to your email', color='green')
                    else:
                        ui.notify('Email failed to send, but a temporary password was generated', color='orange')
                    temp_label.set_text(temp_pswd)
                    dialog.open()
                else:
                    ui.notify('Email not found or error occurred', color='red')

            # Primary Action Button
            ui.button('Send Reset Link', on_click=reset_click) \
                .props('unelevated') \
                .classes('w-full py-3 rounded-xl font-bold hover:scale-[1.01] transition-transform shadow-lg shadow-indigo-200') \
                .style('background: #4f46e5 !important; color: white !important;')

            # Back to Login: Subtle and centered
            with ui.row().classes('w-full justify-center mt-6 pt-4 border-t border-slate-100'):
                ui.link('← Back to Login', '/login').classes('text-sm text-slate-500 hover:text-indigo-600 font-medium no-underline')