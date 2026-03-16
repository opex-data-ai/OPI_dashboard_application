class ThemeManager:
    """
    Centralized manager for application design system.
    Handles color palettes, typography, and styling.
    """
    
    # --------------------------------------------------------------------------
    # Design Tokens (Colors)
    # --------------------------------------------------------------------------
    COLORS = {
        'primary': {
            'DEFAULT': 'blue-600',  # #2563eb
            'light': 'blue-50',     # #eff6ff
            'dark': 'blue-800',     # #1e40af
            'hex': '#2563eb'
        },
        'secondary': {
            'DEFAULT': 'slate-600', # #475569
            'light': 'slate-50',    # #f8fafc
            'dark': 'slate-800',    # #1e293b
            'hex': '#475569'
        },
        'accent': {
            'success': 'emerald-600',
            'warning': 'orange-500',
            'danger': 'red-600',
            'info': 'cyan-600',
            'hex_palette': ['#2563eb', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899'] # Blue, Green, Orange, Purple, Pink
        },
        'background': {
            'white': 'bg-white'
        },
        'text': {
            'primary': 'text-slate-900',
            'secondary': 'text-slate-600',
            'muted': 'text-slate-400'
        }
    }

    # --------------------------------------------------------------------------
    # Typography
    # --------------------------------------------------------------------------
    TYPOGRAPHY = {
        'h1': 'text-4xl font-black tracking-tight text-slate-900',
        'h2': 'text-2xl font-bold text-slate-900',
        'h3': 'text-xl font-bold text-slate-800',
        'body': 'text-base text-slate-600',
        'small': 'text-sm text-slate-500',
        'tiny': 'text-xs text-slate-400 font-medium'
    }

    @staticmethod
    def get_current_theme():
        """Always returns 'light' (white theme only)"""
        return 'light'

    @classmethod
    def get_primary_color(cls):
        """Return primary color class"""
        return cls.COLORS['primary']['DEFAULT']

    @classmethod
    def get_chart_colors(cls):
        """Return list of hex colors for charts"""
        return cls.COLORS['accent']['hex_palette']
    
    @classmethod
    def get_bg_gradient(cls):
        """Get the main background style (white)"""
        return 'background: #ffffff;'

    @classmethod
    def get_card_style(cls):
        """Standard card styling"""
        return 'border border-slate-200 shadow-sm bg-white rounded-xl'

theme_manager = ThemeManager()
