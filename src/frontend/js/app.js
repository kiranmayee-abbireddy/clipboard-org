// src/frontend/js/app.js

class ClipboardApp {
    constructor() {
        this.clips = [];
        this.currentCategory = 'all';
        this.filterType = 'none'; // 'none', 'pinned', 'favorite'
        this.categoryInfo = {};
        this.searchTimeout = null;
        this.searchQuery = '';
        this.passwordLocked = true;
        this.lastVersion = 0;
        this.isEditing = false;
        this.currentPreviewClip = null;

        this.init();
    }

    async init() {
        console.log('ClipBox initializing...');
        await this.waitForPyWebView();
        await this.loadCategoryInfo();
        await this.loadSettings();
        await this.loadClips();
        this.setupEventListeners();
        this.setupKeyboardShortcuts();
        this.startSmartPolling();
        console.log('ClipBox initialized successfully.');
    }

    waitForPyWebView() {
        return new Promise((resolve) => {
            if (window.pywebview && window.pywebview.api) {
                resolve();
                return;
            }
            const interval = setInterval(() => {
                if (window.pywebview && window.pywebview.api) {
                    clearInterval(interval);
                    resolve();
                }
            }, 50);
        });
    }

    // ============= Data Loading =============

    async loadCategoryInfo() {
        try {
            const info = await window.pywebview.api.get_category_info();
            this.categoryInfo = JSON.parse(info);
        } catch (error) {
            console.error('Failed to load category info:', error);
        }
    }

    async loadSettings() {
        try {
            const categorySettings = await window.pywebview.api.get_category_settings();
            const settings = JSON.parse(categorySettings);

            document.querySelectorAll('.toggle-item input[type="checkbox"]').forEach(checkbox => {
                const category = checkbox.dataset.category;
                if (category in settings) {
                    checkbox.checked = settings[category];
                }
            });

            this.passwordLocked = await window.pywebview.api.is_password_locked();
            const passkeySet = await window.pywebview.api.is_passkey_set();

            const setupDiv = document.getElementById('passkeySetup');
            const statusDiv = document.getElementById('passkeyStatus');
            if (setupDiv && statusDiv) {
                setupDiv.style.display = passkeySet ? 'none' : 'flex';
                statusDiv.style.display = passkeySet ? 'block' : 'none';
            }
        } catch (error) {
            console.error('Failed to load settings:', error);
        }
    }

    async loadClips(category = this.currentCategory, resetScroll = false) {
        try {
            let clipsJson;
            if (this.searchQuery) {
                clipsJson = await window.pywebview.api.search_clips(this.searchQuery);
            } else if (category === 'all') {
                clipsJson = await window.pywebview.api.get_all_clips();
            } else {
                clipsJson = await window.pywebview.api.get_clips_by_category(category);
            }

            let loadedClips = JSON.parse(clipsJson);

            // Apply filter chips (Pinned or Favorites)
            if (this.filterType === 'pinned') {
                loadedClips = loadedClips.filter(c => c.is_pinned);
            } else if (this.filterType === 'favorite') {
                loadedClips = loadedClips.filter(c => c.is_favorite);
            }

            this.clips = loadedClips;
            this.renderClips(resetScroll);

            // Update version tracking
            try {
                this.lastVersion = await window.pywebview.api.get_clips_version();
            } catch (e) {
                // Ignore version check errors
            }
        } catch (error) {
            console.error('Failed to load clips:', error);
        }
    }

    // ============= Smart Zero-Overhead Polling =============

    startSmartPolling() {
        // Polls monotonic version every 750ms instead of heavy full-DOM re-renders
        setInterval(async () => {
            if (this.searchQuery || this.isEditing) {
                return; // Pause auto-refresh while searching or editing
            }
            try {
                if (window.pywebview && window.pywebview.api) {
                    const currentVersion = await window.pywebview.api.get_clips_version();
                    if (this.lastVersion !== 0 && currentVersion !== this.lastVersion) {
                        this.lastVersion = currentVersion;
                        await this.loadClips(this.currentCategory, false);
                    } else if (this.lastVersion === 0) {
                        this.lastVersion = currentVersion;
                    }
                }
            } catch (e) {
                // Silently handle polling pause
            }
        }, 750);
    }

