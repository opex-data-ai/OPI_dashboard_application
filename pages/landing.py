from nicegui import ui
from components.theme_manager import ThemeManager

def show_landing_page():
    # Inject Tailwind
    ui.add_head_html('<link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">')

    # ---------------------------
    # Header (Logo + Auth Buttons)
    # ---------------------------
    with ui.row().classes('w-full justify-between items-center border-b-2 border-gray-200 p-4'):
        # Left: Logo
        with ui.row().classes('space-x-2 items-center'):
            ui.image('/assets/img/opex_logo.png').classes('w-20 h-12 object-cover')
            ui.image('/assets/img/epi_logo_black.png').classes('w-20 h-12 object-cover m-0 p-0')
        
        # Right: Login / Signup
        with ui.row().classes('space-x-4 items-center'):
            ui.button('Login', on_click=lambda: ui.navigate.to('/login')).classes('bg-gray-100 text-gray-800 px-4 py-2 rounded-lg')
            ui.button('Sign Up', on_click=lambda: ui.navigate.to('/register')).classes(f'bg-{ThemeManager.get_primary_color()} text-white px-4 py-2 rounded-lg')

    # ---------------------------
    # Hero Section
    # ---------------------------
    with ui.row().classes('flex flex-col md:flex-row items-center px-4 py-4 border-b-2 border-gray-200 gap-8 w-full'):
        
        # Left: Title and Vision Statement
        with ui.column().classes('space-y-4 space-x-1 text-center md:text-left md:w-3/5'):
            with ui.column().classes('gap-2'):
                    ui.label('Enterprise Performance').classes(f'text-{ThemeManager.get_primary_color()} font-bold tracking-wider uppercase text-3xl')
                    ui.label('Intelligence').classes(f'text-5xl md:text-6xl font-black {ThemeManager.COLORS["text"]["primary"]} leading-[1.1]')
            ui.label(
                'Enterprise Performance Intelligence (EPI) at Opex Consulting leverages data, analytics, and AI to provide deep, real-time insight into our organization’s operations. '
                'It empowers our teams to make faster, better-informed decisions, continuously improve performance, and align day-to-day activities with our strategic objectives, '
                'bridging the gap between enterprise strategy and operational execution.'
            ).classes(f'text-lg {ThemeManager.COLORS["text"]["secondary"]} leading-relaxed mx-auto md:mx-0')
        
        # Primary Action Button placed directly under text
            with ui.row().classes('justify-between items-center pt-1'):
                ui.button('Explore Metrics', on_click=lambda: ui.notify('Exploring...')).props('elevated') \
                    .classes(f'bg-{ThemeManager.get_primary_color()} text-white px-8 py-4 rounded-full text-lg font-semibold hover:scale-105 transition-transform')

        # Right: Visual Area (Carousel in a floating card)
        with ui.column().classes('md:w-1/3 flex items-center justify-center'):
            # The "Floating" Card effect - fixed height here controls the card size
            with ui.card().classes('w-full h-full p-0 overflow-hidden rounded-3xl shadow-2xl border-none'):
                
                # We use h-full and remove internal padding via props
                with ui.carousel(animated=True, arrows=True, navigation=True).classes('w-full h-full'):                    
                    with ui.carousel_slide().classes('p-0'):
                        ui.image('/assets/img/carousel1.png').classes('h-full w-full object-cover')                       
                    with ui.carousel_slide().classes('p-0'):
                        ui.image('/assets/img/carousel2.png').classes('h-full w-full object-cover')                        
                    with ui.carousel_slide().classes('p-0'):
                        ui.image('/assets/img/carousel3.png').classes('h-full w-full object-cover')

    with ui.column().classes(f'w-full py-16 px-6 {ThemeManager.COLORS["background"]["white"]} items-center justify-between'):
        ui.label("What the Platform Offers").classes(f'text-3xl font-bold {ThemeManager.COLORS["text"]["primary"]} mb-12')
        
        # Grid layout: 1 column on mobile, 5 on large screens
        with ui.row().classes('w-full max-w-7xl justify-center gap-6'):
            
            offers = [
                {'title': 'Unified Performance', 'icon': 'insights', 'color': 'bg-blue-100'},
                {'title': 'Product Intelligence', 'icon': 'inventory_2', 'color': 'bg-green-100'},
                {'title': 'Real-Time Monitoring', 'icon': 'visibility', 'color': 'bg-orange-100'},
                {'title': 'Workforce Intelligence', 'icon': 'groups', 'color': 'bg-purple-100'},
                {'title': 'AI-Powered Insights', 'icon': 'psychology', 'color': 'bg-pink-100'},
            ]

            for item in offers:
                with ui.card().classes(f'w-40 h-40 {item["color"]} border-none shadow-sm hover:shadow-md transition-all cursor-pointer items-center justify-center p-6 rounded-2xl'):
                    # Icon using Material Icons (included in NiceGUI/Quasar by default)
                    ui.icon(item['icon']).classes('text-4xl text-slate-700 mb-4')
                    ui.label(item['title']).classes('text-center font-bold text-slate-800 leading-tight')
    
    
    # ---------------------------
    # Footer
    # ---------------------------
    with ui.row().classes('flex md:flex-row justify-between items-center bg-gray-50  px-4 py-2 space-y-2 md:space-y-0 w-full'):
        with ui.row().classes('space-x-4'):
            link_class = f'text-gray-600 hover:text-{ThemeManager.get_primary_color()}'
            ui.link('Profile', '#').classes(link_class)
            ui.link('Settings', '#').classes(link_class)
            ui.link('Help', '#').classes(link_class)
        ui.label('© 2026 Opex Consulting').classes('text-gray-500 text-sm')


