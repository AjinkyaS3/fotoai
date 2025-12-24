// API base URL - backend runs on port 8000
const API_URL = 'http://localhost:8000';

// Debug: Log API URL
console.log('Image Import Frontend Loaded');
console.log('API URL:', API_URL);
console.log('Frontend URL:', window.location.origin);

// Start Google Drive import
async function startImport() {
    const urlInput = document.getElementById('drive-url');
    const button = document.getElementById('import-btn');
    const messageDiv = document.getElementById('message');
    
    const folderUrl = urlInput.value.trim();
    
    if (!folderUrl) {
        showMessage('Please enter a Google Drive folder URL', 'error');
        return;
    }
    
    // Disable button and show loading
    button.disabled = true;
    button.textContent = 'Importing...';
    showMessage('Starting import process...');
    
    try {
        console.log('Sending import request for:', folderUrl);
        
        const response = await fetch(`${API_URL}/import/google-drive`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({
                folder_url: folderUrl
            })
        });
        
        console.log('Import response status:', response.status);
        console.log('Import response headers:', [...response.headers.entries()]);
        
        // Handle non-JSON responses
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            const text = await response.text();
            console.error('Non-JSON response:', text);
            throw new Error(`Server returned ${response.status}: ${text.substring(0, 100)}`);
        }
        
        const data = await response.json();
        console.log('Import response data:', data);
        
        if (response.ok) {
            showMessage('✅ Import started successfully! Images will appear soon.');
            // Refresh images after 3 seconds
            setTimeout(loadImages, 3000);
        } else {
            showMessage(`❌ Failed to start import: ${data.detail || 'Unknown error'}`, 'error');
        }
        
    } catch (error) {
        console.error('Import Error:', error);
        showMessage(`❌ Error: ${error.message}`, 'error');
    } finally {
        // Reset button
        button.disabled = false;
        button.textContent = 'Start Import';
    }
}

// Load all imported images
async function loadImages() {
    const container = document.getElementById('images-container');
    console.log('Loading images from:', `${API_URL}/images`);
    
    try {
        const response = await fetch(`${API_URL}/images`, {
            headers: {
                'Accept': 'application/json'
            }
        });
        
        console.log('Images response status:', response.status);
        console.log('Images response headers:', [...response.headers.entries()]);
        
        // Check if response is OK
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        // Handle non-JSON responses
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            const text = await response.text();
            console.error('Non-JSON response:', text);
            throw new Error('Server did not return JSON');
        }
        
        const images = await response.json();
        console.log('Images received:', images);
        
        if (images.length === 0) {
            container.innerHTML = '<p class="no-images">No images imported yet. Start by importing from Google Drive!</p>';
            return;
        }
        
        // Create HTML for images
        container.innerHTML = images.map(image => `
            <div class="image-card">
                <img src="${image.storage_url}" alt="${image.name}" 
                     onerror="this.src='https://via.placeholder.com/300x200?text=Image+Not+Found'">
                <div class="image-info">
                    <h4>${image.name}</h4>
                    <p>Size: ${formatFileSize(image.size)}</p>
                    <p>Source: ${image.source || 'unknown'}</p>
                    <p class="image-id">ID: ${image.id || 'N/A'}</p>
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Error loading images:', error);
        container.innerHTML = `
            <div class="error-message">
                <p>⚠️ Error loading images: ${error.message}</p>
                <p>Please check:</p>
                <ul>
                    <li>Backend is running at ${API_URL}</li>
                    <li>CORS is configured on backend</li>
                    <li>Check browser console for details</li>
                </ul>
                <button onclick="loadImages()" class="retry-btn">Retry</button>
            </div>
        `;
    }
}

// Helper function to format file size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Show message to user
function showMessage(text, type = 'info') {
    const messageDiv = document.getElementById('message');
    messageDiv.textContent = text;
    messageDiv.className = `message ${type}`;
    messageDiv.style.display = 'block';
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        messageDiv.style.display = 'none';
    }, 5000);
}

// Test backend connection
async function testBackendConnection() {
    console.log('Testing backend connection...');
    try {
        const response = await fetch(`${API_URL}/`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json'
            }
        });
        const data = await response.json();
        console.log('Backend test successful:', data);
        return true;
    } catch (error) {
        console.error('Backend test failed:', error);
        return false;
    }
}

// Enhanced page load with connection test
window.onload = async function() {
    console.log('Page loaded, testing backend connection...');
    
    // Test connection first
    const isConnected = await testBackendConnection();
    
    if (isConnected) {
        console.log('Backend connected successfully, loading images...');
        loadImages();
    } else {
        console.error('Cannot connect to backend');
        const container = document.getElementById('images-container');
        container.innerHTML = `
            <div class="error-message">
                <p>🚨 Cannot connect to backend at ${API_URL}</p>
                <p>Make sure:</p>
                <ol>
                    <li>Backend is running: <code>docker-compose up backend</code></li>
                    <li>Backend has CORS enabled for ${window.location.origin}</li>
                    <li>Check Docker logs: <code>docker-compose logs backend</code></li>
                </ol>
                <button onclick="window.location.reload()" class="retry-btn">Refresh Page</button>
            </div>
        `;
    }
    
    // Add click event for import button
    document.getElementById('import-btn').addEventListener('click', startImport);
    
    // Add Enter key support for input
    document.getElementById('drive-url').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            startImport();
        }
    });
};