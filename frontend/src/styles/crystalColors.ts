/**
 * Crystal Ops Console Color Scheme
 * Purple, Teal, and Cyan palette inspired by the design system
 */

export const crystalColors = {
  // Primary accent colors
  primary: {
    purple: '#7C3AED', // Vibrant purple for CTAs and highlights
    purpleLight: '#EDE9FE',
    purpleDark: '#5B21B6',
    
    teal: '#0D9488', // Deep teal
    tealLight: '#CCFBF1',
    tealDark: '#134E4A',
    
    cyan: '#06B6D4', // Bright cyan
    cyanLight: '#CFFAFE',
    cyanDark: '#164E63',
  },

  // Status colors
  status: {
    active: '#10B981', // Green
    activeLight: '#D1FAE5',
    activeDark: '#065F46',
    
    pending: '#F59E0B', // Amber
    pendingLight: '#FEF3C7',
    pendingDark: '#78350F',
    
    warning: '#EF4444', // Red
    warningLight: '#FEE2E2',
    warningDark: '#7F1D1D',
  },

  // Background colors
  backgrounds: {
    white: '#FFFFFF',
    light: '#F8FAFC',
    lighter: '#F1F5F9',
    gray: '#E2E8F0',
  },

  // Text colors
  text: {
    dark: '#0F172A',
    medium: '#475569',
    light: '#78909C',
  },

  // Borders
  borders: {
    light: '#E2E8F0',
    medium: '#CBD5E1',
  },
};

export const getCrystalGradient = (type: 'card' | 'header' | 'button' | 'subtle') => {
  switch (type) {
    case 'card':
      return 'linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 100%)';
    case 'header':
      return 'linear-gradient(135deg, #7C3AED 0%, #0D9488 100%)';
    case 'button':
      return 'linear-gradient(135deg, #7C3AED 0%, #06B6D4 100%)';
    case 'subtle':
      return 'linear-gradient(135deg, #EDE9FE 0%, #CCFBF1 100%)';
  }
};