    // ============= Rendering =============

    renderClips(resetScroll = false) {
        const grid = document.getElementById('clipsGrid');
        const emptyState = document.getElementById('emptyState');
        const clipCount = document.getElementById('clipCount');

        if (!grid || !emptyState || !clipCount) return;

        if (this.clips.length === 0) {
            grid.style.display = 'none';
            emptyState.style.display = 'block';
            clipCount.textContent = '0 clips';
            return;
        }

        grid.style.display = 'grid';
        emptyState.style.display = 'none';
        const suffix = this.searchQuery ? ' matching' : '';
        clipCount.textContent = `${this.clips.length} clip${this.clips.length !== 1 ? 's' : ''}${suffix}`;

        grid.innerHTML = this.clips.map(clip => this.createClipCardHtml(clip)).join('');
        this.attachClipEventListeners();

        if (resetScroll) {
            document.querySelector('.main-content').scrollTop = 0;
        }
    }

    createClipCardHtml(clip) {
        const category = clip.category || 'text';
        const info = this.categoryInfo[category] || { color: '#6B7280', icon: '📝' };
        const isPassword = category === 'password';
        const isMasked = isPassword && this.passwordLocked;
        const isCode = category === 'code';

        let displayContent = clip.content || '';
        if (displayContent.length > 220) {
            displayContent = displayContent.substring(0, 220) + '...';
        }

        const timeDisplay = this.formatRelativeTime(clip.timestamp);
        const fullTime = clip.timestamp ? new Date(clip.timestamp + 'Z').toLocaleString() : '';

        return `
            <div class="clip-card ${isCode ? 'is-code' : ''}" data-id="${clip.id}" style="--category-color: ${info.color}">
                <div class="clip-header">
                    <div class="clip-category">
                        <span>${info.icon}</span>
                        <span>${category}</span>
                    </div>
                    <div class="clip-actions">
                        <button class="clip-action-btn" data-action="${clip.is_pinned ? 'unpin' : 'pin'}" title="${clip.is_pinned ? 'Unpin' : 'Pin'}">
                            ${clip.is_pinned ? '📌' : '📍'}
                        </button>
                        <button class="clip-action-btn" data-action="${clip.is_favorite ? 'unfavorite' : 'favorite'}" title="${clip.is_favorite ? 'Unfavorite' : 'Favorite'}">
                            ${clip.is_favorite ? '⭐' : '☆'}
                        </button>
                        <button class="clip-action-btn" data-action="delete" title="Delete Clip">🗑️</button>
                    </div>
                </div>

                <div class="clip-content ${isMasked ? 'masked' : ''}">${this.escapeHtml(displayContent)}</div>

                ${isMasked ? `
                    <div style="margin-bottom: 0.5rem;">
                        <button class="secondary-btn" data-action="unlock" style="font-size: 0.78rem; padding: 0.35rem 0.65rem; width: 100%;">
                            👁️ Unlock Password
                        </button>
                    </div>
                ` : ''}

                <div class="clip-footer">
                    <span class="clip-time" title="${fullTime}">${timeDisplay}</span>
                    <button class="clip-copy-btn" data-action="copy" title="Copy to clipboard">
                        📋 Copy
                    </button>
                </div>
            </div>
        `;
    }

