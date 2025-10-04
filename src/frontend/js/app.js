// frontend/js/app.js

class ClipboardApp {
    constructor() {
        this.clips = [];
        this.currentCategory = 'all';
        this.categoryInfo = {};
        this.searchTimeout = null;
        this.passwordLocked = true;
        this.setupPreviewModal();
        
        this.init();
    }

    async init() {
        console.log('Waiting for pywebview API...');
        await this.waitForPyWebView();
        console.log('pywebview API available:', window.pywebview.api);
        await this.loadCategoryInfo();
        await this.loadClips();
        await this.loadSettings();
        this.setupEventListeners();
        this.startAutoRefresh();
    }

    waitForPyWebView() {
        return new Promise((resolve) => {
            const checkInterval = setInterval(() => {
                if (window.pywebview && window.pywebview.api) {
                    clearInterval(checkInterval);
                    resolve();
                }
            }, 100);
        });
    }

    setupPreviewModal() {
        this.previewModal = document.getElementById('previewModal');
        this.previewContent = document.getElementById('previewContent');
        this.previewEditContent = document.getElementById('previewEditContent');
        this.previewTitle = document.getElementById('previewTitle');
        this.previewCloseBtn = document.getElementById('previewCloseBtn');
        this.previewCopyBtn = document.getElementById('previewCopyBtn');
        this.previewEditBtn = document.getElementById('previewEditBtn');
        this.previewSaveBtn = document.getElementById('previewSaveBtn');
        this.previewCancelBtn = document.getElementById('previewCancelBtn');
    
        this.previewCloseBtn.addEventListener('click', () => this.closePreview());
        this.previewModal.addEventListener('click', (e) => {
          if (e.target === this.previewModal) this.closePreview();
        });
        this.previewCopyBtn.addEventListener('click', () => this.copyPreviewContent());
        this.previewCopyBtn.addEventListener('click', () => this.copyPreviewContent());
        this.previewEditBtn.addEventListener('click', () => this.enterEditMode());
        this.previewCancelBtn.addEventListener('click', () => this.exitEditMode());
        this.previewSaveBtn.addEventListener('click', () => this.saveEditedContent());
      }
    
      openPreview(clip) {
        this.currentPreviewClip = clip;
        this.previewTitle.textContent = `Preview - ${clip.category}`;

        this.previewContent.textContent = clip.content;
        this.previewEditContent.value = clip.content;

        // Show view mode, hide edit mode initially
        this.previewContent.style.display = 'block';
        this.previewEditContent.style.display = 'none';
        this.previewCopyBtn.style.display = 'inline-block';
        this.previewEditBtn.style.display = 'inline-block';
        this.previewSaveBtn.style.display = 'none';
        this.previewCancelBtn.style.display = 'none';

        this.previewModal.style.display = 'block';
      }
      enterEditMode() {
        this.previewContent.style.display = 'none';
        this.previewEditContent.style.display = 'block';
    
        this.previewCopyBtn.style.display = 'none';
        this.previewEditBtn.style.display = 'none';
        this.previewSaveBtn.style.display = 'inline-block';
        this.previewCancelBtn.style.display = 'inline-block';
    
        this.previewEditContent.focus();
      }
    
      exitEditMode() {
        this.previewContent.style.display = 'block';
        this.previewEditContent.style.display = 'none';
    
        this.previewCopyBtn.style.display = 'inline-block';
        this.previewEditBtn.style.display = 'inline-block';
        this.previewSaveBtn.style.display = 'none';
        this.previewCancelBtn.style.display = 'none';
    
        // Reset textarea content to last saved clip content
        this.previewEditContent.value = this.currentPreviewClip.content;
      }
    
      async saveEditedContent() {
        const newContent = this.previewEditContent.value.trim();
        if (!newContent) {
          alert('Content cannot be empty!');
          return;
        }
    
        if (newContent === this.currentPreviewClip.content) {
          this.exitEditMode();
          return;
        }
    
        try {
          // Call backend API to update clip content
          // Assuming you add an API method `update_clip_content(clipId, content)`
          const success = await window.pywebview.api.update_clip_content(this.currentPreviewClip.id, newContent);
          if (success) {
            this.showNotification('✅ Clip updated!');
            // Update local clip content and UI
            this.currentPreviewClip.content = newContent;
            this.previewContent.textContent = newContent;
            this.exitEditMode();
            // Reload clips list if desired
            await this.loadClips(this.currentCategory);
          } else {
            alert('Failed to update clip.');
          }
        } catch (error) {
          console.error('Update clip failed:', error);
          alert('Error updating clip.');
        }
      }
    
