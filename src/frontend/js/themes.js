// src/frontend/js/themes.js

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

        themeGrid.innerHTML = '';
        const themes = THEMES[this.currentMode];

        themes.forEach(theme => {
            const themeOption = document.createElement('div');
            themeOption.className = 'theme-option';
            themeOption.dataset.theme = theme.id;
            themeOption.innerHTML = `
                <div style="font-size: 1.6rem; margin-bottom: 0.25rem;">${theme.preview}</div>
                <div style="font-size: 0.8rem; font-weight: 500;">${theme.name}</div>
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
        // Mode toggle buttons in settings
        document.querySelectorAll('.mode-btn').forEach(btn => {
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

        // Keyboard shortcut: Ctrl + T (or Alt + T) to toggle light/dark mode
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.altKey) && e.key.toLowerCase() === 't') {
                e.preventDefault();
                this.toggleMode();
            }
        });
    }

    switchMode(mode) {
        this.currentMode = mode;

        document.querySelectorAll('.mode-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.mode === mode);
        });

        // Pick default theme for mode if current theme doesn't belong to it
        const currentModeThemes = THEMES[this.currentMode].map(t => t.id);
        if (!currentModeThemes.includes(this.currentTheme)) {
            this.currentTheme = this.currentMode === 'light' ? 'sunrise' : 'midnight';
        }

        this.loadThemeGrid();
        this.applyTheme(mode, this.currentTheme);
    }

    toggleMode() {
        const newMode = this.currentMode === 'light' ? 'dark' : 'light';
        this.switchMode(newMode);
    }

    selectTheme(themeId) {
        this.currentTheme = themeId;

        document.querySelectorAll('.theme-option').forEach(option => {
            option.classList.toggle('active', option.dataset.theme === themeId);
        });

        this.applyTheme(this.currentMode, themeId);
    }

    applyTheme(mode, themeId) {
        const body = document.body;

        body.className = body.className.split(' ')
            .filter(c => !c.startsWith('theme-'))
            .join(' ');

        body.classList.add(`theme-${mode}`, `theme-${themeId}`);

        if (window.pywebview && window.pywebview.api) {
            try {
                window.pywebview.api.set_theme(mode, themeId);
            } catch (e) {
                console.debug('Failed to persist theme setting:', e);
            }
        }
    }

    async waitForAPI() {
        while (!(window.pywebview && window.pywebview.api)) {
            await new Promise(resolve => setTimeout(resolve, 50));
        }
    }

    async loadSavedTheme() {
        await this.waitForAPI();
        
        try {
            const settings = await window.pywebview.api.get_theme_settings();
            const themeSettings = JSON.parse(settings);
            
            this.currentMode = themeSettings.mode || 'light';
            this.currentTheme = themeSettings.style || (this.currentMode === 'light' ? 'sunrise' : 'midnight');

            document.querySelectorAll('.mode-btn').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.mode === this.currentMode);
            });

            this.loadThemeGrid();
            this.applyTheme(this.currentMode, this.currentTheme);
        } catch (error) {
            console.debug('Using default theme:', error);
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.themeManager = new ThemeManager();
});