    attachClipEventListeners() {
        document.querySelectorAll('.clip-card').forEach(card => {
            const clipId = parseInt(card.dataset.id, 10);
            const clip = this.clips.find(c => c.id === clipId);

            card.addEventListener('click', (event) => {
                if (event.target.closest('[data-action]')) {
                    return; // Handled by action buttons
                }
                if (clip) {
                    if (clip.category === 'password' && this.passwordLocked) {
                        this.openUnlockModal();
                    } else {
                        this.openPreview(clip);
                    }
                }
            });

            card.querySelectorAll('[data-action]').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.handleClipAction(clipId, btn.dataset.action, btn);
                });
            });
        });
    }

    // ============= Actions =============

    async handleClipAction(clipId, action, btnElement = null) {
        try {
            switch (action) {
                case 'copy':
                    await this.copyClip(clipId, btnElement);
                    break;
                case 'pin':
                case 'unpin':
                    await window.pywebview.api.toggle_pin(clipId);
                    await this.loadClips(this.currentCategory);
                    break;
                case 'favorite':
                case 'unfavorite':
                    await window.pywebview.api.toggle_favorite(clipId);
                    await this.loadClips(this.currentCategory);
                    break;
                case 'delete':
                    if (confirm('Are you sure you want to delete this clip?')) {
                        await window.pywebview.api.delete_clip(clipId);
                        await this.loadClips(this.currentCategory);
                        this.showToast('🗑️ Clip deleted');
                    }
                    break;
                case 'unlock':
                    this.openUnlockModal();
                    break;
            }
        } catch (error) {
            console.error('Clip action failed:', error);
        }
    }

    async copyClip(clipId, btnElement = null) {
        try {
            const success = await window.pywebview.api.copy_clip(clipId);
            if (success) {
                if (btnElement) {
                    const originalHtml = btnElement.innerHTML;
                    btnElement.innerHTML = '✓ Copied!';
                    btnElement.classList.add('copied');
                    setTimeout(() => {
                        btnElement.innerHTML = originalHtml;
                        btnElement.classList.remove('copied');
                    }, 1400);
                }
                this.showToast('📋 Copied to clipboard!');
            } else {
                this.showToast('❌ Copy failed: clip is protected or unavailable');
            }
        } catch (error) {
            console.error('Copy failed:', error);
        }
    }

    // ============= Preview & Editing =============

    openPreview(clip) {
        this.currentPreviewClip = clip;
        this.isEditing = false;

        const modal = document.getElementById('previewModal');
        const title = document.getElementById('previewTitle');
        const tag = document.getElementById('previewCategoryTag');
        const time = document.getElementById('previewTimestamp');
        const chars = document.getElementById('previewCharCount');
        const viewContent = document.getElementById('previewContent');
        const editContent = document.getElementById('previewEditContent');

        const copyBtn = document.getElementById('previewCopyBtn');
        const editBtn = document.getElementById('previewEditBtn');
        const saveBtn = document.getElementById('previewSaveBtn');
        const cancelBtn = document.getElementById('previewCancelBtn');

        title.textContent = `Clip Preview #${clip.id}`;
        tag.textContent = clip.category;
        time.textContent = clip.timestamp ? new Date(clip.timestamp + 'Z').toLocaleString() : '';
        chars.textContent = `${(clip.content || '').length} characters`;

        viewContent.textContent = clip.content;
        editContent.value = clip.content;

        viewContent.style.display = 'block';
        editContent.style.display = 'none';

        copyBtn.style.display = 'inline-block';
        editBtn.style.display = 'inline-block';
        saveBtn.style.display = 'none';
        cancelBtn.style.display = 'none';

        modal.classList.add('active');
    }

    enterEditMode() {
        this.isEditing = true;
        document.getElementById('previewContent').style.display = 'none';
        const editContent = document.getElementById('previewEditContent');
        editContent.style.display = 'block';

        document.getElementById('previewCopyBtn').style.display = 'none';
        document.getElementById('previewEditBtn').style.display = 'none';
        document.getElementById('previewSaveBtn').style.display = 'inline-block';
        document.getElementById('previewCancelBtn').style.display = 'inline-block';

        editContent.focus();
    }

    exitEditMode() {
        this.isEditing = false;
        document.getElementById('previewContent').style.display = 'block';
        document.getElementById('previewEditContent').style.display = 'none';

        document.getElementById('previewCopyBtn').style.display = 'inline-block';
        document.getElementById('previewEditBtn').style.display = 'inline-block';
        document.getElementById('previewSaveBtn').style.display = 'none';
        document.getElementById('previewCancelBtn').style.display = 'none';

        if (this.currentPreviewClip) {
            document.getElementById('previewEditContent').value = this.currentPreviewClip.content;
        }
    }

    async saveEditedContent() {
        const editContent = document.getElementById('previewEditContent');
        const newText = editContent.value.trim();

        if (!newText) {
            alert('Clip content cannot be empty.');
            return;
        }

        if (newText === this.currentPreviewClip.content) {
            this.exitEditMode();
            return;
        }

        try {
            const success = await window.pywebview.api.update_clip_content(this.currentPreviewClip.id, newText);
            if (success) {
                this.currentPreviewClip.content = newText;
                document.getElementById('previewContent').textContent = newText;
                document.getElementById('previewCharCount').textContent = `${newText.length} characters`;
                this.exitEditMode();
                await this.loadClips(this.currentCategory);
                this.showToast('✅ Clip updated successfully!');
            } else {
                alert('Failed to update clip.');
            }
        } catch (error) {
            console.error('Update clip error:', error);
        }
    }

    // ============= Modals Management =============

    openUnlockModal() {
        const modal = document.getElementById('unlockModal');
        const input = document.getElementById('unlockPasskeyInput');
        const errorMsg = document.getElementById('unlockError');

        modal.classList.add('active');
        input.value = '';
        errorMsg.style.display = 'none';
        setTimeout(() => input.focus(), 100);
    }

    async submitUnlock() {
        const input = document.getElementById('unlockPasskeyInput');
        const errorMsg = document.getElementById('unlockError');
        const passkey = input.value;

        if (!passkey) return;

        const verified = await window.pywebview.api.verify_passkey(passkey);
        if (verified) {
            this.passwordLocked = false;
            document.getElementById('unlockModal').classList.remove('active');
            await this.loadClips(this.currentCategory);
            this.showToast('🔓 Password clips unlocked');
        } else {
            errorMsg.style.display = 'block';
        }
    }

    async openStatsModal() {
        try {
            const statsStr = await window.pywebview.api.get_app_stats();
            const stats = JSON.parse(statsStr);

            document.getElementById('statTotalClips').textContent = stats.total_clips;
            document.getElementById('statPinnedClips').textContent = stats.pinned_clips;
            document.getElementById('statFavoriteClips').textContent = stats.favorite_clips;

            const sizeKb = (stats.db_size_bytes / 1024).toFixed(1);
            document.getElementById('statDbSize').textContent = `${sizeKb} KB`;

            const catContainer = document.getElementById('statsCategories');
            catContainer.innerHTML = Object.entries(stats.categories || {})
                .map(([cat, count]) => {
                    const info = this.categoryInfo[cat] || { icon: '📝' };
                    return `
                        <div class="stat-cat-row">
                            <span>${info.icon} ${cat}</span>
                            <strong>${count}</strong>
                        </div>
                    `;
                }).join('');

            document.getElementById('statsModal').classList.add('active');
        } catch (error) {
            console.error('Failed to load stats:', error);
        }
    }

    // ============= Event Listeners & Hotkeys =============

    setupEventListeners() {
        // Category navigation
        document.querySelectorAll('.category-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.category-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                this.currentCategory = btn.dataset.category;
                this.searchQuery = '';
                document.getElementById('searchInput').value = '';
                document.getElementById('searchClearBtn').style.display = 'none';

                const label = btn.querySelector('.cat-label').textContent;
                document.getElementById('contentTitle').textContent = label;

                this.loadClips(this.currentCategory, true);
            });
        });

        // Filter chips (Pinned & Favorites)
        const filterPinnedBtn = document.getElementById('filterPinnedBtn');
        filterPinnedBtn.addEventListener('click', () => {
            if (this.filterType === 'pinned') {
                this.filterType = 'none';
                filterPinnedBtn.classList.remove('active');
            } else {
                this.filterType = 'pinned';
                filterPinnedBtn.classList.add('active');
                document.getElementById('filterFavoriteBtn').classList.remove('active');
            }
            this.loadClips(this.currentCategory);
        });

        const filterFavoriteBtn = document.getElementById('filterFavoriteBtn');
        filterFavoriteBtn.addEventListener('click', () => {
            if (this.filterType === 'favorite') {
                this.filterType = 'none';
                filterFavoriteBtn.classList.remove('active');
            } else {
                this.filterType = 'favorite';
                filterFavoriteBtn.classList.add('active');
                document.getElementById('filterPinnedBtn').classList.remove('active');
            }
            this.loadClips(this.currentCategory);
        });

        // Search Input & Clear
        const searchInput = document.getElementById('searchInput');
        const clearBtn = document.getElementById('searchClearBtn');

        searchInput.addEventListener('input', (e) => {
            const query = e.target.value.trim();
            this.searchQuery = query;
            clearBtn.style.display = query ? 'block' : 'none';

            clearTimeout(this.searchTimeout);
            this.searchTimeout = setTimeout(() => {
                this.loadClips(this.currentCategory);
            }, 250);
        });

        clearBtn.addEventListener('click', () => {
            searchInput.value = '';
            this.searchQuery = '';
            clearBtn.style.display = 'none';
            this.loadClips(this.currentCategory);
            searchInput.focus();
        });

        // Floating manual snippet add
        const manualAddBtn = document.getElementById('manualAddBtn');
        const manualInput = document.getElementById('manualSnippetInput');

        const addSnippet = async () => {
            const content = manualInput.value.trim();
            if (!content) return;

            const category = document.getElementById('manualCategorySelect').value;
            const success = await window.pywebview.api.manual_add_clip(content, category);
            if (success) {
                manualInput.value = '';
                this.showToast('✅ Snippet added to clips');
                await this.loadClips(this.currentCategory);
            }
        };

        manualAddBtn.addEventListener('click', addSnippet);
        manualInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                addSnippet();
            }
        });

        // Header Buttons
        document.getElementById('statsBtn').addEventListener('click', () => this.openStatsModal());
        document.getElementById('settingsBtn').addEventListener('click', () => {
            document.getElementById('settingsModal').classList.add('active');
        });

        // Generic Modal close buttons
        document.querySelectorAll('.close-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const modalId = btn.dataset.modal;
                if (modalId) {
                    document.getElementById(modalId).classList.remove('active');
                } else {
                    btn.closest('.modal').classList.remove('active');
                }
                this.exitEditMode();
            });
        });

        // Close modal on outside backdrop click
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.classList.remove('active');
                    this.exitEditMode();
                }
            });
        });

        // Passkey setup
        document.getElementById('setPasskeyBtn').addEventListener('click', async () => {
            const passkey = document.getElementById('passkeyInput').value;
            if (passkey.length < 4) {
                alert('Passkey must be at least 4 characters');
                return;
            }
            const success = await window.pywebview.api.setup_passkey(passkey);
            if (success) {
                document.getElementById('passkeySetup').style.display = 'none';
                document.getElementById('passkeyStatus').style.display = 'block';
                this.passwordLocked = false;
                this.showToast('🔒 Master passkey configured!');
                await this.loadClips(this.currentCategory);
            }
        });

        // Lock Passwords button
        document.getElementById('lockPasswordsBtn').addEventListener('click', async () => {
            await window.pywebview.api.lock_passwords();
            this.passwordLocked = true;
            await this.loadClips(this.currentCategory);
            this.showToast('🔒 Passwords locked');
        });

        // Unlock Modal submit
        document.getElementById('unlockBtn').addEventListener('click', () => this.submitUnlock());
        document.getElementById('unlockPasskeyInput').addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.submitUnlock();
            }
        });

        // Category checkboxes in Settings
        document.querySelectorAll('.toggle-item input[type="checkbox"]').forEach(checkbox => {
            checkbox.addEventListener('change', async (e) => {
                const category = e.target.dataset.category;
                await window.pywebview.api.set_category_enabled(category, e.target.checked);
            });
        });

        // Export button
        document.getElementById('exportBtn').addEventListener('click', async () => {
            try {
                const filePath = await window.pywebview.api.export_clips_to_file();
                this.showToast(`📤 Clips exported to:\n${filePath}`);
            } catch (error) {
                // Fallback to in-browser JSON blob download
                try {
                    const data = await window.pywebview.api.export_clips();
                    this.downloadFile('clipboard_export.json', data);
                    this.showToast('📤 Clips downloaded as JSON');
                } catch (e) {
                    alert('Export failed: ' + error.message);
                }
            }
        });

        // Cleanup button
        document.getElementById('cleanupBtn').addEventListener('click', async () => {
            if (confirm('Delete unpinned clips older than 30 days?')) {
                const count = await window.pywebview.api.cleanup_old_clips(30);
                this.showToast(`🗑️ Cleaned up ${count} old clips`);
                await this.loadClips(this.currentCategory);
            }
        });

        // Preview modal buttons
        document.getElementById('previewCopyBtn').addEventListener('click', () => {
            if (this.currentPreviewClip) {
                this.copyClip(this.currentPreviewClip.id);
            }
        });
        document.getElementById('previewEditBtn').addEventListener('click', () => this.enterEditMode());
        document.getElementById('previewSaveBtn').addEventListener('click', () => this.saveEditedContent());
        document.getElementById('previewCancelBtn').addEventListener('click', () => this.exitEditMode());
    }

    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Escape: Close modals or clear search
            if (e.key === 'Escape') {
                const openModal = document.querySelector('.modal.active');
                if (openModal) {
                    openModal.classList.remove('active');
                    this.exitEditMode();
                } else if (this.searchQuery) {
                    document.getElementById('searchInput').value = '';
                    this.searchQuery = '';
                    document.getElementById('searchClearBtn').style.display = 'none';
                    this.loadClips(this.currentCategory);
                }
            }

            // Ctrl + F or Slash: Focus search
            if ((e.ctrlKey && e.key.toLowerCase() === 'f') || (e.key === '/' && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA')) {
                e.preventDefault();
                const input = document.getElementById('searchInput');
                input.focus();
                input.select();
            }

            // Ctrl + N: Focus new snippet
            if (e.ctrlKey && e.key.toLowerCase() === 'n') {
                e.preventDefault();
                document.getElementById('manualSnippetInput').focus();
            }

            // Ctrl + I: Stats
            if (e.ctrlKey && e.key.toLowerCase() === 'i') {
                e.preventDefault();
                this.openStatsModal();
            }

            // Ctrl + ,: Settings
            if (e.ctrlKey && e.key === ',') {
                e.preventDefault();
                document.getElementById('settingsModal').classList.toggle('active');
            }

            // Ctrl + Enter in Edit Mode: Save
            if (e.ctrlKey && e.key === 'Enter' && this.isEditing) {
                e.preventDefault();
                this.saveEditedContent();
            }
        });
    }

    // ============= Utilities =============

    formatRelativeTime(isoString) {
        if (!isoString) return '';
        try {
            const date = new Date(isoString.replace(' ', 'T') + 'Z');
            const now = new Date();
            const diffSec = Math.floor((now - date) / 1000);

            if (diffSec < 60) return 'Just now';
            if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
            if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
            if (diffSec < 604800) return `${Math.floor(diffSec / 86400)}d ago`;

            return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
        } catch (e) {
            return isoString;
        }
    }

    escapeHtml(text) {
        if (!text) return '';
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    }

    showToast(message) {
        let container = document.querySelector('.toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container';
            document.body.appendChild(container);
        }

        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.textContent = message;
        container.appendChild(toast);

        setTimeout(() => toast.remove(), 3000);
    }

    downloadFile(filename, content) {
        const blob = new Blob([content], { type: 'application/json;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
}

// Initialize application on DOM readiness
document.addEventListener('DOMContentLoaded', () => {
    window.clipboardApp = new ClipboardApp();
});
