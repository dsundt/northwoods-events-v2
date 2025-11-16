// ============================================================================
// Configuration Sync - Store API Keys in GitHub Repository
// ============================================================================
// This allows API keys to sync across different machines and browsers

(function() {
    'use strict';
    
    const CONFIG_FILE_PATH = 'config/api-keys.json';
    const STORAGE_KEY_PREFIX = 'northwoods_';
    
    /**
     * Encrypt text using AES-like encryption with a password
     * Note: This is basic encryption. For production, use a proper crypto library.
     */
    async function encrypt(text, password) {
        const encoder = new TextEncoder();
        const data = encoder.encode(text);
        const passwordKey = await crypto.subtle.importKey(
            'raw',
            encoder.encode(password.padEnd(32, '0').slice(0, 32)),
            { name: 'AES-GCM' },
            false,
            ['encrypt']
        );
        
        const iv = crypto.getRandomValues(new Uint8Array(12));
        const encrypted = await crypto.subtle.encrypt(
            { name: 'AES-GCM', iv },
            passwordKey,
            data
        );
        
        // Combine IV and encrypted data
        const combined = new Uint8Array(iv.length + encrypted.byteLength);
        combined.set(iv);
        combined.set(new Uint8Array(encrypted), iv.length);
        
        // Convert to base64
        return btoa(String.fromCharCode(...combined));
    }
    
    /**
     * Decrypt text using AES-like decryption with a password
     */
    async function decrypt(encryptedBase64, password) {
        try {
            const encoder = new TextEncoder();
            const combined = Uint8Array.from(atob(encryptedBase64), c => c.charCodeAt(0));
            
            const iv = combined.slice(0, 12);
            const encrypted = combined.slice(12);
            
            const passwordKey = await crypto.subtle.importKey(
                'raw',
                encoder.encode(password.padEnd(32, '0').slice(0, 32)),
                { name: 'AES-GCM' },
                false,
                ['decrypt']
            );
            
            const decrypted = await crypto.subtle.decrypt(
                { name: 'AES-GCM', iv },
                passwordKey,
                encrypted
            );
            
            return new TextDecoder().decode(decrypted);
        } catch (error) {
            throw new Error('Decryption failed - wrong password or corrupted data');
        }
    }
    
    /**
     * Get current configuration from localStorage
     */
    function getCurrentConfig() {
        return {
            github_token: localStorage.getItem('github_token') || '',
            openai_api_key: localStorage.getItem('openai_api_key') || '',
            runway_api_key: localStorage.getItem('runway_api_key') || '',
            beatoven_api_key: localStorage.getItem('beatoven_api_key') || '',
            reel_backend_url: localStorage.getItem('reel_backend_url') || '',
            github_owner: localStorage.getItem('github_owner') || '',
            github_repo: localStorage.getItem('github_repo') || '',
            github_branch: localStorage.getItem('github_branch') || 'main',
        };
    }
    
    /**
     * Apply configuration to localStorage
     */
    function applyConfig(config) {
        if (config.github_token) localStorage.setItem('github_token', config.github_token);
        if (config.openai_api_key) localStorage.setItem('openai_api_key', config.openai_api_key);
        if (config.runway_api_key) localStorage.setItem('runway_api_key', config.runway_api_key);
        if (config.beatoven_api_key) localStorage.setItem('beatoven_api_key', config.beatoven_api_key);
        if (config.reel_backend_url) localStorage.setItem('reel_backend_url', config.reel_backend_url);
        if (config.github_owner) localStorage.setItem('github_owner', config.github_owner);
        if (config.github_repo) localStorage.setItem('github_repo', config.github_repo);
        if (config.github_branch) localStorage.setItem('github_branch', config.github_branch);
    }
    
    /**
     * Upload encrypted config to GitHub
     */
    async function uploadConfigToGitHub(password) {
        const config = getCurrentConfig();
        
        if (!config.github_token || !config.github_owner || !config.github_repo) {
            throw new Error('GitHub configuration required (token, owner, repo)');
        }
        
        // Encrypt the entire config
        const encryptedConfig = await encrypt(JSON.stringify(config), password);
        
        // Check if file exists
        const checkUrl = `https://api.github.com/repos/${config.github_owner}/${config.github_repo}/contents/${CONFIG_FILE_PATH}`;
        const checkResponse = await fetch(checkUrl, {
            headers: {
                'Authorization': `Bearer ${config.github_token}`,
                'Accept': 'application/vnd.github.v3+json',
            }
        });
        
        let sha = null;
        if (checkResponse.ok) {
            const existingFile = await checkResponse.json();
            sha = existingFile.sha;
        }
        
        // Upload to GitHub
        const uploadData = {
            message: 'Update encrypted API keys configuration',
            content: btoa(encryptedConfig), // Base64 encode the encrypted data
            branch: config.github_branch || 'main',
        };
        
        if (sha) {
            uploadData.sha = sha; // Update existing file
        }
        
        const uploadResponse = await fetch(checkUrl, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${config.github_token}`,
                'Accept': 'application/vnd.github.v3+json',
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(uploadData),
        });
        
        if (!uploadResponse.ok) {
            const error = await uploadResponse.json();
            throw new Error(error.message || 'Failed to upload configuration');
        }
        
        return true;
    }
    
    /**
     * Download and decrypt config from GitHub
     */
    async function downloadConfigFromGitHub(githubToken, owner, repo, password, branch = 'main') {
        const url = `https://api.github.com/repos/${owner}/${repo}/contents/${CONFIG_FILE_PATH}`;
        
        const response = await fetch(url, {
            headers: {
                'Authorization': `Bearer ${githubToken}`,
                'Accept': 'application/vnd.github.v3+json',
            }
        });
        
        if (!response.ok) {
            if (response.status === 404) {
                throw new Error('Configuration file not found in repository');
            }
            throw new Error(`Failed to download configuration: ${response.status}`);
        }
        
        const fileData = await response.json();
        const encryptedConfig = atob(fileData.content.replace(/\n/g, ''));
        
        // Decrypt the config
        const decryptedJson = await decrypt(encryptedConfig, password);
        const config = JSON.parse(decryptedJson);
        
        // Apply to localStorage
        applyConfig(config);
        
        return config;
    }
    
    /**
     * Show sync dialog
     */
    function showSyncDialog() {
        const dialog = document.createElement('div');
        dialog.id = 'config-sync-dialog';
        dialog.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.7);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 100000;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
        `;
        
        dialog.innerHTML = `
            <div style="background: white; padding: 2.5rem; border-radius: 12px; max-width: 600px; width: 90%; box-shadow: 0 20px 60px rgba(0,0,0,0.3);">
                <h2 style="margin: 0 0 1.5rem 0; color: #2c3e50;">🔄 Sync API Keys Across Machines</h2>
                
                <div style="background: #e7f3ff; border-left: 4px solid #2196F3; padding: 1rem; margin-bottom: 1.5rem; border-radius: 4px;">
                    <strong>💡 How it works:</strong>
                    <ul style="margin: 0.5rem 0 0 0; padding-left: 1.5rem;">
                        <li>Encrypts your API keys with a master password</li>
                        <li>Stores encrypted file in your GitHub repository</li>
                        <li>Access keys from any machine with the same password</li>
                    </ul>
                </div>
                
                <div style="display: flex; gap: 1rem; margin-bottom: 1.5rem;">
                    <button id="sync-upload-btn" style="flex: 1; padding: 1rem; background: #28a745; color: white; border: none; border-radius: 6px; font-size: 1rem; font-weight: 600; cursor: pointer;">
                        ⬆️ Upload to GitHub
                    </button>
                    <button id="sync-download-btn" style="flex: 1; padding: 1rem; background: #2196F3; color: white; border: none; border-radius: 6px; font-size: 1rem; font-weight: 600; cursor: pointer;">
                        ⬇️ Download from GitHub
                    </button>
                </div>
                
                <div id="sync-form" style="display: none;">
                    <div style="margin-bottom: 1rem;">
                        <label style="display: block; margin-bottom: 0.5rem; font-weight: 600; color: #2c3e50;">Master Password</label>
                        <input type="password" id="sync-password" placeholder="Enter a strong password" 
                               style="width: 100%; padding: 0.75rem; border: 2px solid #dee2e6; border-radius: 6px; font-size: 1rem;">
                        <div style="font-size: 0.85rem; color: #6c757d; margin-top: 0.5rem;">
                            ⚠️ Remember this password - it cannot be recovered!
                        </div>
                    </div>
                    
                    <div id="download-inputs" style="display: none;">
                        <div style="margin-bottom: 1rem;">
                            <label style="display: block; margin-bottom: 0.5rem; font-weight: 600; color: #2c3e50;">GitHub Token</label>
                            <input type="password" id="sync-github-token" placeholder="ghp_..." 
                                   style="width: 100%; padding: 0.75rem; border: 2px solid #dee2e6; border-radius: 6px; font-size: 1rem;">
                        </div>
                        <div style="display: flex; gap: 0.5rem; margin-bottom: 1rem;">
                            <div style="flex: 1;">
                                <label style="display: block; margin-bottom: 0.5rem; font-weight: 600; color: #2c3e50;">Owner</label>
                                <input type="text" id="sync-owner" placeholder="username" 
                                       style="width: 100%; padding: 0.75rem; border: 2px solid #dee2e6; border-radius: 6px; font-size: 1rem;">
                            </div>
                            <div style="flex: 1;">
                                <label style="display: block; margin-bottom: 0.5rem; font-weight: 600; color: #2c3e50;">Repo</label>
                                <input type="text" id="sync-repo" placeholder="repository-name" 
                                       style="width: 100%; padding: 0.75rem; border: 2px solid #dee2e6; border-radius: 6px; font-size: 1rem;">
                            </div>
                        </div>
                    </div>
                    
                    <div id="sync-status" style="display: none; padding: 1rem; border-radius: 6px; margin-bottom: 1rem;"></div>
                    
                    <div style="display: flex; gap: 0.5rem; justify-content: flex-end;">
                        <button id="sync-cancel-btn" style="padding: 0.75rem 1.5rem; background: #6c757d; color: white; border: none; border-radius: 6px; font-weight: 600; cursor: pointer;">
                            Cancel
                        </button>
                        <button id="sync-execute-btn" style="padding: 0.75rem 1.5rem; background: #0066cc; color: white; border: none; border-radius: 6px; font-weight: 600; cursor: pointer;">
                            Execute
                        </button>
                    </div>
                </div>
                
                <button id="sync-close-btn" style="width: 100%; padding: 0.75rem; background: #6c757d; color: white; border: none; border-radius: 6px; font-weight: 600; cursor: pointer; margin-top: 1rem;">
                    Close
                </button>
            </div>
        `;
        
        document.body.appendChild(dialog);
        
        // Event listeners
        let currentMode = null;
        
        document.getElementById('sync-upload-btn').onclick = () => {
            currentMode = 'upload';
            document.getElementById('sync-form').style.display = 'block';
            document.getElementById('sync-close-btn').style.display = 'none';
            document.getElementById('download-inputs').style.display = 'none';
        };
        
        document.getElementById('sync-download-btn').onclick = () => {
            currentMode = 'download';
            document.getElementById('sync-form').style.display = 'block';
            document.getElementById('sync-close-btn').style.display = 'none';
            document.getElementById('download-inputs').style.display = 'block';
        };
        
        document.getElementById('sync-execute-btn').onclick = async () => {
            const password = document.getElementById('sync-password').value;
            const statusDiv = document.getElementById('sync-status');
            
            if (!password) {
                statusDiv.style.display = 'block';
                statusDiv.style.background = '#ffe7e7';
                statusDiv.style.color = '#cc0000';
                statusDiv.textContent = '❌ Please enter a master password';
                return;
            }
            
            try {
                statusDiv.style.display = 'block';
                statusDiv.style.background = '#e7f3ff';
                statusDiv.style.color = '#0066cc';
                statusDiv.textContent = currentMode === 'upload' ? '⏳ Uploading...' : '⏳ Downloading...';
                
                if (currentMode === 'upload') {
                    await uploadConfigToGitHub(password);
                    statusDiv.style.background = '#d4edda';
                    statusDiv.style.color = '#155724';
                    statusDiv.textContent = '✅ Configuration uploaded successfully! You can now access it from other machines.';
                } else {
                    const token = document.getElementById('sync-github-token').value;
                    const owner = document.getElementById('sync-owner').value;
                    const repo = document.getElementById('sync-repo').value;
                    
                    if (!token || !owner || !repo) {
                        throw new Error('GitHub token, owner, and repo are required');
                    }
                    
                    await downloadConfigFromGitHub(token, owner, repo, password);
                    statusDiv.style.background = '#d4edda';
                    statusDiv.style.color = '#155724';
                    statusDiv.textContent = '✅ Configuration downloaded successfully! All API keys have been loaded. Refresh the page to use them.';
                    
                    setTimeout(() => window.location.reload(), 2000);
                }
            } catch (error) {
                statusDiv.style.background = '#ffe7e7';
                statusDiv.style.color = '#cc0000';
                statusDiv.textContent = `❌ Error: ${error.message}`;
            }
        };
        
        document.getElementById('sync-cancel-btn').onclick = () => {
            document.getElementById('sync-form').style.display = 'none';
            document.getElementById('sync-close-btn').style.display = 'block';
            currentMode = null;
        };
        
        document.getElementById('sync-close-btn').onclick = () => {
            dialog.remove();
        };
    }
    
    // Expose functions globally
    window.configSync = {
        showDialog: showSyncDialog,
        upload: uploadConfigToGitHub,
        download: downloadConfigFromGitHub,
    };
    
})();
