from nicegui import ui, app
from services.auth_service import register_user, user_exists, is_strong_password
from services.google_auth import get_google_auth_url


def show_register_page():

    with ui.column().classes(
        'w-full min-h-screen items-center justify-center bg-slate-100 p-4'
    ):

        with ui.card().classes(
            'w-full max-w-md p-6 bg-white rounded-2xl shadow-xl border-none'
        ):

            # --------------------
            # Header
            # --------------------
            with ui.column().classes('w-full items-center mb-6 gap-1'):
                ui.icon('person_add').classes('text-4xl text-indigo-600')
                ui.label('Create Account').classes(
                    'text-xl font-black text-slate-900 leading-tight'
                )
                ui.label('Enter your details to join').classes(
                    'text-slate-500 text-xs'
                )

            # --------------------
            # Google Sign-Up
            # --------------------
            def google_signin():
                auth_url, state = get_google_auth_url()
                app.storage.user['oauth_state'] = state
                ui.navigate.to(auth_url, new_tab=False)

            GOOGLE_ICON = (
                '<svg width="20" height="20" viewBox="0 0 24 24">'
                '<path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>'
                '<path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>'
                '<path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>'
                '<path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>'
                '</svg>'
            )

            with ui.button(on_click=google_signin).props(
                'unelevated no-caps'
            ).classes(
                'w-full py-2 mb-3 bg-white border border-slate-300 '
                'rounded-xl hover:bg-slate-50 transition-all shadow-sm'
            ):
                with ui.row().classes('items-center justify-center gap-3'):
                    ui.html(GOOGLE_ICON, sanitize=False)
                    ui.label('Sign up with Google').classes(
                        'text-[#3c4043] font-medium text-sm'
                    )

            # --------------------
            # Divider
            # --------------------
            with ui.row().classes('w-full items-center gap-2 my-3'):
                ui.element('div').classes('flex-1 h-px bg-slate-200')
                ui.label('OR').classes(
                    'text-[10px] font-bold text-slate-400 tracking-widest'
                )
                ui.element('div').classes('flex-1 h-px bg-slate-200')

            # --------------------
            # Form
            # --------------------
            with ui.column().classes('w-full gap-2'):
                first_name_input = ui.input(
                    label='First Name'
                ).classes('w-full')

                last_name_input = ui.input(
                    label='Last Name'
                ).classes('w-full')

                email_input = ui.input(
                    label='Business Email'
                ).classes('w-full')

                # --------------------
                # Password
                # --------------------
                password_input = ui.input(
                    label='Password',
                    password=True,
                ).classes('w-full')

                with password_input.add_slot('append'):
                    password_eye = ui.button(
                        icon='visibility_off',
                        on_click=lambda: toggle_password(),
                    ).props('flat dense round').classes('text-slate-400')

                def toggle_password():
                    is_password = password_input.props.get('type', 'password') == 'password'

                    if is_password:
                        password_input.props('type=text')
                        password_eye.props('icon=visibility')
                    else:
                        password_input.props('type=password')
                        password_eye.props('icon=visibility_off')


                # --------------------
                # Confirm Password
                # --------------------
                cpassword_input = ui.input(
                    label='Confirm Password',
                    password=True,
                ).classes('w-full')

                with cpassword_input.add_slot('append'):
                    cpassword_eye = ui.button(
                        icon='visibility_off',
                        on_click=lambda: toggle_cpassword(),
                    ).props('flat dense round').classes('text-slate-400')

                def toggle_cpassword():
                    is_password = cpassword_input.props.get('type', 'password') == 'password'

                    if is_password:
                        cpassword_input.props('type=text')
                        cpassword_eye.props('icon=visibility')
                    else:
                        cpassword_input.props('type=password')
                        cpassword_eye.props('icon=visibility_off')

            # --------------------
            # Terms
            # --------------------
            with ui.row().classes('w-full items-center mt-2'):
                terms_checkbox = ui.checkbox()
                ui.label(
                    'I agree to the Terms of Service'
                ).classes(
                    'text-xs text-slate-600 ml-[-6px]'
                )

            # --------------------
            # Register Logic
            # --------------------
            def register_click():
                first_name = first_name_input.value
                last_name = last_name_input.value
                email = email_input.value
                pwd = password_input.value
                cpwd = cpassword_input.value

                if not first_name or not last_name:
                    ui.notify('First name and last name are required', color='red')
                    return

                if not email or not pwd:
                    ui.notify('Email and password are required', color='red')
                    return

                if not terms_checkbox.value:
                    ui.notify('You must agree to the Terms of Service', color='orange')
                    return

                user_exists_result = user_exists(email)
                if user_exists_result['exists'] == True and user_exists_result['google_only']:
                    ui.notify('This email is registered with Google Sign-In. Please use Google to sign in.', color='red')
                    return
                elif user_exists_result['exists'] == True:
                    ui.notify('An account with this email already exists', color='red')               
                    return

                if pwd != cpwd:
                    ui.notify('Passwords do not match', color='red')
                    return

                if not is_strong_password(pwd):
                    ui.notify(
                        'Password must be at least 8 characters and contain letters and numbers',
                        color='red'
                    )
                    return

                register_user(email, pwd, first_name, last_name)
                ui.notify('Account created successfully!', color='green')
                ui.navigate.to('/login')

            # Bind Enter key to submit registration form
            first_name_input.on('keydown.enter', register_click)
            last_name_input.on('keydown.enter', register_click)
            email_input.on('keydown.enter', register_click)
            password_input.on('keydown.enter', register_click)
            cpassword_input.on('keydown.enter', register_click)

            # --------------------
            # Register Button
            # --------------------
            ui.button(
                'Get Started', on_click=register_click
            ).props('unelevated').classes(
                'w-full py-2 mt-3 rounded-xl font-bold shadow-lg shadow-indigo-200'
            ).style('background: #4f46e5 !important; color: white !important;')

            # --------------------
            # Footer
            # --------------------
            with ui.row().classes(
                'w-full justify-center mt-6 pt-4 border-t border-slate-100'
            ):
                ui.label(
                    'Already have an account?'
                ).classes(
                    'text-xs text-slate-500'
                )
                ui.link(
                    'Sign in', '/login'
                ).classes(
                    'ml-1 text-xs text-indigo-600 font-bold no-underline hover:text-indigo-800'
                )
