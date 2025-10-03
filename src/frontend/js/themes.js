// frontend/js/themes.js

const THEMES = {
    light: [
        { id: 'sunrise', name: 'Sunrise', preview: '🌅' },
        { id: 'mint', name: 'Mint Fresh', preview: '🌿' },
        { id: 'peach', name: 'Peach Blossom', preview: '🍑' },
        { id: 'cotton', name: 'Cotton Candy', preview: '🍭' },
        { id: 'sky', name: 'Sky Breeze', preview: '☁️' },
        { id: 'lemonade', name: 'Lemonade', preview: '🍋' },
        { id: 'vanilla', name: 'Vanilla Cream', preview: '🍦' },
        { id: 'rainbow', name: 'Pastel Rainbow', preview: '🌈' },
        { id: 'ocean', name: 'Ocean Foam', preview: '🌊' },
        { id: 'lily', name: 'Lily Garden', preview: '🌸' }
    ],
    dark: [
        { id: 'midnight', name: 'Midnight Blue', preview: '🌃' },
        { id: 'crimson', name: 'Crimson Night', preview: '🌹' },
        { id: 'charcoal', name: 'Charcoal', preview: '⬛' },
        { id: 'emerald', name: 'Emerald Dark', preview: '💚' },
        { id: 'amethyst', name: 'Amethyst', preview: '💜' },
        { id: 'slate', name: 'Slate', preview: '🌫️' },
        { id: 'burnt', name: 'Burnt Orange', preview: '🔥' },
        { id: 'cosmic', name: 'Cosmic Black', preview: '✨' },
        { id: 'deepocean', name: 'Deep Ocean', preview: '🐋' },
        { id: 'mystic', name: 'Mystic Berry', preview: '🔮' }
    ]
};

class ThemeManager {
    constructor() {
        this.currentMode = 'light';
        this.currentTheme = 'sunrise';
        this.init();
    }

    init() {
        this.loadThemeGrid();
        this.setupEventListeners();
        this.loadSavedTheme();
    }

    loadThemeGrid() {
        const themeGrid = document.getElementById('themeGrid');
        if (!themeGrid) return;

        // Clear existing themes
        themeGrid.innerHTML = '';

        // Load themes for current mode
        const themes = THEMES[this.currentMode];
        themes.forEach(theme => {
            const themeOption = document.createElement('div');
            themeOption.className = 'theme-option';
            themeOption.dataset.theme = theme.id;
            themeOption.innerHTML = `
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">${theme.preview}</div>
                <div style="font-size: 0.85rem;">${theme.name}</div>
            `;
            
            if (theme.id === this.currentTheme) {
                themeOption.classList.add('active');
            }

            themeOption.addEventListener('click', () => {
                this.selectTheme(theme.id);
            });

            themeGrid.appendChild(themeOption);
        });
    }

    setupEventListeners() {
        // Mode toggle buttons
        const modeButtons = document.querySelectorAll('.mode-btn');
        modeButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const mode = btn.dataset.mode;
                this.switchMode(mode);
            });
        });

        // Quick theme toggle in header
        const themeToggle = document.getElementById('themeToggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => {
                this.toggleMode();
            });
        }
    }

    switchMode(mode) {
        this.currentMode = mode;

        // Update mode buttons
        document.querySelectorAll('.mode-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.mode === mode);
        });

        // Reload theme grid
        this.loadThemeGrid();

        // Apply theme
        this.applyTheme(mode, this.currentTheme);
    }

    toggleMode() {
        const newMode = this.currentMode === 'light' ? 'dark' : 'light';
        this.switchMode(newMode);
    }

    selectTheme(themeId) {
        this.currentTheme = themeId;

        // Update active state
        document.querySelectorAll('.theme-option').forEach(option => {
            option.classList.toggle('active', option.dataset.theme === themeId);
        });

        // Apply theme
        this.applyTheme(this.currentMode, themeId);
    }

    applyTheme(mode, themeId) {
        const body = document.body;

        // Remove all theme classes
        body.className = body.className.split(' ')
            .filter(c => !c.startsWith('theme-'))
            .join(' ');

        // Add new theme classes
        body.classList.add(`theme-${mode}`, `theme-${themeId}`);

        // Save to backend
        if (window.pywebview && window.pywebview.api) {
            window.pywebview.api.set_theme(mode, themeId);
        }
    }

    async loadSavedTheme() {
        if (window.pywebview && window.pywebview.api) {
            try {
                const settings = await window.pywebview.api.get_theme_settings();
                const themeSettings = JSON.parse(settings);
                
                this.currentMode = themeSettings.mode || 'light';
                this.currentTheme = themeSettings.style || 'sunrise';

                // Update UI
                document.querySelectorAll('.mode-btn').forEach(btn => {
                    btn.classList.toggle('active', btn.dataset.mode === this.currentMode);
                });

                this.loadThemeGrid();
                this.applyTheme(this.currentMode, this.currentTheme);
            } catch (error) {
                console.error('Failed to load theme settings:', error);
            }
        }
    }
}

// Initialize theme manager when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.themeManager = new ThemeManager();
});
