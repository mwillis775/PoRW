/**
 * Main JavaScript file for the PoRW Blockchain web interface.
 */

// Wait for the DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Add active class to current nav item
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav-link');
    
    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });

    // Format timestamps
    const timestamps = document.querySelectorAll('.timestamp');
    timestamps.forEach(timestamp => {
        const date = new Date(parseInt(timestamp.dataset.timestamp) * 1000);
        timestamp.textContent = date.toLocaleString();
    });

    // Format addresses
    const addresses = document.querySelectorAll('.address');
    addresses.forEach(address => {
        const fullAddress = address.textContent;
        if (fullAddress.length > 16) {
            address.textContent = `${fullAddress.substring(0, 8)}...${fullAddress.substring(fullAddress.length - 8)}`;
            address.setAttribute('title', fullAddress);
            address.setAttribute('data-bs-toggle', 'tooltip');
            address.setAttribute('data-bs-placement', 'top');
        }
    });

    // Format hashes
    const hashes = document.querySelectorAll('.hash');
    hashes.forEach(hash => {
        const fullHash = hash.textContent;
        if (fullHash.length > 16) {
            hash.textContent = `${fullHash.substring(0, 8)}...${fullHash.substring(fullHash.length - 8)}`;
            hash.setAttribute('title', fullHash);
            hash.setAttribute('data-bs-toggle', 'tooltip');
            hash.setAttribute('data-bs-placement', 'top');
        }
    });

    // Copy to clipboard functionality
    const copyButtons = document.querySelectorAll('.copy-button');
    copyButtons.forEach(button => {
        button.addEventListener('click', function() {
            const textToCopy = this.dataset.copy;
            navigator.clipboard.writeText(textToCopy).then(() => {
                // Show success message
                const originalText = this.innerHTML;
                this.innerHTML = '<i class="fas fa-check"></i> Copied!';
                setTimeout(() => {
                    this.innerHTML = originalText;
                }, 2000);
            });
        });
    });

    // Toggle private key visibility
    const togglePrivateKeyButton = document.getElementById('toggle_private_key');
    if (togglePrivateKeyButton) {
        togglePrivateKeyButton.addEventListener('click', function() {
            const privateKeyInput = document.getElementById('private_key_display');
            const icon = this.querySelector('i');
            
            if (privateKeyInput.type === 'password') {
                privateKeyInput.type = 'text';
                icon.classList.remove('fa-eye');
                icon.classList.add('fa-eye-slash');
            } else {
                privateKeyInput.type = 'password';
                icon.classList.remove('fa-eye-slash');
                icon.classList.add('fa-eye');
            }
        });
    }

    // Refresh status periodically
    function refreshStatus() {
        fetch('/api/status')
            .then(response => response.json())
            .then(data => {
                // Update wallet balance if element exists
                const walletBalance = document.getElementById('wallet-balance');
                if (walletBalance && data.wallet.balance) {
                    walletBalance.textContent = data.wallet.balance;
                }

                // Update blockchain height if element exists
                const blockchainHeight = document.getElementById('blockchain-height');
                if (blockchainHeight && data.blockchain.height) {
                    blockchainHeight.textContent = data.blockchain.height;
                }

                // Update peer count if element exists
                const peerCount = document.getElementById('peer-count');
                if (peerCount && data.node.peers) {
                    peerCount.textContent = data.node.peers;
                }

                // Update mining status if element exists
                const miningStatus = document.getElementById('mining-status');
                if (miningStatus) {
                    if (data.miner.running) {
                        miningStatus.innerHTML = '<span class="badge bg-success">Running</span>';
                    } else {
                        miningStatus.innerHTML = '<span class="badge bg-secondary">Stopped</span>';
                    }
                }

                // Update storage status if element exists
                const storageStatus = document.getElementById('storage-status');
                if (storageStatus) {
                    if (data.storage_node.running) {
                        storageStatus.innerHTML = '<span class="badge bg-success">Running</span>';
                    } else {
                        storageStatus.innerHTML = '<span class="badge bg-secondary">Stopped</span>';
                    }
                }
            })
            .catch(error => {
                console.error('Error fetching status:', error);
            });
    }

    // Refresh status every 30 seconds
    setInterval(refreshStatus, 30000);

    // Initial refresh
    refreshStatus();
});

/**
 * Copy text to clipboard
 * @param {string} elementId - ID of the element containing text to copy
 */
function copyToClipboard(elementId) {
    const element = document.getElementById(elementId);
    const text = element.textContent || element.value;
    
    navigator.clipboard.writeText(text).then(() => {
        // Show a temporary tooltip
        const tooltip = document.createElement('div');
        tooltip.textContent = 'Copied!';
        tooltip.className = 'tooltip';
        
        // Position the tooltip near the element
        const rect = element.getBoundingClientRect();
        tooltip.style.top = `${rect.top - 30}px`;
        tooltip.style.left = `${rect.left + rect.width / 2 - 30}px`;
        
        document.body.appendChild(tooltip);
        
        // Remove the tooltip after 2 seconds
        setTimeout(() => {
            document.body.removeChild(tooltip);
        }, 2000);
    });
}

/**
 * Format a timestamp as a human-readable date
 * @param {number} timestamp - Unix timestamp in seconds
 * @returns {string} Formatted date string
 */
function formatTimestamp(timestamp) {
    const date = new Date(timestamp * 1000);
    return date.toLocaleString();
}

/**
 * Format a file size in bytes to a human-readable format
 * @param {number} bytes - Size in bytes
 * @returns {string} Formatted size string (e.g., "1.5 MB")
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Truncate a string in the middle
 * @param {string} str - String to truncate
 * @param {number} startChars - Number of characters to keep at the start
 * @param {number} endChars - Number of characters to keep at the end
 * @returns {string} Truncated string
 */
function truncateMiddle(str, startChars, endChars) {
    if (str.length <= startChars + endChars) {
        return str;
    }
    
    return `${str.substring(0, startChars)}...${str.substring(str.length - endChars)}`;
}
