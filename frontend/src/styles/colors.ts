/**
 * Design System and Color Palette
 * Modern, softer colors with gradients and enhanced shadows
 */

export const colors = {
  // Status colors - pastel palette
  status: {
    critical: {
      bg: 'from-rose-50 to-rose-100/50',
      border: 'border-rose-200',
      text: 'text-rose-700',
      badge: 'bg-rose-100 text-rose-700 border-rose-200',
      icon: '🔴',
    },
    warning: {
      bg: 'from-amber-50 to-amber-100/50',
      border: 'border-amber-200',
      text: 'text-amber-700',
      badge: 'bg-amber-100 text-amber-700 border-amber-200',
      icon: '🟠',
    },
    excess: {
      bg: 'from-sky-50 to-sky-100/50',
      border: 'border-sky-200',
      text: 'text-sky-700',
      badge: 'bg-sky-100 text-sky-700 border-sky-200',
      icon: '🔵',
    },
    normal: {
      bg: 'from-emerald-50 to-emerald-100/50',
      border: 'border-emerald-200',
      text: 'text-emerald-700',
      badge: 'bg-emerald-100 text-emerald-700 border-emerald-200',
      icon: '🟢',
    },
  },

  // Health status
  health: {
    critical: 'text-rose-500',
    needs_attention: 'text-amber-500',
    overstocked: 'text-sky-500',
    healthy: 'text-emerald-500',
  },

  // Card backgrounds with gradients
  cards: {
    primary: 'bg-gradient-to-br from-white via-slate-50/50 to-slate-50',
    secondary: 'bg-gradient-to-br from-slate-50 via-white to-slate-50',
    accent: 'bg-gradient-to-br from-indigo-50 to-blue-50',
  },

  // Shadows - enhanced
  shadows: {
    sm: 'shadow-sm',
    md: 'shadow-md',
    lg: 'shadow-lg',
    xl: 'shadow-xl',
    glow: 'shadow-lg shadow-slate-200/50',
  },

  // Borders
  borders: {
    light: 'border-slate-100',
    medium: 'border-slate-200',
    dark: 'border-slate-300',
  },
};

export const getStatusColor = (status: string) => {
  switch (status?.toUpperCase()) {
    case 'CRITICAL':
      return colors.status.critical;
    case 'WARNING':
      return colors.status.warning;
    case 'EXCESS':
      return colors.status.excess;
    case 'NORMAL':
    case 'OK':
      return colors.status.normal;
    default:
      return {
        bg: 'from-slate-50 to-slate-100/50',
        border: 'border-slate-200',
        text: 'text-slate-700',
        badge: 'bg-slate-100 text-slate-700 border-slate-200',
        icon: '⚪',
      };
  }
};

export const getHealthColor = (health: string) => {
  switch (health?.toUpperCase()) {
    case 'CRITICAL':
      return colors.health.critical;
    case 'NEEDS_ATTENTION':
      return colors.health.needs_attention;
    case 'OVERSTOCKED':
      return colors.health.overstocked;
    case 'HEALTHY':
      return colors.health.healthy;
    default:
      return 'text-slate-500';
  }
};

export const getHealthBgColor = (health: string) => {
  switch (health?.toUpperCase()) {
    case 'CRITICAL':
      return 'bg-rose-50 border-rose-200';
    case 'NEEDS_ATTENTION':
      return 'bg-amber-50 border-amber-200';
    case 'OVERSTOCKED':
      return 'bg-sky-50 border-sky-200';
    case 'HEALTHY':
      return 'bg-emerald-50 border-emerald-200';
    default:
      return 'bg-slate-50 border-slate-200';
  }
};