      closePreview() {
        this.previewModal.style.display = 'none';
      }
    
      async copyPreviewContent() {
        if (!this.currentPreviewClip) return;
        try {
          await navigator.clipboard.writeText(this.currentPreviewClip.content);
          this.showNotification('Copied preview content to clipboard!');
        } catch {
          alert('Failed to copy to clipboard');
        }
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

    async loadClips(category = 'all') {
        try {
            let clipsJson;
            if (category === 'all') {
                clipsJson = await window.pywebview.api.get_all_clips();
            } else {
                clipsJson = await window.pywebview.api.get_clips_by_category(category);
            }
            
            this.clips = JSON.parse(clipsJson);
            this.renderClips();
        } catch (error) {
            console.error('Failed to load clips:', error);
        }
    }

    async loadSettings() {
        try {
            // Load category settings
            const categorySettings = await window.pywebview.api.get_category_settings();
            const settings = JSON.parse(categorySettings);
            
            // Update checkboxes
            document.querySelectorAll('.toggle-item input[type="checkbox"]').forEach(checkbox => {
                const category = checkbox.dataset.category;
                checkbox.checked = settings[category] || false;
            });

            // Check password lock status
            this.passwordLocked = await window.pywebview.api.is_password_locked();
            const passkeySet = await window.pywebview.api.is_passkey_set();
            
            if (passkeySet) {
                document.getElementById('passkeySetup').style.display = 'none';
                document.getElementById('passkeyStatus').style.display = 'block';
            }
        } catch (error) {
            console.error('Failed to load settings:', error);
        }
    }

    // ============= Rendering =============

    renderClips() {
        const grid = document.getElementById('clipsGrid');
        const emptyState = document.getElementById('emptyState');
        const clipCount = document.getElementById('clipCount');

        if (this.clips.length === 0) {
            grid.style.display = 'none';
            emptyState.style.display = 'block';
            clipCount.textContent = '0 clips';
            return;
        }

        grid.style.display = 'grid';
        emptyState.style.display = 'none';
        clipCount.textContent = `${this.clips.length} clip${this.clips.length !== 1 ? 's' : ''}`;

        grid.innerHTML = this.clips.map(clip => this.createClipCard(clip)).join('');
        
        // Attach event listeners
        this.attachClipEventListeners();
    }

    createClipCard(clip) {
        const category = clip.category;
        const info = this.categoryInfo[category] || { color: '#6B7280', icon: '📝' };
        const isPassword = category === 'password';
        const isEncrypted = clip.is_encrypted;
        const isMasked = isPassword && this.passwordLocked;

        const truncatedContent = clip.content.length > 200 
            ? clip.content.substring(0, 200) + '...' 
            : clip.content;

        const timeAgo = this.formatTimestampIST(clip.timestamp);

        return `
            <div class="clip-card" data-id="${clip.id}" style="--category-color: ${info.color}">
                <div class="clip-header">
                    <div class="clip-category">
                        <span>${info.icon}</span>
                        <span>${category}</span>
                    </div>
                    <div class="clip-actions">
                        ${clip.is_pinned ? 
                            '<button class="clip-action-btn" data-action="unpin" title="Unpin">📌</button>' :
                            '<button class="clip-action-btn" data-action="pin" title="Pin">📍</button>'
                        }
                        ${clip.is_favorite ? 
                            '<button class="clip-action-btn" data-action="unfavorite" title="Unfavorite">⭐</button>' :
                            '<button class="clip-action-btn" data-action="favorite" title="Favorite">☆</button>'
                        }
                        <button class="clip-action-btn" data-action="delete" title="Delete">🗑️</button>
                    </div>
                </div>
                <div class="clip-content ${isMasked ? 'masked' : ''}">${this.escapeHtml(truncatedContent)}</div>
                ${isMasked ? `
                    <div style="margin-top: 0.5rem;">
                        <button class="clip-action-btn" data-action="unlock" style="opacity: 1;">
                            👁️ Show Password
                        </button>
                    </div>
                ` : ''}
                <div class="clip-footer">
                    <span class="clip-time">${timeAgo}</span>
                    <button class="clip-copy-btn" data-action="copy">
                        📋 Copy
                    </button>
                </div>
            </div>
        `;
    }

    attachClipEventListeners() {
        document.querySelectorAll('.clip-card').forEach(card => {
            const clipId = parseInt(card.dataset.id);
            const clip = this.clips.find(c => c.id === clipId);
        
            card.addEventListener('click', (event) => {
                if (clip && clip.category === 'password' && this.passwordLocked) {
                    // Check if click target is the unlock button
                    if (!event.target.closest('[data-action="unlock"]')) {
                        // Ignore clicks outside the unlock button - do not open preview
                        return;
                    }
                }
                if (clip) this.openPreview(clip);
            });
    
            card.querySelectorAll('[data-action]').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.handleClipAction(clipId, btn.dataset.action);
                });
            });
        });
    }
    

    // ============= Actions =============

    async handleClipAction(clipId, action) {
        try {
            switch (action) {
                case 'copy':
                    await this.copyClip(clipId);
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
                    if (confirm('Delete this clip?')) {
                        await window.pywebview.api.delete_clip(clipId);
                        await this.loadClips(this.currentCategory);
                    }
                    break;
                case 'unlock':
                    await this.unlockPassword(clipId);
                    break;
            }
        } catch (error) {
            console.error('Action failed:', error);
        }
    }

    async copyClip(clipId) {
        try {
            const success = await window.pywebview.api.copy_clip(clipId);
            if (success) {
                this.showNotification('✅ Copied to clipboard!');
            }
        } catch (error) {
            console.error('Copy failed:', error);
        }
    }

    async unlockPassword(clipId) {
        const modal = document.getElementById('unlockModal');
        const input = document.getElementById('unlockPasskeyInput');
        const unlockBtn = document.getElementById('unlockBtn');
        const errorMsg = document.getElementById('unlockError');

        modal.classList.add('active');
        input.value = '';
        errorMsg.style.display = 'none';

        unlockBtn.onclick = async () => {
            const passkey = input.value;
            const verified = await window.pywebview.api.verify_passkey(passkey);
            
            if (verified) {
                this.passwordLocked = false;
                modal.classList.remove('active');
                await this.loadClips(this.currentCategory);
            } else {
                errorMsg.style.display = 'block';
            }
        };
    }

    // ============= Event Listeners =============

    setupEventListeners() {
        // Category navigation
        document.querySelectorAll('.category-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.category-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                
                const category = btn.dataset.category;
                this.currentCategory = category;
                
                // Update title
                const title = btn.textContent.trim();
                document.getElementById('contentTitle').textContent = title;
                
                this.loadClips(category);
            });
        });

        // Search
        const searchInput = document.getElementById('searchInput');
        searchInput.addEventListener('input', (e) => {
            clearTimeout(this.searchTimeout);
            this.searchTimeout = setTimeout(() => {
                this.searchClips(e.target.value);
            }, 300);
        });

        // Settings modal
        const settingsBtn = document.getElementById('settingsBtn');
        const settingsModal = document.getElementById('settingsModal');
        const closeBtn = settingsModal.querySelector('.close-btn');

        settingsBtn.addEventListener('click', () => {
            settingsModal.classList.add('active');
        });

        closeBtn.addEventListener('click', () => {
            settingsModal.classList.remove('active');
        });

        // Category toggles
        document.querySelectorAll('.toggle-item input[type="checkbox"]').forEach(checkbox => {
            checkbox.addEventListener('change', async (e) => {
                const category = e.target.dataset.category;
                const enabled = e.target.checked;
                await window.pywebview.api.set_category_enabled(category, enabled);
            });
        });

        // Passkey setup
        const setPasskeyBtn = document.getElementById('setPasskeyBtn');
        setPasskeyBtn.addEventListener('click', async () => {
            const passkey = document.getElementById('passkeyInput').value;
            if (passkey.length < 4) {
                alert('Passkey must be at least 4 characters');
                return;
            }
            
            const success = await window.pywebview.api.setup_passkey(passkey);
            if (success) {
                document.getElementById('passkeySetup').style.display = 'none';
                document.getElementById('passkeyStatus').style.display = 'block';
                this.showNotification('✅ Passkey set successfully!');
            }
        });

        // Lock passwords
        const lockBtn = document.getElementById('lockPasswordsBtn');
        lockBtn.addEventListener('click', async () => {
            await window.pywebview.api.lock_passwords();
            this.passwordLocked = true;
            await this.loadClips(this.currentCategory);
            this.showNotification('🔒 Passwords locked');
        });

        // Cleanup
        const cleanupBtn = document.getElementById('cleanupBtn');
        cleanupBtn.addEventListener('click', async () => {
            if (confirm('Delete clips older than 30 days?')) {
                const deleted = await window.pywebview.api.cleanup_old_clips(30);
                this.showNotification(`🗑️ Deleted ${deleted} old clips`);
                await this.loadClips(this.currentCategory);
            }
        });

        // Export
        const exportBtn = document.getElementById('exportBtn');
        exportBtn.addEventListener('click', async () => {
            const data = await window.pywebview.api.export_clips();
            this.downloadFile('clipboard_export.json', data);
            this.showNotification('📤 Clips exported!');
        });

        // Manual snippet add
        const manualAddBtn = document.getElementById('manualAddBtn');
        manualAddBtn.addEventListener('click', async () => {
            const content = document.getElementById('manualSnippetInput').value.trim();
            if (!content) {
                alert('Please enter a snippet to add.');
                return;
            }
            const category = document.getElementById('manualCategorySelect').value;

            try {
                const success = await window.pywebview.api.manual_add_clip(content, category);
                if (success) {
                    this.showNotification('✅ Snippet added!');
                    document.getElementById('manualSnippetInput').value = '';
                    if (this.currentCategory === 'all' || this.currentCategory === category) {
                        await this.loadClips(this.currentCategory);
                    }
                } else {
                    alert('Failed to add snippet.');
                }
            } catch (error) {
                console.error('Error adding snippet:', error);
            }
        });
    }

    async searchClips(query) {
        if (!query.trim()) {
            await this.loadClips(this.currentCategory);
            return;
        }

        try {
            const results = await window.pywebview.api.search_clips(query);
            this.clips = JSON.parse(results);
            this.renderClips();
        } catch (error) {
            console.error('Search failed:', error);
        }
    }

    // ============= Utilities =============

    startAutoRefresh() {
        // Refresh clips every 2 seconds to catch new ones
        setInterval(async () => {
            if (this.currentCategory === 'all' && !document.getElementById('searchInput').value) {
                await this.loadClips('all');
            }
        }, 2000);
    }

    getTimeAgo(utcTimestamp) {
        // Parse the UTC timestamp, add +5:30 hours for IST
        const utcDate = new Date(utcTimestamp + "Z");
        const istOffsetMs = 5.5 * 60 * 60 * 1000;
        const istDate = new Date(utcDate.getTime() + istOffsetMs);
        const now = new Date();
        const secondsAgo = Math.floor((now - istDate) / 1000);
      
        if (secondsAgo < 60) return 'Just now';
        if (secondsAgo < 3600) return `${Math.floor(secondsAgo / 60)}m ago`;
        if (secondsAgo < 86400) return `${Math.floor(secondsAgo / 3600)}h ago`;
        return `${Math.floor(secondsAgo / 86400)}d ago`;
    }
    formatTimestampIST(isoTimestamp) {
        // Parse as local date (no manual offset)
        const utcDate = new Date(isoTimestamp + 'Z');
  
        // Format to string in Asia/Kolkata timezone (IST)
        return utcDate.toLocaleString('en-IN', {
            timeZone: 'Asia/Kolkata',
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        });
    }
    
      

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showNotification(message) {
        // Simple notification - could be enhanced with toast library
        const notification = document.createElement('div');
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: var(--primary-color);
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            box-shadow: var(--shadow-lg);
            z-index: 10000;
            animation: slideIn 0.3s ease;
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    downloadFile(filename, content) {
        const blob = new Blob([content], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.clipboardApp = new ClipboardApp();
});

// Export all clips
document.getElementById('exportBtn').onclick = async function() {
    try {
        const filePath = await window.pywebview.api.export_clips_to_file();
        console.log("Exported file path:", filePath);
        alert('Export completed! File saved at:\n' + filePath);
    } catch (error) {
        alert('Export failed: ' + error.message);
    }
};


document.getElementById('cleanupBtn').onclick = async function() {
    if (window.pywebview) {
        await window.pywebview.api.cleanup_old_clips();
        // Optionally: refresh UI
    }
};
const unlockModal = document.getElementById('unlockModal');
const unlockCloseBtn = document.getElementById('unlockCloseBtn');

unlockCloseBtn.addEventListener('click', () => {
  unlockModal.classList.remove('active');
});
