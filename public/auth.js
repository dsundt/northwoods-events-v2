// ============================================================================
// Simple Authentication for GitHub Pages
// ============================================================================
// This provides basic access control for static GitHub Pages sites
// Note: This is CLIENT-SIDE security only - not suitable for highly sensitive data
// For stronger security, use a backend service with proper authentication

(function() {
    'use strict';
    
    // Configuration
    const AUTH_KEY = 'northwoods_auth_token';
    const AUTH_EXPIRY_KEY = 'northwoods_auth_expiry';
    const SESSION_DURATION = 24 * 60 * 60 * 1000; // 24 hours in milliseconds
    
    // Allowed credentials (usernames and SHA-256 hashed passwords)
    // To generate a hash: https://emn178.github.io/online-tools/sha256.html
    // Or in browser console: crypto.subtle.digest('SHA-256', new TextEncoder().encode('yourpassword')).then(h => console.log(Array.from(new Uint8Array(h)).map(b => b.toString(16).padStart(2, '0')).join('')))
    const VALID_USERS = {
        // Example: username: password hash
        // 'admin': 'hash_of_admin_password_here',
        // Default: user1 / northwoods2025
        'dsundt': 'ec2ec78b0b75a5a6c3d2da9f09141adb164361e8f1c15d8a852179efe1e3897d',
        // Add more users as needed
        'asundt': 'ec2ec78b0b75a5a6c3d2da9f09141adb164361e8f1c15d8a852179efe1e3897d',
    };
    
    // Custom password (you can change this)
    // SHA-256 hash of "RCL2025"
    const VALID_PASSWORD_HASH = 'ec2ec78b0b75a5a6c3d2da9f09141adb164361e8f1c15d8a852179efe1e3897d';
    
    /**
     * Hash a password using SHA-256
     */
    async function hashPassword(password) {
        const encoder = new TextEncoder();
        const data = encoder.encode(password);
        const hashBuffer = await crypto.subtle.digest('SHA-256', data);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    }
    
    /**
     * Check if user is authenticated
     */
    function isAuthenticated() {
        const token = localStorage.getItem(AUTH_KEY);
        const expiry = localStorage.getItem(AUTH_EXPIRY_KEY);
        
        if (!token || !expiry) {
            return false;
        }
        
        const expiryTime = parseInt(expiry, 10);
        const now = Date.now();
        
        if (now > expiryTime) {
            // Session expired
            localStorage.removeItem(AUTH_KEY);
            localStorage.removeItem(AUTH_EXPIRY_KEY);
            return false;
        }
        
        return true;
    }
    
    /**
     * Authenticate user with username/password
     */
    async function authenticate(username, password) {
        const passwordHash = await hashPassword(password);
        
        // Check username/password combination
        if (VALID_USERS[username] && VALID_USERS[username] === passwordHash) {
            const expiry = Date.now() + SESSION_DURATION;
            localStorage.setItem(AUTH_KEY, `${username}:${passwordHash}`);
            localStorage.setItem(AUTH_EXPIRY_KEY, expiry.toString());
            return true;
        }
        
        // Also check simple password-only auth
        if (passwordHash === VALID_PASSWORD_HASH) {
            const expiry = Date.now() + SESSION_DURATION;
            localStorage.setItem(AUTH_KEY, passwordHash);
            localStorage.setItem(AUTH_EXPIRY_KEY, expiry.toString());
            return true;
        }
        
        return false;
    }
    
    /**
     * Log out user
     */
    function logout() {
        localStorage.removeItem(AUTH_KEY);
        localStorage.removeItem(AUTH_EXPIRY_KEY);
        window.location.reload();
    }
    
    /**
     * Show login dialog
     */
    function showLoginDialog() {
        const dialog = document.createElement('div');
        dialog.id = 'auth-dialog';
        dialog.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 99999;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
        `;
        
        dialog.innerHTML = `
            <div style="background: white; padding: 3rem; border-radius: 12px; box-shadow: 0 10px 40px rgba(0,0,0,0.3); max-width: 400px; width: 90%;">
                <div style="text-align: center; margin-bottom: 2rem;">
                    <h1 style="margin: 0 0 0.5rem 0; color: #2c3e50; font-size: 1.8rem;">🌲 Northwoods Events</h1>
                    <p style="margin: 0; color: #6c757d; font-size: 0.95rem;">Please sign in to continue</p>
                </div>
                
                <form id="auth-form" style="display: flex; flex-direction: column; gap: 1.25rem;">
                    <div>
                        <label for="auth-username" style="display: block; margin-bottom: 0.5rem; font-weight: 600; color: #2c3e50; font-size: 0.9rem;">Username (optional)</label>
                        <input type="text" id="auth-username" placeholder="Leave blank for password-only" 
                               style="width: 100%; padding: 0.75rem; border: 2px solid #dee2e6; border-radius: 6px; font-size: 1rem; transition: border-color 0.2s;"
                               onfocus="this.style.borderColor='#667eea'" onblur="this.style.borderColor='#dee2e6'">
                    </div>
                    
                    <div>
                        <label for="auth-password" style="display: block; margin-bottom: 0.5rem; font-weight: 600; color: #2c3e50; font-size: 0.9rem;">Password *</label>
                        <input type="password" id="auth-password" placeholder="Enter password" required
                               style="width: 100%; padding: 0.75rem; border: 2px solid #dee2e6; border-radius: 6px; font-size: 1rem; transition: border-color 0.2s;"
                               onfocus="this.style.borderColor='#667eea'" onblur="this.style.borderColor='#dee2e6'">
                    </div>
                    
                    <div id="auth-error" style="display: none; background: #ffe7e7; color: #cc0000; padding: 0.75rem; border-radius: 6px; font-size: 0.9rem; text-align: center;"></div>
                    
                    <button type="submit" id="auth-submit" 
                            style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 0.875rem; border: none; border-radius: 6px; font-size: 1rem; font-weight: 600; cursor: pointer; transition: opacity 0.2s;"
                            onmouseover="this.style.opacity='0.9'" onmouseout="this.style.opacity='1'">
                        🔓 Sign In
                    </button>
                </form>
                
                <div style="margin-top: 1.5rem; padding-top: 1.5rem; border-top: 1px solid #dee2e6; text-align: center;">
                    <p style="margin: 0; font-size: 0.85rem; color: #6c757d;">
                        Session expires after 24 hours
                    </p>
                </div>
            </div>
        `;
        
        document.body.appendChild(dialog);
        
        // Handle form submission
        const form = document.getElementById('auth-form');
        const errorDiv = document.getElementById('auth-error');
        const submitBtn = document.getElementById('auth-submit');
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const username = document.getElementById('auth-username').value.trim();
            const password = document.getElementById('auth-password').value;
            
            if (!password) {
                errorDiv.textContent = 'Please enter a password';
                errorDiv.style.display = 'block';
                return;
            }
            
            // Disable button and show loading
            submitBtn.disabled = true;
            submitBtn.textContent = '⏳ Authenticating...';
            errorDiv.style.display = 'none';
            
            // Authenticate
            const success = await authenticate(username, password);
            
            if (success) {
                // Success! Remove dialog and show content
                dialog.remove();
                document.body.style.overflow = '';
                showSuccessToast();
            } else {
                // Failed
                errorDiv.textContent = '❌ Invalid credentials. Please try again.';
                errorDiv.style.display = 'block';
                submitBtn.disabled = false;
                submitBtn.textContent = '🔓 Sign In';
                document.getElementById('auth-password').value = '';
                document.getElementById('auth-password').focus();
            }
        });
        
        // Focus password input
        setTimeout(() => {
            const usernameInput = document.getElementById('auth-username');
            if (usernameInput) {
                usernameInput.focus();
            }
        }, 100);
        
        // Prevent scrolling on body
        document.body.style.overflow = 'hidden';
    }
    
    /**
     * Show success toast
     */
    function showSuccessToast() {
        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #28a745;
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 6px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            z-index: 100000;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            animation: slideIn 0.3s ease-out;
        `;
        toast.textContent = '✅ Signed in successfully!';
        
        const style = document.createElement('style');
        style.textContent = '@keyframes slideIn { from { transform: translateX(400px); opacity: 0; } to { transform: translateX(0); opacity: 1; } }';
        document.head.appendChild(style);
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.transition = 'opacity 0.3s';
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
    
    /**
     * Add logout button to page
     */
    function addLogoutButton() {
        // Wait for page to load
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', insertLogoutButton);
        } else {
            insertLogoutButton();
        }
    }
    
    function insertLogoutButton() {
        const logoutBtn = document.createElement('button');
        logoutBtn.textContent = '🚪 Sign Out';
        logoutBtn.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: rgba(255, 255, 255, 0.95);
            border: 2px solid #dee2e6;
            color: #2c3e50;
            padding: 0.75rem 1.25rem;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9rem;
            font-weight: 600;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            z-index: 9999;
            transition: all 0.2s;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
        `;
        
        logoutBtn.onmouseover = () => {
            logoutBtn.style.background = '#f8f9fa';
            logoutBtn.style.borderColor = '#adb5bd';
        };
        
        logoutBtn.onmouseout = () => {
            logoutBtn.style.background = 'rgba(255, 255, 255, 0.95)';
            logoutBtn.style.borderColor = '#dee2e6';
        };
        
        logoutBtn.onclick = () => {
            if (confirm('Are you sure you want to sign out?')) {
                logout();
            }
        };
        
        document.body.appendChild(logoutBtn);
    }
    
    // Initialize authentication check
    function init() {
        if (!isAuthenticated()) {
            showLoginDialog();
        } else {
            addLogoutButton();
        }
    }
    
    // Run authentication check when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
    // Expose logout function globally
    window.northwoodsLogout = logout;
    
})();
