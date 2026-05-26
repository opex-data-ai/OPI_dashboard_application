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
            'DEFAULT': 'indigo-500',  # #6366f1
            'light': 'indigo-50',     # #e0e7ff
            'dark': 'indigo-600',     # #4f46e5
            'hex': '#6366f1'
        },
        'secondary': {
            'DEFAULT': 'slate-600', # #475569
            'light': 'slate-50',    # #f8fafc
            'dark': 'slate-900',    # #0f172a
            'hex': '#475569'
        },
        'accent': {
            'success': 'emerald-500',
            'warning': 'amber-500',
            'danger': 'red-500',
            'info': 'violet-500',
            'hex_palette': ['#6366f1', '#8b5cf6', '#10b981', '#f59e0b', '#ec4899'] # Indigo, Violet, Emerald, Amber, Pink
        },
        'background': {
            'white': 'bg-white',
            'slate': 'bg-slate-50',
            'dark': 'bg-slate-900'
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
        'h1': 'ds-h1',
        'h2': 'ds-h2',
        'h3': 'ds-h3',
        'body': 'ds-body',
        'small': 'ds-small',
        'tiny': 'ds-tiny',
        # Legacy aliases kept for backward compat
        'kpi_label': 'ds-kpi-label',
        'kpi_value': 'ds-kpi-value ds-value',
        'kpi_sub':   'ds-kpi-sub',
        'card_title': 'ds-card-title',
        'card_sub':   'ds-card-sub',
        'section':    'ds-section-label',
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
        """Get the main background style (ash slate-50)"""
        return 'background: #f8fafc;'

    @classmethod
    def get_card_style(cls):
        """Standard card styling"""
        return 'card-default'

theme_manager = ThemeManager()
