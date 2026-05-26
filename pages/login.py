from nicegui import ui, app, run
from services.auth_service import validate_login
from services.google_auth import get_google_auth_url
from components.theme_manager import ThemeManager
from config import FEATURES


def show_login_page():

    # Disable body scrolling
    ui.add_head_html('<script>document.body.classList.add("no-scroll");</script>')


    with ui.row().classes('h-screen w-screen m-0 p-0 overflow-hidden bg-slate-50 items-center justify-center'):
        with ui.card().classes('w-full max-w-md p-8 rounded-2xl shadow-xl border border-slate-200 bg-white'):
            # --------------------
            # Header
            # --------------------
            with ui.column().classes('w-full items-center mb-6 gap-1'):
                ui.label('Welcome back').classes('text-3xl font-bold text-slate-900 tracking-tight text-center')
                ui.label('Sign in to your account').classes('text-sm text-slate-500 text-center')

            # --------------------
            # Google Sign-In
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
                    ui.label('Sign in with Google').classes(
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
            # Inputs
            # --------------------
            # Input Fields
            with ui.column().classes('w-full gap-3'):
                email_input = ui.input(label='Email Address').classes('w-full')
            
                # Password field with visibility toggle
                # Password field with visibility toggle
                password_input = ui.input(
                    label='Password',
                    password=True,
                ).classes('w-full')

                with password_input.add_slot('append'):
                    eye_button = ui.button(
                        icon='visibility_off',
                        on_click=lambda: toggle_password(),
                    ).props('flat dense round').classes('text-slate-400')

                def toggle_password():
                    is_password = password_input.props.get('type', 'password') == 'password'
                
                    if is_password:
                        password_input.props('type=text')
                        eye_button.props('icon=visibility')
                    else:
                        password_input.props('type=password')
                        eye_button.props('icon=visibility_off')

            # --------------------
            # Forgot Password
            # --------------------
            with ui.row().classes('w-full justify-end mt-1'):
                ui.link(
                    'Forgot password?', '/forgot'
                ).classes(
                    'text-xs text-indigo-600 font-medium no-underline hover:text-indigo-800'
                )

            # --------------------
            # Login Logic
            # --------------------
            async def login_click():
                try:
                    print("Attempting login with:", email_input.value, password_input.value)
                    result = await run.io_bound(validate_login, 
                        email_input.value,
                        password_input.value
                    )  
                
                    print("Login result:", result)
                    if not result:
                        ui.notify('Invalid credentials', color='red')
                        return

                    if result.get('isActive') == 'Deactivated':
                        ui.notify('Account is deactivated. Please contact support.', type='negative')
                        return

                    if result.get("force_change") == "YES":
                        ui.navigate.to(
                            f'/change_password?email={email_input.value}'
                        )
                        return

                    # Store user data in session
                    app.storage.user['email'] = result['email']
                    app.storage.user['first_name'] = result['first_name']
                    app.storage.user['last_name'] = result['last_name']
                    app.storage.user['role'] = result['role']
                    app.storage.user['logged_in'] = True
                    app.storage.user['auth_method'] = result['auth_method']
                    app.storage.user['isActive'] = result.get('isActive', 'Active')

                    # Sync preferences from DB
                    from services.auth_service import get_user_settings, get_user_notifications
                    settings = await run.io_bound(get_user_settings, result['email'])
                    notifications = await run.io_bound(get_user_notifications, result['email'])
                
                    app.storage.user['theme_mode'] = settings.get('theme', 'light')
                    app.storage.user['notifications'] = notifications

                    ui.notify('Login successful', color='green')
                    if FEATURES.get('overview'):
                        ui.navigate.to('/overview')
                    else:
                        ui.navigate.to('/product/home')
                except Exception as e:
                    print("Login error:", e)
                    ui.notify('An error occurred during login', color='red')

            # Bind Enter key to submit login
            email_input.on('keydown.enter', login_click)
            password_input.on('keydown.enter', login_click)

            # --------------------
            # Login Button
            # --------------------
            ui.button(
                'Sign In', on_click=login_click
            ).props('unelevated').classes('w-full py-2 mt-3 rounded-xl font-bold shadow-lg shadow-indigo-200').style('background: #4f46e5 !important; color: white !important;')

            # --------------------
            # Footer
            # --------------------
            with ui.row().classes(
                'w-full justify-center mt-6 pt-4 border-t border-slate-100'
            ):
                ui.label('New here?').classes(
                    'text-xs text-slate-400'
                )
                ui.link(
                    'Create account', '/register'
                ).classes(
                    'ml-1 text-xs text-indigo-600 font-bold hover:text-indigo-800'
                )
